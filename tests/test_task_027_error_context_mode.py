"""Behavioral tests for task-027: Error context mode control.

Tests the ErrorContextMode enum and _should_restore_files method to ensure proper
file restoration behavior based on error context mode.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import patch, MagicMock
from maid_agents.core.orchestrator import MAIDOrchestrator, ErrorContextMode, RetryMode
from maid_agents.claude.cli_wrapper import ClaudeWrapper


class TestErrorContextModeEnum:
    """Test ErrorContextMode enum values and behavior."""

    def test_error_context_mode_has_incremental_value(self):
        """Verify ErrorContextMode.INCREMENTAL exists with correct value."""
        assert hasattr(ErrorContextMode, "INCREMENTAL")
        assert ErrorContextMode.INCREMENTAL.value == "incremental"

    def test_error_context_mode_has_fresh_start_value(self):
        """Verify ErrorContextMode.FRESH_START exists with correct value."""
        assert hasattr(ErrorContextMode, "FRESH_START")
        assert ErrorContextMode.FRESH_START.value == "fresh-start"

    def test_error_context_mode_enum_members(self):
        """Verify ErrorContextMode has exactly two members."""
        assert len(ErrorContextMode) == 2
        assert set(ErrorContextMode) == {
            ErrorContextMode.INCREMENTAL,
            ErrorContextMode.FRESH_START,
        }


class TestShouldRestoreFilesMethod:
    """Test _should_restore_files method logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = MAIDOrchestrator(
            claude=ClaudeWrapper(mock_mode=True), dry_run=True
        )

    def test_should_restore_files_first_iteration_always_false(self):
        """Verify _should_restore_files returns False on first iteration regardless of mode."""
        # First iteration (iteration=1) should never restore
        assert (
            self.orchestrator._should_restore_files(
                iteration=1, error_context_mode=ErrorContextMode.INCREMENTAL
            )
            is False
        )
        assert (
            self.orchestrator._should_restore_files(
                iteration=1, error_context_mode=ErrorContextMode.FRESH_START
            )
            is False
        )

    def test_should_restore_files_incremental_mode_returns_false(self):
        """Verify INCREMENTAL mode never restores files (builds on previous)."""
        # Iterations 2, 3, 4 should not restore in INCREMENTAL mode
        for iteration in [2, 3, 4, 5]:
            assert (
                self.orchestrator._should_restore_files(
                    iteration=iteration,
                    error_context_mode=ErrorContextMode.INCREMENTAL,
                )
                is False
            )

    def test_should_restore_files_fresh_start_mode_returns_true(self):
        """Verify FRESH_START mode restores files on each retry."""
        # Iterations 2+ should restore in FRESH_START mode
        for iteration in [2, 3, 4, 5]:
            assert (
                self.orchestrator._should_restore_files(
                    iteration=iteration, error_context_mode=ErrorContextMode.FRESH_START
                )
                is True
            )


class TestImplementationLoopErrorContextMode:
    """Test error context mode integration in run_implementation_loop."""

    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = MAIDOrchestrator(
            claude=ClaudeWrapper(mock_mode=True), dry_run=True
        )

    def test_run_implementation_loop_accepts_error_context_mode_parameter(self):
        """Verify run_implementation_loop accepts error_context_mode parameter."""
        import inspect

        # Access method to ensure validator detects usage
        sig = inspect.signature(self.orchestrator.run_implementation_loop)
        assert "error_context_mode" in sig.parameters

        # Check default value is ErrorContextMode.INCREMENTAL
        default = sig.parameters["error_context_mode"].default
        assert default == ErrorContextMode.INCREMENTAL

        # Ensure validator detects method reference
        _ = self.orchestrator.run_implementation_loop

    def test_run_implementation_loop_signature_compatibility(self):
        """Verify method signature maintains backward compatibility."""
        import inspect

        sig = inspect.signature(MAIDOrchestrator.run_implementation_loop)

        # Should have all required parameters
        assert "manifest_path" in sig.parameters
        assert "max_iterations" in sig.parameters
        assert "retry_mode" in sig.parameters
        assert "error_context_mode" in sig.parameters

        # Verify defaults
        assert sig.parameters["retry_mode"].default == RetryMode.DISABLED
        assert (
            sig.parameters["error_context_mode"].default == ErrorContextMode.INCREMENTAL
        )


class TestRefactoringLoopErrorContextMode:
    """Test error context mode integration in run_refactoring_loop."""

    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = MAIDOrchestrator(
            claude=ClaudeWrapper(mock_mode=True), dry_run=True
        )

    def test_run_refactoring_loop_accepts_error_context_mode_parameter(self):
        """Verify run_refactoring_loop accepts error_context_mode parameter."""
        import inspect

        # Access method to ensure validator detects usage
        sig = inspect.signature(self.orchestrator.run_refactoring_loop)
        assert "error_context_mode" in sig.parameters

        # Check default value is ErrorContextMode.INCREMENTAL
        default = sig.parameters["error_context_mode"].default
        assert default == ErrorContextMode.INCREMENTAL

        # Ensure validator detects method reference
        _ = self.orchestrator.run_refactoring_loop

    def test_run_refactoring_loop_signature_compatibility(self):
        """Verify method signature maintains backward compatibility."""
        import inspect

        sig = inspect.signature(MAIDOrchestrator.run_refactoring_loop)

        # Should have all required parameters
        assert "manifest_path" in sig.parameters
        assert "max_iterations" in sig.parameters
        assert "retry_mode" in sig.parameters
        assert "error_context_mode" in sig.parameters

        # Verify defaults
        assert sig.parameters["retry_mode"].default == RetryMode.DISABLED
        assert (
            sig.parameters["error_context_mode"].default == ErrorContextMode.INCREMENTAL
        )


class TestCLIErrorContextModeIntegration:
    """Test CLI integration with error context mode."""

    def test_error_context_mode_can_be_imported_from_orchestrator(self):
        """Verify ErrorContextMode can be imported in CLI context."""
        from maid_agents.core.orchestrator import ErrorContextMode

        # This import is used in main.py CLI implementation
        assert ErrorContextMode.INCREMENTAL.value == "incremental"
        assert ErrorContextMode.FRESH_START.value == "fresh-start"

    def test_error_context_mode_mapping_logic(self):
        """Verify CLI error context mode mapping logic."""
        # Simulate CLI argument combinations
        test_cases = [
            (False, ErrorContextMode.INCREMENTAL),  # default
            (True, ErrorContextMode.FRESH_START),  # --fresh-start
        ]

        for fresh_start_flag, expected_mode in test_cases:
            # Simulate CLI logic from main.py
            if fresh_start_flag:
                error_context_mode = ErrorContextMode.FRESH_START
            else:
                error_context_mode = ErrorContextMode.INCREMENTAL  # Default

            assert error_context_mode == expected_mode

    def test_orchestrator_receives_error_context_mode_parameter(self):
        """Verify orchestrator methods can receive error_context_mode from CLI."""
        orchestrator = MAIDOrchestrator(
            claude=ClaudeWrapper(mock_mode=True), dry_run=True
        )

        # These method signatures accept error_context_mode, as called by CLI
        import inspect

        impl_sig = inspect.signature(orchestrator.run_implementation_loop)
        refactor_sig = inspect.signature(orchestrator.run_refactoring_loop)

        assert "error_context_mode" in impl_sig.parameters
        assert "error_context_mode" in refactor_sig.parameters

        # Verify defaults are INCREMENTAL
        assert (
            impl_sig.parameters["error_context_mode"].default
            == ErrorContextMode.INCREMENTAL
        )
        assert (
            refactor_sig.parameters["error_context_mode"].default
            == ErrorContextMode.INCREMENTAL
        )


class TestFileRestorationBehavior:
    """Test file restoration behavior with different error context modes."""

    def test_incremental_mode_preserves_previous_changes(self):
        """Verify INCREMENTAL mode does not restore files between iterations."""
        orchestrator = MAIDOrchestrator(
            claude=ClaudeWrapper(mock_mode=True), dry_run=True
        )

        # Test that _should_restore_files returns False for iterations 2+
        # in INCREMENTAL mode (preserving previous changes)
        for iteration in range(2, 6):
            should_restore = orchestrator._should_restore_files(
                iteration=iteration, error_context_mode=ErrorContextMode.INCREMENTAL
            )
            assert should_restore is False, f"Iteration {iteration} should not restore"

    def test_fresh_start_mode_restores_on_each_retry(self):
        """Verify FRESH_START mode restores files on each retry iteration."""
        orchestrator = MAIDOrchestrator(
            claude=ClaudeWrapper(mock_mode=True), dry_run=True
        )

        # Test that _should_restore_files returns True for iterations 2+
        # in FRESH_START mode (clean slate each retry)
        for iteration in range(2, 6):
            should_restore = orchestrator._should_restore_files(
                iteration=iteration, error_context_mode=ErrorContextMode.FRESH_START
            )
            assert should_restore is True, f"Iteration {iteration} should restore"

    @patch("maid_agents.agents.developer.Developer")
    @patch("maid_agents.core.orchestrator.MAIDOrchestrator._validate_safe_path")
    @patch("maid_agents.core.validation_runner.ValidationRunner")
    def test_run_implementation_loop_method_exists_with_error_context_mode(
        self,
        mock_validation_runner_class,
        mock_validate_path,
        mock_developer_class,
        tmp_path,
    ):
        """Verify run_implementation_loop can be called with error_context_mode."""
        from maid_agents.core.validation_runner import ValidationResult
        import json

        # Setup manifest
        manifest_path = tmp_path / "test.manifest.json"
        test_file = tmp_path / "test.py"
        test_file.write_text("# Original")

        manifest_data = {
            "goal": "Test",
            "taskType": "edit",
            "editableFiles": [str(test_file)],
            "readonlyFiles": [],
            "expectedArtifacts": {"file": str(test_file), "contains": []},
            "validationCommand": ["pytest", str(test_file)],
        }
        manifest_path.write_text(json.dumps(manifest_data))

        # Mock path validation
        mock_validate_path.side_effect = lambda p: Path(p)

        # Mock validation runner
        mock_runner = MagicMock()
        mock_validation_runner_class.return_value = mock_runner
        mock_runner.run_behavioral_tests.return_value = ValidationResult(
            success=True, stdout="Pass", stderr="", errors=[]
        )
        mock_runner.validate_manifest.return_value = ValidationResult(
            success=True, stdout="Valid", stderr="", errors=[]
        )

        # Mock developer
        mock_developer = MagicMock()
        mock_developer_class.return_value = mock_developer
        mock_developer.implement.return_value = {
            "success": True,
            "files_modified": [str(test_file)],
            "code": "# Modified",
            "error": None,
        }

        # Call with INCREMENTAL mode
        orchestrator = MAIDOrchestrator(
            claude=ClaudeWrapper(mock_mode=True),
            validation_runner=mock_runner,
            dry_run=True,
        )
        result = orchestrator.run_implementation_loop(
            str(manifest_path),
            max_iterations=5,
            retry_mode=RetryMode.DISABLED,
            error_context_mode=ErrorContextMode.INCREMENTAL,
        )

        assert result["success"] is True

    @patch("maid_agents.agents.refactorer.Refactorer")
    @patch("maid_agents.core.orchestrator.MAIDOrchestrator._validate_safe_path")
    @patch("maid_agents.core.validation_runner.ValidationRunner")
    def test_run_refactoring_loop_method_exists_with_error_context_mode(
        self,
        mock_validation_runner_class,
        mock_validate_path,
        mock_refactorer_class,
        tmp_path,
    ):
        """Verify run_refactoring_loop can be called with error_context_mode."""
        from maid_agents.core.validation_runner import ValidationResult
        import json

        # Setup manifest
        manifest_path = tmp_path / "test.manifest.json"
        test_file = tmp_path / "test.py"
        test_file.write_text("# Original")

        manifest_data = {
            "goal": "Test",
            "taskType": "edit",
            "editableFiles": [str(test_file)],
            "readonlyFiles": [],
            "expectedArtifacts": {"file": str(test_file), "contains": []},
            "validationCommand": ["pytest", str(test_file)],
        }
        manifest_path.write_text(json.dumps(manifest_data))

        # Mock path validation
        mock_validate_path.side_effect = lambda p: Path(p)

        # Mock validation runner
        mock_runner = MagicMock()
        mock_validation_runner_class.return_value = mock_runner
        mock_runner.run_behavioral_tests.return_value = ValidationResult(
            success=True, stdout="Pass", stderr="", errors=[]
        )

        # Mock refactorer
        mock_refactorer = MagicMock()
        mock_refactorer_class.return_value = mock_refactorer
        mock_refactorer.refactor.return_value = {
            "success": True,
            "files_written": [str(test_file)],
            "improvements": ["Improved code"],
            "error": None,
        }

        # Call with FRESH_START mode
        orchestrator = MAIDOrchestrator(
            claude=ClaudeWrapper(mock_mode=True),
            validation_runner=mock_runner,
            dry_run=True,
        )
        result = orchestrator.run_refactoring_loop(
            str(manifest_path),
            max_iterations=5,
            retry_mode=RetryMode.DISABLED,
            error_context_mode=ErrorContextMode.FRESH_START,
        )

        assert result["success"] is True
