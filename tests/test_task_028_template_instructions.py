"""Test task-028: Template rendering with instructions.

This test verifies that templates properly render the additional_instructions_section
variable when instructions are provided.
"""

from maid_agents.config.template_manager import get_template_manager


class TestTemplateInstructions:
    """Test template rendering with instructions."""

    def test_manifest_creation_template_with_instructions(self):
        """Test that manifest_creation template renders with instructions."""
        # Arrange
        manager = get_template_manager()
        additional_instructions_section = """
## Additional Instructions

Use dependency injection pattern.

Please incorporate these instructions when creating the manifest.
"""

        # Act
        prompts = manager.render_for_agent(
            "manifest_creation",
            task_number="001",
            goal="Test goal",
            additional_instructions_section=additional_instructions_section,
        )

        # Assert
        assert "system_prompt" in prompts
        assert "user_message" in prompts
        assert "dependency injection" in prompts["user_message"]
        assert "Additional Instructions" in prompts["user_message"]

    def test_manifest_creation_template_without_instructions(self):
        """Test that manifest_creation template works without instructions."""
        # Arrange
        manager = get_template_manager()

        # Act
        prompts = manager.render_for_agent(
            "manifest_creation",
            task_number="001",
            goal="Test goal",
            additional_instructions_section="",
        )

        # Assert
        assert "system_prompt" in prompts
        assert "user_message" in prompts
        # Should not contain instructions section when empty
        assert "Additional Instructions" not in prompts["user_message"]

    def test_implementation_template_with_instructions(self):
        """Test that implementation template renders with instructions."""
        # Arrange
        manager = get_template_manager()
        additional_instructions_section = """
## Additional Instructions

Follow pattern Y.

Please incorporate these instructions when implementing.
"""

        # Act
        prompts = manager.render_for_agent(
            "implementation",
            manifest_path="manifests/task-001.manifest.json",
            goal="Test goal",
            test_output="No tests yet",
            artifacts_summary="- Function: test()",
            files_to_modify="test.py",
            additional_instructions_section=additional_instructions_section,
        )

        # Assert
        assert "pattern Y" in prompts["user_message"]
        assert "Additional Instructions" in prompts["user_message"]

    def test_refactor_template_with_instructions(self):
        """Test that refactor template renders with instructions."""
        # Arrange
        manager = get_template_manager()
        additional_instructions_section = """
## Additional Instructions

Focus on performance.

Please incorporate these instructions when refactoring.
"""

        # Act
        prompts = manager.render_for_agent(
            "refactor",
            manifest_path="manifests/task-001.manifest.json",
            goal="Test goal",
            files_to_refactor="File: test.py\n```python\ncode\n```",
            test_file="tests/test.py",
            additional_instructions_section=additional_instructions_section,
        )

        # Assert
        assert "Focus on performance" in prompts["user_message"]
        assert "Additional Instructions" in prompts["user_message"]

    def test_refine_template_with_instructions(self):
        """Test that refine template renders with instructions."""
        # Arrange
        manager = get_template_manager()
        additional_instructions_section = """
## Additional Instructions

Add edge case tests.

Please incorporate these instructions when refining.
"""

        # Act
        prompts = manager.render_for_agent(
            "refine",
            manifest_path="manifests/task-001.manifest.json",
            test_file_path="tests/test.py",
            goal="Improve tests",
            validation_errors="None",
            additional_instructions_section=additional_instructions_section,
        )

        # Assert
        assert "Add edge case tests" in prompts["user_message"]
        assert "Additional Instructions" in prompts["user_message"]

    def test_all_templates_handle_empty_instructions(self):
        """Test that all templates work with empty instructions section."""
        # Arrange
        manager = get_template_manager()
        templates = [
            (
                "manifest_creation",
                {
                    "task_number": "001",
                    "goal": "Test",
                    "additional_instructions_section": "",
                },
            ),
            (
                "implementation",
                {
                    "manifest_path": "test.json",
                    "goal": "Test",
                    "test_output": "No tests",
                    "artifacts_summary": "None",
                    "files_to_modify": "test.py",
                    "additional_instructions_section": "",
                },
            ),
            (
                "refactor",
                {
                    "manifest_path": "test.json",
                    "goal": "Test",
                    "files_to_refactor": "code",
                    "test_file": "test.py",
                    "additional_instructions_section": "",
                },
            ),
            (
                "refine",
                {
                    "manifest_path": "test.json",
                    "test_file_path": "test.py",
                    "goal": "Test",
                    "validation_errors": "None",
                    "additional_instructions_section": "",
                },
            ),
        ]

        # Act & Assert
        for template_name, variables in templates:
            prompts = manager.render_for_agent(template_name, **variables)
            assert "system_prompt" in prompts
            assert "user_message" in prompts
            # Empty instructions should not add section
            assert "Additional Instructions" not in prompts["user_message"]
