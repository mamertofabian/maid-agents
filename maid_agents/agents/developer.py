"""Developer Agent - Phase 3: Implements code to pass tests."""

import json
import re
from typing import Dict, Any, List, Optional

from maid_agents.agents.base_agent import BaseAgent
from maid_agents.claude.cli_wrapper import ClaudeWrapper
from maid_agents.config.template_manager import get_template_manager


class Developer(BaseAgent):
    """Agent that implements code to make behavioral tests pass.

    This agent is responsible for Phase 3 of the MAID workflow,
    generating implementation code that satisfies the requirements
    defined in the manifest and makes the behavioral tests pass.
    """

    # Constants for better maintainability
    _CODE_BLOCK_PATTERN = r"```(?:python)?\s*\n(.*?)\n```"
    _DEFAULT_PLACEHOLDER = "(none specified)"
    _MANIFEST_PATH_TEMPLATE = "manifests/{}.manifest.json"
    _MAX_GOAL_LENGTH = 30

    def __init__(self, claude: ClaudeWrapper) -> None:
        """Initialize developer agent.

        Args:
            claude: Claude wrapper instance for AI-powered code generation.
        """
        super().__init__()
        self.claude = claude

    def execute(self) -> dict:
        """Execute implementation.

        Returns:
            Dictionary containing agent status and identification.
        """
        return {"status": "ready", "agent": "Developer"}

    def implement(self, manifest_path: str, test_errors: str = "") -> dict:
        """Implement code to pass behavioral tests based on manifest specifications.

        Args:
            manifest_path: Path to the MAID manifest file containing task specifications.
            test_errors: Optional test error output from previous implementation attempts,
                        used to guide corrective implementation.

        Returns:
            Dictionary containing:
                - success (bool): Whether implementation generation succeeded
                - files_modified (List[str]): List of files that will be modified
                - code (str): Generated implementation code (if successful)
                - error (Optional[str]): Error message (if unsuccessful)
        """
        # Load and validate manifest
        manifest_data = self._load_manifest(manifest_path)
        if manifest_data is None:
            return self._create_error_response(
                f"Failed to load manifest: {manifest_path}"
            )

        # Build implementation prompt
        prompt = self._build_implementation_prompt(manifest_data, test_errors)

        # Generate implementation using Claude
        response = self.claude.generate(prompt)
        if not response.success:
            return self._create_error_response(response.error)

        # Extract and process generated code
        code = self._extract_code_from_response(response.result)
        files_to_modify = self._get_modifiable_files(manifest_data)

        return self._create_success_response(files_to_modify, code)

    def _load_manifest(self, manifest_path: str) -> Optional[Dict[str, Any]]:
        """Load and parse manifest file with error handling.

        Args:
            manifest_path: Path to the manifest JSON file.

        Returns:
            Parsed manifest data or None if loading failed.
        """
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, IOError):
            return None

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response.

        Args:
            error_message: The error message to include.

        Returns:
            Dictionary with error status and empty files list.
        """
        return {
            "success": False,
            "error": error_message,
            "files_modified": [],
        }

    def _create_success_response(
        self, files_modified: List[str], code: str
    ) -> Dict[str, Any]:
        """Create standardized success response.

        Args:
            files_modified: List of files that will be modified.
            code: Generated implementation code.

        Returns:
            Dictionary with success status and implementation details.
        """
        return {
            "success": True,
            "files_modified": files_modified,
            "code": code,
            "error": None,
        }

    def _get_modifiable_files(self, manifest_data: Dict[str, Any]) -> List[str]:
        """Extract list of files that can be modified from manifest.

        Args:
            manifest_data: Parsed manifest dictionary.

        Returns:
            Combined list of creatable and editable files.
        """
        creatable = manifest_data.get("creatableFiles", [])
        editable = manifest_data.get("editableFiles", [])
        return creatable + editable

    def _extract_code_from_response(self, response: str) -> str:
        """Extract code from Claude response, handling markdown code fences.

        Args:
            response: Raw response from Claude containing code.

        Returns:
            Extracted code string, either from code blocks or raw response.
        """
        # Find all code blocks within markdown fences
        matches = re.findall(self._CODE_BLOCK_PATTERN, response, re.DOTALL)

        if matches:
            # Return the largest code block (likely the main implementation)
            return max(matches, key=len).strip()

        # Fallback: return cleaned response if no code fences found
        return response.strip()

    def _build_implementation_prompt(
        self, manifest_data: Dict[str, Any], test_errors: str
    ) -> str:
        """Build prompt for Claude to generate implementation.

        Args:
            manifest_data: Parsed manifest data containing goal and artifacts.
            test_errors: Test error output from previous attempts, if any.

        Returns:
            Formatted prompt string ready for Claude generation.
        """
        # Extract manifest components
        goal = self._get_manifest_goal(manifest_data)
        artifacts_summary = self._build_artifacts_summary(
            manifest_data.get("expectedArtifacts", {})
        )
        files_to_modify_str = self._format_modifiable_files(manifest_data)
        test_output = self._format_test_output(test_errors)
        manifest_filename = self._generate_manifest_filename(goal)

        # Render prompt using template
        template_manager = get_template_manager()
        return template_manager.render(
            "implementation",
            manifest_path=manifest_filename,
            goal=goal,
            test_output=test_output,
            artifacts_summary=artifacts_summary,
            files_to_modify=files_to_modify_str,
        )

    def _get_manifest_goal(self, manifest_data: Dict[str, Any]) -> str:
        """Extract goal from manifest with fallback.

        Args:
            manifest_data: Parsed manifest dictionary.

        Returns:
            Goal string or empty string if not found.
        """
        return manifest_data.get("goal", "")

    def _format_test_output(self, test_errors: str) -> str:
        """Format test output for prompt inclusion.

        Args:
            test_errors: Raw test error output.

        Returns:
            Formatted test output or default message.
        """
        if test_errors:
            return test_errors
        return "No test failures yet (first iteration)"

    def _generate_manifest_filename(self, goal: str) -> str:
        """Generate manifest filename from goal.

        Args:
            goal: The task goal string.

        Returns:
            Formatted manifest path.
        """
        truncated_goal = goal[: self._MAX_GOAL_LENGTH] if goal else "unknown"
        return self._MANIFEST_PATH_TEMPLATE.format(truncated_goal)

    def _format_modifiable_files(self, manifest_data: Dict[str, Any]) -> str:
        """Format list of modifiable files for display.

        Args:
            manifest_data: Parsed manifest dictionary.

        Returns:
            Formatted string listing files to modify.
        """
        files = self._get_modifiable_files(manifest_data)

        if not files:
            return f"  {self._DEFAULT_PLACEHOLDER}"

        return "\n".join(f"  - {file}" for file in files)

    def _build_artifacts_summary(self, artifacts: Dict[str, Any]) -> str:
        """Build human-readable summary of expected artifacts.

        Args:
            artifacts: expectedArtifacts dictionary from manifest containing
                      artifact definitions.

        Returns:
            Formatted multi-line string describing all artifacts,
            or placeholder if none specified.
        """
        artifact_list = []

        for artifact in artifacts.get("contains", []):
            formatted_artifact = self._format_single_artifact(artifact)
            if formatted_artifact:
                artifact_list.append(formatted_artifact)

        if not artifact_list:
            return f"  {self._DEFAULT_PLACEHOLDER}"

        return "\n".join(artifact_list)

    def _format_single_artifact(self, artifact: Dict[str, Any]) -> Optional[str]:
        """Format a single artifact definition.

        Args:
            artifact: Single artifact definition from manifest.

        Returns:
            Formatted artifact string or None if type unknown.
        """
        artifact_type = artifact.get("type")

        if artifact_type == "function":
            return self._format_function_artifact(artifact)
        elif artifact_type == "class":
            return self._format_class_artifact(artifact)
        elif artifact_type == "attribute":
            return self._format_attribute_artifact(artifact)

        return None

    def _format_function_artifact(self, artifact: Dict[str, Any]) -> str:
        """Format function or method artifact.

        Args:
            artifact: Function artifact definition.

        Returns:
            Formatted function/method string.
        """
        name = artifact.get("name", "unknown")
        args_str = self._format_function_args(artifact.get("args", []))
        returns = artifact.get("returns", "None")

        if "class" in artifact:
            class_name = artifact["class"]
            return f"  - Method: {class_name}.{name}({args_str}) -> {returns}"

        return f"  - Function: {name}({args_str}) -> {returns}"

    def _format_function_args(self, args: List[Dict[str, str]]) -> str:
        """Format function arguments list.

        Args:
            args: List of argument definitions.

        Returns:
            Comma-separated argument string.
        """
        return ", ".join(
            f"{arg.get('name', 'arg')}: {arg.get('type', 'Any')}" for arg in args
        )

    def _format_class_artifact(self, artifact: Dict[str, Any]) -> str:
        """Format class artifact.

        Args:
            artifact: Class artifact definition.

        Returns:
            Formatted class string.
        """
        name = artifact.get("name", "unknown")
        bases = artifact.get("bases", [])

        if bases:
            bases_str = f"({', '.join(bases)})"
        else:
            bases_str = ""

        return f"  - Class: {name}{bases_str}"

    def _format_attribute_artifact(self, artifact: Dict[str, Any]) -> str:
        """Format attribute artifact.

        Args:
            artifact: Attribute artifact definition.

        Returns:
            Formatted attribute string.
        """
        name = artifact.get("name", "unknown")

        if "class" in artifact:
            class_name = artifact["class"]
            return f"  - Attribute: {class_name}.{name}"

        return f"  - Attribute: {name}"
