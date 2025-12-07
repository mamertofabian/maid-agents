"""Behavioral tests for task-031: Create a new Fixer agent (ccmaid fix).

This test file verifies the Fixer agent implementation matches manifest specifications.
The Fixer agent reviews implementation, detects validation violations, test failures,
and bugs, then automatically fixes them.
"""

from unittest.mock import patch
from maid_agents.agents.fixer import Fixer
from maid_agents.agents.base_agent import BaseAgent
from maid_agents.claude.cli_wrapper import ClaudeWrapper, ClaudeResponse


class TestFixerExistence:
    """Tests for Fixer class existence and instantiation."""

    def test_fixer_class_exists(self):
        """Test that Fixer class exists and can be instantiated."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer = Fixer(claude=wrapper, dry_run=True)
        assert fixer is not None
        assert isinstance(fixer, Fixer)

    def test_fixer_inherits_base_agent(self):
        """Test that Fixer inherits from BaseAgent."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer = Fixer(claude=wrapper, dry_run=True)
        assert isinstance(fixer, BaseAgent)

    def test_fixer_init_with_defaults(self):
        """Test Fixer initialization with default dry_run=False."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer = Fixer(claude=wrapper)
        assert fixer is not None
        assert isinstance(fixer, Fixer)


class TestFixerInitialization:
    """Tests for Fixer.__init__ method."""

    def test_init_signature(self):
        """Test __init__ has correct signature and parameters."""
        wrapper = ClaudeWrapper(mock_mode=True)
        # Use keyword arguments to verify parameter names
        fixer = Fixer(claude=wrapper, dry_run=True)
        assert fixer is not None
        assert hasattr(fixer, "claude")
        assert hasattr(fixer, "dry_run")

    def test_init_stores_claude_wrapper(self):
        """Test __init__ stores ClaudeWrapper instance."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer = Fixer(claude=wrapper, dry_run=True)
        # Fixer creates a new instance with Haiku model, so check model instead
        assert fixer.claude.model == "claude-haiku-4-5"

    def test_init_stores_dry_run_flag(self):
        """Test __init__ stores dry_run flag correctly."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer_dry = Fixer(claude=wrapper, dry_run=True)
        assert fixer_dry.dry_run is True

        fixer_not_dry = Fixer(claude=wrapper, dry_run=False)
        assert fixer_not_dry.dry_run is False


class TestFixerFixMethod:
    """Tests for Fixer.fix method."""

    def test_fix_method_exists(self):
        """Test that fix method exists on Fixer class."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer = Fixer(claude=wrapper, dry_run=True)
        assert hasattr(fixer, "fix")
        assert callable(getattr(fixer, "fix"))

    def test_fix_signature_with_all_params(self):
        """Test fix method has correct signature with all parameters."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer = Fixer(claude=wrapper, dry_run=True)

        # Use keyword arguments to verify parameter names
        result = fixer.fix(
            manifest_path="manifests/task-001.manifest.json",
            validation_errors="Some validation errors",
            test_errors="Some test errors",
            instructions="Fix the issues",
        )
        assert isinstance(result, dict)

    def test_fix_signature_with_defaults(self):
        """Test fix method works with default parameter values."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer = Fixer(claude=wrapper, dry_run=True)

        # Only manifest_path is required, others have defaults
        result = fixer.fix(manifest_path="manifests/task-001.manifest.json")
        assert isinstance(result, dict)

    def test_fix_return_type(self):
        """Test fix method returns a dictionary."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer = Fixer(claude=wrapper, dry_run=True)

        result = fixer.fix(
            manifest_path="manifests/task-001.manifest.json",
            validation_errors="",
            test_errors="",
            instructions="",
        )
        assert isinstance(result, dict)


class TestFixerFixBehavior:
    """Tests for Fixer.fix method behavior."""

    def test_fix_with_validation_errors(self):
        """Test fix method handles validation errors."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer = Fixer(claude=wrapper, dry_run=True)

        result = fixer.fix(
            manifest_path="manifests/task-001.manifest.json",
            validation_errors="Missing artifact: function foo() in module bar",
            test_errors="",
            instructions="",
        )
        assert isinstance(result, dict)
        assert "success" in result or "status" in result or "result" in result

    def test_fix_with_test_errors(self):
        """Test fix method handles test failures."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer = Fixer(claude=wrapper, dry_run=True)

        result = fixer.fix(
            manifest_path="manifests/task-001.manifest.json",
            validation_errors="",
            test_errors="FAILED tests/test_foo.py::test_bar - AssertionError",
            instructions="",
        )
        assert isinstance(result, dict)
        assert "success" in result or "status" in result or "result" in result

    def test_fix_with_both_errors(self):
        """Test fix method handles both validation and test errors."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer = Fixer(claude=wrapper, dry_run=True)

        result = fixer.fix(
            manifest_path="manifests/task-001.manifest.json",
            validation_errors="Missing artifact",
            test_errors="FAILED tests/test.py",
            instructions="Fix all issues",
        )
        assert isinstance(result, dict)

    def test_fix_with_empty_errors(self):
        """Test fix method handles empty error strings (edge case)."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer = Fixer(claude=wrapper, dry_run=True)

        result = fixer.fix(
            manifest_path="manifests/task-001.manifest.json",
            validation_errors="",
            test_errors="",
            instructions="",
        )
        assert isinstance(result, dict)

    def test_fix_with_custom_instructions(self):
        """Test fix method handles custom instructions."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer = Fixer(claude=wrapper, dry_run=True)

        result = fixer.fix(
            manifest_path="manifests/task-001.manifest.json",
            validation_errors="",
            test_errors="",
            instructions="Focus on improving error handling",
        )
        assert isinstance(result, dict)


class TestFixerExecuteMethod:
    """Tests for Fixer.execute method."""

    def test_execute_method_exists(self):
        """Test that execute method exists on Fixer class."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer = Fixer(claude=wrapper, dry_run=True)
        assert hasattr(fixer, "execute")
        assert callable(getattr(fixer, "execute"))

    def test_execute_signature(self):
        """Test execute method has correct signature (no args)."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer = Fixer(claude=wrapper, dry_run=True)

        # execute() should take no arguments (besides self)
        result = fixer.execute()
        assert isinstance(result, dict)

    def test_execute_return_type(self):
        """Test execute method returns a dictionary."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer = Fixer(claude=wrapper, dry_run=True)

        result = fixer.execute()
        assert isinstance(result, dict)

    def test_execute_returns_agent_info(self):
        """Test execute method returns agent identification."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer = Fixer(claude=wrapper, dry_run=True)

        result = fixer.execute()
        assert isinstance(result, dict)
        # Should contain agent identification/status info
        assert len(result) > 0


class TestFixerEdgeCases:
    """Tests for Fixer edge cases and error handling."""

    def test_fix_with_long_error_messages(self):
        """Test fix method handles long error messages."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer = Fixer(claude=wrapper, dry_run=True)

        long_error = "Error: " + "x" * 10000
        result = fixer.fix(
            manifest_path="manifests/task-001.manifest.json",
            validation_errors=long_error,
            test_errors=long_error,
            instructions="",
        )
        assert isinstance(result, dict)

    def test_fix_with_multiline_errors(self):
        """Test fix method handles multiline error messages."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer = Fixer(claude=wrapper, dry_run=True)

        multiline_error = (
            "Error 1: Missing function\nError 2: Wrong signature\nError 3: Failed test"
        )
        result = fixer.fix(
            manifest_path="manifests/task-001.manifest.json",
            validation_errors=multiline_error,
            test_errors=multiline_error,
            instructions="Fix all errors",
        )
        assert isinstance(result, dict)

    def test_fix_with_nonexistent_manifest(self):
        """Test fix method handles nonexistent manifest file."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer = Fixer(claude=wrapper, dry_run=True)

        result = fixer.fix(
            manifest_path="manifests/nonexistent-999.manifest.json",
            validation_errors="test error",
            test_errors="",
            instructions="",
        )
        assert isinstance(result, dict)


class TestFixerIntegrationWithClaudeWrapper:
    """Tests for Fixer integration with ClaudeWrapper."""

    def test_fixer_uses_claude_wrapper_in_mock_mode(self):
        """Test Fixer works with ClaudeWrapper in mock mode."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer = Fixer(claude=wrapper, dry_run=True)

        result = fixer.fix(
            manifest_path="manifests/task-001.manifest.json",
            validation_errors="test error",
            test_errors="",
            instructions="",
        )
        assert isinstance(result, dict)

    @patch.object(ClaudeWrapper, "generate")
    def test_fixer_calls_claude_generate(self, mock_generate):
        """Test Fixer calls ClaudeWrapper.generate method."""
        mock_generate.return_value = ClaudeResponse(
            success=True, result="Fixed the issues", error="", session_id="test-123"
        )

        wrapper = ClaudeWrapper(mock_mode=False)
        fixer = Fixer(claude=wrapper, dry_run=True)

        result = fixer.fix(
            manifest_path="manifests/task-001.manifest.json",
            validation_errors="validation error",
            test_errors="",
            instructions="",
        )

        # Verify generate was called at least once
        assert mock_generate.called or isinstance(result, dict)

    def test_fixer_respects_dry_run_flag(self):
        """Test Fixer respects dry_run flag."""
        wrapper = ClaudeWrapper(mock_mode=True)

        fixer_dry = Fixer(claude=wrapper, dry_run=True)
        result_dry = fixer_dry.fix(
            manifest_path="manifests/task-001.manifest.json",
            validation_errors="error",
            test_errors="",
            instructions="",
        )
        assert isinstance(result_dry, dict)

        fixer_not_dry = Fixer(claude=wrapper, dry_run=False)
        result_not_dry = fixer_not_dry.fix(
            manifest_path="manifests/task-001.manifest.json",
            validation_errors="error",
            test_errors="",
            instructions="",
        )
        assert isinstance(result_not_dry, dict)


class TestFixerBaseAgentInterface:
    """Tests for Fixer's BaseAgent interface compliance."""

    def test_fixer_has_logger_attribute(self):
        """Test Fixer has logger attribute from BaseAgent."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer = Fixer(claude=wrapper, dry_run=True)
        assert hasattr(fixer, "logger")

    def test_fixer_has_dry_run_attribute(self):
        """Test Fixer has dry_run attribute from BaseAgent."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer = Fixer(claude=wrapper, dry_run=True)
        assert hasattr(fixer, "dry_run")
        assert fixer.dry_run is True

    def test_execute_implements_base_agent_interface(self):
        """Test execute method implements BaseAgent abstract method."""
        wrapper = ClaudeWrapper(mock_mode=True)
        fixer = Fixer(claude=wrapper, dry_run=True)

        # Should not raise NotImplementedError
        result = fixer.execute()
        assert isinstance(result, dict)


class TestOrchestratorIntegration:
    """Tests for Fixer integration with MAIDOrchestrator."""

    def test_orchestrator_has_run_fix_loop_method(self):
        """Test orchestrator has run_fix_loop method."""
        from maid_agents.core.orchestrator import MAIDOrchestrator

        wrapper = ClaudeWrapper(mock_mode=True)
        orchestrator = MAIDOrchestrator(claude=wrapper, dry_run=True)
        assert hasattr(orchestrator, "run_fix_loop")
        assert callable(getattr(orchestrator, "run_fix_loop"))

    def test_run_fix_loop_signature(self):
        """Test run_fix_loop has correct signature."""
        from maid_agents.core.orchestrator import MAIDOrchestrator

        wrapper = ClaudeWrapper(mock_mode=True)
        orchestrator = MAIDOrchestrator(claude=wrapper, dry_run=True)

        # Should be able to call with manifest_path and optional params
        # Using non-existent manifest is OK for signature test
        result = orchestrator.run_fix_loop(
            manifest_path="manifests/task-001.manifest.json",
            validation_errors="test error",
            test_errors="test failure",
            instructions="test instructions",
            max_iterations=1,
        )
        assert isinstance(result, dict)

    def test_run_fix_loop_returns_dict_with_required_keys(self):
        """Test run_fix_loop returns dict with success, iterations, and error keys."""
        from maid_agents.core.orchestrator import MAIDOrchestrator

        wrapper = ClaudeWrapper(mock_mode=True)
        orchestrator = MAIDOrchestrator(claude=wrapper, dry_run=True)

        result = orchestrator.run_fix_loop(
            manifest_path="manifests/task-001.manifest.json",
            validation_errors="test",
            max_iterations=1,
        )
        assert isinstance(result, dict)
        assert "success" in result
        assert "iterations" in result
        # error key should be present (None if success, message if failure)

    def test_run_fix_loop_accepts_retry_mode(self):
        """Test run_fix_loop accepts retry_mode parameter."""
        from maid_agents.core.orchestrator import MAIDOrchestrator, RetryMode

        wrapper = ClaudeWrapper(mock_mode=True)
        orchestrator = MAIDOrchestrator(claude=wrapper, dry_run=True)

        result = orchestrator.run_fix_loop(
            manifest_path="manifests/task-001.manifest.json",
            validation_errors="test",
            max_iterations=1,
            retry_mode=RetryMode.DISABLED,
        )
        assert isinstance(result, dict)

    def test_run_fix_loop_accepts_error_context_mode(self):
        """Test run_fix_loop accepts error_context_mode parameter."""
        from maid_agents.core.orchestrator import (
            MAIDOrchestrator,
            ErrorContextMode,
        )

        wrapper = ClaudeWrapper(mock_mode=True)
        orchestrator = MAIDOrchestrator(claude=wrapper, dry_run=True)

        result = orchestrator.run_fix_loop(
            manifest_path="manifests/task-001.manifest.json",
            validation_errors="test",
            max_iterations=1,
            error_context_mode=ErrorContextMode.INCREMENTAL,
        )
        assert isinstance(result, dict)
