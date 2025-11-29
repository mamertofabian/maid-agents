"""Plan Reviewer Agent - Reviews and validates plan quality after planning phase."""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from maid_agents.agents.base_agent import BaseAgent
from maid_agents.claude.cli_wrapper import ClaudeWrapper
from maid_agents.config.template_manager import get_template_manager


class PlanReviewer(BaseAgent):
    """Agent that reviews manifest and behavioral tests for architectural soundness.

    This intermediate agent (not part of main MAID phases) validates that the
    planning agent created a sound architectural plan. It checks:
    - Goal clarity and achievability
    - Test coverage and quality
    - Architectural design decisions
    - Artifact separation of concerns
    """

    def __init__(self, claude: ClaudeWrapper, dry_run: bool = False) -> None:
        """Initialize Plan Reviewer agent with ClaudeWrapper instance.

        Args:
            claude: Claude wrapper instance for AI-powered plan review.
            dry_run: If True, skip expensive operations like subprocess calls
        """
        super().__init__(dry_run=dry_run)
        self.claude = claude

    def execute(self) -> dict:
        """Execute method required by BaseAgent interface.

        Returns:
            Dictionary containing agent status and identification.
        """
        return {"status": "ready", "agent": "PlanReviewer"}

    def review_plan(
        self,
        manifest_path: str,
        review_feedback: str = "",
        instructions: str = "",
    ) -> dict:
        """Review manifest and behavioral tests for architectural soundness.

        Args:
            manifest_path: Path to the MAID manifest file to review.
            review_feedback: Optional feedback from previous review iteration.
            instructions: Optional additional instructions or context for review.

        Returns:
            Dictionary containing:
                - success (bool): Whether review succeeded
                - issues_found (list): List of architectural issues identified
                - improvements (list): List of improvements made
                - manifest_data (dict): Updated manifest data
                - test_code (dict): Updated test code
                - error (Optional[str]): Error message (if unsuccessful)
        """
        # Load and validate manifest
        manifest_data = self._load_manifest(manifest_path)
        if manifest_data is None:
            return self._create_error_response(
                f"Failed to load manifest: {manifest_path}"
            )

        # Load test files
        test_files = manifest_data.get("readonlyFiles", [])
        test_contents = self._load_test_files(test_files)

        if not test_contents:
            return self._create_error_response(
                "No test files found in manifest readonlyFiles"
            )

        # Generate review with split prompts
        response = self._generate_review_with_claude(
            manifest_path, manifest_data, test_contents, review_feedback, instructions
        )

        if not response.success:
            return self._create_error_response(response.error)

        # Extract issues and improvements from Claude's response
        issues_found = self._extract_issues(response.result)
        improvements = self._extract_improvements(response.result)

        # Read the updated files from disk (Claude Code wrote them directly)
        try:
            updated_manifest = self._read_updated_manifest(manifest_path)
            updated_tests = self._read_updated_tests(list(test_contents.keys()))
        except Exception as e:
            return self._create_error_response(
                f"Failed to read updated files from disk: {e}"
            )

        return {
            "success": True,
            "issues_found": issues_found,
            "improvements": improvements,
            "manifest_data": updated_manifest,
            "test_code": updated_tests,
            "error": None,
        }

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

    def _load_test_files(self, test_file_paths: list) -> Dict[str, str]:
        """Load contents of test files.

        Args:
            test_file_paths: List of test file paths from manifest.

        Returns:
            Dict mapping file paths to their contents.
        """
        contents = {}
        for file_path in test_file_paths:
            # Only load test files (not other readonly files)
            if "test" not in Path(file_path).name.lower():
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    contents[file_path] = f.read()
            except FileNotFoundError:
                # Test file might not exist yet
                contents[file_path] = ""

        return contents

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response.

        Args:
            error_message: The error message to include.

        Returns:
            Dictionary with error status and empty data.
        """
        return {
            "success": False,
            "error": error_message,
            "issues_found": [],
            "improvements": [],
            "manifest_data": {},
            "test_code": {},
        }

    def _generate_review_with_claude(
        self,
        manifest_path: str,
        manifest_data: Dict[str, Any],
        test_contents: Dict[str, str],
        review_feedback: str,
        instructions: str = "",
    ):
        """Generate review using Claude API with split prompts.

        Args:
            manifest_path: Path to manifest file
            manifest_data: Current manifest data
            test_contents: Dict of test file paths to contents
            review_feedback: Feedback from previous review iteration
            instructions: Optional additional instructions or context

        Returns:
            ClaudeResponse object with generation result
        """
        template_manager = get_template_manager()

        # Extract manifest components
        goal = manifest_data.get("goal", "")
        artifacts = manifest_data.get("expectedArtifacts", {}).get("contains", [])

        # Format artifacts for display
        artifacts_section = self._format_artifacts(artifacts)

        # Get primary test file path
        test_file_path = (
            list(test_contents.keys())[0] if test_contents else "No test file"
        )

        # Build additional instructions section
        if instructions:
            additional_instructions_section = f"""
## Additional Instructions

{instructions}

Please incorporate these instructions when reviewing the plan.
"""
        else:
            additional_instructions_section = ""

        # Get split prompts (system + user)
        prompts = template_manager.render_for_agent(
            "plan_reviewer",
            manifest_path=manifest_path,
            test_file_path=test_file_path,
            goal=goal,
            artifacts_section=artifacts_section,
            review_feedback=(
                review_feedback
                if review_feedback
                else "No feedback from previous iteration."
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

CRITICAL: Use your file editing tools to directly update these files if improvements are needed:
{files_list}

- Review the manifest and test files for architectural soundness
- Make improvements directly using your file editing capabilities
- Ensure goal clarity, test coverage, and proper architecture
- Update files only if improvements are needed
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

        self.logger.debug("Calling Claude to review plan with split prompts...")
        return claude_with_system.generate(user_message)

    def _format_artifacts(self, artifacts: list) -> str:
        """Format artifacts list for display in prompt.

        Args:
            artifacts: List of artifact dictionaries from manifest.

        Returns:
            Formatted string listing artifacts.
        """
        if not artifacts:
            return "  (no artifacts defined)"

        lines = []
        for artifact in artifacts:
            name = artifact.get("name", "unnamed")
            artifact_type = artifact.get("type", "unknown")
            lines.append(f"  - {name} ({artifact_type})")

        return "\n".join(lines)

    def _extract_issues(self, response: str) -> list:
        """Extract list of issues found from Claude's response.

        Args:
            response: Claude's review response

        Returns:
            List of issue descriptions
        """
        issues = []
        in_issues_section = False

        for line in response.split("\n"):
            line = line.strip()

            # Detect issues section
            if "## Issues" in line or "## issues" in line.lower():
                in_issues_section = True
                continue

            # Stop at next section
            if in_issues_section and line.startswith("##"):
                break

            # Extract bullet points in issues section
            if in_issues_section and (
                line.startswith("-")
                or line.startswith("*")
                or (len(line) > 2 and line[0].isdigit() and line[1] in ".)")
            ):
                issue = line.lstrip("-*0123456789.) ").strip()
                if issue:
                    issues.append(issue)

        return issues

    def _extract_improvements(self, response: str) -> list:
        """Extract list of improvements from Claude's response.

        Args:
            response: Claude's review response

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

        # If no structured improvements found, check if review passed
        if not improvements:
            if "no issues" in response.lower() or "looks good" in response.lower():
                improvements = ["Plan review passed - no improvements needed"]
            else:
                improvements = ["Plan review completed"]

        return improvements

    def _read_updated_manifest(self, manifest_path: str) -> dict:
        """Read updated manifest from disk after Claude Code writes it.

        Args:
            manifest_path: Path to manifest file

        Returns:
            Parsed manifest dict

        Raises:
            FileNotFoundError: If manifest file doesn't exist
            json.JSONDecodeError: If manifest is invalid JSON
        """
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Manifest file not found after review: {manifest_path}"
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in updated manifest: {e}")

    def _read_updated_tests(self, test_file_paths: list) -> Dict[str, str]:
        """Read updated test files from disk after Claude Code writes them.

        Args:
            test_file_paths: List of test file paths

        Returns:
            Dict mapping test file paths to their contents
        """
        updated_tests = {}
        for file_path in test_file_paths:
            # Only read test files (not other readonly files)
            if "test" not in Path(file_path).name.lower():
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    updated_tests[file_path] = f.read()
            except FileNotFoundError:
                # Test file might not exist if Claude Code didn't create it
                continue

        return updated_tests
