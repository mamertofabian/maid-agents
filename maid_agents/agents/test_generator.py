"""Test Generator - Creates or enhances tests from existing implementation."""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from maid_agents.claude.cli_wrapper import ClaudeWrapper
from maid_agents.config.template_manager import get_template_manager


class TestGenerator:
    """Generates or enhances behavioral tests from existing implementation files."""

    def __init__(self, claude: ClaudeWrapper) -> None:
        """Initialize test generator.

        Args:
            claude: Claude wrapper for AI generation
        """
        self.claude = claude

    def generate_test_from_implementation(
        self, manifest_path: str, implementation_path: str
    ) -> dict:
        """Generate or enhance tests from existing implementation.

        This method supports the workflow where `maid snapshot` creates a manifest
        (and optionally a test stub), and we need to generate behavioral tests
        that validate the existing implementation.

        Args:
            manifest_path: Path to manifest file
            implementation_path: Path to existing implementation file

        Returns:
            Dict with test generation results:
                - success: Boolean indicating if generation succeeded
                - test_path: Path to generated/enhanced test file
                - test_code: Generated test code string or None
                - mode: 'created', 'enhanced', or 'error'
                - error: Error message if failed, None otherwise
        """
        # Load manifest
        load_result = self._load_manifest(manifest_path)
        if not load_result["success"]:
            return self._create_error_result(load_result["error"])

        manifest_data = load_result["data"]

        # Load implementation file
        impl_result = self._load_implementation(implementation_path)
        if not impl_result["success"]:
            return self._create_error_result(impl_result["error"])

        implementation_code = impl_result["code"]

        # Detect if there's an existing test file
        existing_test_path = self._detect_existing_test_file(manifest_data)

        # Analyze existing test if present
        existing_test_code = None
        test_analysis = None
        if existing_test_path:
            test_analysis = self._analyze_test_stub(existing_test_path)
            if test_analysis.get("exists"):
                existing_test_code = test_analysis.get("code")

        # Generate/enhance tests with split prompts
        response = self._generate_tests_with_claude(
            manifest_data=manifest_data,
            manifest_path=manifest_path,
            implementation_code=implementation_code,
            implementation_path=implementation_path,
            existing_test_code=existing_test_code,
            existing_test_path=existing_test_path,
            test_analysis=test_analysis,
        )
        if not response.success:
            return self._create_error_result(response.error)

        # Determine test file path
        if existing_test_path:
            test_path = existing_test_path
            mode = "enhanced"
        else:
            # Extract from manifest or use convention
            test_path = self._determine_test_path(manifest_data)
            mode = "created"

        # Read the generated test file
        try:
            with open(test_path, "r") as f:
                test_code = f.read()
        except FileNotFoundError:
            return self._create_error_result(
                f"Test file {test_path} was not created by Claude Code"
            )
        except Exception as e:
            return self._create_error_result(f"Failed to read test file: {e}")

        return {
            "success": True,
            "test_path": test_path,
            "test_code": test_code,
            "mode": mode,
            "error": None,
        }

    def _detect_existing_test_file(self, manifest_data: dict) -> Optional[str]:
        """Detect if there's an existing test file in manifest.

        Args:
            manifest_data: Parsed manifest data

        Returns:
            Path to existing test file or None
        """
        readonly_files = manifest_data.get("readonlyFiles", [])

        # Look for test files in readonlyFiles
        for file_path in readonly_files:
            if "test_" in file_path or "_test.py" in file_path:
                # Check if file actually exists
                if Path(file_path).exists():
                    return file_path

        return None

    def _analyze_test_stub(self, test_file_path: str) -> dict:
        """Analyze a test file to determine if it's a stub or has real tests.

        Args:
            test_file_path: Path to test file

        Returns:
            Dict with analysis:
                - exists: Boolean
                - is_stub: Boolean (True if mostly placeholder/pass statements)
                - test_count: Number of test functions found
                - code: Test file contents
        """
        try:
            with open(test_file_path, "r") as f:
                code = f.read()
        except FileNotFoundError:
            return {
                "exists": False,
                "is_stub": False,
                "test_count": 0,
                "code": None,
            }
        except Exception:
            return {
                "exists": False,
                "is_stub": False,
                "test_count": 0,
                "code": None,
            }

        # Count test functions
        test_count = code.count("def test_")

        # Heuristic: check if it's mostly stubs
        # A stub typically has lots of 'pass' or 'assert True' or '...'
        stub_indicators = (
            code.count("pass") + code.count("assert True") + code.count("...")
        )

        # If more than half the test functions are stubs, consider it a stub file
        is_stub = test_count > 0 and stub_indicators >= test_count / 2

        return {
            "exists": True,
            "is_stub": is_stub,
            "test_count": test_count,
            "code": code,
        }

    def _load_manifest(self, manifest_path: str) -> Dict[str, Any]:
        """Load and parse manifest file.

        Args:
            manifest_path: Path to manifest file

        Returns:
            Dict with success status and data or error
        """
        try:
            with open(manifest_path) as f:
                data = json.load(f)
            return {"success": True, "data": data}
        except FileNotFoundError:
            return {"success": False, "error": f"Manifest not found: {manifest_path}"}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid manifest JSON: {e}"}

    def _load_implementation(self, implementation_path: str) -> Dict[str, Any]:
        """Load implementation file code.

        Args:
            implementation_path: Path to implementation file

        Returns:
            Dict with success status and code or error
        """
        try:
            with open(implementation_path, "r") as f:
                code = f.read()
            return {"success": True, "code": code}
        except FileNotFoundError:
            return {
                "success": False,
                "error": f"Implementation file not found: {implementation_path}",
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to read implementation: {e}"}

    def _determine_test_path(self, manifest_data: Dict[str, Any]) -> str:
        """Determine test file path from manifest or convention.

        Args:
            manifest_data: Parsed manifest data

        Returns:
            Path where test file should be created
        """
        # Try to extract from validationCommand
        validation_cmd = manifest_data.get("validationCommand", [])
        for part in validation_cmd:
            if "test_" in part and ".py" in part:
                return part

        # Fall back to convention: tests/test_<goal_slug>.py
        goal = manifest_data.get("goal", "unknown")
        slug = goal.lower().replace(" ", "_")[:50]
        return f"tests/test_{slug}.py"

    def _generate_tests_with_claude(
        self,
        manifest_data: Dict[str, Any],
        manifest_path: str,
        implementation_code: str,
        implementation_path: str,
        existing_test_code: Optional[str],
        existing_test_path: Optional[str],
        test_analysis: Optional[Dict[str, Any]],
    ):
        """Generate tests using Claude API with split prompts.

        Args:
            manifest_data: Parsed manifest data
            manifest_path: Path to manifest
            implementation_code: Existing implementation code
            implementation_path: Path to implementation
            existing_test_code: Existing test code if any
            existing_test_path: Path to existing test
            test_analysis: Analysis of existing test

        Returns:
            ClaudeResponse object with generation result
        """
        artifacts = manifest_data.get("expectedArtifacts", {})

        # Determine mode
        if existing_test_code:
            if test_analysis and test_analysis.get("is_stub"):
                mode = "enhance stub"
            else:
                mode = "improve existing"
        else:
            mode = "create new"

        # Build mode-specific task instructions
        if mode == "create new":
            mode_specific_task = """
1. Create comprehensive behavioral tests that validate the existing implementation
2. Test all artifacts declared in the manifest's expectedArtifacts
3. Use the actual implementation code as reference for expected behavior
4. Follow pytest conventions and MAID behavioral test patterns
"""
            test_path = self._determine_test_path(manifest_data)
        elif mode == "enhance stub":
            mode_specific_task = """
1. Fill in the stub/placeholder tests with real behavioral assertions
2. Use the existing implementation to understand expected behavior
3. Preserve the existing test structure but replace placeholders with real tests
4. Ensure all artifacts from manifest are tested
"""
            test_path = existing_test_path
        else:  # improve existing
            mode_specific_task = """
1. Review and improve the existing tests
2. Add missing test cases for any untested artifacts from manifest
3. Enhance assertions to be more comprehensive
4. Fix any broken tests based on the actual implementation
"""
            test_path = existing_test_path

        # Get split prompts (system + user)
        template_manager = get_template_manager()
        prompts = template_manager.render_for_agent(
            "test_generation_from_implementation",
            manifest_path=manifest_path,
            implementation_file=implementation_path,
            test_file_path=test_path,
            test_mode=mode,
            test_mode_instructions=mode_specific_task,
            artifacts_summary=self._format_artifacts(artifacts),
        )

        # Add file path instruction to user message
        user_message = (
            prompts["user_message"]
            + f"""

CRITICAL: Use your file editing tools to directly create/update this test file:
- {test_path}

- Write the complete Python test code to the file listed above
- Make all changes directly using your file editing capabilities
- Do not just show the code - actually write the file
- Ensure tests are behavioral (call methods, verify behavior)
"""
        )

        # Create ClaudeWrapper with system prompt
        claude_with_system = ClaudeWrapper(
            mock_mode=self.claude.mock_mode,
            model=self.claude.model,
            timeout=self.claude.timeout,
            temperature=self.claude.temperature,
            system_prompt=prompts["system_prompt"],
        )

        return claude_with_system.generate(user_message)

    def _build_test_enhancement_prompt(
        self,
        manifest_data: Dict[str, Any],
        manifest_path: str,
        implementation_code: str,
        implementation_path: str,
        existing_test_code: Optional[str],
        existing_test_path: Optional[str],
        test_analysis: Optional[Dict[str, Any]],
    ) -> str:
        """Build prompt for test generation/enhancement using template.

        Args:
            manifest_data: Parsed manifest data
            manifest_path: Path to manifest
            implementation_code: Existing implementation code
            implementation_path: Path to implementation
            existing_test_code: Existing test code if any
            existing_test_path: Path to existing test
            test_analysis: Analysis of existing test

        Returns:
            Formatted prompt for Claude Code
        """
        artifacts = manifest_data.get("expectedArtifacts", {})

        # Determine mode
        if existing_test_code:
            if test_analysis and test_analysis.get("is_stub"):
                mode = "enhance stub"
            else:
                mode = "improve existing"
        else:
            mode = "create new"

        # Build mode-specific task instructions
        if mode == "create new":
            mode_specific_task = """
1. Create comprehensive behavioral tests that validate the existing implementation
2. Test all artifacts declared in the manifest's expectedArtifacts
3. Use the actual implementation code as reference for expected behavior
4. Follow pytest conventions and MAID behavioral test patterns
"""
            test_path = self._determine_test_path(manifest_data)
        elif mode == "enhance stub":
            mode_specific_task = """
1. Fill in the stub/placeholder tests with real behavioral assertions
2. Use the existing implementation to understand expected behavior
3. Preserve the existing test structure but replace placeholders with real tests
4. Ensure all artifacts from manifest are tested
"""
            test_path = existing_test_path
        else:  # improve existing
            mode_specific_task = """
1. Review and improve the existing tests
2. Add missing test cases for any untested artifacts from manifest
3. Enhance assertions to be more comprehensive
4. Fix any broken tests based on the actual implementation
"""
            test_path = existing_test_path

        # Use template manager to render prompt
        template_manager = get_template_manager()
        prompt = template_manager.render(
            "test_generation_from_implementation",
            manifest_path=manifest_path,
            implementation_file=implementation_path,
            test_file_path=test_path,
            test_mode=mode,
            test_mode_instructions=mode_specific_task,
            artifacts_summary=self._format_artifacts(artifacts),
        )

        return prompt

    def _format_artifacts(self, artifacts: Dict[str, Any]) -> str:
        """Format artifacts for prompt.

        Args:
            artifacts: expectedArtifacts from manifest

        Returns:
            Formatted string
        """
        if not artifacts:
            return "No artifacts specified"

        file_path = artifacts.get("file", "unknown")
        contains = artifacts.get("contains", [])

        lines = [f"File: {file_path}"]
        for artifact in contains:
            artifact_type = artifact.get("type", "unknown")
            name = artifact.get("name", "unnamed")

            if artifact_type == "class":
                lines.append(f"  - Class: {name}")
            elif artifact_type == "function":
                class_name = artifact.get("class")
                args = artifact.get("args", [])
                returns = artifact.get("returns", "None")
                args_str = ", ".join([f"{a['name']}: {a['type']}" for a in args])

                if class_name:
                    lines.append(
                        f"  - Method: {class_name}.{name}({args_str}) -> {returns}"
                    )
                else:
                    lines.append(f"  - Function: {name}({args_str}) -> {returns}")
            else:
                lines.append(f"  - {artifact_type}: {name}")

        return "\n".join(lines)

    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create error result dictionary.

        Args:
            error_message: Error message

        Returns:
            Error result dict
        """
        return {
            "success": False,
            "test_path": None,
            "test_code": None,
            "mode": "error",
            "error": error_message,
        }
