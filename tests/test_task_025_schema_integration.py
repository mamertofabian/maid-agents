"""Behavioral tests for task-025: Schema Integration.

Tests that ManifestArchitect retrieves and uses the MAID schema
when generating manifests.
"""

from unittest.mock import Mock, patch

from maid_agents.agents.manifest_architect import ManifestArchitect
from maid_agents.claude.cli_wrapper import ClaudeWrapper, ClaudeResponse


class TestManifestArchitectSchemaIntegration:
    """Test that ManifestArchitect uses the schema when generating manifests."""

    def test_manifest_architect_retrieves_schema(self):
        """ManifestArchitect should retrieve schema before generating manifest."""
        # Create mock for ClaudeWrapper instance
        mock_claude_instance = Mock(spec=ClaudeWrapper)
        mock_claude_instance.mock_mode = False
        mock_claude_instance.generate.return_value = ClaudeResponse(
            success=True, result="Manifest created", error=""
        )

        # Mock subprocess to capture maid schema call
        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = (
                '{"$schema": "https://example.com/schema", "properties": {}}'
            )
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            # Patch ClaudeWrapper constructor to prevent real API calls
            with patch(
                "maid_agents.agents.manifest_architect.ClaudeWrapper"
            ) as mock_wrapper_class:
                mock_wrapper_class.return_value = mock_claude_instance

                # Create architect with simple mock
                simple_mock = Mock(spec=ClaudeWrapper)
                simple_mock.mock_mode = False
                simple_mock.model = "test-model"
                simple_mock.timeout = 300
                simple_mock.temperature = 0.0
                architect = ManifestArchitect(claude=simple_mock)

                # Mock file operations to avoid actual file creation
                with patch("glob.glob") as mock_glob:
                    mock_glob.return_value = ["manifests/task-001-test.manifest.json"]
                    with patch("builtins.open", create=True) as mock_open:
                        mock_open.return_value.__enter__.return_value.read.return_value = (
                            '{"goal": "test"}'
                        )

                        # Call create_manifest
                        architect.create_manifest(goal="Test goal", task_number=1)

        # Should have called maid schema command
        assert any(
            "maid" in str(call) and "schema" in str(call)
            for call in mock_run.call_args_list
        )

    def test_schema_included_in_claude_prompt(self):
        """The schema should be included in the prompt sent to Claude."""
        # Capture the prompt sent to Claude
        captured_prompt = None

        def capture_generate(prompt):
            nonlocal captured_prompt
            captured_prompt = prompt
            return ClaudeResponse(success=True, result="Manifest created", error="")

        # Mock ClaudeWrapper to capture the prompt
        mock_claude_instance = Mock(spec=ClaudeWrapper)
        mock_claude_instance.mock_mode = False
        mock_claude_instance.model = "claude-sonnet-4-5-20250929"
        mock_claude_instance.timeout = 300
        mock_claude_instance.temperature = 0.0
        mock_claude_instance.generate = capture_generate

        # Mock subprocess for maid schema
        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = '{"$schema": "http://json-schema.org/draft-07/schema#", "properties": {}}'
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            # Patch ClaudeWrapper constructor to return our mock
            with patch(
                "maid_agents.agents.manifest_architect.ClaudeWrapper"
            ) as mock_wrapper_class:
                mock_wrapper_class.return_value = mock_claude_instance

                # Create architect with a simple mock
                simple_mock_claude = Mock(spec=ClaudeWrapper)
                simple_mock_claude.mock_mode = False
                simple_mock_claude.model = "claude-sonnet-4-5-20250929"
                simple_mock_claude.timeout = 300
                simple_mock_claude.temperature = 0.0
                architect = ManifestArchitect(claude=simple_mock_claude)

                # Mock file operations
                with patch("glob.glob") as mock_glob:
                    mock_glob.return_value = ["manifests/task-001-test.manifest.json"]
                    with patch("builtins.open", create=True) as mock_open:
                        mock_open.return_value.__enter__.return_value.read.return_value = (
                            '{"goal": "test"}'
                        )

                        # Call create_manifest
                        architect.create_manifest(goal="Test goal", task_number=1)

        # Verify schema was included in prompt
        assert captured_prompt is not None
        # The schema should be mentioned or included as JSON in the prompt
        assert (
            "schema" in captured_prompt.lower()
            or "json-schema" in captured_prompt.lower()
        )

    def test_manifest_generation_works_without_schema(self):
        """ManifestArchitect should still work if schema retrieval fails."""
        # Create mock for ClaudeWrapper instance
        mock_claude_instance = Mock(spec=ClaudeWrapper)
        mock_claude_instance.mock_mode = False
        mock_claude_instance.generate.return_value = ClaudeResponse(
            success=True, result="Manifest created", error=""
        )

        # Mock subprocess to simulate schema command failure
        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1  # Command failed
            mock_result.stdout = ""
            mock_result.stderr = "Error running maid schema"
            mock_run.return_value = mock_result

            # Patch ClaudeWrapper constructor to prevent real API calls
            with patch(
                "maid_agents.agents.manifest_architect.ClaudeWrapper"
            ) as mock_wrapper_class:
                mock_wrapper_class.return_value = mock_claude_instance

                # Create architect with simple mock
                simple_mock = Mock(spec=ClaudeWrapper)
                simple_mock.mock_mode = False
                simple_mock.model = "test-model"
                simple_mock.timeout = 300
                simple_mock.temperature = 0.0
                architect = ManifestArchitect(claude=simple_mock)

                # Mock file operations
                with patch("glob.glob") as mock_glob:
                    mock_glob.return_value = ["manifests/task-001-test.manifest.json"]
                    with patch("builtins.open", create=True) as mock_open:
                        mock_open.return_value.__enter__.return_value.read.return_value = (
                            '{"goal": "test"}'
                        )

                        # Should still succeed even without schema
                        result = architect.create_manifest(
                            goal="Test goal", task_number=1
                        )
                        assert result["success"]


class TestManifestArchitectExecute:
    """Test the execute method of ManifestArchitect."""

    def test_execute_returns_ready_status(self):
        """ManifestArchitect.execute() should return ready status."""
        mock_claude = Mock(spec=ClaudeWrapper)
        architect = ManifestArchitect(claude=mock_claude)

        result = architect.execute()

        assert result["status"] == "ready"
        assert result["agent"] == "ManifestArchitect"
