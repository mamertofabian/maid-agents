"""Test Generator - Creates or enhances tests from existing implementation."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from maid_agents.claude.cli_wrapper import ClaudeWrapper
from maid_agents.config.template_manager import get_template_manager
from maid_agents.core.validation_runner import ValidationRunner

logger = logging.getLogger(__name__)


class TestGenerator:
    """Generates or enhances behavioral tests from existing implementation files."""

    def __init__(self, claude: ClaudeWrapper) -> None:
        """Initialize test generator.

        Args:
            claude: Claude wrapper for AI generation
        """
        self.claude = claude
        self.validation_runner = ValidationRunner()

    def generate_test_from_implementation(
        self, manifest_path: str, implementation_path: str, max_iterations: int = 5
    ) -> dict:
        """Generate or enhance tests from existing implementation.

        This method supports the workflow where `maid snapshot` creates a manifest
        (and optionally a test stub), and we need to generate behavioral tests
        that validate the existing implementation.

        The method now includes a validation loop that ensures the generated tests
        actually pass against the implementation before returning success.

        Args:
            manifest_path: Path to manifest file
            implementation_path: Path to existing implementation file
            max_iterations: Maximum iterations for fixing failing tests (default: 5)

        Returns:
            Dict with test generation results:
                - success: Boolean indicating if generation succeeded AND tests pass
                - test_path: Path to generated/enhanced test file
                - test_code: Generated test code string or None
                - mode: 'created', 'enhanced', or 'error'
                - iterations: Number of iterations used to get passing tests
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

        # Run validation loop to ensure tests pass
        logger.info(
            f"Running validation loop to ensure tests pass (max {max_iterations} iterations)"
        )
        validation_result = self._run_test_validation_loop(
            manifest_path=manifest_path,
            test_path=test_path,
            implementation_path=implementation_path,
            manifest_data=manifest_data,
            max_iterations=max_iterations,
        )

        return {
            "success": validation_result["success"],
            "test_path": test_path,
            "test_code": test_code,
            "mode": mode,
            "iterations": validation_result["iterations"],
            "error": validation_result.get("error"),
        }

    def _run_test_validation_loop(
        self,
        manifest_path: str,
        test_path: str,
        implementation_path: str,
        manifest_data: Dict[str, Any],
        max_iterations: int,
    ) -> Dict[str, Any]:
        """Run validation loop to ensure generated tests pass.

        This method runs the tests and iteratively fixes them until they pass
        or max iterations is reached.

        Args:
            manifest_path: Path to manifest file
            test_path: Path to test file
            implementation_path: Path to implementation file
            manifest_data: Parsed manifest data
            max_iterations: Maximum iterations for fixing tests

        Returns:
            Dict with:
                - success: Boolean indicating if tests pass
                - iterations: Number of iterations used
                - error: Error message if failed
        """
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Test validation iteration {iteration}/{max_iterations}")

            # Run the tests
            test_result = self.validation_runner.run_behavioral_tests(manifest_path)

            if test_result.success:
                logger.info(f"Tests passed on iteration {iteration}!")
                return {
                    "success": True,
                    "iterations": iteration,
                    "error": None,
                }

            # Tests failed - collect error messages
            test_errors = f"{test_result.stdout}\n{test_result.stderr}"
            logger.warning(
                f"Tests failed on iteration {iteration}: {len(test_errors)} chars of errors"
            )

            # Try to fix the tests
            fix_result = self._fix_failing_tests_with_claude(
                test_path=test_path,
                test_errors=test_errors,
                manifest_data=manifest_data,
                implementation_path=implementation_path,
            )

            if not fix_result["success"]:
                logger.error(f"Failed to fix tests: {fix_result['error']}")
                return {
                    "success": False,
                    "iterations": iteration,
                    "error": f"Failed to fix tests on iteration {iteration}: {fix_result['error']}",
                }

        # Max iterations reached without passing tests
        logger.error(f"Tests did not pass after {max_iterations} iterations")
        return {
            "success": False,
            "iterations": max_iterations,
            "error": f"Tests did not pass after {max_iterations} iterations",
        }

    def _fix_failing_tests_with_claude(
        self,
        test_path: str,
        test_errors: str,
        manifest_data: Dict[str, Any],
        implementation_path: str,
    ) -> Dict[str, Any]:
        """Fix failing tests by calling Claude with error messages.

        Args:
            test_path: Path to test file that needs fixing
            test_errors: Error messages from test run
            manifest_data: Parsed manifest data
            implementation_path: Path to implementation file

        Returns:
            Dict with:
                - success: Boolean indicating if fix succeeded
                - error: Error message if failed
        """
        # Read current test file
        try:
            with open(test_path, "r") as f:
                current_test_code = f.read()
        except Exception as e:
            return {"success": False, "error": f"Failed to read test file: {e}"}

        # Build prompt for fixing tests
        artifacts = manifest_data.get("expectedArtifacts", {})

        # Create a prompt for fixing the failing tests
        user_message = f"""The behavioral tests for this implementation are failing. Your task is to fix the tests so they pass.

**Implementation File:** {implementation_path}

**Test File:** {test_path}

**Test Errors:**
```
{test_errors}
```

**Expected Artifacts from Manifest:**
{self._format_artifacts(artifacts)}

**Instructions:**
1. Analyze the test errors to understand what's failing
2. Review the implementation to understand the actual behavior
3. Fix the test file to correctly test the implementation's actual behavior
4. Ensure all tests follow behavioral testing patterns (call methods, verify behavior)
5. DO NOT change the implementation - only fix the tests
6. Use your file editing tools to directly update the test file: {test_path}

CRITICAL: Use your file editing tools to update the test file at: {test_path}
"""

        # Create ClaudeWrapper with appropriate system prompt
        system_prompt = """You are a test engineer specializing in behavioral testing. Your task is to fix failing tests by analyzing error messages and understanding the actual implementation behavior.

Key principles:
- Tests should validate behavior, not implementation details
- Fix tests to match actual implementation behavior
- Never change the implementation - only fix tests
- Ensure tests follow pytest conventions
- Use clear, descriptive test names and assertions"""

        claude_with_system = ClaudeWrapper(
            mock_mode=self.claude.mock_mode,
            model=self.claude.model,
            timeout=self.claude.timeout,
            temperature=self.claude.temperature,
            system_prompt=system_prompt,
        )

        logger.debug("Calling Claude to fix failing tests...")
        response = claude_with_system.generate(user_message)

        if not response.success:
            return {"success": False, "error": response.error}

        # Verify the test file was updated
        try:
            with open(test_path, "r") as f:
                updated_test_code = f.read()

            if updated_test_code == current_test_code:
                return {
                    "success": False,
                    "error": "Test file was not updated by Claude Code",
                }

            logger.info(f"Test file {test_path} updated successfully")
            return {"success": True, "error": None}

        except Exception as e:
            return {"success": False, "error": f"Failed to verify test update: {e}"}

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
                args_str = ", ".join(
                    [
                        f"{a['name']}: {a['type']}" if "type" in a else a["name"]
                        for a in args
                    ]
                )

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
            "iterations": 0,
            "error": error_message,
        }
