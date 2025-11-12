"""Manifest Architect Agent - Phase 1: Creates manifests from goals."""

import json
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

        # Create manifest path
        manifest_path = self._build_manifest_path(goal, task_number)

        # Read the generated manifest from disk (Claude Code wrote it directly)
        try:
            with open(manifest_path) as f:
                manifest_data = json.load(f)
        except FileNotFoundError:
            return self._build_error_response(
                f"Manifest file {manifest_path} was not created by Claude Code. "
                "Ensure Claude Code writes the manifest file directly."
            )
        except json.JSONDecodeError as e:
            return self._build_error_response(
                f"Invalid JSON in generated manifest: {e}"
            )

        self.logger.info(f"Successfully created manifest: {manifest_path}")
        return self._build_success_response(manifest_path, manifest_data)

    # ==================== Core Generation Methods ====================

    def _generate_manifest_with_claude(self, goal: str, task_number: int):
        """Generate manifest using Claude API.

        Args:
            goal: High-level goal description
            task_number: Task number for manifest

        Returns:
            ClaudeResponse object with generation result
        """
        prompt = self._build_manifest_prompt(goal, task_number)
        self.logger.debug("Calling Claude to generate manifest...")
        return self.claude.generate(prompt)

    def _build_manifest_prompt(self, goal: str, task_number: int) -> str:
        """Build prompt for Claude Code to generate manifest directly.

        Args:
            goal: High-level goal description
            task_number: Task number for manifest

        Returns:
            Formatted prompt string using template
        """
        template_manager = get_template_manager()
        prompt = template_manager.render(
            "manifest_creation", goal=goal, task_number=f"{task_number:03d}"
        )

        # Add instruction for Claude Code to write manifest file directly
        manifest_path = self._build_manifest_path(goal, task_number)
        prompt += f"""

CRITICAL: Use your file editing tools to directly create this manifest file:
- {manifest_path}

- Write the complete JSON manifest to the file listed above
- Make all changes directly using your file editing capabilities
- Do not just show the JSON - actually write the file
- Ensure the JSON is valid and matches the MAID v1.2 spec
"""
        return prompt

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
