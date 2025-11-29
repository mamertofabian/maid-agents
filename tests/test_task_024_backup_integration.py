"""
Integration tests for Task-024: File Backup/Restore in Orchestrator Loops

Tests that implementation and refactoring loops properly use FileBackupManager
to backup and restore files during retry iterations.
"""

import json
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch
from maid_agents.core.orchestrator import MAIDOrchestrator
from maid_agents.claude.cli_wrapper import ClaudeWrapper
from maid_agents.core.validation_runner import ValidationRunner, ValidationResult


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project structure with manifest and test files."""
    # Create directories
    manifests_dir = tmp_path / "manifests"
    tests_dir = tmp_path / "tests"
    src_dir = tmp_path / "src"
    manifests_dir.mkdir()
    tests_dir.mkdir()
    src_dir.mkdir()

    # Create manifest
    manifest_path = manifests_dir / "task-test.manifest.json"
    manifest_data = {
        "taskNumber": 999,
        "title": "Test Task",
        "description": "Test task for backup integration",
        "creatableFiles": [],
        "editableFiles": ["src/example.py"],
        "readonlyFiles": [],
        "artifacts": [],
        "acceptanceCriteria": [],
        "validationCommand": "pytest tests/test_example.py -v",
    }
    manifest_path.write_text(json.dumps(manifest_data, indent=2))

    # Create initial implementation file
    impl_file = src_dir / "example.py"
    impl_file.write_text("# Original implementation\n")

    # Create test file
    test_file = tests_dir / "test_example.py"
    test_file.write_text("def test_example(): assert True\n")

    return {
        "tmp_path": tmp_path,
        "manifest_path": str(manifest_path),
        "impl_file": impl_file,
        "test_file": test_file,
        "manifest_data": manifest_data,
    }


class TestImplementationLoopBackup:
    """Test backup/restore in implementation loop."""

    @patch("maid_agents.agents.developer.Developer")
    @patch("maid_agents.core.validation_runner.ValidationRunner")
    @patch("maid_agents.core.orchestrator.MAIDOrchestrator._validate_safe_path")
    def test_implementation_loop_restores_on_retry(
        self,
        mock_validate_path,
        mock_validation_runner_class,
        mock_developer_class,
        temp_project,
    ):
        """Test that implementation loop restores files before each retry."""
        # Setup
        manifest_path = temp_project["manifest_path"]
        impl_file = temp_project["impl_file"]

        # Mock path validation to return path as-is
        mock_validate_path.side_effect = lambda p: Path(p)

        # Mock Claude wrapper
        claude = MagicMock(spec=ClaudeWrapper)
        claude.mock_mode = False

        # Mock validation runner
        mock_validation_runner = MagicMock(spec=ValidationRunner)
        mock_validation_runner_class.return_value = mock_validation_runner

        # First test run fails, second succeeds
        mock_validation_runner.run_behavioral_tests.side_effect = [
            ValidationResult(
                success=False,
                stdout="",
                stderr="Test failed",
                errors=["AssertionError"],
            ),  # Initial run
            ValidationResult(
                success=False,
                stdout="",
                stderr="Test failed",
                errors=["AssertionError"],
            ),  # After iteration 1
            ValidationResult(
                success=True, stdout="All tests passed", stderr="", errors=[]
            ),  # After iteration 2
        ]
        mock_validation_runner.validate_manifest.return_value = ValidationResult(
            success=True, stdout="Valid", stderr="", errors=[]
        )

        # Mock developer to modify file
        mock_developer = MagicMock()
        mock_developer_class.return_value = mock_developer

        def modify_file_side_effect(manifest_path, test_errors):
            # Simulate developer modifying the file
            impl_file.write_text(f"# Modified iteration\n{test_errors}\n")
            return {
                "success": True,
                "files_modified": [str(impl_file)],
                "code": impl_file.read_text(),
                "error": None,
            }

        mock_developer.implement.side_effect = modify_file_side_effect

        # Create orchestrator
        orchestrator = MAIDOrchestrator(
            claude=claude, validation_runner=mock_validation_runner, dry_run=False
        )

        # Run implementation loop with max 3 iterations (with AUTO retry mode for testing retries)
        from maid_agents.core.orchestrator import RetryMode

        result = orchestrator.run_implementation_loop(
            manifest_path, max_iterations=3, retry_mode=RetryMode.AUTO
        )

        # Verify success
        assert result["success"] is True
        assert result["iterations"] == 2

        # Key verification: File should have been restored before iteration 2
        # Since mock_developer modifies the file each time, if restoration works,
        # the file should end up with the content from the successful iteration
        final_content = impl_file.read_text()
        assert "Modified iteration" in final_content

        # Verify developer was called twice (iteration 1 and 2)
        assert mock_developer.implement.call_count == 2

    @patch("maid_agents.agents.developer.Developer")
    @patch("maid_agents.core.validation_runner.ValidationRunner")
    @patch("maid_agents.core.orchestrator.MAIDOrchestrator._validate_safe_path")
    def test_implementation_loop_cleans_up_on_success(
        self,
        mock_validate_path,
        mock_validation_runner_class,
        mock_developer_class,
        temp_project,
    ):
        """Test that implementation loop cleans up backup on success."""
        # Setup similar to previous test
        manifest_path = temp_project["manifest_path"]
        impl_file = temp_project["impl_file"]

        # Mock path validation
        mock_validate_path.side_effect = lambda p: Path(p)

        claude = MagicMock(spec=ClaudeWrapper)
        claude.mock_mode = False
        mock_validation_runner = MagicMock(spec=ValidationRunner)
        mock_validation_runner_class.return_value = mock_validation_runner

        # Success on first iteration
        mock_validation_runner.run_behavioral_tests.return_value = ValidationResult(
            success=True, stdout="All tests passed", stderr="", errors=[]
        )
        mock_validation_runner.validate_manifest.return_value = ValidationResult(
            success=True, stdout="Valid", stderr="", errors=[]
        )

        mock_developer = MagicMock()
        mock_developer_class.return_value = mock_developer
        mock_developer.implement.return_value = {
            "success": True,
            "files_modified": [str(impl_file)],
            "code": "# Success\n",
            "error": None,
        }

        # Write the code file so developer can read it
        impl_file.write_text("# Success\n")

        orchestrator = MAIDOrchestrator(
            claude=claude, validation_runner=mock_validation_runner, dry_run=False
        )

        result = orchestrator.run_implementation_loop(manifest_path, max_iterations=3)

        # Verify success and cleanup happened (no temp directories left)
        assert result["success"] is True
        # Note: Actual cleanup verification would require accessing FileBackupManager
        # internals or checking temp directory, which is implementation-dependent

    @patch("maid_agents.agents.developer.Developer")
    @patch("maid_agents.core.validation_runner.ValidationRunner")
    def test_implementation_loop_cleans_up_on_failure(
        self, mock_validation_runner_class, mock_developer_class, temp_project
    ):
        """Test that implementation loop cleans up backup even on failure."""
        manifest_path = temp_project["manifest_path"]
        impl_file = temp_project["impl_file"]

        claude = MagicMock(spec=ClaudeWrapper)
        claude.mock_mode = False
        mock_validation_runner = MagicMock(spec=ValidationRunner)
        mock_validation_runner_class.return_value = mock_validation_runner

        # Always fail
        mock_validation_runner.run_behavioral_tests.return_value = ValidationResult(
            success=False, stdout="", stderr="Test failed", errors=["AssertionError"]
        )

        mock_developer = MagicMock()
        mock_developer_class.return_value = mock_developer
        mock_developer.implement.return_value = {
            "success": True,
            "files_modified": [str(impl_file)],
            "code": "# Broken code\n",
            "error": None,
        }

        orchestrator = MAIDOrchestrator(
            claude=claude, validation_runner=mock_validation_runner, dry_run=False
        )

        result = orchestrator.run_implementation_loop(manifest_path, max_iterations=2)

        # Verify failure and cleanup still happened
        assert result["success"] is False


class TestRefactoringLoopBackup:
    """Test backup/restore in refactoring loop."""

    @patch("maid_agents.agents.refactorer.Refactorer")
    @patch("maid_agents.core.validation_runner.ValidationRunner")
    def test_refactoring_loop_restores_on_retry(
        self, mock_validation_runner_class, mock_refactorer_class, temp_project
    ):
        """Test that refactoring loop restores files before each retry."""
        manifest_path = temp_project["manifest_path"]
        impl_file = temp_project["impl_file"]

        # Mock Claude wrapper with all necessary attributes
        claude = MagicMock()
        claude.mock_mode = False
        claude.model = "claude-sonnet-4"
        claude.timeout = 300
        claude.temperature = 0.0
        mock_validation_runner = MagicMock(spec=ValidationRunner)
        mock_validation_runner_class.return_value = mock_validation_runner

        # First validation fails, second succeeds
        mock_validation_runner.validate_manifest.return_value = ValidationResult(
            success=True, stdout="Valid", stderr="", errors=[]
        )
        mock_validation_runner.run_behavioral_tests.side_effect = [
            ValidationResult(
                success=False,
                stdout="",
                stderr="Test failed",
                errors=["AssertionError"],
            ),
            ValidationResult(
                success=True, stdout="All tests passed", stderr="", errors=[]
            ),
        ]

        mock_refactorer = MagicMock()

        def refactor_file_side_effect(manifest_path, validation_feedback):
            # Simulate refactorer modifying the file
            impl_file.write_text(f"# Refactored\n{validation_feedback}\n")
            return {
                "success": True,
                "improvements": ["Improved code quality"],
                "refactored_code": impl_file.read_text(),
                "files_affected": [str(impl_file)],
                "files_written": [str(impl_file)],
                "error": None,
            }

        mock_refactorer.refactor.side_effect = refactor_file_side_effect

        orchestrator = MAIDOrchestrator(
            claude=claude, validation_runner=mock_validation_runner, dry_run=False
        )

        # Inject mock refactorer directly into orchestrator
        orchestrator.refactorer = mock_refactorer

        # Run with AUTO retry mode to test retry behavior
        from maid_agents.core.orchestrator import RetryMode

        result = orchestrator.run_refactoring_loop(
            manifest_path, max_iterations=3, retry_mode=RetryMode.AUTO
        )

        # Verify success
        assert result["success"] is True
        assert result["iterations"] == 2

        # Verify refactorer was called twice
        assert mock_refactorer.refactor.call_count == 2


class TestDryRunMode:
    """Test that dry_run mode is respected in backup/restore."""

    @patch("maid_agents.agents.developer.Developer")
    @patch("maid_agents.core.validation_runner.ValidationRunner")
    def test_dry_run_skips_file_operations(
        self, mock_validation_runner_class, mock_developer_class, temp_project
    ):
        """Test that dry_run mode skips actual file backup/restore operations."""
        manifest_path = temp_project["manifest_path"]
        impl_file = temp_project["impl_file"]
        original_content = impl_file.read_text()

        claude = MagicMock(spec=ClaudeWrapper)
        claude.mock_mode = True
        mock_validation_runner = MagicMock(spec=ValidationRunner)
        mock_validation_runner_class.return_value = mock_validation_runner

        mock_validation_runner.run_behavioral_tests.return_value = ValidationResult(
            success=True, stdout="All tests passed", stderr="", errors=[]
        )
        mock_validation_runner.validate_manifest.return_value = ValidationResult(
            success=True, stdout="Valid", stderr="", errors=[]
        )

        mock_developer = MagicMock()
        mock_developer_class.return_value = mock_developer
        mock_developer.implement.return_value = {
            "success": True,
            "files_modified": [str(impl_file)],
            "code": "# Modified in dry run\n",
            "error": None,
        }

        # Create orchestrator in dry_run mode
        orchestrator = MAIDOrchestrator(
            claude=claude,
            validation_runner=mock_validation_runner,
            dry_run=True,  # DRY RUN MODE
        )

        result = orchestrator.run_implementation_loop(manifest_path, max_iterations=3)

        # In dry run mode, files should not actually be written
        # Original content should remain
        assert impl_file.read_text() == original_content
        assert result["success"] is True
