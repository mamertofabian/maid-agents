"""Refactorer Agent - Phase 3.5: Improves code quality while maintaining compliance."""

import json
import re
from pathlib import Path
from typing import Dict, Any

from maid_agents.agents.base_agent import BaseAgent
from maid_agents.claude.cli_wrapper import ClaudeWrapper
from maid_agents.config.template_manager import get_template_manager


class Refactorer(BaseAgent):
    """Agent that refactors code while maintaining manifest compliance."""

    def __init__(self, claude: ClaudeWrapper):
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
        # Load manifest
        try:
            with open(manifest_path) as f:
                manifest_data = json.load(f)
        except FileNotFoundError:
            return {
                "success": False,
                "error": f"Manifest not found: {manifest_path}",
                "improvements": [],
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON in manifest: {e}",
                "improvements": [],
            }

        # Get target files to refactor
        files_to_refactor = manifest_data.get("editableFiles", []) + manifest_data.get(
            "creatableFiles", []
        )

        if not files_to_refactor:
            return {
                "success": False,
                "error": "No files to refactor in manifest",
                "improvements": [],
            }

        # Load current code from target files
        file_contents = self._load_file_contents(files_to_refactor)

        # Build prompt for Claude
        prompt = self._build_refactor_prompt(
            manifest_data, file_contents, validation_feedback
        )

        # Generate refactoring suggestions using Claude
        response = self.claude.generate(prompt)

        if not response.success:
            return {"success": False, "error": response.error, "improvements": []}

        # Parse improvements from response
        improvements = self._extract_improvements(response.result)

        # Parse refactored code blocks for each file
        refactored_files = self._parse_refactored_code(
            response.result, files_to_refactor
        )

        # Write refactored code to files
        files_written = []
        for file_path, code in refactored_files.items():
            try:
                # Use normalized path for writing
                normalized_path = self._normalize_path(file_path)
                target_file = Path(normalized_path)
                target_file.parent.mkdir(parents=True, exist_ok=True)

                with open(target_file, "w") as f:
                    f.write(code)
                files_written.append(normalized_path)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to write refactored code to {file_path}: {e}",
                    "improvements": improvements,
                }

        return {
            "success": True,
            "improvements": improvements,
            "refactored_code": response.result,
            "files_affected": files_to_refactor,
            "files_written": files_written,
            "error": None,
        }

    def _load_file_contents(self, file_paths: list) -> Dict[str, str]:
        """Load contents of files to be refactored.

        Args:
            file_paths: List of file paths to load

        Returns:
            Dict mapping file paths to their contents
        """
        contents = {}
        for file_path in file_paths:
            # Try original path first
            try:
                with open(file_path) as f:
                    contents[file_path] = f.read()
                    continue
            except FileNotFoundError:
                pass

            # Try normalized path (remove duplicate maid_agents/ prefix)
            normalized_path = self._normalize_path(file_path)
            if normalized_path != file_path:
                try:
                    with open(normalized_path) as f:
                        contents[file_path] = f.read()
                        continue
                except FileNotFoundError:
                    pass

            # File not found with either path
            contents[file_path] = f"# File not found: {file_path}"
        return contents

    def _normalize_path(self, path: str) -> str:
        """Normalize file path by removing duplicate maid_agents/ prefix.

        Args:
            path: Original file path

        Returns:
            Normalized path with duplicate prefix removed
        """
        # Remove duplicate maid_agents/maid_agents/ prefix
        if path.startswith("maid_agents/maid_agents/"):
            return path.replace("maid_agents/maid_agents/", "maid_agents/", 1)
        return path

    def _extract_improvements(self, response: str) -> list:
        """Extract list of improvements from Claude's response.

        Args:
            response: Claude's refactoring response

        Returns:
            List of improvement descriptions
        """
        # Simple extraction: look for bullet points or numbered lists
        improvements = []
        for line in response.split("\n"):
            line = line.strip()
            # Match lines starting with -, *, or numbers
            if (
                line.startswith("-")
                or line.startswith("*")
                or (len(line) > 2 and line[0].isdigit() and line[1] in ".)")
            ):
                improvement = line.lstrip("-*0123456789.) ").strip()
                if improvement:
                    improvements.append(improvement)

        # If no structured improvements found, provide generic response
        if not improvements:
            improvements = ["Code quality improvements applied"]

        return improvements

    def _parse_refactored_code(self, response: str, file_paths: list) -> Dict[str, str]:
        """Parse refactored code blocks from Claude's response.

        Args:
            response: Claude's refactoring response
            file_paths: List of file paths that were refactored

        Returns:
            Dict mapping file paths to their refactored code
        """
        refactored_files = {}

        # Pattern to match: File: path\n```python\ncode\n```
        # This handles both the original path format and normalized paths
        # Allow for optional whitespace/newlines between File: line and code block
        # Handle code blocks ending with ``` on same or next line
        pattern = r"File:\s*([^\n]+)\s*\n\s*```python\s*\n(.*?)\n\s*```"
        matches = re.findall(pattern, response, re.DOTALL)

        for file_path, code in matches:
            # Normalize the path from response
            normalized_response_path = self._normalize_path(file_path.strip())

            # Find matching file from the original list
            for original_path in file_paths:
                normalized_original = self._normalize_path(original_path)
                if normalized_response_path == normalized_original:
                    refactored_files[original_path] = code.strip()
                    break

        # If no matches found, try to extract single code block (fallback)
        if not refactored_files and file_paths:
            # Try to find any code block
            code_block_pattern = r"```python\n(.*?)\n```"
            code_matches = re.findall(code_block_pattern, response, re.DOTALL)
            if code_matches:
                # Use the largest code block for the first file
                code = max(code_matches, key=len).strip()
                refactored_files[file_paths[0]] = code

        return refactored_files

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

        # Build file context section
        files_section = "\n\n".join(
            [
                f"File: {path}\n```python\n{content}\n```"
                for path, content in file_contents.items()
            ]
        )

        # Add validation feedback if provided
        feedback_section = ""
        if validation_feedback:
            feedback_section = f"\n\nVALIDATION ERRORS FROM PREVIOUS ITERATION:\n{validation_feedback}\n\nPlease fix these issues while maintaining code quality improvements."

        template_manager = get_template_manager()
        return template_manager.render(
            "refactor",
            goal=goal,
            file_contents=files_section + feedback_section,
        )
