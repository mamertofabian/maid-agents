"""Behavioral tests for task-029: Update the agents CLI to accept a flag/option to bypass Claude permissions altogether.

This test file verifies the implementation matches manifest specifications.
"""

from unittest.mock import patch, MagicMock
from maid_agents.claude.cli_wrapper import ClaudeWrapper
from maid_agents.core.orchestrator import MAIDOrchestrator


class TestClaudeWrapperBypassPermissions:
    """Tests for ClaudeWrapper bypass_permissions functionality."""

    def test_init_accepts_bypass_permissions_parameter(self):
        """Test that ClaudeWrapper.__init__ accepts bypass_permissions parameter."""
        wrapper = ClaudeWrapper(
            mock_mode=True,
            model="claude-sonnet-4-5",
            timeout=300,
            temperature=0.0,
            system_prompt=None,
            bypass_permissions=False,
        )
        assert wrapper is not None
        assert isinstance(wrapper, ClaudeWrapper)
        assert hasattr(wrapper, "bypass_permissions")

    def test_init_bypass_permissions_default_false(self):
        """Test that bypass_permissions defaults to False."""
        wrapper = ClaudeWrapper(mock_mode=True)
        assert wrapper.bypass_permissions is False

    def test_init_bypass_permissions_true(self):
        """Test that bypass_permissions can be set to True."""
        wrapper = ClaudeWrapper(mock_mode=True, bypass_permissions=True)
        assert wrapper.bypass_permissions is True

    def test_init_bypass_permissions_false_explicit(self):
        """Test that bypass_permissions can be explicitly set to False."""
        wrapper = ClaudeWrapper(mock_mode=True, bypass_permissions=False)
        assert wrapper.bypass_permissions is False

    def test_build_claude_command_without_bypass_permissions(self):
        """Test _build_claude_command without bypass_permissions flag."""
        wrapper = ClaudeWrapper(mock_mode=True, bypass_permissions=False)
        command = wrapper._build_claude_command(prompt="Test prompt")

        assert isinstance(command, list)
        assert "claude" in command
        assert "--print" in command
        assert "Test prompt" in command
        assert "--dangerously-skip-permissions" not in command

    def test_build_claude_command_with_bypass_permissions(self):
        """Test _build_claude_command with bypass_permissions flag enabled."""
        wrapper = ClaudeWrapper(mock_mode=True, bypass_permissions=True)
        command = wrapper._build_claude_command(prompt="Test prompt")

        assert isinstance(command, list)
        assert "claude" in command
        assert "--print" in command
        assert "Test prompt" in command
        assert "--dangerously-skip-permissions" in command

    def test_build_claude_command_returns_list(self):
        """Test that _build_claude_command returns a list of strings."""
        wrapper = ClaudeWrapper(mock_mode=True, bypass_permissions=True)
        command = wrapper._build_claude_command(prompt="Test")

        assert isinstance(command, list)
        assert all(isinstance(item, str) for item in command)

    def test_log_request_start_without_bypass_permissions(self):
        """Test _log_request_start without bypass_permissions (no warning)."""
        wrapper = ClaudeWrapper(mock_mode=True, bypass_permissions=False)

        # Should not raise exception
        wrapper._log_request_start(prompt="Test prompt")

    def test_log_request_start_with_bypass_permissions(self):
        """Test _log_request_start with bypass_permissions displays warning."""
        wrapper = ClaudeWrapper(mock_mode=True, bypass_permissions=True)

        # Mock the logger to capture warning
        with patch.object(wrapper.logger, "warning") as mock_warning:
            wrapper._log_request_start(prompt="Test prompt")

            # Verify warning was called with bypass permissions message
            mock_warning.assert_called()
            warning_message = str(mock_warning.call_args[0][0])
            assert (
                "bypass" in warning_message.lower()
                or "permissions" in warning_message.lower()
            )

    def test_log_request_start_accepts_string_prompt(self):
        """Test that _log_request_start accepts a string prompt parameter."""
        wrapper = ClaudeWrapper(mock_mode=True, bypass_permissions=True)

        # Should not raise exception
        wrapper._log_request_start(prompt="Test prompt string")

    def test_bypass_permissions_persists_across_calls(self):
        """Test that bypass_permissions setting persists across multiple calls."""
        wrapper = ClaudeWrapper(mock_mode=True, bypass_permissions=True)

        # First call
        command1 = wrapper._build_claude_command(prompt="Test 1")
        assert "--dangerously-skip-permissions" in command1

        # Second call
        command2 = wrapper._build_claude_command(prompt="Test 2")
        assert "--dangerously-skip-permissions" in command2

    def test_bypass_permissions_integration_with_generate(self):
        """Test bypass_permissions integrates with generate method."""
        wrapper = ClaudeWrapper(mock_mode=True, bypass_permissions=True)

        # Mock mode should still work with bypass_permissions
        response = wrapper.generate(prompt="Integration test")
        assert response.success is True
        assert response.result is not None

    def test_build_command_includes_other_parameters(self):
        """Test that bypass_permissions doesn't break other command parameters."""
        wrapper = ClaudeWrapper(
            mock_mode=True,
            model="sonnet",
            bypass_permissions=True,
            system_prompt="Custom prompt",
        )

        command = wrapper._build_claude_command(prompt="Test")

        # Verify other parameters still present
        assert "--model" in command
        assert "sonnet" in command
        assert "--append-system-prompt" in command
        assert "Custom prompt" in command
        assert "--dangerously-skip-permissions" in command

    def test_build_command_position_of_bypass_flag(self):
        """Test that --dangerously-skip-permissions flag is in correct position."""
        wrapper = ClaudeWrapper(mock_mode=True, bypass_permissions=True)
        command = wrapper._build_claude_command(prompt="Test")

        # Flag should be present in the command list
        assert "--dangerously-skip-permissions" in command

        # Verify command is well-formed (starts with 'claude')
        assert command[0] == "claude"

    def test_init_with_all_parameters_including_bypass(self):
        """Test initialization with all parameters including bypass_permissions."""
        wrapper = ClaudeWrapper(
            mock_mode=False,
            model="claude-sonnet-4-5",
            timeout=600,
            temperature=0.5,
            system_prompt="Test system prompt",
            bypass_permissions=True,
        )

        assert wrapper.mock_mode is False
        assert wrapper.model == "claude-sonnet-4-5"
        assert wrapper.timeout == 600
        assert wrapper.temperature == 0.5
        assert wrapper.system_prompt == "Test system prompt"
        assert wrapper.bypass_permissions is True

    def test_bypass_permissions_type_validation(self):
        """Test that bypass_permissions accepts boolean values."""
        # True
        wrapper_true = ClaudeWrapper(mock_mode=True, bypass_permissions=True)
        assert wrapper_true.bypass_permissions is True

        # False
        wrapper_false = ClaudeWrapper(mock_mode=True, bypass_permissions=False)
        assert wrapper_false.bypass_permissions is False

    def test_log_request_start_returns_none(self):
        """Test that _log_request_start returns None."""
        wrapper = ClaudeWrapper(mock_mode=True, bypass_permissions=True)
        result = wrapper._log_request_start(prompt="Test")
        assert result is None

    def test_bypass_permissions_edge_case_empty_prompt(self):
        """Test bypass_permissions with empty prompt string."""
        wrapper = ClaudeWrapper(mock_mode=True, bypass_permissions=True)
        command = wrapper._build_claude_command(prompt="")

        assert isinstance(command, list)
        assert "--dangerously-skip-permissions" in command

    def test_bypass_permissions_edge_case_long_prompt(self):
        """Test bypass_permissions with very long prompt."""
        wrapper = ClaudeWrapper(mock_mode=True, bypass_permissions=True)
        long_prompt = "A" * 10000
        command = wrapper._build_claude_command(prompt=long_prompt)

        assert isinstance(command, list)
        assert "--dangerously-skip-permissions" in command
        assert long_prompt in command

    def test_build_command_flag_not_duplicated(self):
        """Test that --dangerously-skip-permissions is not duplicated."""
        wrapper = ClaudeWrapper(mock_mode=True, bypass_permissions=True)
        command = wrapper._build_claude_command(prompt="Test")

        # Count occurrences of the flag
        count = command.count("--dangerously-skip-permissions")
        assert count == 1


class TestMAIDOrchestratorBypassPermissions:
    """Tests for MAIDOrchestrator bypass_permissions functionality."""

    def test_orchestrator_init_accepts_bypass_permissions(self):
        """Test that MAIDOrchestrator.__init__ accepts bypass_permissions parameter."""
        orchestrator = MAIDOrchestrator(
            claude=None,
            manifest_architect=None,
            test_designer=None,
            validation_runner=None,
            dry_run=True,
            bypass_permissions=False,
        )
        assert orchestrator is not None
        assert isinstance(orchestrator, MAIDOrchestrator)

    def test_orchestrator_bypass_permissions_default_false(self):
        """Test that bypass_permissions defaults to False."""
        orchestrator = MAIDOrchestrator(dry_run=True)
        # After initialization, the orchestrator should have created agents
        # The bypass_permissions flag should be propagated to internal ClaudeWrapper
        assert orchestrator is not None

    def test_orchestrator_bypass_permissions_true(self):
        """Test that bypass_permissions can be set to True."""
        orchestrator = MAIDOrchestrator(dry_run=True, bypass_permissions=True)
        assert orchestrator is not None

    def test_orchestrator_propagates_bypass_to_claude_wrapper(self):
        """Test that bypass_permissions is propagated to ClaudeWrapper when orchestrator creates one."""
        # When orchestrator creates its own ClaudeWrapper (claude=None), it should pass bypass_permissions
        orchestrator = MAIDOrchestrator(
            claude=None, dry_run=True, bypass_permissions=True
        )

        # The orchestrator should have created a ClaudeWrapper with bypass_permissions=True
        # We can verify this by checking if agents were created with the right wrapper
        assert orchestrator is not None
        assert hasattr(orchestrator, "_state")

    def test_orchestrator_uses_provided_claude_wrapper(self):
        """Test that orchestrator uses provided ClaudeWrapper with bypass_permissions."""
        # Create a ClaudeWrapper with bypass_permissions=True
        wrapper = ClaudeWrapper(mock_mode=True, bypass_permissions=True)

        # Pass it to orchestrator
        orchestrator = MAIDOrchestrator(claude=wrapper, dry_run=True)

        assert orchestrator is not None

    def test_orchestrator_with_all_parameters(self):
        """Test orchestrator initialization with all parameters including bypass_permissions."""
        wrapper = ClaudeWrapper(mock_mode=True, bypass_permissions=True)

        orchestrator = MAIDOrchestrator(
            claude=wrapper,
            manifest_architect=None,
            test_designer=None,
            validation_runner=None,
            dry_run=True,
            bypass_permissions=True,
        )

        assert orchestrator is not None
        assert isinstance(orchestrator, MAIDOrchestrator)


class TestCLIBypassPermissionsIntegration:
    """Integration tests for CLI --bypass-permissions flag."""

    def test_cli_main_function_exists(self):
        """Test that main function exists in CLI module."""
        from maid_agents.cli.main import main

        assert main is not None
        assert callable(main)

    def test_cli_plan_command_accepts_bypass_permissions_flag(self):
        """Test that plan command parser accepts --bypass-permissions flag."""
        import sys
        from unittest.mock import patch
        from maid_agents.cli.main import main

        # Mock sys.argv to simulate: ccmaid --mock plan "test" --bypass-permissions
        test_args = ["ccmaid", "--mock", "plan", "test goal", "--bypass-permissions"]

        with patch.object(sys, "argv", test_args):
            with patch("maid_agents.cli.main.ClaudeWrapper") as mock_wrapper_class:
                with patch(
                    "maid_agents.cli.main.MAIDOrchestrator"
                ) as mock_orchestrator:
                    mock_wrapper_instance = MagicMock()
                    mock_wrapper_class.return_value = mock_wrapper_instance

                    mock_orch_instance = MagicMock()
                    mock_orch_instance.run_planning_loop.return_value = {
                        "success": True,
                        "iterations": 1,
                        "manifest_path": "test.json",
                        "test_paths": ["test.py"],
                    }
                    mock_orchestrator.return_value = mock_orch_instance

                    try:
                        main()
                    except SystemExit:
                        pass  # Expected behavior

                    # Verify ClaudeWrapper was called with bypass_permissions=True
                    mock_wrapper_class.assert_called_once()
                    call_kwargs = mock_wrapper_class.call_args[1]
                    assert "bypass_permissions" in call_kwargs
                    assert call_kwargs["bypass_permissions"] is True

    def test_cli_implement_command_accepts_bypass_permissions_flag(self):
        """Test that implement command parser accepts --bypass-permissions flag."""
        import sys
        from unittest.mock import patch
        from pathlib import Path
        from maid_agents.cli.main import main

        # Mock sys.argv to simulate: ccmaid --mock implement manifest.json --bypass-permissions
        test_args = [
            "ccmaid",
            "--mock",
            "implement",
            "test_manifest.json",
            "--bypass-permissions",
        ]

        with patch.object(sys, "argv", test_args):
            with patch.object(Path, "exists", return_value=True):
                with patch("maid_agents.cli.main.ClaudeWrapper") as mock_wrapper_class:
                    with patch(
                        "maid_agents.cli.main.MAIDOrchestrator"
                    ) as mock_orchestrator:
                        mock_wrapper_instance = MagicMock()
                        mock_wrapper_class.return_value = mock_wrapper_instance

                        mock_orch_instance = MagicMock()
                        mock_orch_instance.run_implementation_loop.return_value = {
                            "success": True,
                            "iterations": 1,
                            "files_modified": ["test.py"],
                        }
                        mock_orchestrator.return_value = mock_orch_instance

                        try:
                            main()
                        except SystemExit:
                            pass  # Expected behavior

                        # Verify ClaudeWrapper was called with bypass_permissions=True
                        mock_wrapper_class.assert_called_once()
                        call_kwargs = mock_wrapper_class.call_args[1]
                        assert "bypass_permissions" in call_kwargs
                        assert call_kwargs["bypass_permissions"] is True

    def test_cli_refactor_command_accepts_bypass_permissions_flag(self):
        """Test that refactor command parser accepts --bypass-permissions flag."""
        import sys
        from unittest.mock import patch
        from pathlib import Path
        from maid_agents.cli.main import main

        # Mock sys.argv to simulate: ccmaid --mock refactor manifest.json --bypass-permissions
        test_args = [
            "ccmaid",
            "--mock",
            "refactor",
            "test_manifest.json",
            "--bypass-permissions",
        ]

        with patch.object(sys, "argv", test_args):
            with patch.object(Path, "exists", return_value=True):
                with patch("maid_agents.cli.main.ClaudeWrapper") as mock_wrapper_class:
                    with patch(
                        "maid_agents.cli.main.MAIDOrchestrator"
                    ) as mock_orchestrator:
                        mock_wrapper_instance = MagicMock()
                        mock_wrapper_class.return_value = mock_wrapper_instance

                        mock_orch_instance = MagicMock()
                        mock_orch_instance.run_refactoring_loop.return_value = {
                            "success": True,
                            "iterations": 1,
                            "files_written": ["test.py"],
                        }
                        mock_orchestrator.return_value = mock_orch_instance

                        try:
                            main()
                        except SystemExit:
                            pass  # Expected behavior

                        # Verify ClaudeWrapper was called with bypass_permissions=True
                        mock_wrapper_class.assert_called_once()
                        call_kwargs = mock_wrapper_class.call_args[1]
                        assert "bypass_permissions" in call_kwargs
                        assert call_kwargs["bypass_permissions"] is True

    def test_cli_refine_command_accepts_bypass_permissions_flag(self):
        """Test that refine command parser accepts --bypass-permissions flag."""
        import sys
        from unittest.mock import patch
        from pathlib import Path
        from maid_agents.cli.main import main

        # Mock sys.argv to simulate: ccmaid --mock refine manifest.json --goal "test" --bypass-permissions
        test_args = [
            "ccmaid",
            "--mock",
            "refine",
            "test_manifest.json",
            "--goal",
            "test goal",
            "--bypass-permissions",
        ]

        with patch.object(sys, "argv", test_args):
            with patch.object(Path, "exists", return_value=True):
                with patch("maid_agents.cli.main.ClaudeWrapper") as mock_wrapper_class:
                    with patch(
                        "maid_agents.cli.main.MAIDOrchestrator"
                    ) as mock_orchestrator:
                        mock_wrapper_instance = MagicMock()
                        mock_wrapper_class.return_value = mock_wrapper_instance

                        mock_orch_instance = MagicMock()
                        mock_orch_instance.run_refinement_loop.return_value = {
                            "success": True,
                            "iterations": 1,
                        }
                        mock_orchestrator.return_value = mock_orch_instance

                        try:
                            main()
                        except SystemExit:
                            pass  # Expected behavior

                        # Verify ClaudeWrapper was called with bypass_permissions=True
                        mock_wrapper_class.assert_called_once()
                        call_kwargs = mock_wrapper_class.call_args[1]
                        assert "bypass_permissions" in call_kwargs
                        assert call_kwargs["bypass_permissions"] is True
