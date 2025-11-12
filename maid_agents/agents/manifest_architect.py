"""Manifest Architect Agent - Phase 1: Creates manifests from goals."""

import glob
import json
import os
import re

from maid_agents.agents.base_agent import BaseAgent
from maid_agents.claude.cli_wrapper import ClaudeWrapper
from maid_agents.config.template_manager import get_template_manager


class ManifestArchitect(BaseAgent):
    """Agent that creates MAID manifests from high-level goals."""

    # Configuration constants
    _MAX_SLUG_LENGTH = 50
    _MIN_WORD_BOUNDARY = 30
    _GOAL_PREVIEW_LENGTH = 60

    def __init__(self, claude: ClaudeWrapper):
        """Initialize manifest architect.

        Args:
            claude: Claude wrapper for AI generation
        """
        super().__init__()
        self.claude = claude

    def execute(self) -> dict:
        """Execute manifest creation.

        Returns:
            dict with manifest creation results
        """
        return {"status": "ready", "agent": "ManifestArchitect"}

    def create_manifest(self, goal: str, task_number: int) -> dict:
        """Create manifest from goal description.

        Args:
            goal: High-level goal description
            task_number: Task number for manifest naming

        Returns:
            dict with manifest data and path
        """
        self.logger.debug(
            f"Creating manifest for task-{task_number:03d}: "
            f"{goal[:self._GOAL_PREVIEW_LENGTH]}..."
        )

        # Generate manifest using Claude Code
        response = self._generate_manifest_with_claude(goal, task_number)
        if not response.success:
            return self._build_error_response(response.error)

        # Find the actual manifest file created by Claude Code
        # (Claude Code may use a different slug than we expect)
        manifest_result = self._find_created_manifest(task_number)
        if not manifest_result["success"]:
            return manifest_result

        manifest_path = manifest_result["manifest_path"]
        manifest_data = manifest_result["manifest_data"]

        self.logger.info(f"Successfully created manifest: {manifest_path}")
        return self._build_success_response(manifest_path, manifest_data)

    # ==================== Core Generation Methods ====================

    def _generate_manifest_with_claude(self, goal: str, task_number: int):
        """Generate manifest using Claude API with split prompts.

        Args:
            goal: High-level goal description
            task_number: Task number for manifest

        Returns:
            ClaudeResponse object with generation result
        """
        # Get split prompts (system + user)
        template_manager = get_template_manager()
        manifests_dir = os.path.abspath("manifests")

        prompts = template_manager.render_for_agent(
            "manifest_creation", goal=goal, task_number=f"{task_number:03d}"
        )

        # Add file path instruction to user message
        # Note: We give Claude Code flexibility on the slug, but require the task number format
        user_message = (
            prompts["user_message"]
            + f"""

CRITICAL: Use your file editing tools to directly create the manifest file.

Required format: {manifests_dir}/task-{task_number:03d}-<descriptive-slug>.manifest.json

Requirements:
- File MUST be in the manifests/ directory
- Filename MUST start with "task-{task_number:03d}-"
- Filename MUST end with ".manifest.json"
- Use a descriptive slug (lowercase, hyphens) between the task number and extension
- Write the complete JSON manifest using your file editing capabilities
- Do not just show the JSON - actually write the file
- Ensure the JSON is valid and matches the MAID v1.2 spec
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

        self.logger.debug("Calling Claude to generate manifest with split prompts...")
        return claude_with_system.generate(user_message)

    def _find_created_manifest(self, task_number: int) -> dict:
        """Find manifest file created by Claude Code for given task number.

        Claude Code may create a file with a different slug than expected,
        so we search for any manifest matching the task number pattern.

        Args:
            task_number: Task number to search for

        Returns:
            dict with success status, manifest_path, and manifest_data
        """
        # Search for manifests matching task number
        pattern = f"manifests/task-{task_number:03d}-*.manifest.json"
        matches = glob.glob(pattern)

        if not matches:
            return self._build_error_response(
                f"No manifest file found for task-{task_number:03d}. "
                f"Searched pattern: {pattern}. "
                "Claude Code may not have created the file. "
                "Check the response output for errors."
            )

        if len(matches) > 1:
            # Multiple matches - use the most recent one
            matches.sort(key=os.path.getmtime, reverse=True)
            manifest_path = matches[0]
            self.logger.warning(
                f"Found {len(matches)} manifests for task-{task_number:03d}. "
                f"Using most recent: {manifest_path}"
            )
        else:
            manifest_path = matches[0]

        # Read and parse the manifest
        try:
            with open(manifest_path) as f:
                manifest_data = json.load(f)
        except json.JSONDecodeError as e:
            return self._build_error_response(
                f"Invalid JSON in manifest {manifest_path}: {e}"
            )
        except Exception as e:
            return self._build_error_response(
                f"Error reading manifest {manifest_path}: {e}"
            )

        return {
            "success": True,
            "manifest_path": manifest_path,
            "manifest_data": manifest_data,
        }

    # ==================== Path and Naming Methods ====================

    def _build_manifest_path(self, goal: str, task_number: int) -> str:
        """Create the full path for the manifest file.

        Args:
            goal: High-level goal description
            task_number: Task number for manifest

        Returns:
            Full path for manifest file
        """
        slug = self._generate_slug(goal)
        return f"manifests/task-{task_number:03d}-{slug}.manifest.json"

    def _generate_slug(self, goal: str) -> str:
        """Generate a URL-friendly slug from goal description.

        Args:
            goal: High-level goal description

        Returns:
            Slug suitable for filenames (lowercase, hyphens, max 50 chars)
        """
        slug = self._sanitize_text_for_slug(goal)
        slug = self._normalize_slug_separators(slug)
        return self._enforce_slug_length(slug)

    def _sanitize_text_for_slug(self, text: str) -> str:
        """Clean and sanitize text for slug generation.

        Args:
            text: Original text to sanitize

        Returns:
            Cleaned text with only alphanumeric and hyphens
        """
        # Convert to lowercase and remove special characters
        sanitized = text.lower()
        return re.sub(r"[^a-z0-9\s-]", "", sanitized)

    def _normalize_slug_separators(self, text: str) -> str:
        """Normalize spaces and hyphens to single hyphens.

        Args:
            text: Text with spaces and possibly multiple hyphens

        Returns:
            Text with normalized single hyphens
        """
        # Replace spaces and multiple hyphens with single hyphen
        normalized = re.sub(r"[\s-]+", "-", text)
        # Remove leading/trailing hyphens
        return normalized.strip("-")

    def _enforce_slug_length(self, slug: str) -> str:
        """Ensure slug meets length requirements.

        Args:
            slug: Original slug to check

        Returns:
            Slug truncated at word boundary if needed
        """
        if len(slug) <= self._MAX_SLUG_LENGTH:
            return slug

        # Try to cut at word boundary for cleaner truncation
        truncated = slug[: self._MAX_SLUG_LENGTH]
        last_separator = truncated.rfind("-")

        # Use word boundary if it's reasonable, otherwise hard truncate
        if last_separator > self._MIN_WORD_BOUNDARY:
            return truncated[:last_separator]

        return truncated

    # ==================== Response Building Methods ====================

    def _build_error_response(self, error: str) -> dict:
        """Build standardized error response.

        Args:
            error: Error message to include

        Returns:
            dict with error information
        """
        self.logger.error(f"Manifest creation failed: {error}")
        return {
            "success": False,
            "error": error,
            "manifest_path": None,
            "manifest_data": None,
        }

    def _build_success_response(self, manifest_path: str, manifest_data: dict) -> dict:
        """Build standardized success response.

        Args:
            manifest_path: Path to the manifest file
            manifest_data: Parsed manifest data

        Returns:
            dict with success information
        """
        return {
            "success": True,
            "manifest_path": manifest_path,
            "manifest_data": manifest_data,
            "error": None,
        }
