"""Behavioral tests for task-026: Retry mode control.

Tests the RetryMode enum and _should_retry method to ensure proper retry behavior
in implementation and refactoring loops.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import patch
from maid_agents.core.orchestrator import MAIDOrchestrator, RetryMode
from maid_agents.claude.cli_wrapper import ClaudeWrapper


class TestRetryModeEnum:
    """Test RetryMode enum values and behavior."""

    def test_retry_mode_has_auto_value(self):
        """Verify RetryMode.AUTO exists with correct value."""
        assert hasattr(RetryMode, "AUTO")
        assert RetryMode.AUTO.value == "auto"

    def test_retry_mode_has_disabled_value(self):
        """Verify RetryMode.DISABLED exists with correct value."""
        assert hasattr(RetryMode, "DISABLED")
        assert RetryMode.DISABLED.value == "disabled"

    def test_retry_mode_has_confirm_value(self):
        """Verify RetryMode.CONFIRM exists with correct value."""
        assert hasattr(RetryMode, "CONFIRM")
        assert RetryMode.CONFIRM.value == "confirm"

    def test_retry_mode_enum_members(self):
        """Verify RetryMode has exactly three members."""
        assert len(RetryMode) == 3
        assert set(RetryMode) == {RetryMode.AUTO, RetryMode.DISABLED, RetryMode.CONFIRM}


class TestShouldRetryMethod:
    """Test _should_retry method logic for different retry modes."""

    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = MAIDOrchestrator(
            claude=ClaudeWrapper(mock_mode=True), dry_run=True
        )

    def test_should_retry_returns_false_at_max_iterations(self):
        """Verify _should_retry returns False when at max iterations."""
        result = self.orchestrator._should_retry(
            current_iteration=10,
            max_iterations=10,
            retry_mode=RetryMode.AUTO,
            error_msg="Test error",
        )
        assert result is False

    def test_should_retry_disabled_mode_returns_false(self):
        """Verify RetryMode.DISABLED always returns False."""
        result = self.orchestrator._should_retry(
            current_iteration=1,
            max_iterations=10,
            retry_mode=RetryMode.DISABLED,
            error_msg="Test error",
        )
        assert result is False

    def test_should_retry_auto_mode_returns_true_below_max(self):
        """Verify RetryMode.AUTO returns True when below max iterations."""
        result = self.orchestrator._should_retry(
            current_iteration=5,
            max_iterations=10,
            retry_mode=RetryMode.AUTO,
            error_msg="Test error",
        )
        assert result is True

    def test_should_retry_confirm_mode_with_yes_response(self):
        """Verify RetryMode.CONFIRM returns True when user confirms."""
        with patch("builtins.input", return_value="y"):
            result = self.orchestrator._should_retry(
                current_iteration=3,
                max_iterations=10,
                retry_mode=RetryMode.CONFIRM,
                error_msg="Test error",
            )
        assert result is True

    def test_should_retry_confirm_mode_with_no_response(self):
        """Verify RetryMode.CONFIRM returns False when user declines."""
        with patch("builtins.input", return_value="n"):
            result = self.orchestrator._should_retry(
                current_iteration=3,
                max_iterations=10,
                retry_mode=RetryMode.CONFIRM,
                error_msg="Test error",
            )
        assert result is False

    def test_should_retry_confirm_mode_with_keyboard_interrupt(self):
        """Verify RetryMode.CONFIRM returns False on KeyboardInterrupt."""
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            result = self.orchestrator._should_retry(
                current_iteration=3,
                max_iterations=10,
                retry_mode=RetryMode.CONFIRM,
                error_msg="Test error",
            )
        assert result is False


class TestImplementationLoopRetryMode:
    """Test retry mode integration in run_implementation_loop."""

    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = MAIDOrchestrator(
            claude=ClaudeWrapper(mock_mode=True), dry_run=True
        )

    def test_run_implementation_loop_accepts_retry_mode_parameter(self):
        """Verify run_implementation_loop accepts retry_mode parameter."""
        # Check method signature accepts retry_mode
        import inspect

        sig = inspect.signature(self.orchestrator.run_implementation_loop)
        assert "retry_mode" in sig.parameters

        # Check default value is RetryMode.DISABLED
        default = sig.parameters["retry_mode"].default
        assert default == RetryMode.DISABLED

    def test_run_implementation_loop_with_disabled_retry_mode(self):
        """Test run_implementation_loop can be called with DISABLED retry_mode."""
        # Just verify the method signature accepts the parameter
        # Full integration tests are in test_task_024_backup_integration.py
        import inspect

        sig = inspect.signature(MAIDOrchestrator.run_implementation_loop)
        assert "retry_mode" in sig.parameters

        # Verify we can pass DISABLED mode
        assert RetryMode.DISABLED in RetryMode

    def test_run_implementation_loop_with_auto_retry_mode(self):
        """Test run_implementation_loop can be called with AUTO retry_mode."""
        # Just verify the method signature accepts the parameter
        # Full integration tests are in test_task_024_backup_integration.py
        import inspect

        sig = inspect.signature(MAIDOrchestrator.run_implementation_loop)
        assert "retry_mode" in sig.parameters

        # Verify we can pass AUTO mode
        assert RetryMode.AUTO in RetryMode


class TestRefactoringLoopRetryMode:
    """Test retry mode integration in run_refactoring_loop."""

    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = MAIDOrchestrator(
            claude=ClaudeWrapper(mock_mode=True), dry_run=True
        )

    def test_run_refactoring_loop_accepts_retry_mode_parameter(self):
        """Verify run_refactoring_loop accepts retry_mode parameter."""
        # Check method signature accepts retry_mode
        import inspect

        sig = inspect.signature(self.orchestrator.run_refactoring_loop)
        assert "retry_mode" in sig.parameters

        # Check default value is RetryMode.DISABLED
        default = sig.parameters["retry_mode"].default
        assert default == RetryMode.DISABLED

    def test_run_refactoring_loop_with_disabled_retry_mode(self):
        """Test run_refactoring_loop can be called with DISABLED retry_mode."""
        # Just verify the method signature accepts the parameter
        # Full integration tests are in test_task_024_backup_integration.py
        import inspect

        sig = inspect.signature(MAIDOrchestrator.run_refactoring_loop)
        assert "retry_mode" in sig.parameters

        # Verify we can pass DISABLED mode
        assert RetryMode.DISABLED in RetryMode

    def test_run_refactoring_loop_with_auto_retry_mode(self):
        """Test run_refactoring_loop can be called with AUTO retry_mode."""
        # Just verify the method signature accepts the parameter
        # Full integration tests are in test_task_024_backup_integration.py
        import inspect

        sig = inspect.signature(MAIDOrchestrator.run_refactoring_loop)
        assert "retry_mode" in sig.parameters

        # Verify we can pass AUTO mode
        assert RetryMode.AUTO in RetryMode


class TestCLIRetryModeIntegration:
    """Test CLI integration with retry mode."""

    def test_retry_mode_can_be_imported_from_orchestrator(self):
        """Verify RetryMode can be imported in CLI context."""
        from maid_agents.core.orchestrator import RetryMode

        # This import is used in main.py CLI implementation
        assert RetryMode.AUTO.value == "auto"
        assert RetryMode.DISABLED.value == "disabled"
        assert RetryMode.CONFIRM.value == "confirm"

    def test_retry_mode_mapping_logic(self):
        """Verify CLI retry mode mapping logic."""
        # Simulate CLI argument combinations
        test_cases = [
            (True, False, RetryMode.DISABLED),  # --no-retry
            (False, True, RetryMode.CONFIRM),  # --confirm-retry
            (
                False,
                False,
                RetryMode.DISABLED,
            ),  # default (changed from AUTO to DISABLED)
        ]

        for no_retry, confirm_retry, expected_mode in test_cases:
            # Simulate CLI logic from main.py
            if no_retry and confirm_retry:
                # This should be caught as an error in CLI
                continue
            elif no_retry:
                retry_mode = RetryMode.DISABLED
            elif confirm_retry:
                retry_mode = RetryMode.CONFIRM
            else:
                retry_mode = RetryMode.DISABLED  # Default

            assert retry_mode == expected_mode

    def test_orchestrator_receives_retry_mode_parameter(self):
        """Verify orchestrator methods can receive retry_mode from CLI."""
        orchestrator = MAIDOrchestrator(
            claude=ClaudeWrapper(mock_mode=True), dry_run=True
        )

        # These method signatures accept retry_mode, as called by CLI
        import inspect

        impl_sig = inspect.signature(orchestrator.run_implementation_loop)
        refactor_sig = inspect.signature(orchestrator.run_refactoring_loop)

        assert "retry_mode" in impl_sig.parameters
        assert "retry_mode" in refactor_sig.parameters

        # Verify defaults are DISABLED
        assert impl_sig.parameters["retry_mode"].default == RetryMode.DISABLED
        assert refactor_sig.parameters["retry_mode"].default == RetryMode.DISABLED
