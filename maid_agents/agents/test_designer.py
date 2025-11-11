"""Test Designer Agent - Phase 2: Creates behavioral tests from manifests."""

import json
import re
from typing import Dict, Any, List, Optional

from maid_agents.agents.base_agent import BaseAgent
from maid_agents.claude.cli_wrapper import ClaudeWrapper
from maid_agents.config.template_manager import get_template_manager


class TestDesigner(BaseAgent):
    """Agent that creates behavioral tests from manifests."""

    def __init__(self, claude: ClaudeWrapper):
        """Initialize test designer.

        Args:
            claude: Claude wrapper for AI generation
        """
        super().__init__()
        self.claude = claude

    def execute(self) -> dict:
        """Execute test generation.

        Returns:
            Dict with test generation results
        """
        return {"status": "ready", "agent": "TestDesigner"}

    def create_tests(self, manifest_path: str) -> dict:
        """Create behavioral tests from manifest.

        Args:
            manifest_path: Path to manifest file

        Returns:
            Dict with test file paths and success status containing:
                - success: Boolean indicating if test generation succeeded
                - test_paths: List of test file paths
                - test_code: Generated test code string or None
                - error: Error message if failed, None otherwise
        """
        # Load and validate manifest
        load_result = self._load_manifest(manifest_path)
        if not load_result["success"]:
            return load_result

        manifest_data = load_result["data"]

        # Build prompt for Claude
        prompt = self._build_test_prompt(manifest_data, manifest_path)

        # Generate tests using Claude
        response = self.claude.generate(prompt)
        if not response.success:
            return self._create_error_result(response.error)

        # Extract and process generated code
        return self._process_generated_code(response.result, manifest_data)

    def _load_manifest(self, manifest_path: str) -> Dict[str, Any]:
        """Load and parse manifest file with error handling.

        Args:
            manifest_path: Path to manifest file

        Returns:
            Dict with success status and either data or error result
        """
        try:
            with open(manifest_path) as manifest_file:
                manifest_data = json.load(manifest_file)
            return {"success": True, "data": manifest_data}
        except FileNotFoundError:
            return self._create_error_result(f"Manifest not found: {manifest_path}")
        except json.JSONDecodeError as error:
            return self._create_error_result(f"Invalid manifest JSON: {error}")

    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create a standardized error result dictionary.

        Args:
            error_message: The error message to include

        Returns:
            Dict with error result structure
        """
        return {
            "success": False,
            "error": error_message,
            "test_paths": [],
            "test_code": None,
        }

    def _process_generated_code(
        self, response_text: str, manifest_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process generated code from Claude response.

        Args:
            response_text: Raw response from Claude
            manifest_data: Parsed manifest data

        Returns:
            Dict with processed test code and paths
        """
        try:
            test_code = self._extract_code_from_response(response_text)
            test_paths = self._extract_test_paths(manifest_data)

            return {
                "success": True,
                "test_paths": test_paths,
                "test_code": test_code,
                "error": None,
            }
        except Exception as error:
            error_preview = response_text[:200] if response_text else "Empty response"
            return self._create_error_result(
                f"Failed to extract test code: {error}. Response preview: {error_preview}"
            )

    def _extract_test_paths(self, manifest_data: Dict[str, Any]) -> List[str]:
        """Extract test file paths from manifest data.

        Args:
            manifest_data: Parsed manifest data

        Returns:
            List of test file paths
        """
        readonly_files = manifest_data.get("readonlyFiles", [])
        return [file_path for file_path in readonly_files if "test_" in file_path]

    def _extract_code_from_response(self, response: str) -> str:
        """Extract Python code from Claude response, handling markdown code fences.

        Args:
            response: Raw response from Claude

        Returns:
            Extracted Python code string

        Raises:
            ValueError: If no valid Python code could be extracted
        """
        # Check for markdown code blocks first
        code = self._extract_markdown_code_block(response)
        if code:
            return code

        # Check if response contains Python syntax indicators
        if self._contains_python_syntax(response):
            return response.strip()

        # Return stripped response as fallback
        return response.strip()

    def _extract_markdown_code_block(self, response: str) -> Optional[str]:
        """Extract code from markdown code fence blocks.

        Args:
            response: Text that may contain markdown code blocks

        Returns:
            Extracted code or None if no code blocks found
        """
        # Pattern matches ```python ... ``` or ``` ... ```
        python_block_pattern = r"```(?:python)?\s*\n(.*?)\n```"
        matches = re.findall(python_block_pattern, response, re.DOTALL)

        if matches:
            return matches[0].strip()
        return None

    def _contains_python_syntax(self, text: str) -> bool:
        """Check if text contains Python syntax indicators.

        Args:
            text: Text to check for Python syntax

        Returns:
            True if text appears to contain Python code
        """
        python_indicators = ["import ", "def ", "class ", "@"]
        return any(indicator in text for indicator in python_indicators)

    def _build_test_prompt(
        self, manifest_data: Dict[str, Any], manifest_path: str
    ) -> str:
        """Build prompt for Claude to generate tests.

        Args:
            manifest_data: Parsed manifest data
            manifest_path: Path to manifest file

        Returns:
            Formatted prompt string for test generation
        """
        goal = manifest_data.get("goal", "")
        artifacts_summary = self._summarize_artifacts(
            manifest_data.get("expectedArtifacts", {})
        )

        template_manager = get_template_manager()
        return template_manager.render(
            "test_generation",
            manifest_path=manifest_path,
            goal=goal,
            artifacts_summary=artifacts_summary,
        )

    def _summarize_artifacts(self, artifacts: Dict[str, Any]) -> str:
        """Summarize artifacts for prompt with detailed signatures.

        Args:
            artifacts: expectedArtifacts from manifest

        Returns:
            Human-readable summary with full signatures
        """
        if not artifacts:
            return "No artifacts specified"

        file_path = artifacts.get("file", "unknown")
        contains = artifacts.get("contains", [])

        summary_lines = [f"File: {file_path}", ""]

        for artifact in contains:
            artifact_line = self._format_artifact(artifact)
            summary_lines.append(artifact_line)

        return "\n".join(summary_lines)

    def _format_artifact(self, artifact: Dict[str, Any]) -> str:
        """Format a single artifact for display.

        Args:
            artifact: Single artifact dictionary from manifest

        Returns:
            Formatted string representation of the artifact
        """
        artifact_type = artifact.get("type", "unknown")
        name = artifact.get("name", "unnamed")

        if artifact_type == "function":
            return self._format_function_artifact(artifact, name)
        elif artifact_type == "class":
            return self._format_class_artifact(artifact, name)
        elif artifact_type == "attribute":
            return self._format_attribute_artifact(artifact, name)
        else:
            return f"  - {artifact_type}: {name}"

    def _format_function_artifact(self, artifact: Dict[str, Any], name: str) -> str:
        """Format a function artifact with signature.

        Args:
            artifact: Function artifact data
            name: Function name

        Returns:
            Formatted function signature string
        """
        args = artifact.get("args", [])
        returns = artifact.get("returns", "None")
        class_name = artifact.get("class")

        args_str = self._format_function_arguments(args)

        if class_name:
            return f"  - Method: {class_name}.{name}({args_str}) -> {returns}"
        return f"  - Function: {name}({args_str}) -> {returns}"

    def _format_function_arguments(self, args: List[Dict[str, Any]]) -> str:
        """Format function arguments list.

        Args:
            args: List of argument dictionaries

        Returns:
            Formatted arguments string
        """
        formatted_args = []
        for arg in args:
            arg_name = arg.get("name", "unknown")
            arg_type = arg.get("type", "Any")
            formatted_args.append(f"{arg_name}: {arg_type}")
        return ", ".join(formatted_args)

    def _format_class_artifact(self, artifact: Dict[str, Any], name: str) -> str:
        """Format a class artifact with bases.

        Args:
            artifact: Class artifact data
            name: Class name

        Returns:
            Formatted class declaration string
        """
        bases = artifact.get("bases", [])
        bases_str = f"({', '.join(bases)})" if bases else ""
        return f"  - Class: {name}{bases_str}"

    def _format_attribute_artifact(self, artifact: Dict[str, Any], name: str) -> str:
        """Format an attribute artifact with type.

        Args:
            artifact: Attribute artifact data
            name: Attribute name

        Returns:
            Formatted attribute declaration string
        """
        attr_type = artifact.get("attributeType", "Any")
        class_name = artifact.get("class")

        if class_name:
            return f"  - Attribute: {class_name}.{name}: {attr_type}"
        return f"  - Attribute: {name}: {attr_type}"
