"""Refactorer Agent - Phase 3.5: Improves code quality while maintaining compliance."""

import json
import re
from pathlib import Path
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

    DUPLICATE_PREFIX = "maid_agents/maid_agents/"
    NORMALIZED_PREFIX = "maid_agents/"
    FILE_NOT_FOUND_PREFIX = "# File not found: "
    DEFAULT_IMPROVEMENT_MESSAGE = "Code quality improvements applied"

    def __init__(self, claude: ClaudeWrapper) -> None:
        """Initialize refactorer agent.

        Args:
            claude: Claude wrapper for AI generation
        """
        super().__init__()
        self.claude = claude

    def execute(self) -> dict:
        """Execute refactoring.

        Returns:
            Dict with refactoring results
        """
        return {"status": "ready", "agent": "Refactorer"}

    def refactor(self, manifest_path: str, validation_feedback: str = "") -> dict:
        """Refactor code while maintaining tests and manifest compliance.

        Args:
            manifest_path: Path to manifest file
            validation_feedback: Optional error messages from previous validation/test failures

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

        # Generate refactoring via Claude
        refactoring_result = self._generate_refactoring(
            manifest_data, file_contents, validation_feedback
        )
        if not refactoring_result["success"]:
            return refactoring_result

        # Write refactored code to files
        write_result = self._write_refactored_files(
            refactoring_result["refactored_files"], refactoring_result["improvements"]
        )
        if not write_result["success"]:
            return write_result

        return self._create_success_response(
            refactoring_result["improvements"],
            refactoring_result["raw_response"],
            files_to_refactor,
            write_result["files_written"],
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
    ) -> Dict[str, Any]:
        """Generate refactoring through Claude API.

        Args:
            manifest_data: Parsed manifest
            file_contents: Current file contents
            validation_feedback: Previous validation errors

        Returns:
            Dict with success status, improvements, refactored files, and raw response
        """
        prompt = self._build_refactor_prompt(
            manifest_data, file_contents, validation_feedback
        )
        response = self.claude.generate(prompt)

        if not response.success:
            return {
                "success": False,
                "error": response.error,
                "improvements": [],
            }

        improvements = self._extract_improvements(response.result)
        refactored_files = self._parse_refactored_code(
            response.result, list(file_contents.keys())
        )

        return {
            "success": True,
            "improvements": improvements,
            "refactored_files": refactored_files,
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

    def _parse_refactored_code(
        self, response: str, file_paths: List[str]
    ) -> Dict[str, str]:
        """Parse refactored code blocks from Claude's response.

        Args:
            response: Claude's refactoring response
            file_paths: List of file paths that were refactored

        Returns:
            Dict mapping file paths to their refactored code
        """
        # Try to extract file-specific code blocks first
        refactored_files = self._extract_file_code_blocks(response, file_paths)

        # Fall back to single code block extraction if needed
        if not refactored_files and file_paths:
            refactored_files = self._extract_fallback_code_block(response, file_paths)

        return refactored_files

    def _extract_file_code_blocks(
        self, response: str, file_paths: List[str]
    ) -> Dict[str, str]:
        """Extract code blocks with file path labels.

        Args:
            response: Claude's response text
            file_paths: Expected file paths

        Returns:
            Dict mapping file paths to code
        """
        refactored_files = {}

        # Pattern to match: File: path\n```python\ncode\n```
        pattern = r"File:\s*([^\n]+)\s*\n\s*```python\s*\n(.*?)\n\s*```"
        matches = re.findall(pattern, response, re.DOTALL)

        for file_path, code in matches:
            matched_path = self._match_file_path(file_path.strip(), file_paths)
            if matched_path:
                refactored_files[matched_path] = code.strip()

        return refactored_files

    def _match_file_path(
        self, response_path: str, file_paths: List[str]
    ) -> Optional[str]:
        """Match a response path to one of the expected file paths.

        Args:
            response_path: Path from Claude's response
            file_paths: List of expected paths

        Returns:
            Matching original path or None
        """
        normalized_response = self._normalize_path(response_path)

        for original_path in file_paths:
            if normalized_response == self._normalize_path(original_path):
                return original_path

        return None

    def _extract_fallback_code_block(
        self, response: str, file_paths: List[str]
    ) -> Dict[str, str]:
        """Extract a single unlabeled code block as fallback.

        Args:
            response: Claude's response text
            file_paths: List of file paths

        Returns:
            Dict with first file mapped to largest code block
        """
        code_block_pattern = r"```python\n(.*?)\n```"
        code_matches = re.findall(code_block_pattern, response, re.DOTALL)

        if not code_matches:
            return {}

        # Use the largest code block for the first file
        largest_code = max(code_matches, key=len).strip()
        return {file_paths[0]: largest_code}

    def _write_refactored_files(
        self, refactored_files: Dict[str, str], improvements: List[str]
    ) -> Dict[str, Any]:
        """Write refactored code to files.

        Args:
            refactored_files: Dict mapping paths to refactored code
            improvements: List of improvements for error response

        Returns:
            Dict with success status and files written
        """
        files_written = []

        for file_path, code in refactored_files.items():
            write_result = self._write_single_file(file_path, code)
            if not write_result["success"]:
                return self._create_write_error_response(
                    write_result["error"], improvements
                )
            files_written.append(write_result["path"])

        return {"success": True, "files_written": files_written}

    def _write_single_file(self, file_path: str, code: str) -> Dict[str, Any]:
        """Write code to a single file.

        Args:
            file_path: Path to write to
            code: Code content to write

        Returns:
            Dict with success status and normalized path or error
        """
        try:
            normalized_path = self._normalize_path(file_path)
            target_file = Path(normalized_path)
            target_file.parent.mkdir(parents=True, exist_ok=True)

            with open(target_file, "w") as f:
                f.write(code)

            return {"success": True, "path": normalized_path}
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to write refactored code to {file_path}: {e}",
            }

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

    def _create_write_error_response(
        self, error: str, improvements: List[str]
    ) -> Dict[str, Any]:
        """Create error response for write failures.

        Args:
            error: Error message
            improvements: List of attempted improvements

        Returns:
            Error response dictionary with improvements
        """
        return {
            "success": False,
            "error": error,
            "improvements": improvements,
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
        """Build prompt for Claude to refactor code.

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
        return template_manager.render(
            "refactor",
            goal=goal,
            file_contents=files_section + feedback_section,
        )

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
