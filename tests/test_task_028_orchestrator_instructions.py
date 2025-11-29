"""Test task-028: Orchestrator instructions parameter support.

This test verifies that orchestrator methods properly accept and pass
the instructions parameter to agents.
"""

from unittest.mock import MagicMock, patch
from maid_agents.core.orchestrator import MAIDOrchestrator, RetryMode, ErrorContextMode
from maid_agents.claude.cli_wrapper import ClaudeWrapper


class TestOrchestratorInstructions:
    """Test orchestrator instructions parameter handling."""

    def test_run_planning_loop_accepts_instructions(self):
        """Test that run_planning_loop accepts instructions parameter."""
        # Arrange
        mock_claude = MagicMock(spec=ClaudeWrapper)
        orchestrator = MAIDOrchestrator(claude=mock_claude, dry_run=True)

        # Mock the manifest architect and test designer
        orchestrator.manifest_architect = MagicMock()
        orchestrator.manifest_architect.create_manifest.return_value = {
            "success": True,
            "manifest_path": "manifests/task-001.manifest.json",
            "manifest_data": {
                "goal": "Test",
                "readonlyFiles": ["tests/test_001.py"],
            },
        }

        orchestrator.test_designer = MagicMock()
        orchestrator.test_designer.create_tests.return_value = {
            "success": True,
            "test_paths": ["tests/test_001.py"],
            "test_code": "# test code",
        }

        # Mock behavioral validation
        with patch.object(orchestrator, "_validate_behavioral_tests") as mock_validate:
            mock_validate.return_value = {"success": True}

            # Act
            result = orchestrator.run_planning_loop(
                goal="Test goal",
                max_iterations=10,
                instructions="Use dependency injection",
            )

        # Assert
        assert result["success"] is True
        orchestrator.manifest_architect.create_manifest.assert_called_once()
        call_kwargs = orchestrator.manifest_architect.create_manifest.call_args.kwargs
        assert "instructions" in call_kwargs
        assert call_kwargs["instructions"] == "Use dependency injection"

    def test_run_planning_loop_works_without_instructions(self):
        """Test that run_planning_loop works with empty instructions (backward compatibility)."""
        # Arrange
        mock_claude = MagicMock(spec=ClaudeWrapper)
        orchestrator = MAIDOrchestrator(claude=mock_claude, dry_run=True)

        orchestrator.manifest_architect = MagicMock()
        orchestrator.manifest_architect.create_manifest.return_value = {
            "success": True,
            "manifest_path": "manifests/task-001.manifest.json",
            "manifest_data": {
                "goal": "Test",
                "readonlyFiles": ["tests/test_001.py"],
            },
        }

        orchestrator.test_designer = MagicMock()
        orchestrator.test_designer.create_tests.return_value = {
            "success": True,
            "test_paths": ["tests/test_001.py"],
            "test_code": "# test code",
        }

        with patch.object(orchestrator, "_validate_behavioral_tests") as mock_validate:
            mock_validate.return_value = {"success": True}

            # Act - call without instructions parameter
            result = orchestrator.run_planning_loop(goal="Test goal", max_iterations=10)

        # Assert
        assert result["success"] is True
        orchestrator.manifest_architect.create_manifest.assert_called_once()
        call_kwargs = orchestrator.manifest_architect.create_manifest.call_args.kwargs
        assert "instructions" in call_kwargs
        assert call_kwargs["instructions"] == ""

    def test_run_implementation_loop_accepts_instructions(self):
        """Test that run_implementation_loop accepts instructions parameter."""
        # Arrange
        mock_claude = MagicMock(spec=ClaudeWrapper)
        orchestrator = MAIDOrchestrator(claude=mock_claude, dry_run=True)

        # Mock _load_manifest
        with patch.object(orchestrator, "_load_manifest") as mock_load:
            mock_load.return_value = {
                "goal": "Test",
                "creatableFiles": [],
                "editableFiles": ["test.py"],
            }

            # Mock validation runner
            orchestrator.validation_runner = MagicMock()
            orchestrator.validation_runner.run_behavioral_tests.return_value = (
                MagicMock(success=True)
            )
            orchestrator.validation_runner.validate_manifest.return_value = MagicMock(
                success=True
            )

            # Act
            result = orchestrator.run_implementation_loop(
                manifest_path="manifests/task-001.manifest.json",
                max_iterations=1,
                retry_mode=RetryMode.DISABLED,
                error_context_mode=ErrorContextMode.INCREMENTAL,
                instructions="Follow existing patterns",
            )

        # Assert - implementation loop should succeed
        # The developer agent would be called with instructions
        assert "iterations" in result

    def test_run_refactoring_loop_accepts_instructions(self):
        """Test that run_refactoring_loop accepts instructions parameter."""
        # Arrange
        mock_claude = MagicMock(spec=ClaudeWrapper)
        orchestrator = MAIDOrchestrator(claude=mock_claude, dry_run=True)

        # Mock _load_manifest
        with patch.object(orchestrator, "_load_manifest") as mock_load:
            mock_load.return_value = {
                "goal": "Test",
                "creatableFiles": [],
                "editableFiles": ["test.py"],
                "readonlyFiles": ["tests/test.py"],
            }

            # Mock refactorer
            orchestrator.refactorer = MagicMock()
            orchestrator.refactorer.refactor.return_value = {
                "success": True,
                "improvements": ["Better code"],
                "files_written": ["test.py"],
            }

            # Mock validation runner
            orchestrator.validation_runner = MagicMock()
            orchestrator.validation_runner.validate_manifest.return_value = MagicMock(
                success=True
            )
            orchestrator.validation_runner.run_behavioral_tests.return_value = (
                MagicMock(success=True)
            )

            # Act
            result = orchestrator.run_refactoring_loop(
                manifest_path="manifests/task-001.manifest.json",
                max_iterations=1,
                retry_mode=RetryMode.DISABLED,
                error_context_mode=ErrorContextMode.INCREMENTAL,
                instructions="Focus on readability",
            )

        # Assert
        assert result["success"] is True
        orchestrator.refactorer.refactor.assert_called_once()
        call_kwargs = orchestrator.refactorer.refactor.call_args.kwargs
        assert "instructions" in call_kwargs
        assert call_kwargs["instructions"] == "Focus on readability"

    def test_run_refinement_loop_accepts_instructions(self):
        """Test that run_refinement_loop accepts instructions parameter."""
        # Arrange
        mock_claude = MagicMock(spec=ClaudeWrapper)
        orchestrator = MAIDOrchestrator(claude=mock_claude, dry_run=True)

        # Mock refiner
        orchestrator.refiner = MagicMock()
        orchestrator.refiner.refine.return_value = {
            "success": True,
            "manifest_data": {"goal": "Test"},
            "test_code": {"tests/test.py": "# test"},
            "improvements": ["Better tests"],
        }

        # Mock validation runner
        orchestrator.validation_runner = MagicMock()
        orchestrator.validation_runner.validate_manifest.return_value = MagicMock(
            success=True
        )

        # Mock behavioral validation
        with patch.object(orchestrator, "_validate_behavioral_tests") as mock_validate:
            mock_validate.return_value = {"success": True}

            # Act
            result = orchestrator.run_refinement_loop(
                manifest_path="manifests/task-001.manifest.json",
                refinement_goal="Improve coverage",
                max_iterations=1,
                instructions="Add edge case tests",
            )

        # Assert
        assert result["success"] is True
        orchestrator.refiner.refine.assert_called_once()
        call_kwargs = orchestrator.refiner.refine.call_args.kwargs
        assert "instructions" in call_kwargs
        assert call_kwargs["instructions"] == "Add edge case tests"
