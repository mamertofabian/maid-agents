"""Behavioral tests for task-023: Improve manifest descriptions.

This test file verifies that ManifestArchitect generates manifests with
proper description fields at both manifest level and artifact level.
"""

import json
import os
import tempfile
from unittest.mock import patch


from maid_agents.agents.manifest_architect import ManifestArchitect
from maid_agents.claude.cli_wrapper import ClaudeWrapper, ClaudeResponse


class TestManifestArchitectExists:
    """Tests for ManifestArchitect class existence."""

    def test_class_exists(self):
        """Test that ManifestArchitect exists and can be instantiated."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)
        assert architect is not None
        assert isinstance(architect, ManifestArchitect)

    def test_class_inheritance(self):
        """Test ManifestArchitect inherits from BaseAgent."""
        from maid_agents.agents.base_agent import BaseAgent

        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)
        assert isinstance(architect, BaseAgent)


class TestManifestArchitectExecute:
    """Tests for ManifestArchitect execute method."""

    def test_execute_method_exists(self):
        """Test that execute method exists and is callable."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)
        assert hasattr(architect, "execute")
        assert callable(architect.execute)

    def test_execute_returns_dict(self):
        """Test that execute returns a dictionary."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)
        result = architect.execute()
        assert isinstance(result, dict)
        assert "status" in result
        assert "agent" in result


class TestManifestArchitectInitialization:
    """Tests for ManifestArchitect initialization."""

    def test_initialization_with_claude_wrapper(self):
        """Test initialization accepts ClaudeWrapper."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)
        assert architect.claude is not None
        assert architect.claude is claude

    def test_initialization_stores_claude_instance(self):
        """Test that claude instance is stored correctly."""
        claude = ClaudeWrapper(mock_mode=True, model="test-model")
        architect = ManifestArchitect(claude=claude)
        assert architect.claude.model == "test-model"


class TestManifestArchitectCreateManifest:
    """Tests for create_manifest method."""

    def test_create_manifest_method_exists(self):
        """Test that create_manifest method exists."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)
        assert hasattr(architect, "create_manifest")
        assert callable(architect.create_manifest)

    def test_create_manifest_signature_with_previous_errors(self):
        """Test create_manifest accepts previous_errors parameter."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        with (
            patch.object(architect, "_generate_manifest_with_claude") as mock_generate,
            patch.object(architect, "_find_created_manifest") as mock_find,
        ):
            mock_generate.return_value = ClaudeResponse(
                success=True, result="test", error=""
            )
            mock_find.return_value = {
                "success": True,
                "manifest_path": "test.json",
                "manifest_data": {"goal": "test", "description": "test description"},
            }

            result = architect.create_manifest(
                goal="Test goal", task_number=1, previous_errors="Some error message"
            )
            assert isinstance(result, dict)

    def test_create_manifest_signature_with_none_previous_errors(self):
        """Test create_manifest accepts None for previous_errors."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        with (
            patch.object(architect, "_generate_manifest_with_claude") as mock_generate,
            patch.object(architect, "_find_created_manifest") as mock_find,
        ):
            mock_generate.return_value = ClaudeResponse(
                success=True, result="test", error=""
            )
            mock_find.return_value = {
                "success": True,
                "manifest_path": "test.json",
                "manifest_data": {"goal": "test", "description": "test description"},
            }

            result = architect.create_manifest(
                goal="Test goal", task_number=1, previous_errors=None
            )
            assert isinstance(result, dict)

    def test_create_manifest_returns_dict(self):
        """Test create_manifest returns a dictionary."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        with (
            patch.object(architect, "_generate_manifest_with_claude") as mock_generate,
            patch.object(architect, "_find_created_manifest") as mock_find,
        ):
            mock_generate.return_value = ClaudeResponse(
                success=True, result="test", error=""
            )
            mock_find.return_value = {
                "success": True,
                "manifest_path": "test.json",
                "manifest_data": {"goal": "test", "description": "test description"},
            }

            result = architect.create_manifest(
                goal="Test goal", task_number=1, previous_errors=None
            )
            assert isinstance(result, dict)


class TestManifestArchitectHappyPath:
    """Tests for successful manifest creation."""

    @patch("maid_agents.agents.manifest_architect.glob.glob")
    def test_create_manifest_success_with_description(self, mock_glob):
        """Test successful manifest creation includes description field."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".manifest.json", delete=False
        ) as tf:
            manifest_data = {
                "goal": "Test goal",
                "description": "Detailed description of what this manifest accomplishes",
                "taskType": "create",
                "expectedArtifacts": [],
            }
            json.dump(manifest_data, tf)
            temp_path = tf.name

        try:
            mock_glob.return_value = [temp_path]

            with patch.object(
                architect, "_generate_manifest_with_claude"
            ) as mock_generate:
                mock_generate.return_value = ClaudeResponse(
                    success=True, result="Manifest created", error=""
                )

                result = architect.create_manifest(
                    goal="Test goal", task_number=1, previous_errors=None
                )

                assert result["success"] is True
                assert result["manifest_path"] == temp_path
                assert result["manifest_data"] is not None
                assert "description" in result["manifest_data"]
                assert result["error"] is None
        finally:
            os.unlink(temp_path)

    @patch("maid_agents.agents.manifest_architect.glob.glob")
    def test_create_manifest_includes_artifact_descriptions(self, mock_glob):
        """Test that manifests include description for each artifact."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".manifest.json", delete=False
        ) as tf:
            manifest_data = {
                "goal": "Add authentication system",
                "description": "Implement JWT-based authentication with user management",
                "taskType": "create",
                "expectedArtifacts": {
                    "file": "auth.py",
                    "contains": [
                        {
                            "type": "class",
                            "name": "AuthManager",
                            "description": "Main authentication manager class",
                        },
                        {
                            "type": "function",
                            "name": "verify_token",
                            "description": "Token verification function",
                        },
                    ],
                },
            }
            json.dump(manifest_data, tf)
            temp_path = tf.name

        try:
            mock_glob.return_value = [temp_path]

            with patch.object(
                architect, "_generate_manifest_with_claude"
            ) as mock_generate:
                mock_generate.return_value = ClaudeResponse(
                    success=True, result="test", error=""
                )

                result = architect.create_manifest(
                    goal="Add authentication system",
                    task_number=1,
                    previous_errors=None,
                )

                assert result["success"] is True
                artifacts = result["manifest_data"]["expectedArtifacts"]["contains"]

                for artifact in artifacts:
                    assert "description" in artifact
                    assert isinstance(artifact["description"], str)
                    assert len(artifact["description"]) > 0
        finally:
            os.unlink(temp_path)

    @patch("maid_agents.agents.manifest_architect.glob.glob")
    def test_create_manifest_with_previous_errors_context(self, mock_glob):
        """Test create_manifest incorporates previous_errors into generation."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".manifest.json", delete=False
        ) as tf:
            manifest_data = {
                "goal": "Test goal",
                "description": "Improved description after fixing errors",
                "taskType": "create",
                "expectedArtifacts": [],
            }
            json.dump(manifest_data, tf)
            temp_path = tf.name

        try:
            mock_glob.return_value = [temp_path]

            with patch.object(
                architect, "_generate_manifest_with_claude"
            ) as mock_generate:
                mock_generate.return_value = ClaudeResponse(
                    success=True, result="test", error=""
                )

                previous_error = "Validation failed: missing description field"
                result = architect.create_manifest(
                    goal="Test goal", task_number=1, previous_errors=previous_error
                )

                assert result["success"] is True
                assert "description" in result["manifest_data"]
        finally:
            os.unlink(temp_path)


class TestManifestArchitectErrorHandling:
    """Tests for error handling in manifest creation."""

    def test_create_manifest_handles_generation_failure(self):
        """Test handling of Claude generation failure."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        with patch.object(architect, "_generate_manifest_with_claude") as mock_generate:
            mock_generate.return_value = ClaudeResponse(
                success=False, result="", error="API error"
            )

            result = architect.create_manifest(
                goal="Test goal", task_number=1, previous_errors=None
            )

            assert result["success"] is False
            assert result["error"] is not None
            assert result["manifest_path"] is None
            assert result["manifest_data"] is None

    @patch("maid_agents.agents.manifest_architect.glob.glob")
    def test_create_manifest_handles_missing_file(self, mock_glob):
        """Test handling when manifest file is not found."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        mock_glob.return_value = []

        with patch.object(architect, "_generate_manifest_with_claude") as mock_generate:
            mock_generate.return_value = ClaudeResponse(
                success=True, result="test", error=""
            )

            result = architect.create_manifest(
                goal="Test goal", task_number=1, previous_errors=None
            )

            assert result["success"] is False
            assert "No manifest file found" in result["error"]

    @patch("maid_agents.agents.manifest_architect.glob.glob")
    def test_create_manifest_handles_invalid_json(self, mock_glob):
        """Test handling of invalid JSON in manifest file."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".manifest.json", delete=False
        ) as tf:
            tf.write("{ invalid json }")
            temp_path = tf.name

        try:
            mock_glob.return_value = [temp_path]

            with patch.object(
                architect, "_generate_manifest_with_claude"
            ) as mock_generate:
                mock_generate.return_value = ClaudeResponse(
                    success=True, result="test", error=""
                )

                result = architect.create_manifest(
                    goal="Test goal", task_number=1, previous_errors=None
                )

                assert result["success"] is False
                assert "Invalid JSON" in result["error"]
        finally:
            os.unlink(temp_path)


class TestManifestArchitectEdgeCases:
    """Tests for edge cases in manifest creation."""

    @patch("maid_agents.agents.manifest_architect.glob.glob")
    def test_create_manifest_with_empty_goal(self, mock_glob):
        """Test manifest creation with empty goal string."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".manifest.json", delete=False
        ) as tf:
            manifest_data = {
                "goal": "",
                "description": "Manifest with empty goal",
                "taskType": "create",
                "expectedArtifacts": [],
            }
            json.dump(manifest_data, tf)
            temp_path = tf.name

        try:
            mock_glob.return_value = [temp_path]

            with patch.object(
                architect, "_generate_manifest_with_claude"
            ) as mock_generate:
                mock_generate.return_value = ClaudeResponse(
                    success=True, result="test", error=""
                )

                result = architect.create_manifest(
                    goal="", task_number=1, previous_errors=None
                )

                assert isinstance(result, dict)
                assert "success" in result
        finally:
            os.unlink(temp_path)

    @patch("maid_agents.agents.manifest_architect.glob.glob")
    def test_create_manifest_with_very_long_goal(self, mock_glob):
        """Test manifest creation with very long goal string."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        long_goal = "A" * 1000

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".manifest.json", delete=False
        ) as tf:
            manifest_data = {
                "goal": long_goal,
                "description": "Manifest with long goal",
                "taskType": "create",
                "expectedArtifacts": [],
            }
            json.dump(manifest_data, tf)
            temp_path = tf.name

        try:
            mock_glob.return_value = [temp_path]

            with patch.object(
                architect, "_generate_manifest_with_claude"
            ) as mock_generate:
                mock_generate.return_value = ClaudeResponse(
                    success=True, result="test", error=""
                )

                result = architect.create_manifest(
                    goal=long_goal, task_number=1, previous_errors=None
                )

                assert isinstance(result, dict)
                assert "success" in result
        finally:
            os.unlink(temp_path)

    @patch("maid_agents.agents.manifest_architect.glob.glob")
    def test_create_manifest_with_special_characters_in_goal(self, mock_glob):
        """Test manifest creation with special characters in goal."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        special_goal = "Test @#$%^&*() goal with 特殊字符"

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".manifest.json", delete=False
        ) as tf:
            manifest_data = {
                "goal": special_goal,
                "description": "Manifest with special characters",
                "taskType": "create",
                "expectedArtifacts": [],
            }
            json.dump(manifest_data, tf)
            temp_path = tf.name

        try:
            mock_glob.return_value = [temp_path]

            with patch.object(
                architect, "_generate_manifest_with_claude"
            ) as mock_generate:
                mock_generate.return_value = ClaudeResponse(
                    success=True, result="test", error=""
                )

                result = architect.create_manifest(
                    goal=special_goal, task_number=1, previous_errors=None
                )

                assert isinstance(result, dict)
                assert "success" in result
        finally:
            os.unlink(temp_path)

    @patch("maid_agents.agents.manifest_architect.glob.glob")
    def test_create_manifest_with_empty_previous_errors(self, mock_glob):
        """Test create_manifest with empty string for previous_errors."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".manifest.json", delete=False
        ) as tf:
            manifest_data = {
                "goal": "Test",
                "description": "Test description",
                "taskType": "create",
                "expectedArtifacts": [],
            }
            json.dump(manifest_data, tf)
            temp_path = tf.name

        try:
            mock_glob.return_value = [temp_path]

            with patch.object(
                architect, "_generate_manifest_with_claude"
            ) as mock_generate:
                mock_generate.return_value = ClaudeResponse(
                    success=True, result="test", error=""
                )

                result = architect.create_manifest(
                    goal="Test", task_number=1, previous_errors=""
                )

                assert isinstance(result, dict)
                assert "success" in result
        finally:
            os.unlink(temp_path)

    @patch("maid_agents.agents.manifest_architect.glob.glob")
    def test_create_manifest_handles_multiple_matching_files(self, mock_glob):
        """Test that most recent file is used when multiple matches exist."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".manifest.json", delete=False
        ) as tf1:
            json.dump({"goal": "old", "description": "old description"}, tf1)
            old_path = tf1.name

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".manifest.json", delete=False
        ) as tf2:
            json.dump({"goal": "new", "description": "new description"}, tf2)
            new_path = tf2.name

        try:
            mock_glob.return_value = [new_path, old_path]

            with (
                patch.object(
                    architect, "_generate_manifest_with_claude"
                ) as mock_generate,
                patch("os.path.getmtime") as mock_mtime,
            ):
                mock_generate.return_value = ClaudeResponse(
                    success=True, result="test", error=""
                )
                mock_mtime.side_effect = lambda p: 2.0 if p == new_path else 1.0

                result = architect.create_manifest(
                    goal="Test", task_number=1, previous_errors=None
                )

                assert result["success"] is True
                assert result["manifest_data"]["goal"] == "new"
        finally:
            os.unlink(old_path)
            os.unlink(new_path)


class TestManifestArchitectSlugGeneration:
    """Tests for slug generation methods."""

    def test_generate_slug_method_exists(self):
        """Test that _generate_slug method exists."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)
        assert hasattr(architect, "_generate_slug")
        assert callable(architect._generate_slug)

    def test_generate_slug_basic(self):
        """Test slug generation with simple text."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        slug = architect._generate_slug(goal="Add user authentication")
        assert slug == "add-user-authentication"
        assert isinstance(slug, str)

    def test_generate_slug_removes_special_chars(self):
        """Test slug removes special characters."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        slug = architect._generate_slug(goal="Fix bug #123 @urgent!")
        assert "#" not in slug
        assert "@" not in slug
        assert "!" not in slug

    def test_generate_slug_handles_long_text(self):
        """Test slug truncation for long text."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        long_goal = "This is a very long goal description that should be truncated"
        slug = architect._generate_slug(goal=long_goal)

        assert len(slug) <= 50
        assert isinstance(slug, str)

    def test_generate_slug_normalizes_whitespace(self):
        """Test slug normalizes multiple spaces and hyphens."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        slug = architect._generate_slug(goal="Fix    multiple   spaces")
        assert "  " not in slug
        assert "--" not in slug


class TestManifestArchitectResponseBuilding:
    """Tests for response building methods."""

    def test_build_error_response_structure(self):
        """Test error response has correct structure."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        response = architect._build_error_response(error="Test error")

        assert response["success"] is False
        assert response["error"] == "Test error"
        assert response["manifest_path"] is None
        assert response["manifest_data"] is None

    def test_build_success_response_structure(self):
        """Test success response has correct structure."""
        claude = ClaudeWrapper(mock_mode=True)
        architect = ManifestArchitect(claude=claude)

        test_data = {"goal": "test", "description": "test description"}
        response = architect._build_success_response(
            manifest_path="test.json", manifest_data=test_data
        )

        assert response["success"] is True
        assert response["manifest_path"] == "test.json"
        assert response["manifest_data"] == test_data
        assert response["error"] is None
