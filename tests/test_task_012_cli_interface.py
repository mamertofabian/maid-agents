"""Behavioral tests for Task-012: CLI Interface."""

import sys
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from maid_agents.cli.main import main


def test_main_function_exists():
    """Test main function can be imported."""
    assert callable(main)


def test_main_function_with_help():
    """Test calling main() with --help argument."""
    with patch("sys.argv", ["ccmaid", "--help"]):
        try:
            main()
        except SystemExit as e:
            # --help causes sys.exit(0)
            assert e.code == 0


def test_cli_help_command():
    """Test CLI --help works."""
    result = subprocess.run(
        ["python", "-m", "maid_agents.cli.main", "--help"],
        capture_output=True,
        text=True,
        cwd="maid_agents",
    )
    # Should show help text without error
    assert result.returncode == 0 or "ccmaid" in result.stdout.lower()


def test_cli_version_command():
    """Test CLI --version works."""
    result = subprocess.run(
        ["python", "-m", "maid_agents.cli.main", "--version"],
        capture_output=True,
        text=True,
        cwd="maid_agents",
    )
    # Should show version or exit cleanly
    assert result.returncode == 0 or "version" in result.stdout.lower()


# ============================================================================
# Subcommand Tests
# ============================================================================


def test_no_subcommand_shows_help():
    """Test that running without subcommand shows help and exits."""
    with patch("sys.argv", ["ccmaid"]):
        try:
            main()
        except SystemExit as e:
            assert e.code == 1


def test_run_command_with_mock():
    """Test run command with --mock flag."""
    from maid_agents.core.orchestrator import RetryMode, ErrorContextMode

    mock_orchestrator = MagicMock()
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.message = "Success"
    mock_result.manifest_path = "manifests/test.manifest.json"
    mock_orchestrator.run_full_workflow.return_value = mock_result

    with patch("sys.argv", ["ccmaid", "--mock", "run", "test goal"]):
        with patch(
            "maid_agents.cli.main.MAIDOrchestrator", return_value=mock_orchestrator
        ):
            try:
                main()
            except SystemExit as e:
                assert e.code == 0
                mock_orchestrator.run_full_workflow.assert_called_once_with(
                    goal="test goal",
                    max_iterations_planning=10,
                    max_iterations_implementation=20,
                    retry_mode=RetryMode.DISABLED,
                    error_context_mode=ErrorContextMode.INCREMENTAL,
                    instructions="",
                )


def test_plan_command_with_mock():
    """Test plan command with --mock flag."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run_planning_loop.return_value = {
        "success": True,
        "iterations": 3,
        "manifest_path": "manifests/test.manifest.json",
        "test_paths": ["tests/test_example.py"],
    }

    with patch("sys.argv", ["ccmaid", "--mock", "plan", "test goal"]):
        with patch(
            "maid_agents.cli.main.MAIDOrchestrator", return_value=mock_orchestrator
        ):
            try:
                main()
            except SystemExit as e:
                assert e.code == 0
                mock_orchestrator.run_planning_loop.assert_called_once()


def test_plan_command_with_max_iterations():
    """Test plan command with custom max iterations."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run_planning_loop.return_value = {
        "success": True,
        "iterations": 5,
        "manifest_path": "manifests/test.manifest.json",
        "test_paths": ["tests/test_example.py"],
    }

    with patch(
        "sys.argv", ["ccmaid", "--mock", "plan", "test goal", "--max-iterations", "15"]
    ):
        with patch(
            "maid_agents.cli.main.MAIDOrchestrator", return_value=mock_orchestrator
        ):
            try:
                main()
            except SystemExit as e:
                assert e.code == 0
                call_args = mock_orchestrator.run_planning_loop.call_args
                assert call_args.kwargs["max_iterations"] == 15


def test_implement_command_with_mock():
    """Test implement command with --mock flag."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run_implementation_loop.return_value = {
        "success": True,
        "iterations": 2,
        "files_modified": ["main.py"],
    }

    with tempfile.NamedTemporaryFile(suffix=".manifest.json", delete=False) as tmp:
        tmp.write(b'{"goal": "test"}')
        tmp.flush()
        manifest_path = tmp.name

    try:
        with patch("sys.argv", ["ccmaid", "--mock", "implement", manifest_path]):
            with patch(
                "maid_agents.cli.main.MAIDOrchestrator", return_value=mock_orchestrator
            ):
                try:
                    main()
                except SystemExit as e:
                    assert e.code == 0
                    mock_orchestrator.run_implementation_loop.assert_called_once()
    finally:
        Path(manifest_path).unlink(missing_ok=True)


def test_implement_with_missing_manifest():
    """Test implement command with non-existent manifest."""
    with patch("sys.argv", ["ccmaid", "implement", "nonexistent.manifest.json"]):
        try:
            main()
        except SystemExit as e:
            assert e.code == 1


def test_refactor_command_with_mock():
    """Test refactor command with --mock flag."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run_refactoring_loop.return_value = {
        "success": True,
        "iterations": 1,
        "improvements": ["Improved readability", "Added type hints"],
        "files_written": ["main.py"],
    }

    with tempfile.NamedTemporaryFile(suffix=".manifest.json", delete=False) as tmp:
        tmp.write(b'{"goal": "test"}')
        tmp.flush()
        manifest_path = tmp.name

    try:
        with patch("sys.argv", ["ccmaid", "--mock", "refactor", manifest_path]):
            with patch(
                "maid_agents.cli.main.MAIDOrchestrator", return_value=mock_orchestrator
            ):
                try:
                    main()
                except SystemExit as e:
                    assert e.code == 0
                    mock_orchestrator.run_refactoring_loop.assert_called_once()
    finally:
        Path(manifest_path).unlink(missing_ok=True)


def test_refactor_with_missing_manifest():
    """Test refactor command with non-existent manifest."""
    with patch("sys.argv", ["ccmaid", "refactor", "nonexistent.manifest.json"]):
        try:
            main()
        except SystemExit as e:
            assert e.code == 1


def test_refine_command_with_mock():
    """Test refine command with --mock flag."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run_refinement_loop.return_value = {
        "success": True,
        "iterations": 2,
        "improvements": ["Better test coverage", "Clearer manifest"],
    }

    with tempfile.NamedTemporaryFile(suffix=".manifest.json", delete=False) as tmp:
        tmp.write(b'{"goal": "test"}')
        tmp.flush()
        manifest_path = tmp.name

    try:
        with patch(
            "sys.argv",
            ["ccmaid", "--mock", "refine", manifest_path, "--goal", "improve tests"],
        ):
            with patch(
                "maid_agents.cli.main.MAIDOrchestrator", return_value=mock_orchestrator
            ):
                try:
                    main()
                except SystemExit as e:
                    assert e.code == 0
                    mock_orchestrator.run_refinement_loop.assert_called_once()
    finally:
        Path(manifest_path).unlink(missing_ok=True)


def test_refine_without_goal_flag():
    """Test refine command without required --goal flag."""
    with tempfile.NamedTemporaryFile(suffix=".manifest.json", delete=False) as tmp:
        tmp.write(b'{"goal": "test"}')
        tmp.flush()
        manifest_path = tmp.name

    try:
        with patch("sys.argv", ["ccmaid", "refine", manifest_path]):
            try:
                main()
            except SystemExit as e:
                # argparse error for missing required argument
                assert e.code == 2
    finally:
        Path(manifest_path).unlink(missing_ok=True)


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_plan_command_failure():
    """Test plan command when orchestrator fails."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run_planning_loop.return_value = {
        "success": False,
        "iterations": 10,
        "error": "Validation failed",
    }

    with patch("sys.argv", ["ccmaid", "--mock", "plan", "test goal"]):
        with patch(
            "maid_agents.cli.main.MAIDOrchestrator", return_value=mock_orchestrator
        ):
            try:
                main()
            except SystemExit as e:
                assert e.code == 1


def test_implement_command_failure():
    """Test implement command when implementation fails."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run_implementation_loop.return_value = {
        "success": False,
        "iterations": 20,
        "error": "Tests still failing",
    }

    with tempfile.NamedTemporaryFile(suffix=".manifest.json", delete=False) as tmp:
        tmp.write(b'{"goal": "test"}')
        tmp.flush()
        manifest_path = tmp.name

    try:
        with patch("sys.argv", ["ccmaid", "--mock", "implement", manifest_path]):
            with patch(
                "maid_agents.cli.main.MAIDOrchestrator", return_value=mock_orchestrator
            ):
                try:
                    main()
                except SystemExit as e:
                    assert e.code == 1
    finally:
        Path(manifest_path).unlink(missing_ok=True)


def test_refactor_command_failure():
    """Test refactor command when refactoring fails."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run_refactoring_loop.return_value = {
        "success": False,
        "iterations": 1,
        "error": "Could not improve code",
    }

    with tempfile.NamedTemporaryFile(suffix=".manifest.json", delete=False) as tmp:
        tmp.write(b'{"goal": "test"}')
        tmp.flush()
        manifest_path = tmp.name

    try:
        with patch("sys.argv", ["ccmaid", "--mock", "refactor", manifest_path]):
            with patch(
                "maid_agents.cli.main.MAIDOrchestrator", return_value=mock_orchestrator
            ):
                try:
                    main()
                except SystemExit as e:
                    assert e.code == 1
    finally:
        Path(manifest_path).unlink(missing_ok=True)


def test_run_command_failure():
    """Test run command when workflow fails."""
    mock_orchestrator = MagicMock()
    mock_result = MagicMock()
    mock_result.success = False
    mock_result.message = "Workflow failed"
    mock_orchestrator.run_full_workflow.return_value = mock_result

    with patch("sys.argv", ["ccmaid", "--mock", "run", "test goal"]):
        with patch(
            "maid_agents.cli.main.MAIDOrchestrator", return_value=mock_orchestrator
        ):
            try:
                main()
            except SystemExit as e:
                assert e.code == 1


def test_config_example_flag():
    """Test --config-example flag displays config."""
    with patch("sys.argv", ["ccmaid", "--config-example"]):
        try:
            main()
        except SystemExit as e:
            # Should exit successfully after showing example
            assert e.code == 0
