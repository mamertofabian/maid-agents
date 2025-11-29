"""Behavioral tests for task-030: Add flags to run command.

This test file verifies that new flags (--no-retry, --confirm-retry, --fresh-start,
--instructions, --bypass-permissions) are properly integrated into the run command.
"""

from unittest.mock import patch

from maid_agents.core.orchestrator import (
    MAIDOrchestrator,
    WorkflowResult,
    RetryMode,
    ErrorContextMode,
)


class TestRunFullWorkflowSignature:
    """Tests for run_full_workflow method signature."""

    def test_method_exists(self):
        """Test that run_full_workflow method exists on MAIDOrchestrator."""
        orchestrator = MAIDOrchestrator(dry_run=True)
        assert hasattr(orchestrator, "run_full_workflow")
        assert callable(getattr(orchestrator, "run_full_workflow"))

    def test_method_accepts_retry_mode(self):
        """Test method accepts retry_mode parameter."""
        orchestrator = MAIDOrchestrator(dry_run=True)

        with patch.object(orchestrator, "run_planning_loop") as mock_planning:
            mock_planning.return_value = {"success": False, "error": "test error"}

            result = orchestrator.run_full_workflow(
                goal="test goal", retry_mode=RetryMode.DISABLED
            )

            assert isinstance(result, WorkflowResult)

    def test_method_accepts_error_context_mode(self):
        """Test method accepts error_context_mode parameter."""
        orchestrator = MAIDOrchestrator(dry_run=True)

        with patch.object(orchestrator, "run_planning_loop") as mock_planning:
            mock_planning.return_value = {"success": False, "error": "test error"}

            result = orchestrator.run_full_workflow(
                goal="test goal", error_context_mode=ErrorContextMode.FRESH_START
            )

            assert isinstance(result, WorkflowResult)

    def test_method_accepts_instructions(self):
        """Test method accepts instructions parameter."""
        orchestrator = MAIDOrchestrator(dry_run=True)

        with patch.object(orchestrator, "run_planning_loop") as mock_planning:
            mock_planning.return_value = {"success": False, "error": "test error"}

            result = orchestrator.run_full_workflow(
                goal="test goal", instructions="custom instructions"
            )

            assert isinstance(result, WorkflowResult)

    def test_method_accepts_max_iterations(self):
        """Test method accepts max_iterations parameters."""
        orchestrator = MAIDOrchestrator(dry_run=True)

        with patch.object(orchestrator, "run_planning_loop") as mock_planning:
            mock_planning.return_value = {"success": False, "error": "test error"}

            result = orchestrator.run_full_workflow(
                goal="test goal",
                max_iterations_planning=5,
                max_iterations_implementation=15,
            )

            assert isinstance(result, WorkflowResult)

    def test_method_accepts_all_parameters(self):
        """Test method accepts all parameters together."""
        orchestrator = MAIDOrchestrator(dry_run=True)

        with patch.object(orchestrator, "run_planning_loop") as mock_planning:
            mock_planning.return_value = {"success": False, "error": "test error"}

            result = orchestrator.run_full_workflow(
                goal="test goal",
                max_iterations_planning=5,
                max_iterations_implementation=15,
                retry_mode=RetryMode.CONFIRM,
                error_context_mode=ErrorContextMode.INCREMENTAL,
                instructions="test instructions",
            )

            assert isinstance(result, WorkflowResult)


class TestRunFullWorkflowBehavior:
    """Tests for run_full_workflow behavior with new flags."""

    def test_retry_mode_disabled_passed_to_implementation(self):
        """Test retry_mode=DISABLED is passed to implementation loop."""
        orchestrator = MAIDOrchestrator(dry_run=True)

        mock_planning_result = {
            "success": True,
            "manifest_path": "manifests/task-999.manifest.json",
        }

        with patch.object(
            orchestrator, "run_planning_loop", return_value=mock_planning_result
        ):
            with patch.object(orchestrator, "run_implementation_loop") as mock_impl:
                mock_impl.return_value = {
                    "success": True,
                    "message": "Implementation complete",
                }

                orchestrator.run_full_workflow(
                    goal="test", retry_mode=RetryMode.DISABLED
                )

                mock_impl.assert_called_once()
                call_kwargs = mock_impl.call_args.kwargs
                assert call_kwargs.get("retry_mode") == RetryMode.DISABLED

    def test_retry_mode_confirm_passed_to_implementation(self):
        """Test retry_mode=CONFIRM is passed to implementation loop."""
        orchestrator = MAIDOrchestrator(dry_run=True)

        mock_planning_result = {
            "success": True,
            "manifest_path": "manifests/task-999.manifest.json",
        }

        with patch.object(
            orchestrator, "run_planning_loop", return_value=mock_planning_result
        ):
            with patch.object(orchestrator, "run_implementation_loop") as mock_impl:
                mock_impl.return_value = {
                    "success": True,
                    "message": "Implementation complete",
                }

                orchestrator.run_full_workflow(
                    goal="test", retry_mode=RetryMode.CONFIRM
                )

                mock_impl.assert_called_once()
                call_kwargs = mock_impl.call_args.kwargs
                assert call_kwargs.get("retry_mode") == RetryMode.CONFIRM

    def test_error_context_mode_fresh_start_passed_to_implementation(self):
        """Test error_context_mode=FRESH_START is passed to implementation loop."""
        orchestrator = MAIDOrchestrator(dry_run=True)

        mock_planning_result = {
            "success": True,
            "manifest_path": "manifests/task-999.manifest.json",
        }

        with patch.object(
            orchestrator, "run_planning_loop", return_value=mock_planning_result
        ):
            with patch.object(orchestrator, "run_implementation_loop") as mock_impl:
                mock_impl.return_value = {
                    "success": True,
                    "message": "Implementation complete",
                }

                orchestrator.run_full_workflow(
                    goal="test", error_context_mode=ErrorContextMode.FRESH_START
                )

                mock_impl.assert_called_once()
                call_kwargs = mock_impl.call_args.kwargs
                assert (
                    call_kwargs.get("error_context_mode")
                    == ErrorContextMode.FRESH_START
                )

    def test_error_context_mode_incremental_passed_to_implementation(self):
        """Test error_context_mode=INCREMENTAL is passed to implementation loop."""
        orchestrator = MAIDOrchestrator(dry_run=True)

        mock_planning_result = {
            "success": True,
            "manifest_path": "manifests/task-999.manifest.json",
        }

        with patch.object(
            orchestrator, "run_planning_loop", return_value=mock_planning_result
        ):
            with patch.object(orchestrator, "run_implementation_loop") as mock_impl:
                mock_impl.return_value = {
                    "success": True,
                    "message": "Implementation complete",
                }

                orchestrator.run_full_workflow(
                    goal="test", error_context_mode=ErrorContextMode.INCREMENTAL
                )

                mock_impl.assert_called_once()
                call_kwargs = mock_impl.call_args.kwargs
                assert (
                    call_kwargs.get("error_context_mode")
                    == ErrorContextMode.INCREMENTAL
                )

    def test_instructions_passed_to_planning_loop(self):
        """Test instructions parameter is passed to planning loop."""
        orchestrator = MAIDOrchestrator(dry_run=True)

        custom_instructions = "Use TypeScript instead of JavaScript"

        with patch.object(orchestrator, "run_planning_loop") as mock_planning:
            mock_planning.return_value = {"success": False, "error": "test error"}

            orchestrator.run_full_workflow(
                goal="test", instructions=custom_instructions
            )

            mock_planning.assert_called_once()
            call_kwargs = mock_planning.call_args.kwargs
            assert call_kwargs.get("instructions") == custom_instructions

    def test_max_iterations_passed_to_loops(self):
        """Test max_iterations parameters are passed to planning and implementation loops."""
        orchestrator = MAIDOrchestrator(dry_run=True)

        mock_planning_result = {
            "success": True,
            "manifest_path": "manifests/task-999.manifest.json",
        }

        with patch.object(
            orchestrator, "run_planning_loop", return_value=mock_planning_result
        ) as mock_planning:
            with patch.object(orchestrator, "run_implementation_loop") as mock_impl:
                mock_impl.return_value = {
                    "success": True,
                    "message": "Implementation complete",
                }

                orchestrator.run_full_workflow(
                    goal="test",
                    max_iterations_planning=7,
                    max_iterations_implementation=25,
                )

                planning_kwargs = mock_planning.call_args.kwargs
                impl_kwargs = mock_impl.call_args.kwargs

                assert planning_kwargs.get("max_iterations") == 7
                assert impl_kwargs.get("max_iterations") == 25

    def test_all_flags_work_together(self):
        """Test all new flags can be used together."""
        orchestrator = MAIDOrchestrator(dry_run=True, bypass_permissions=True)

        mock_planning_result = {
            "success": True,
            "manifest_path": "manifests/task-999.manifest.json",
        }

        with patch.object(
            orchestrator, "run_planning_loop", return_value=mock_planning_result
        ) as mock_planning:
            with patch.object(orchestrator, "run_implementation_loop") as mock_impl:
                mock_impl.return_value = {
                    "success": True,
                    "message": "Implementation complete",
                }

                result = orchestrator.run_full_workflow(
                    goal="test goal",
                    max_iterations_planning=5,
                    max_iterations_implementation=15,
                    retry_mode=RetryMode.CONFIRM,
                    error_context_mode=ErrorContextMode.FRESH_START,
                    instructions="custom instructions",
                )

                assert result.success is True

                planning_kwargs = mock_planning.call_args.kwargs
                impl_kwargs = mock_impl.call_args.kwargs

                assert planning_kwargs.get("max_iterations") == 5
                assert planning_kwargs.get("instructions") == "custom instructions"
                assert impl_kwargs.get("max_iterations") == 15
                assert impl_kwargs.get("retry_mode") == RetryMode.CONFIRM
                assert (
                    impl_kwargs.get("error_context_mode")
                    == ErrorContextMode.FRESH_START
                )


class TestRunFullWorkflowDefaultValues:
    """Tests for run_full_workflow default parameter values."""

    def test_default_retry_mode_is_disabled(self):
        """Test default retry_mode is DISABLED."""
        orchestrator = MAIDOrchestrator(dry_run=True)

        mock_planning_result = {
            "success": True,
            "manifest_path": "manifests/task-999.manifest.json",
        }

        with patch.object(
            orchestrator, "run_planning_loop", return_value=mock_planning_result
        ):
            with patch.object(orchestrator, "run_implementation_loop") as mock_impl:
                mock_impl.return_value = {
                    "success": True,
                    "message": "Implementation complete",
                }

                orchestrator.run_full_workflow(goal="test")

                call_kwargs = mock_impl.call_args.kwargs
                assert call_kwargs.get("retry_mode") == RetryMode.DISABLED

    def test_default_error_context_mode_is_incremental(self):
        """Test default error_context_mode is INCREMENTAL."""
        orchestrator = MAIDOrchestrator(dry_run=True)

        mock_planning_result = {
            "success": True,
            "manifest_path": "manifests/task-999.manifest.json",
        }

        with patch.object(
            orchestrator, "run_planning_loop", return_value=mock_planning_result
        ):
            with patch.object(orchestrator, "run_implementation_loop") as mock_impl:
                mock_impl.return_value = {
                    "success": True,
                    "message": "Implementation complete",
                }

                orchestrator.run_full_workflow(goal="test")

                call_kwargs = mock_impl.call_args.kwargs
                assert (
                    call_kwargs.get("error_context_mode")
                    == ErrorContextMode.INCREMENTAL
                )

    def test_default_instructions_is_empty_string(self):
        """Test default instructions is empty string."""
        orchestrator = MAIDOrchestrator(dry_run=True)

        with patch.object(orchestrator, "run_planning_loop") as mock_planning:
            mock_planning.return_value = {"success": False, "error": "test error"}

            orchestrator.run_full_workflow(goal="test")

            call_kwargs = mock_planning.call_args.kwargs
            assert call_kwargs.get("instructions") == ""

    def test_default_max_iterations_planning_is_10(self):
        """Test default max_iterations_planning is 10."""
        orchestrator = MAIDOrchestrator(dry_run=True)

        with patch.object(orchestrator, "run_planning_loop") as mock_planning:
            mock_planning.return_value = {"success": False, "error": "test error"}

            orchestrator.run_full_workflow(goal="test")

            call_kwargs = mock_planning.call_args.kwargs
            assert call_kwargs.get("max_iterations") == 10

    def test_default_max_iterations_implementation_is_20(self):
        """Test default max_iterations_implementation is 20."""
        orchestrator = MAIDOrchestrator(dry_run=True)

        mock_planning_result = {
            "success": True,
            "manifest_path": "manifests/task-999.manifest.json",
        }

        with patch.object(
            orchestrator, "run_planning_loop", return_value=mock_planning_result
        ):
            with patch.object(orchestrator, "run_implementation_loop") as mock_impl:
                mock_impl.return_value = {
                    "success": True,
                    "message": "Implementation complete",
                }

                orchestrator.run_full_workflow(goal="test")

                call_kwargs = mock_impl.call_args.kwargs
                assert call_kwargs.get("max_iterations") == 20


class TestRetryModeEnum:
    """Tests for RetryMode enum."""

    def test_retry_mode_enum_exists(self):
        """Test RetryMode enum exists."""
        assert RetryMode is not None

    def test_retry_mode_has_disabled(self):
        """Test RetryMode has DISABLED value."""
        assert hasattr(RetryMode, "DISABLED")
        assert RetryMode.DISABLED.value == "disabled"

    def test_retry_mode_has_auto(self):
        """Test RetryMode has AUTO value."""
        assert hasattr(RetryMode, "AUTO")
        assert RetryMode.AUTO.value == "auto"

    def test_retry_mode_has_confirm(self):
        """Test RetryMode has CONFIRM value."""
        assert hasattr(RetryMode, "CONFIRM")
        assert RetryMode.CONFIRM.value == "confirm"


class TestErrorContextModeEnum:
    """Tests for ErrorContextMode enum."""

    def test_error_context_mode_enum_exists(self):
        """Test ErrorContextMode enum exists."""
        assert ErrorContextMode is not None

    def test_error_context_mode_has_incremental(self):
        """Test ErrorContextMode has INCREMENTAL value."""
        assert hasattr(ErrorContextMode, "INCREMENTAL")
        assert ErrorContextMode.INCREMENTAL.value == "incremental"

    def test_error_context_mode_has_fresh_start(self):
        """Test ErrorContextMode has FRESH_START value."""
        assert hasattr(ErrorContextMode, "FRESH_START")
        assert ErrorContextMode.FRESH_START.value == "fresh-start"
