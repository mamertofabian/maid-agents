"""Refactorer Agent - Phase 3.5: Improves code quality while maintaining compliance."""

import json
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

    def refactor(self, manifest_path: str) -> dict:
        """Refactor code while maintaining tests and manifest compliance.

        Args:
            manifest_path: Path to manifest file

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
        prompt = self._build_refactor_prompt(manifest_data, file_contents)

        # Generate refactoring suggestions using Claude
        response = self.claude.generate(prompt)

        if not response.success:
            return {"success": False, "error": response.error, "improvements": []}

        # Parse improvements from response
        improvements = self._extract_improvements(response.result)

        return {
            "success": True,
            "improvements": improvements,
            "refactored_code": response.result,
            "files_affected": files_to_refactor,
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

    def _build_refactor_prompt(
        self, manifest_data: Dict[str, Any], file_contents: Dict[str, Any]
    ) -> str:
        """Build prompt for Claude to refactor code.

        Args:
            manifest_data: Parsed manifest data
            file_contents: Dict of file paths to their contents

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

        template_manager = get_template_manager()
        return template_manager.render(
            "refactor",
            goal=goal,
            file_contents=files_section,
        )
