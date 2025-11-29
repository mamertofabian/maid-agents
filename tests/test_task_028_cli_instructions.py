"""Test task-028: CLI --instructions argument support.

This test verifies that the --instructions argument is properly accepted
by all relevant CLI commands (plan, implement, refactor, refine).
"""

from unittest.mock import patch, MagicMock
from maid_agents.cli.main import main


class TestCLIInstructionsArgument:
    """Test CLI --instructions argument handling."""

    @patch("maid_agents.cli.main.MAIDOrchestrator")
    @patch("maid_agents.cli.main.ClaudeWrapper")
    def test_plan_accepts_instructions_argument(self, mock_claude, mock_orch):
        """Test that plan command accepts --instructions argument."""
        # Arrange
        mock_orch_instance = MagicMock()
        mock_orch.return_value = mock_orch_instance
        mock_orch_instance.run_planning_loop.return_value = {
            "success": True,
            "manifest_path": "manifests/task-001.manifest.json",
            "test_paths": ["tests/test_task_001.py"],
            "iterations": 1,
        }

        # Act
        with patch(
            "sys.argv",
            ["ccmaid", "plan", "Test goal", "--instructions", "Use pattern X"],
        ):
            try:
                main()
            except SystemExit as e:
                assert e.code == 0

        # Assert - verify run_planning_loop was called with instructions
        mock_orch_instance.run_planning_loop.assert_called_once()
        call_kwargs = mock_orch_instance.run_planning_loop.call_args.kwargs
        assert "instructions" in call_kwargs
        assert call_kwargs["instructions"] == "Use pattern X"

    @patch("maid_agents.cli.main.MAIDOrchestrator")
    @patch("maid_agents.cli.main.ClaudeWrapper")
    def test_plan_works_without_instructions(self, mock_claude, mock_orch):
        """Test that plan command works without --instructions (backward compatibility)."""
        # Arrange
        mock_orch_instance = MagicMock()
        mock_orch.return_value = mock_orch_instance
        mock_orch_instance.run_planning_loop.return_value = {
            "success": True,
            "manifest_path": "manifests/task-001.manifest.json",
            "test_paths": ["tests/test_task_001.py"],
            "iterations": 1,
        }

        # Act
        with patch("sys.argv", ["ccmaid", "plan", "Test goal"]):
            try:
                main()
            except SystemExit as e:
                assert e.code == 0

        # Assert - verify run_planning_loop was called with empty instructions
        mock_orch_instance.run_planning_loop.assert_called_once()
        call_kwargs = mock_orch_instance.run_planning_loop.call_args.kwargs
        assert "instructions" in call_kwargs
        assert call_kwargs["instructions"] == ""

    @patch("maid_agents.cli.main.MAIDOrchestrator")
    @patch("maid_agents.cli.main.ClaudeWrapper")
    @patch("maid_agents.cli.main.Path")
    def test_implement_accepts_instructions_argument(
        self, mock_path, mock_claude, mock_orch
    ):
        """Test that implement command accepts --instructions argument."""
        # Arrange
        mock_path_instance = MagicMock()
        mock_path.return_value = mock_path_instance
        mock_path_instance.exists.return_value = True

        mock_orch_instance = MagicMock()
        mock_orch.return_value = mock_orch_instance
        mock_orch_instance.run_implementation_loop.return_value = {
            "success": True,
            "iterations": 1,
            "files_modified": ["test.py"],
        }

        # Act
        with patch(
            "sys.argv",
            [
                "ccmaid",
                "implement",
                "manifests/task-001.manifest.json",
                "--instructions",
                "Follow pattern Y",
            ],
        ):
            try:
                main()
            except SystemExit as e:
                assert e.code == 0

        # Assert
        mock_orch_instance.run_implementation_loop.assert_called_once()
        call_kwargs = mock_orch_instance.run_implementation_loop.call_args.kwargs
        assert "instructions" in call_kwargs
        assert call_kwargs["instructions"] == "Follow pattern Y"

    @patch("maid_agents.cli.main.MAIDOrchestrator")
    @patch("maid_agents.cli.main.ClaudeWrapper")
    @patch("maid_agents.cli.main.Path")
    def test_refactor_accepts_instructions_argument(
        self, mock_path, mock_claude, mock_orch
    ):
        """Test that refactor command accepts --instructions argument."""
        # Arrange
        mock_path_instance = MagicMock()
        mock_path.return_value = mock_path_instance
        mock_path_instance.exists.return_value = True

        mock_orch_instance = MagicMock()
        mock_orch.return_value = mock_orch_instance
        mock_orch_instance.run_refactoring_loop.return_value = {
            "success": True,
            "iterations": 1,
            "improvements": ["Improved readability"],
            "files_written": ["test.py"],
        }

        # Act
        with patch(
            "sys.argv",
            [
                "ccmaid",
                "refactor",
                "manifests/task-001.manifest.json",
                "--instructions",
                "Focus on performance",
            ],
        ):
            try:
                main()
            except SystemExit as e:
                assert e.code == 0

        # Assert
        mock_orch_instance.run_refactoring_loop.assert_called_once()
        call_kwargs = mock_orch_instance.run_refactoring_loop.call_args.kwargs
        assert "instructions" in call_kwargs
        assert call_kwargs["instructions"] == "Focus on performance"

    @patch("maid_agents.cli.main.MAIDOrchestrator")
    @patch("maid_agents.cli.main.ClaudeWrapper")
    @patch("maid_agents.cli.main.Path")
    def test_refine_accepts_instructions_argument(
        self, mock_path, mock_claude, mock_orch
    ):
        """Test that refine command accepts --instructions argument."""
        # Arrange
        mock_path_instance = MagicMock()
        mock_path.return_value = mock_path_instance
        mock_path_instance.exists.return_value = True

        mock_orch_instance = MagicMock()
        mock_orch.return_value = mock_orch_instance
        mock_orch_instance.run_refinement_loop.return_value = {
            "success": True,
            "iterations": 1,
            "improvements": ["Better coverage"],
        }

        # Act
        with patch(
            "sys.argv",
            [
                "ccmaid",
                "refine",
                "manifests/task-001.manifest.json",
                "--goal",
                "Improve tests",
                "--instructions",
                "Add edge cases",
            ],
        ):
            try:
                main()
            except SystemExit as e:
                assert e.code == 0

        # Assert
        mock_orch_instance.run_refinement_loop.assert_called_once()
        call_kwargs = mock_orch_instance.run_refinement_loop.call_args.kwargs
        assert "instructions" in call_kwargs
        assert call_kwargs["instructions"] == "Add edge cases"
