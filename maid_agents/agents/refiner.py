"""Refiner Agent - Phase 2 Quality Gate: Improves manifest and test quality."""

import json
import re
from pathlib import Path
from typing import Dict, Any

from maid_agents.agents.base_agent import BaseAgent
from maid_agents.claude.cli_wrapper import ClaudeWrapper
from maid_agents.config.template_manager import get_template_manager


class Refiner(BaseAgent):
    """Agent that refines manifests and tests based on user refinement goals."""

    def __init__(self, claude: ClaudeWrapper):
        """Initialize refiner agent.

        Args:
            claude: Claude wrapper for AI generation
        """
        super().__init__()
        self.claude = claude

    def execute(self) -> dict:
        """Execute refinement.

        Returns:
            Dict with refinement results
        """
        return {"status": "ready", "agent": "Refiner"}

    def refine(
        self, manifest_path: str, refinement_goal: str, validation_feedback: str = ""
    ) -> dict:
        """Refine manifest and tests based on user goal and validation feedback.

        Args:
            manifest_path: Path to manifest file
            refinement_goal: User's refinement objectives
            validation_feedback: Error messages from previous validation iteration

        Returns:
            Dict with refined manifest data, test code, improvements list, and error
        """
        # Load manifest
        try:
            with open(manifest_path) as f:
                manifest_data = json.load(f)
        except FileNotFoundError:
            return {
                "success": False,
                "error": f"Manifest not found: {manifest_path}",
                "manifest_data": {},
                "test_code": {},
                "improvements": [],
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON in manifest: {e}",
                "manifest_data": {},
                "test_code": {},
                "improvements": [],
            }

        # Validate file existence for editableFiles and creatableFiles
        file_validation_errors = self._validate_file_categorization(manifest_data)
        if file_validation_errors:
            # Add file validation errors to validation feedback
            validation_feedback = (
                f"{validation_feedback}\n\nFILE CATEGORIZATION ERRORS:\n{file_validation_errors}"
                if validation_feedback
                else f"FILE CATEGORIZATION ERRORS:\n{file_validation_errors}"
            )

        # Load test files
        test_files = manifest_data.get("readonlyFiles", [])
        test_contents = self._load_test_files(test_files)

        if not test_contents:
            return {
                "success": False,
                "error": "No test files found in manifest readonlyFiles",
                "manifest_data": {},
                "test_code": {},
                "improvements": [],
            }

        # Build prompt for Claude
        prompt = self._build_refine_prompt(
            manifest_data, test_contents, refinement_goal, validation_feedback
        )

        # Generate refined manifest and tests using Claude
        response = self.claude.generate(prompt)

        if not response.success:
            return {
                "success": False,
                "error": response.error,
                "manifest_data": {},
                "test_code": {},
                "improvements": [],
            }

        # Parse response to extract refined manifest and tests
        try:
            improvements = self._extract_improvements(response.result)
            refined_manifest = self._parse_refined_manifest(response.result)
            refined_tests = self._parse_refined_tests(response.result)

            return {
                "success": True,
                "manifest_data": refined_manifest,
                "test_code": refined_tests,
                "improvements": improvements,
                "error": None,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to parse Claude's response: {e}",
                "manifest_data": {},
                "test_code": {},
                "improvements": [],
            }

    def _validate_file_categorization(self, manifest_data: Dict[str, Any]) -> str:
        """Validate that editableFiles exist and creatableFiles don't exist.

        Args:
            manifest_data: Parsed manifest dictionary

        Returns:
            String with validation errors, or empty string if no errors
        """
        errors = []
        editable_files = manifest_data.get("editableFiles", [])
        creatable_files = manifest_data.get("creatableFiles", [])

        # Check that editableFiles exist
        for file_path in editable_files:
            if not Path(file_path).exists():
                errors.append(
                    f"- File '{file_path}' is in editableFiles but does not exist. "
                    f"It should be moved to creatableFiles."
                )

        # Warn if creatableFiles already exist (might be intentional, but worth noting)
        existing_creatable = []
        for file_path in creatable_files:
            if Path(file_path).exists():
                existing_creatable.append(file_path)

        if existing_creatable:
            errors.append(
                f"- Files in creatableFiles already exist: {', '.join(existing_creatable)}. "
                f"Consider moving them to editableFiles if they should be modified."
            )

        return "\n".join(errors) if errors else ""

    def _load_test_files(self, test_file_paths: list) -> Dict[str, str]:
        """Load contents of test files.

        Args:
            test_file_paths: List of test file paths

        Returns:
            Dict mapping file paths to their contents
        """
        contents = {}
        for file_path in test_file_paths:
            # Only load test files (not other readonly files)
            if "test" not in Path(file_path).name.lower():
                continue

            try:
                with open(file_path) as f:
                    contents[file_path] = f.read()
            except FileNotFoundError:
                # Test file might not exist yet if it's a new task
                contents[file_path] = ""

        return contents

    def _extract_improvements(self, response: str) -> list:
        """Extract list of improvements from Claude's response.

        Args:
            response: Claude's refinement response

        Returns:
            List of improvement descriptions
        """
        improvements = []
        in_improvements_section = False

        for line in response.split("\n"):
            line = line.strip()

            # Detect improvements section
            if "## Improvements" in line or "## improvements" in line.lower():
                in_improvements_section = True
                continue

            # Stop at next section
            if in_improvements_section and line.startswith("##"):
                break

            # Extract bullet points in improvements section
            if in_improvements_section and (
                line.startswith("-")
                or line.startswith("*")
                or (len(line) > 2 and line[0].isdigit() and line[1] in ".)")
            ):
                improvement = line.lstrip("-*0123456789.) ").strip()
                if improvement:
                    improvements.append(improvement)

        # If no structured improvements found, provide generic response
        if not improvements:
            improvements = ["Manifest and test quality improvements applied"]

        return improvements

    def _parse_refined_manifest(self, response: str) -> dict:
        """Parse refined manifest JSON from Claude's response.

        Args:
            response: Claude's refinement response

        Returns:
            Parsed manifest dict

        Raises:
            ValueError: If manifest JSON cannot be extracted
        """
        # Look for JSON code block after "## Updated Manifest:" or "## Refined Manifest:"
        # Template uses "Updated" but support both variants for robustness
        pattern = r"## (?:Updated|Refined) Manifest:?\s*```json\s*(.*?)\s*```"
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)

        if not match:
            raise ValueError("Could not find refined manifest JSON in response")

        json_str = match.group(1)
        return json.loads(json_str)

    def _parse_refined_tests(self, response: str) -> Dict[str, str]:
        """Parse refined test code from Claude's response.

        Args:
            response: Claude's refinement response

        Returns:
            Dict mapping test file paths to refined code

        Raises:
            ValueError: If test code cannot be extracted
        """
        # Look for Python code blocks after "## Updated Test File:" or "## Refined Tests"
        # Template format: ## Updated Test File: path/to/test_file.py
        # Also support: ## Refined Tests (path/to/test.py):
        # Pattern matches both formats and handles multiple test files
        test_files = {}

        # Try format: ## Updated Test File: path/to/test.py
        pattern1 = (
            r"## (?:Updated|Refined) Test File:\s*([^\n]+)\s*```python\s*(.*?)\s*```"
        )
        matches1 = re.finditer(pattern1, response, re.DOTALL | re.IGNORECASE)

        for match in matches1:
            test_path = match.group(1).strip()
            test_code = match.group(2).strip()
            test_files[test_path] = test_code

        # Fallback: Try format with parentheses: ## Refined Tests (path/to/test.py):
        if not test_files:
            pattern2 = (
                r"## (?:Updated|Refined) Tests.*?\((.*?)\):?\s*```python\s*(.*?)\s*```"
            )
            matches2 = re.finditer(pattern2, response, re.DOTALL | re.IGNORECASE)

            for match in matches2:
                test_path = match.group(1).strip()
                test_code = match.group(2).strip()
                test_files[test_path] = test_code

        if not test_files:
            raise ValueError("Could not find refined test code in response")

        return test_files

    def _build_refine_prompt(
        self,
        manifest_data: Dict[str, Any],
        test_contents: Dict[str, str],
        refinement_goal: str,
        validation_feedback: str,
    ) -> str:
        """Build prompt for Claude to refine manifest and tests.

        Args:
            manifest_data: Current manifest data
            test_contents: Dict of test file paths to contents
            refinement_goal: User's refinement objectives
            validation_feedback: Validation errors from previous iteration

        Returns:
            Formatted prompt string
        """
        # Build test files section
        tests_section = "\n\n".join(
            [
                f"File: {path}\n```python\n{content}\n```"
                for path, content in test_contents.items()
            ]
        )

        # Build manifest JSON string
        manifest_json = json.dumps(manifest_data, indent=2)

        template_manager = get_template_manager()
        return template_manager.render(
            "refine",
            refinement_goal=refinement_goal,
            manifest_json=manifest_json,
            test_contents=tests_section,
            validation_feedback=(
                validation_feedback
                if validation_feedback
                else "No validation errors from previous iteration."
            ),
        )
