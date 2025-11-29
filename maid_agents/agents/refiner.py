"""Refiner Agent - Phase 2 Quality Gate: Improves manifest and test quality."""

import json
from pathlib import Path
from typing import Dict, Any

from maid_agents.agents.base_agent import BaseAgent
from maid_agents.claude.cli_wrapper import ClaudeWrapper
from maid_agents.config.template_manager import get_template_manager


class Refiner(BaseAgent):
    """Agent that refines manifests and tests based on user refinement goals."""

    def __init__(self, claude: ClaudeWrapper, dry_run: bool = False):
        """Initialize refiner agent.

        Args:
            claude: Claude wrapper for AI generation
            dry_run: If True, skip expensive operations like subprocess calls
        """
        super().__init__(dry_run=dry_run)
        self.claude = claude

    def execute(self) -> dict:
        """Execute refinement.

        Returns:
            Dict with refinement results
        """
        return {"status": "ready", "agent": "Refiner"}

    def refine(
        self,
        manifest_path: str,
        refinement_goal: str,
        validation_feedback: str = "",
        instructions: str = "",
    ) -> dict:
        """Refine manifest and tests based on user goal and validation feedback.

        Args:
            manifest_path: Path to manifest file
            refinement_goal: User's refinement objectives
            validation_feedback: Error messages from previous validation iteration
            instructions: Optional additional instructions or context

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

        # Generate refinements with split prompts
        response = self._generate_refinement_with_claude(
            manifest_path,
            manifest_data,
            test_contents,
            refinement_goal,
            validation_feedback,
            instructions,
        )

        if not response.success:
            return {
                "success": False,
                "error": response.error,
                "manifest_data": {},
                "test_code": {},
                "improvements": [],
            }

        # Extract improvements from Claude's response
        improvements = self._extract_improvements(response.result)

        # Read the refined files back from disk (Claude Code wrote them directly)
        try:
            refined_manifest = self._read_refined_manifest(manifest_path)
            refined_tests = self._read_refined_tests(list(test_contents.keys()))
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read refined files from disk: {e}",
                "manifest_data": {},
                "test_code": {},
                "improvements": improvements,
            }

        return {
            "success": True,
            "manifest_data": refined_manifest,
            "test_code": refined_tests,
            "improvements": improvements,
            "error": None,
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

    def _read_refined_manifest(self, manifest_path: str) -> dict:
        """Read refined manifest from disk after Claude Code writes it.

        Args:
            manifest_path: Path to manifest file

        Returns:
            Parsed manifest dict

        Raises:
            FileNotFoundError: If manifest file doesn't exist
            json.JSONDecodeError: If manifest is invalid JSON
        """
        try:
            with open(manifest_path) as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Manifest file not found after refinement: {manifest_path}"
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in refined manifest: {e}")

    def _read_refined_tests(self, test_file_paths: list) -> Dict[str, str]:
        """Read refined test files from disk after Claude Code writes them.

        Args:
            test_file_paths: List of test file paths

        Returns:
            Dict mapping test file paths to their contents
        """
        refined_tests = {}
        for file_path in test_file_paths:
            # Only read test files (not other readonly files)
            if "test" not in Path(file_path).name.lower():
                continue

            try:
                with open(file_path) as f:
                    refined_tests[file_path] = f.read()
            except FileNotFoundError:
                # Test file might not exist if Claude Code didn't create it
                continue

        return refined_tests

    def _generate_refinement_with_claude(
        self,
        manifest_path: str,
        manifest_data: Dict[str, Any],
        test_contents: Dict[str, str],
        refinement_goal: str,
        validation_feedback: str,
        instructions: str = "",
    ):
        """Generate refinement using Claude API with split prompts.

        Args:
            manifest_path: Path to manifest file to update
            manifest_data: Current manifest data
            test_contents: Dict of test file paths to contents
            refinement_goal: User's refinement objectives
            validation_feedback: Validation errors from previous iteration
            instructions: Optional additional instructions or context

        Returns:
            ClaudeResponse object with generation result
        """
        # Get split prompts (system + user)
        template_manager = get_template_manager()

        # Get primary test file path (first test file from test_contents)
        test_file_path = (
            list(test_contents.keys())[0] if test_contents else "No test file"
        )

        # Build additional instructions section
        if instructions:
            additional_instructions_section = f"""
## Additional Instructions

{instructions}

Please incorporate these instructions when refining.
"""
        else:
            additional_instructions_section = ""

        prompts = template_manager.render_for_agent(
            "refine",
            manifest_path=manifest_path,
            test_file_path=test_file_path,
            goal=refinement_goal,
            validation_errors=(
                validation_feedback
                if validation_feedback
                else "No validation errors from previous iteration."
            ),
            additional_instructions_section=additional_instructions_section,
        )

        # Build list of files Claude Code should update
        files_to_update = [manifest_path] + list(test_contents.keys())
        files_list = "\n".join([f"- {path}" for path in files_to_update])

        # Add file path instruction to user message
        user_message = (
            prompts["user_message"]
            + f"""

CRITICAL: Use your file editing tools to directly update these files:
{files_list}

- Update the manifest and test files listed above
- Make all changes directly using your file editing capabilities
- Do not just show the changes - actually write the files
- Ensure all MAID v1.2 requirements are met
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

        self.logger.debug(
            "Calling Claude to refine manifest and tests with split prompts..."
        )
        return claude_with_system.generate(user_message)

    def _build_refine_prompt(
        self,
        manifest_path: str,
        manifest_data: Dict[str, Any],
        test_contents: Dict[str, str],
        refinement_goal: str,
        validation_feedback: str,
    ) -> str:
        """Build prompt for Claude Code to refine manifest and tests directly.

        Args:
            manifest_path: Path to manifest file to update
            manifest_data: Current manifest data
            test_contents: Dict of test file paths to contents
            refinement_goal: User's refinement objectives
            validation_feedback: Validation errors from previous iteration

        Returns:
            Formatted prompt string
        """
        # Build list of files Claude Code should update
        files_to_update = [manifest_path] + list(test_contents.keys())
        files_list = "\n".join([f"- {path}" for path in files_to_update])

        template_manager = get_template_manager()

        # Get primary test file path (first test file from test_contents)
        test_file_path = (
            list(test_contents.keys())[0] if test_contents else "No test file"
        )

        prompt = template_manager.render(
            "refine",
            manifest_path=manifest_path,
            test_file_path=test_file_path,
            goal=refinement_goal,
            validation_errors=(
                validation_feedback
                if validation_feedback
                else "No validation errors from previous iteration."
            ),
        )

        # Add instruction for Claude Code to write files directly
        prompt += f"""

CRITICAL: Use your file editing tools to directly update these files:
{files_list}

- Update the manifest file ({manifest_path}) with the refined JSON
- Update each test file with the refined Python code
- Make all changes directly using your file editing capabilities
- Do not just show the code - actually write the files

After making changes, provide a summary of improvements made.
"""
        return prompt
