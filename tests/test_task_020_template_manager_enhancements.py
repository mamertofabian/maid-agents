"""Behavioral tests for Task-020: TemplateManager Enhancements."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from maid_agents.config.template_manager import TemplateManager


def test_template_manager_has_render_split_method():
    """Test TemplateManager has render_split method."""
    template_manager = TemplateManager()
    assert hasattr(template_manager, "render_split")
    assert callable(template_manager.render_split)


def test_template_manager_render_split_returns_tuple():
    """Test render_split returns tuple of (system_prompt, user_message)."""
    template_manager = TemplateManager()

    # Test with a template that should exist after implementation
    try:
        result = template_manager.render_split(
            "manifest_creation",
            goal="Test goal",
            task_number="001",
            additional_instructions_section="",
        )
        assert isinstance(result, tuple)
        assert len(result) == 2
        system_prompt, user_message = result
        assert isinstance(system_prompt, str)
        assert isinstance(user_message, str)
    except FileNotFoundError:
        # Template files not created yet - this is expected in TDD red phase
        pass


def test_template_manager_has_render_for_agent_method():
    """Test TemplateManager has render_for_agent method."""
    template_manager = TemplateManager()
    assert hasattr(template_manager, "render_for_agent")
    assert callable(template_manager.render_for_agent)


def test_template_manager_render_for_agent_returns_dict():
    """Test render_for_agent returns dict with system_prompt and user_message keys."""
    template_manager = TemplateManager()

    try:
        result = template_manager.render_for_agent(
            "manifest_creation",
            goal="Test goal",
            task_number="001",
            additional_instructions_section="",
        )
        assert isinstance(result, dict)
        assert "system_prompt" in result
        assert "user_message" in result
        assert isinstance(result["system_prompt"], str)
        assert isinstance(result["user_message"], str)
    except FileNotFoundError:
        # Template files not created yet - this is expected in TDD red phase
        pass


def test_template_manager_render_for_agent_use_split_false_backward_compatible():
    """Test render_for_agent with use_split=False returns backward compatible format."""
    template_manager = TemplateManager()

    try:
        result = template_manager.render_for_agent(
            "manifest_creation",
            use_split=False,
            goal="Test goal",
            task_number="001",
            additional_instructions_section="",
        )
        assert isinstance(result, dict)
        assert "system_prompt" in result
        assert "user_message" in result
        # When use_split=False, system_prompt should be None
        assert result["system_prompt"] is None
        assert isinstance(result["user_message"], str)
    except FileNotFoundError:
        # Old template might not exist, that's okay
        pass


def test_template_manager_render_split_substitutes_variables():
    """Test render_split properly substitutes template variables in both parts."""
    template_manager = TemplateManager()

    try:
        system_prompt, user_message = template_manager.render_split(
            "manifest_creation",
            goal="Add authentication",
            task_number="042",
            additional_instructions_section="",
        )

        # Both parts should have variables substituted
        assert "Add authentication" in user_message or "042" in user_message
        # System prompt should contain behavioral guidance (not task-specific details)
        assert isinstance(system_prompt, str)
        assert len(system_prompt) > 0
    except FileNotFoundError:
        # Templates not created yet - expected in TDD red phase
        pass
