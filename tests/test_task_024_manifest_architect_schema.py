"""Behavioral tests for task-024: Update manifest architect schema.

This test file verifies that ManifestArchitect can retrieve and use the MAID schema
specification when generating manifests.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch


sys.path.insert(0, str(Path(__file__).parent.parent))

from maid_agents.agents.manifest_architect import ManifestArchitect
from maid_agents.claude.cli_wrapper import ClaudeResponse, ClaudeWrapper


class TestGetMaidSchema:
    """Tests for _get_maid_schema method."""

    def test_method_exists(self):
        """Test that _get_maid_schema method exists on ManifestArchitect."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        assert hasattr(architect, "_get_maid_schema")
        assert callable(getattr(architect, "_get_maid_schema"))

    def test_method_signature(self):
        """Test _get_maid_schema has correct signature (no arguments)."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        result = architect._get_maid_schema()

        assert isinstance(result, str)

    def test_returns_string(self):
        """Test _get_maid_schema returns a string."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        result = architect._get_maid_schema()

        assert isinstance(result, str)
        assert len(result) > 0

    @patch("subprocess.run")
    def test_calls_maid_schema_command(self, mock_run):
        """Test _get_maid_schema calls 'maid schema' command."""
        mock_run.return_value = Mock(
            returncode=0, stdout="Mock MAID schema JSON", stderr=""
        )

        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        result = architect._get_maid_schema()

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "maid" in call_args[0][0]
        assert "schema" in call_args[0][0]
        assert isinstance(result, str)

    @patch("subprocess.run")
    def test_returns_schema_from_command_output(self, mock_run):
        """Test _get_maid_schema returns output from maid schema command."""
        expected_schema = '{"version": "1", "properties": {...}}'
        mock_run.return_value = Mock(returncode=0, stdout=expected_schema, stderr="")

        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        result = architect._get_maid_schema()

        assert result == expected_schema

    @patch("subprocess.run")
    def test_handles_command_failure(self, mock_run):
        """Test _get_maid_schema handles command failure gracefully."""
        mock_run.return_value = Mock(
            returncode=1, stdout="", stderr="Command not found"
        )

        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        result = architect._get_maid_schema()

        assert isinstance(result, str)

    @patch("subprocess.run")
    def test_handles_empty_output(self, mock_run):
        """Test _get_maid_schema handles empty output."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        result = architect._get_maid_schema()

        assert isinstance(result, str)


class TestGenerateManifestWithClaude:
    """Tests for _generate_manifest_with_claude method."""

    def test_method_exists(self):
        """Test that _generate_manifest_with_claude method exists."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        assert hasattr(architect, "_generate_manifest_with_claude")
        assert callable(getattr(architect, "_generate_manifest_with_claude"))

    def test_method_signature(self):
        """Test _generate_manifest_with_claude has correct signature."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        result = architect._generate_manifest_with_claude(
            goal="Test goal", task_number=1, previous_errors=None
        )

        assert isinstance(result, ClaudeResponse)

    def test_required_parameters(self):
        """Test _generate_manifest_with_claude requires goal and task_number."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        result = architect._generate_manifest_with_claude(
            goal="Create user authentication", task_number=42
        )

        assert isinstance(result, ClaudeResponse)

    def test_optional_previous_errors_parameter(self):
        """Test _generate_manifest_with_claude accepts optional previous_errors."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        result = architect._generate_manifest_with_claude(
            goal="Create user authentication",
            task_number=42,
            previous_errors="ValidationError: Missing description field",
        )

        assert isinstance(result, ClaudeResponse)

    def test_returns_claude_response(self):
        """Test _generate_manifest_with_claude returns ClaudeResponse."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        result = architect._generate_manifest_with_claude(
            goal="Test feature", task_number=1, previous_errors=None
        )

        assert isinstance(result, ClaudeResponse)
        assert hasattr(result, "success")
        assert hasattr(result, "result")
        assert hasattr(result, "error")

    @patch.object(ManifestArchitect, "_get_maid_schema")
    def test_calls_get_maid_schema(self, mock_get_schema):
        """Test _generate_manifest_with_claude calls _get_maid_schema."""
        mock_get_schema.return_value = '{"version": "1", "properties": {...}}'

        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        result = architect._generate_manifest_with_claude(
            goal="Test feature", task_number=1, previous_errors=None
        )

        mock_get_schema.assert_called_once()
        assert isinstance(result, ClaudeResponse)

    def test_handles_valid_goal(self):
        """Test _generate_manifest_with_claude with valid goal."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        result = architect._generate_manifest_with_claude(
            goal="Add user authentication to the API", task_number=10
        )

        assert result.success is True
        assert isinstance(result.result, str)

    def test_handles_empty_goal(self):
        """Test _generate_manifest_with_claude with empty goal."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        result = architect._generate_manifest_with_claude(
            goal="", task_number=1, previous_errors=None
        )

        assert isinstance(result, ClaudeResponse)

    def test_handles_task_number_zero(self):
        """Test _generate_manifest_with_claude with task_number=0."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        result = architect._generate_manifest_with_claude(
            goal="Test task zero", task_number=0, previous_errors=None
        )

        assert isinstance(result, ClaudeResponse)

    def test_handles_large_task_number(self):
        """Test _generate_manifest_with_claude with large task_number."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        result = architect._generate_manifest_with_claude(
            goal="Test large task number", task_number=999, previous_errors=None
        )

        assert isinstance(result, ClaudeResponse)

    def test_includes_previous_errors_in_prompt(self):
        """Test _generate_manifest_with_claude includes previous_errors context."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        previous_errors = "ValidationError: Missing description field"
        result = architect._generate_manifest_with_claude(
            goal="Fix validation errors",
            task_number=5,
            previous_errors=previous_errors,
        )

        assert isinstance(result, ClaudeResponse)

    def test_handles_none_previous_errors(self):
        """Test _generate_manifest_with_claude with None previous_errors."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        result = architect._generate_manifest_with_claude(
            goal="First attempt", task_number=1, previous_errors=None
        )

        assert isinstance(result, ClaudeResponse)

    def test_handles_multiline_previous_errors(self):
        """Test _generate_manifest_with_claude with multiline previous_errors."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        previous_errors = """ValidationError: Multiple issues found:
        - Missing description field
        - Invalid taskType
        - Missing artifact descriptions"""

        result = architect._generate_manifest_with_claude(
            goal="Fix all errors", task_number=3, previous_errors=previous_errors
        )

        assert isinstance(result, ClaudeResponse)


class TestIntegrationWithCreateManifest:
    """Integration tests verifying _generate_manifest_with_claude is used by create_manifest."""

    @patch.object(ManifestArchitect, "_generate_manifest_with_claude")
    @patch.object(ManifestArchitect, "_find_created_manifest")
    def test_create_manifest_calls_generate_with_claude(self, mock_find, mock_generate):
        """Test create_manifest calls _generate_manifest_with_claude."""
        mock_generate.return_value = ClaudeResponse(
            success=True, result="Mock manifest", error=""
        )
        mock_find.return_value = {
            "success": True,
            "manifest_path": "manifests/task-001-test.manifest.json",
            "manifest_data": {"version": "1", "goal": "Test"},
        }

        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        result = architect.create_manifest(goal="Test feature", task_number=1)

        mock_generate.assert_called_once()
        call_args = mock_generate.call_args
        assert call_args.kwargs["goal"] == "Test feature"
        assert call_args.kwargs["task_number"] == 1
        assert result["success"] is True

    @patch.object(ManifestArchitect, "_generate_manifest_with_claude")
    def test_create_manifest_passes_previous_errors(self, mock_generate):
        """Test create_manifest passes previous_errors to _generate_manifest_with_claude."""
        mock_generate.return_value = ClaudeResponse(
            success=False, result="", error="Test error"
        )

        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        previous_errors = "ValidationError: Test"
        architect.create_manifest(
            goal="Fix errors", task_number=2, previous_errors=previous_errors
        )

        mock_generate.assert_called_once()
        call_args = mock_generate.call_args
        assert call_args.kwargs["previous_errors"] == previous_errors

    @patch.object(ManifestArchitect, "_generate_manifest_with_claude")
    def test_create_manifest_handles_generation_failure(self, mock_generate):
        """Test create_manifest handles failure from _generate_manifest_with_claude."""
        mock_generate.return_value = ClaudeResponse(
            success=False, result="", error="API error: Rate limit exceeded"
        )

        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        result = architect.create_manifest(goal="Test failure", task_number=99)

        assert result["success"] is False
        assert "error" in result
        assert result["error"] is not None
