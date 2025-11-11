"""Manifest Architect Agent - Phase 1: Creates manifests from goals."""

import json

from maid_agents.agents.base_agent import BaseAgent
from maid_agents.claude.cli_wrapper import ClaudeWrapper
from maid_agents.config.template_manager import get_template_manager


class ManifestArchitect(BaseAgent):
    """Agent that creates MAID manifests from high-level goals."""

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
            Dict with manifest creation results
        """
        return {"status": "ready", "agent": "ManifestArchitect"}

    def create_manifest(self, goal: str, task_number: int) -> dict:
        """Create manifest from goal description.

        Args:
            goal: High-level goal description
            task_number: Task number for manifest naming

        Returns:
            Dict with manifest data and path
        """
        self.logger.debug(
            f"Creating manifest for task-{task_number:03d}: {goal[:60]}..."
        )

        # Build prompt for Claude
        prompt = self._build_manifest_prompt(goal, task_number)

        # Generate manifest using Claude
        self.logger.debug("Calling Claude to generate manifest...")
        response = self.claude.generate(prompt)

        if not response.success:
            self.logger.error(f"Claude generation failed: {response.error}")
            return {
                "success": False,
                "error": response.error,
                "manifest_path": None,
                "manifest_data": None,
            }

        # Parse response as JSON manifest
        # Claude may wrap JSON in markdown code fences, so extract it
        try:
            json_text = self._extract_json_from_response(response.result)
            manifest_data = json.loads(json_text)
            manifest_path = f"manifests/task-{task_number:03d}.manifest.json"

            self.logger.info(f"Successfully created manifest: {manifest_path}")
            return {
                "success": True,
                "manifest_path": manifest_path,
                "manifest_data": manifest_data,
                "error": None,
            }
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse manifest JSON: {e}. Response preview: {response.result[:200]}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "manifest_path": None,
                "manifest_data": None,
            }

    def _extract_json_from_response(self, response: str) -> str:
        """Extract JSON from Claude response, handling markdown code fences.

        Args:
            response: Raw response from Claude

        Returns:
            Extracted JSON string
        """
        import re

        # Try to find JSON within markdown code fences
        # Pattern: ```json ... ``` or ``` ... ```
        json_block_pattern = r"```(?:json)?\s*\n(.*?)\n```"
        matches = re.findall(json_block_pattern, response, re.DOTALL)

        if matches:
            # Return the first JSON block found
            return matches[0].strip()

        # If no code fence, try to find JSON object directly
        # Look for { ... } pattern
        json_object_pattern = r"\{.*\}"
        matches = re.findall(json_object_pattern, response, re.DOTALL)

        if matches:
            # Validate each match by attempting to parse as JSON
            # Return the first valid one (prioritizing longer valid JSON)
            sorted_matches = sorted(matches, key=len, reverse=True)
            for candidate in sorted_matches:
                candidate = candidate.strip()
                # Quick sanity check: must start with '{' and end with '}'
                if not (candidate.startswith("{") and candidate.endswith("}")):
                    continue
                try:
                    # Validate it parses as JSON
                    json.loads(candidate)
                    return candidate
                except json.JSONDecodeError:
                    continue  # Try next match

        # If nothing found, return original (will likely fail JSON parsing)
        return response.strip()

    def _build_manifest_prompt(self, goal: str, task_number: int) -> str:
        """Build prompt for Claude to generate manifest.

        Args:
            goal: High-level goal description
            task_number: Task number

        Returns:
            Formatted prompt string
        """
        template_manager = get_template_manager()
        return template_manager.render(
            "manifest_creation", goal=goal, task_number=f"{task_number:03d}"
        )
