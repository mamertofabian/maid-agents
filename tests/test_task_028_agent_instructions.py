"""Test task-028: Agent instructions parameter support.

This test verifies that all agents properly accept the instructions
parameter and pass it to their prompt generation methods.
"""

from unittest.mock import MagicMock, patch, mock_open
from maid_agents.agents.manifest_architect import ManifestArchitect
from maid_agents.agents.developer import Developer
from maid_agents.agents.refactorer import Refactorer
from maid_agents.agents.refiner import Refiner
from maid_agents.claude.cli_wrapper import ClaudeWrapper


class TestAgentInstructions:
    """Test agent instructions parameter handling."""

    def test_manifest_architect_accepts_instructions(self):
        """Test that ManifestArchitect.create_manifest accepts instructions parameter."""
        # Arrange
        mock_claude = MagicMock(spec=ClaudeWrapper)
        mock_claude.mock_mode = True
        mock_claude.model = "test-model"
        mock_claude.timeout = 300
        mock_claude.temperature = 0.0
        architect = ManifestArchitect(claude=mock_claude, dry_run=True)

        # Mock the Claude response
        mock_claude.generate.return_value = MagicMock(
            success=True, result='{"goal": "test"}', error=None
        )

        # Mock file finding
        with patch.object(architect, "_find_created_manifest") as mock_find:
            mock_find.return_value = {
                "success": True,
                "manifest_path": "manifests/task-001.manifest.json",
                "manifest_data": {"goal": "test"},
            }

            # Act
            result = architect.create_manifest(
                goal="Test goal",
                task_number=1,
                previous_errors=None,
                instructions="Use pattern X",
            )

        # Assert
        assert result["success"] is True
        # The method accepted instructions parameter and completed successfully

    def test_manifest_architect_works_without_instructions(self):
        """Test that ManifestArchitect works without instructions (backward compatibility)."""
        # Arrange
        mock_claude = MagicMock(spec=ClaudeWrapper)
        mock_claude.mock_mode = True
        mock_claude.model = "test-model"
        mock_claude.timeout = 300
        mock_claude.temperature = 0.0
        architect = ManifestArchitect(claude=mock_claude, dry_run=True)

        mock_claude.generate.return_value = MagicMock(
            success=True, result='{"goal": "test"}', error=None
        )

        with patch.object(architect, "_find_created_manifest") as mock_find:
            mock_find.return_value = {
                "success": True,
                "manifest_path": "manifests/task-001.manifest.json",
                "manifest_data": {"goal": "test"},
            }

            # Act - call without instructions parameter
            result = architect.create_manifest(
                goal="Test goal", task_number=1, previous_errors=None
            )

        # Assert
        assert result["success"] is True

    def test_developer_accepts_instructions(self):
        """Test that Developer.implement accepts instructions parameter."""
        # Arrange
        mock_claude = MagicMock(spec=ClaudeWrapper)
        mock_claude.mock_mode = True
        mock_claude.model = "test-model"
        mock_claude.timeout = 300
        mock_claude.temperature = 0.0
        mock_claude.bypass_permissions = False
        developer = Developer(claude=mock_claude, dry_run=True)

        # Mock manifest loading
        manifest_data = {
            "goal": "Test",
            "creatableFiles": ["test.py"],
            "editableFiles": [],
            "expectedArtifacts": {"file": "test.py", "contains": []},
        }

        # Mock file reading
        mock_file_content = "# implementation code"

        with patch("builtins.open", mock_open(read_data='{"goal": "test"}')):
            with patch.object(developer, "_load_manifest") as mock_load:
                mock_load.return_value = manifest_data

                # Mock Claude response
                mock_claude.generate.return_value = MagicMock(
                    success=True, result=mock_file_content, error=None
                )

                # Mock file reading
                with patch("builtins.open", mock_open(read_data=mock_file_content)):
                    # Act
                    result = developer.implement(
                        manifest_path="manifests/task-001.manifest.json",
                        test_errors="",
                        instructions="Follow pattern Y",
                    )

        # Assert
        assert result["success"] is True

    def test_refactorer_accepts_instructions(self):
        """Test that Refactorer.refactor accepts instructions parameter."""
        # Arrange
        mock_claude = MagicMock(spec=ClaudeWrapper)
        mock_claude.mock_mode = True
        mock_claude.model = "test-model"
        mock_claude.timeout = 300
        mock_claude.temperature = 0.0
        mock_claude.bypass_permissions = False
        refactorer = Refactorer(claude=mock_claude, dry_run=True)

        manifest_data = {
            "goal": "Test",
            "editableFiles": ["test.py"],
            "creatableFiles": [],
            "readonlyFiles": ["tests/test.py"],
        }

        with patch("builtins.open", mock_open(read_data='{"goal": "test"}')):
            with patch.object(refactorer, "_load_manifest_json") as mock_load:
                mock_load.return_value = manifest_data

                # Mock file reading
                with patch.object(refactorer, "_read_file_with_fallback") as mock_read:
                    mock_read.return_value = "# existing code"

                    # Mock Claude response
                    mock_claude.generate.return_value = MagicMock(
                        success=True, result="# refactored code", error=None
                    )

                    # Mock reading refactored files
                    with patch.object(
                        refactorer, "_read_refactored_files"
                    ) as mock_read_refactored:
                        mock_read_refactored.return_value = {"test.py": "# refactored"}

                        # Act
                        result = refactorer.refactor(
                            manifest_path="manifests/task-001.manifest.json",
                            validation_feedback="",
                            instructions="Focus on performance",
                        )

        # Assert
        assert result["success"] is True

    def test_refiner_accepts_instructions(self):
        """Test that Refiner.refine accepts instructions parameter."""
        # Arrange
        mock_claude = MagicMock(spec=ClaudeWrapper)
        mock_claude.mock_mode = True
        mock_claude.model = "test-model"
        mock_claude.timeout = 300
        mock_claude.temperature = 0.0
        refiner = Refiner(claude=mock_claude, dry_run=True)

        manifest_data = {
            "goal": "Test",
            "editableFiles": [],
            "creatableFiles": [],
            "readonlyFiles": ["tests/test.py"],
        }

        with patch("builtins.open", mock_open(read_data='{"goal": "test"}')):
            # Mock loading manifest
            with patch.object(refiner, "_load_test_files") as mock_load_tests:
                mock_load_tests.return_value = {"tests/test.py": "# test code"}

                # Mock Claude response
                mock_claude.generate.return_value = MagicMock(
                    success=True, result="## Improvements\n- Better tests", error=None
                )

                # Mock reading refined files
                with patch.object(
                    refiner, "_read_refined_manifest"
                ) as mock_read_manifest:
                    mock_read_manifest.return_value = manifest_data

                    with patch.object(
                        refiner, "_read_refined_tests"
                    ) as mock_read_tests:
                        mock_read_tests.return_value = {"tests/test.py": "# refined"}

                        # Act
                        result = refiner.refine(
                            manifest_path="manifests/task-001.manifest.json",
                            refinement_goal="Improve coverage",
                            validation_feedback="",
                            instructions="Add edge cases",
                        )

        # Assert
        assert result["success"] is True
        assert "improvements" in result
