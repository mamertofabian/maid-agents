"""Refactorer Agent - Phase 3.5: Improves code quality while maintaining compliance."""

import json
from typing import Dict, Any, List, Optional

from maid_agents.agents.base_agent import BaseAgent
from maid_agents.claude.cli_wrapper import ClaudeWrapper
from maid_agents.config.template_manager import get_template_manager


class Refactorer(BaseAgent):
    """Agent that refactors code while maintaining manifest compliance.

    The Refactorer agent performs Phase 3.5 of the MAID workflow,
    improving code quality while ensuring all manifest requirements
    and tests continue to pass.
    """

    DUPLICATE_PREFIX = "maid-agents/maid_agents/"
    NORMALIZED_PREFIX = "maid_agents/"
    FILE_NOT_FOUND_PREFIX = "# File not found: "
    DEFAULT_IMPROVEMENT_MESSAGE = "Code quality improvements applied"

    def __init__(self, claude: ClaudeWrapper, dry_run: bool = False) -> None:
        """Initialize refactorer agent.

        Args:
            claude: Claude wrapper for AI generation
            dry_run: If True, skip expensive operations like subprocess calls
        """
        super().__init__(dry_run=dry_run)
        self.claude = claude

    def execute(self) -> dict:
        """Execute refactoring.

        Returns:
            Dict with refactoring results
        """
        return {"status": "ready", "agent": "Refactorer"}

    def refactor(
        self, manifest_path: str, validation_feedback: str = "", instructions: str = ""
    ) -> dict:
        """Refactor code while maintaining tests and manifest compliance.

        Args:
            manifest_path: Path to manifest file
            validation_feedback: Optional error messages from previous validation/test failures
            instructions: Optional additional instructions or context

        Returns:
            Dict with refactoring status, improvements list, and refactored code
        """
        # Load and validate manifest
        manifest_result = self._load_and_validate_manifest(manifest_path)
        if not manifest_result["success"]:
            return manifest_result

        manifest_data = manifest_result["data"]
        files_to_refactor = manifest_result["files"]

        # Load current code from target files
        file_contents = self._load_file_contents(files_to_refactor)

        # Generate refactoring via Claude Code
        refactoring_result = self._generate_refactoring(
            manifest_data,
            file_contents,
            validation_feedback,
            manifest_path,
            instructions,
        )
        if not refactoring_result["success"]:
            return refactoring_result

        # Read refactored files from disk (Claude Code wrote them directly)
        try:
            refactored_files = self._read_refactored_files(files_to_refactor)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read refactored files from disk: {e}",
                "improvements": refactoring_result["improvements"],
            }

        return self._create_success_response(
            refactoring_result["improvements"],
            refactoring_result["raw_response"],
            files_to_refactor,
            list(refactored_files.keys()),
        )

    def _load_and_validate_manifest(self, manifest_path: str) -> Dict[str, Any]:
        """Load and validate manifest file.

        Args:
            manifest_path: Path to manifest file

        Returns:
            Dict with success status, manifest data, and target files
        """
        manifest_data = self._load_manifest_json(manifest_path)
        if isinstance(manifest_data, dict) and "error" in manifest_data:
            return self._create_error_response(manifest_data["error"])

        files_to_refactor = self._get_target_files(manifest_data)
        if not files_to_refactor:
            return self._create_error_response("No files to refactor in manifest")

        return {
            "success": True,
            "data": manifest_data,
            "files": files_to_refactor,
            "improvements": [],
            "error": None,
        }

    def _load_manifest_json(self, manifest_path: str) -> Any:
        """Load and parse manifest JSON file.

        Args:
            manifest_path: Path to manifest file

        Returns:
            Parsed manifest data or error dict
        """
        try:
            with open(manifest_path) as f:
                return json.load(f)
        except FileNotFoundError:
            return {"error": f"Manifest not found: {manifest_path}"}
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON in manifest: {e}"}

    def _get_target_files(self, manifest_data: Dict[str, Any]) -> List[str]:
        """Extract target files from manifest data.

        Args:
            manifest_data: Parsed manifest dictionary

        Returns:
            List of file paths to refactor
        """
        editable_files = manifest_data.get("editableFiles", [])
        creatable_files = manifest_data.get("creatableFiles", [])
        return editable_files + creatable_files

    def _load_file_contents(self, file_paths: List[str]) -> Dict[str, str]:
        """Load contents of files to be refactored.

        Args:
            file_paths: List of file paths to load

        Returns:
            Dict mapping file paths to their contents
        """
        return {
            file_path: self._read_file_with_fallback(file_path)
            for file_path in file_paths
        }

    def _read_file_with_fallback(self, file_path: str) -> str:
        """Attempt to read file with original and normalized paths.

        Args:
            file_path: Path to file

        Returns:
            File contents or error message if not found
        """
        # Try original path first
        content = self._try_read_file(file_path)
        if content is not None:
            return content

        # Try normalized path as fallback
        normalized_path = self._normalize_path(file_path)
        if normalized_path != file_path:
            content = self._try_read_file(normalized_path)
            if content is not None:
                return content

        return f"{self.FILE_NOT_FOUND_PREFIX}{file_path}"

    def _try_read_file(self, path: str) -> Optional[str]:
        """Try to read a file, returning None if not found.

        Args:
            path: File path to read

        Returns:
            File contents or None if not found
        """
        try:
            with open(path) as f:
                return f.read()
        except FileNotFoundError:
            return None

    def _normalize_path(self, path: str) -> str:
        """Normalize file path by removing duplicate maid_agents/ prefix.

        Args:
            path: Original file path

        Returns:
            Normalized path with duplicate prefix removed
        """
        if not path.startswith(self.DUPLICATE_PREFIX):
            return path
        return path.replace(self.DUPLICATE_PREFIX, self.NORMALIZED_PREFIX, 1)

    def _generate_refactoring(
        self,
        manifest_data: Dict[str, Any],
        file_contents: Dict[str, str],
        validation_feedback: str,
        manifest_path: str = "",
        instructions: str = "",
    ) -> Dict[str, Any]:
        """Generate refactoring through Claude API with split prompts.

        Args:
            manifest_data: Parsed manifest
            file_contents: Current file contents
            validation_feedback: Previous validation errors
            manifest_path: Path to the manifest file
            instructions: Optional additional instructions or context

        Returns:
            Dict with success status, improvements, refactored files, and raw response
        """
        # Get split prompts (system + user)
        template_manager = get_template_manager()
        goal = manifest_data.get("goal", "")

        # Format files to refactor
        files_section = self._format_files_section(file_contents)

        # Extract test file from manifest
        readonly_files = manifest_data.get("readonlyFiles", [])
        test_files = [f for f in readonly_files if "test_" in f]
        test_file = test_files[0] if test_files else "tests/test_*.py"

        # Build additional instructions section
        if instructions:
            additional_instructions_section = f"""
## Additional Instructions

{instructions}

Please incorporate these instructions when refactoring.
"""
        else:
            additional_instructions_section = ""

        prompts = template_manager.render_for_agent(
            "refactor",
            manifest_path=manifest_path,
            goal=goal,
            files_to_refactor=files_section,
            test_file=test_file,
            additional_instructions_section=additional_instructions_section,
        )

        # Add file path instruction to user message
        files_list = "\n".join([f"- {path}" for path in file_contents.keys()])
        user_message = (
            prompts["user_message"]
            + f"""

CRITICAL: Use your file editing tools to directly update these files:
{files_list}

- Refactor the code in the file(s) listed above
- Make all changes directly using your file editing capabilities
- Do not just show the code - actually write the files
- Maintain all manifest requirements and test compatibility
"""
        )

        # Create ClaudeWrapper with system prompt
        claude_with_system = ClaudeWrapper(
            mock_mode=self.claude.mock_mode,
            model=self.claude.model,
            timeout=self.claude.timeout,
            temperature=self.claude.temperature,
            system_prompt=prompts["system_prompt"],
            bypass_permissions=self.claude.bypass_permissions,
        )

        self.logger.debug("Calling Claude to refactor code with split prompts...")
        response = claude_with_system.generate(user_message)

        if not response.success:
            return {
                "success": False,
                "error": response.error,
                "improvements": [],
            }

        improvements = self._extract_improvements(response.result)

        return {
            "success": True,
            "improvements": improvements,
            "raw_response": response.result,
        }

    def _extract_improvements(self, response: str) -> List[str]:
        """Extract list of improvements from Claude's response.

        Args:
            response: Claude's refactoring response

        Returns:
            List of improvement descriptions
        """
        improvements = [
            improvement
            for line in response.split("\n")
            if (improvement := self._extract_improvement_from_line(line))
        ]

        return improvements if improvements else [self.DEFAULT_IMPROVEMENT_MESSAGE]

    def _extract_improvement_from_line(self, line: str) -> Optional[str]:
        """Extract improvement description from a single line.

        Args:
            line: Line to parse for improvement

        Returns:
            Improvement description or None if not an improvement line
        """
        line = line.strip()

        if not self._is_improvement_line(line):
            return None

        # Strip leading markers and clean up
        improvement = line.lstrip("-*0123456789.) ").strip()
        return improvement if improvement else None

    def _is_improvement_line(self, line: str) -> bool:
        """Check if line contains an improvement description.

        Args:
            line: Line to check

        Returns:
            True if line appears to be an improvement item
        """
        if not line:
            return False

        # Check for bullet points or numbered lists
        return line.startswith(("-", "*")) or (
            len(line) > 2 and line[0].isdigit() and line[1] in ".)"
        )

    def _read_refactored_files(self, file_paths: List[str]) -> Dict[str, str]:
        """Read refactored files from disk after Claude Code writes them.

        Args:
            file_paths: List of file paths that were refactored

        Returns:
            Dict mapping file paths to their refactored code

        Raises:
            FileNotFoundError: If any file doesn't exist
        """
        refactored_files = {}
        for file_path in file_paths:
            normalized_path = self._normalize_path(file_path)
            try:
                with open(normalized_path, "r") as f:
                    refactored_files[file_path] = f.read()
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"File {normalized_path} was not updated by Claude Code. "
                    "Ensure Claude Code writes the file directly."
                )
        return refactored_files

    def _create_error_response(self, error: str) -> Dict[str, Any]:
        """Create a standardized error response.

        Args:
            error: Error message

        Returns:
            Error response dictionary
        """
        return {
            "success": False,
            "error": error,
            "improvements": [],
        }

    def _create_success_response(
        self,
        improvements: List[str],
        refactored_code: str,
        files_affected: List[str],
        files_written: List[str],
    ) -> Dict[str, Any]:
        """Create a standardized success response.

        Args:
            improvements: List of improvements made
            refactored_code: Full refactoring response
            files_affected: Files that were refactored
            files_written: Files actually written to disk

        Returns:
            Success response dictionary
        """
        return {
            "success": True,
            "improvements": improvements,
            "refactored_code": refactored_code,
            "files_affected": files_affected,
            "files_written": files_written,
            "error": None,
        }

    def _build_refactor_prompt(
        self,
        manifest_data: Dict[str, Any],
        file_contents: Dict[str, Any],
        validation_feedback: str = "",
    ) -> str:
        """Build prompt for Claude Code to refactor code directly.

        Args:
            manifest_data: Parsed manifest data
            file_contents: Dict of file paths to their contents
            validation_feedback: Optional error messages from previous validation/test failures

        Returns:
            Formatted prompt string
        """
        goal = manifest_data.get("goal", "")
        files_section = self._format_files_section(file_contents)
        feedback_section = self._format_feedback_section(validation_feedback)

        template_manager = get_template_manager()
        prompt = template_manager.render(
            "refactor",
            goal=goal,
            file_contents=files_section + feedback_section,
        )

        # Add instruction for Claude Code to write files directly
        files_list = "\n".join([f"- {path}" for path in file_contents.keys()])
        prompt += f"""

CRITICAL: Use your file editing tools to directly update these files:
{files_list}

- Refactor the code in the file(s) listed above
- Make all changes directly using your file editing capabilities
- Do not just show the code - actually write the files
- Maintain all manifest requirements and test compatibility
"""
        return prompt

    def _format_files_section(self, file_contents: Dict[str, str]) -> str:
        """Format file contents for prompt.

        Args:
            file_contents: Dict of paths to contents

        Returns:
            Formatted file section string
        """
        sections = [
            f"File: {path}\n```python\n{content}\n```"
            for path, content in file_contents.items()
        ]
        return "\n\n".join(sections)

    def _format_feedback_section(self, validation_feedback: str) -> str:
        """Format validation feedback for prompt.

        Args:
            validation_feedback: Validation error messages

        Returns:
            Formatted feedback section or empty string
        """
        if not validation_feedback:
            return ""

        return (
            f"\n\nVALIDATION ERRORS FROM PREVIOUS ITERATION:\n"
            f"{validation_feedback}\n\n"
            f"Please fix these issues while maintaining code quality improvements."
        )
