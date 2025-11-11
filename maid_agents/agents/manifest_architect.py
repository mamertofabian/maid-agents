"""Manifest Architect Agent - Phase 1: Creates manifests from goals."""

import json
import re
from typing import Optional

from maid_agents.agents.base_agent import BaseAgent
from maid_agents.claude.cli_wrapper import ClaudeWrapper
from maid_agents.config.template_manager import get_template_manager


class ManifestArchitect(BaseAgent):
    """Agent that creates MAID manifests from high-level goals."""

    # Configuration constants
    _MAX_SLUG_LENGTH = 50
    _MIN_WORD_BOUNDARY = 30
    _GOAL_PREVIEW_LENGTH = 60
    _ERROR_PREVIEW_LENGTH = 200

    # JSON validation patterns
    _JSON_FENCE_PATTERN = r"```(?:json)?\s*\n(.*?)\n```"
    _JSON_OBJECT_PATTERN = r"\{.*\}"

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

        # Generate manifest using Claude
        response = self._generate_manifest_with_claude(goal, task_number)
        if not response.success:
            return self._build_error_response(response.error)

        # Parse and validate manifest
        manifest_result = self._extract_and_validate_manifest(response.result)
        if not manifest_result["success"]:
            return self._build_error_response(manifest_result["error"])

        # Create manifest path
        manifest_path = self._build_manifest_path(goal, task_number)

        self.logger.info(f"Successfully created manifest: {manifest_path}")
        return self._build_success_response(manifest_path, manifest_result["data"])

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
        """Build prompt for Claude to generate manifest.

        Args:
            goal: High-level goal description
            task_number: Task number for manifest

        Returns:
            Formatted prompt string using template
        """
        template_manager = get_template_manager()
        return template_manager.render(
            "manifest_creation", goal=goal, task_number=f"{task_number:03d}"
        )

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

    # ==================== JSON Extraction and Validation ====================

    def _extract_and_validate_manifest(self, response_text: str) -> dict:
        """Extract and validate manifest JSON from Claude's response.

        Args:
            response_text: Raw response from Claude

        Returns:
            dict with success status and parsed data or error
        """
        try:
            json_content = self._extract_json_content(response_text)
            manifest_data = json.loads(json_content)
            return {"success": True, "data": manifest_data}
        except json.JSONDecodeError as e:
            error_msg = self._format_parse_error(e, response_text)
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def _extract_json_content(self, response: str) -> str:
        """Extract JSON content from various response formats.

        Args:
            response: Raw response from Claude

        Returns:
            Extracted JSON string
        """
        # Try markdown code fence extraction first (most common)
        json_from_fence = self._try_extract_from_markdown(response)
        if json_from_fence:
            return json_from_fence

        # Fall back to direct JSON object extraction
        json_object = self._try_extract_raw_json(response)
        if json_object:
            return json_object

        # If nothing found, return original (will likely fail JSON parsing)
        return response.strip()

    def _try_extract_from_markdown(self, response: str) -> Optional[str]:
        """Attempt to extract JSON from markdown code fence.

        Args:
            response: Raw response possibly containing markdown

        Returns:
            Extracted JSON string or None if not found
        """
        matches = re.findall(self._JSON_FENCE_PATTERN, response, re.DOTALL)

        if matches:
            return matches[0].strip()
        return None

    def _try_extract_raw_json(self, response: str) -> Optional[str]:
        """Attempt to extract raw JSON object from response.

        Args:
            response: Raw response possibly containing JSON

        Returns:
            Valid JSON string or None if not found
        """
        matches = re.findall(self._JSON_OBJECT_PATTERN, response, re.DOTALL)

        if not matches:
            return None

        # Validate each match and return the best one
        return self._select_best_json_match(matches)

    def _select_best_json_match(self, candidates: list) -> Optional[str]:
        """Select the best valid JSON from candidates.

        Args:
            candidates: List of potential JSON strings

        Returns:
            Best valid JSON string or None if none valid
        """
        # Prefer longer matches (more complete JSON)
        sorted_candidates = sorted(candidates, key=len, reverse=True)

        for candidate in sorted_candidates:
            candidate = candidate.strip()

            # Quick structural check
            if not self._has_json_structure(candidate):
                continue

            # Validate it parses correctly
            if self._validate_json_syntax(candidate):
                return candidate

        return None

    def _has_json_structure(self, text: str) -> bool:
        """Check if text has basic JSON structure.

        Args:
            text: Text to check for JSON structure

        Returns:
            True if text appears to be JSON object
        """
        return text.startswith("{") and text.endswith("}")

    def _validate_json_syntax(self, text: str) -> bool:
        """Validate JSON syntax by attempting to parse.

        Args:
            text: Text to validate as JSON

        Returns:
            True if valid JSON syntax
        """
        try:
            json.loads(text)
            return True
        except json.JSONDecodeError:
            return False

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

    def _format_parse_error(
        self, error: json.JSONDecodeError, response_text: str
    ) -> str:
        """Format JSON parse error with helpful context.

        Args:
            error: JSON decode error that occurred
            response_text: Original response text for context

        Returns:
            Formatted error message with context
        """
        preview = response_text[: self._ERROR_PREVIEW_LENGTH]
        if len(response_text) > self._ERROR_PREVIEW_LENGTH:
            preview += "..."
        return f"Failed to parse manifest JSON: {error}. Response preview: {preview}"
