"""Fixer Agent - Reviews and fixes implementation issues."""

import json
from typing import Dict, Any, List, Optional

from maid_agents.agents.base_agent import BaseAgent
from maid_agents.claude.cli_wrapper import ClaudeWrapper
from maid_agents.config.template_manager import get_template_manager


class Fixer(BaseAgent):
    """Agent that reviews and fixes implementation issues including validation violations, test failures, and bugs.

    This agent is similar to the Developer agent but specialized for fixing
    existing implementations. It accepts error context from validation and tests
    to guide the fixing process.
    """

    def __init__(self, claude: ClaudeWrapper, dry_run: bool = False) -> None:
        """Initialize Fixer agent with ClaudeWrapper instance and optional dry_run flag.

        Args:
            claude: Claude wrapper instance for AI-powered code fixing.
            dry_run: If True, skip expensive operations like subprocess calls
        """
        super().__init__(dry_run=dry_run)
        self.claude = claude

    def execute(self) -> dict:
        """Execute method required by BaseAgent interface, returns agent status and identification.

        Returns:
            Dictionary containing agent status and identification.
        """
        return {"status": "ready", "agent": "Fixer"}

    def fix(
        self,
        manifest_path: str,
        validation_errors: str = "",
        test_errors: str = "",
        instructions: str = "",
    ) -> dict:
        """Review implementation and automatically fix validation violations, test failures, and bugs.

        Args:
            manifest_path: Path to the MAID manifest file containing task specifications.
            validation_errors: Optional validation error output from manifest validation.
            test_errors: Optional test error output from pytest or other test frameworks.
            instructions: Optional additional instructions or context for fixing.

        Returns:
            Dictionary containing:
                - success (bool): Whether fix generation succeeded
                - files_modified (List[str]): List of files that were modified
                - code (str): Generated fix code (if successful)
                - error (Optional[str]): Error message (if unsuccessful)
        """
        # Load and validate manifest
        manifest_data = self._load_manifest(manifest_path)
        if manifest_data is None:
            return self._create_error_response(
                f"Failed to load manifest: {manifest_path}"
            )

        # Generate fix with split prompts
        response = self._generate_fix_with_claude(
            manifest_data, validation_errors, test_errors, instructions
        )
        if not response.success:
            return self._create_error_response(response.error)

        # Read the generated code from disk (Claude Code wrote it directly)
        files_to_modify = self._get_modifiable_files(manifest_data)
        if not files_to_modify:
            return self._create_error_response("No files to modify in manifest")

        # Read the primary file that Claude Code should have written
        try:
            primary_file = files_to_modify[0]
            with open(primary_file, "r") as f:
                generated_code = f.read()
        except FileNotFoundError:
            return self._create_error_response(
                f"File {primary_file} was not created by Claude Code. "
                "Ensure Claude Code writes the file directly."
            )
        except Exception as e:
            return self._create_error_response(f"Failed to read generated file: {e}")

        return self._create_success_response(files_to_modify, generated_code)

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
            files_modified: List of files that were modified.
            code: Generated fix code.

        Returns:
            Dictionary with success status and fix details.
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

    def _generate_fix_with_claude(
        self,
        manifest_data: Dict[str, Any],
        validation_errors: str,
        test_errors: str,
        instructions: str = "",
    ):
        """Generate fix using Claude API with split prompts.

        Args:
            manifest_data: Parsed manifest data
            validation_errors: Validation error output from manifest validation
            test_errors: Test error output from pytest
            instructions: Optional additional instructions or context

        Returns:
            ClaudeResponse object with generation result
        """
        # Extract manifest components
        template_manager = get_template_manager()
        goal = manifest_data.get("goal", "")

        # Format errors for the prompt
        errors_section = self._build_errors_section(validation_errors, test_errors)

        # Get files to modify
        files_to_modify_str = self._format_modifiable_files(manifest_data)

        # Build additional instructions section
        if instructions:
            additional_instructions_section = f"""
## Additional Instructions

{instructions}

Please incorporate these instructions when fixing the issues.
"""
        else:
            additional_instructions_section = ""

        # Get split prompts (system + user)
        prompts = template_manager.render_for_agent(
            "fixer",
            goal=goal,
            errors_section=errors_section,
            files_to_modify=files_to_modify_str,
            additional_instructions_section=additional_instructions_section,
        )

        # Add file path instruction to user message
        files_to_modify = self._get_modifiable_files(manifest_data)
        user_message = prompts["user_message"]
        if files_to_modify:
            files_list = "\n".join([f"- {path}" for path in files_to_modify])
            user_message += f"""

CRITICAL: Use your file editing tools to directly write/update these files:
{files_list}

- Fix all issues in the implementation code
- Make all changes directly using your file editing capabilities
- Ensure all validation errors and test failures are resolved
- Ensure the code matches all artifact signatures exactly
"""

        # Create ClaudeWrapper with system prompt
        claude_with_system = ClaudeWrapper(
            mock_mode=self.claude.mock_mode,
            model=self.claude.model,
            timeout=self.claude.timeout,
            temperature=self.claude.temperature,
            system_prompt=prompts["system_prompt"],
            bypass_permissions=self.claude.bypass_permissions,
        )

        self.logger.debug("Calling Claude to generate fix with split prompts...")
        return claude_with_system.generate(user_message)

    def _build_errors_section(self, validation_errors: str, test_errors: str) -> str:
        """Build the errors section for the prompt.

        Args:
            validation_errors: Validation error output
            test_errors: Test error output

        Returns:
            Formatted errors section
        """
        sections = []

        if validation_errors and validation_errors.strip():
            sections.append(
                f"""### Validation Errors

```
{validation_errors}
```"""
            )

        if test_errors and test_errors.strip():
            sections.append(
                f"""### Test Failures

```
{test_errors}
```"""
            )

        if not sections:
            return "No errors provided. Please review the implementation for potential issues."

        return "\n\n".join(sections)

    def _format_modifiable_files(self, manifest_data: Dict[str, Any]) -> str:
        """Format list of modifiable files for display.

        Args:
            manifest_data: Parsed manifest dictionary.

        Returns:
            Formatted string listing files to modify.
        """
        files = self._get_modifiable_files(manifest_data)

        if not files:
            return "  (none specified)"

        return "\n".join(f"  - {file}" for file in files)
