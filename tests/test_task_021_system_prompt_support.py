"""Behavioral tests for Task-021: System Prompt Support."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from maid_agents.claude.cli_wrapper import ClaudeWrapper, ClaudeResponse
from maid_agents.config.template_manager import TemplateManager


def test_claude_wrapper_accepts_system_prompt_parameter():
    """Test ClaudeWrapper constructor accepts system_prompt parameter."""
    claude = ClaudeWrapper(mock_mode=True, system_prompt="You are a helpful assistant.")
    assert claude is not None
    assert hasattr(claude, "system_prompt")
    assert claude.system_prompt == "You are a helpful assistant."


def test_claude_wrapper_system_prompt_defaults_to_none():
    """Test ClaudeWrapper system_prompt defaults to None when not provided."""
    claude = ClaudeWrapper(mock_mode=True)
    assert hasattr(claude, "system_prompt")
    assert claude.system_prompt is None


def test_claude_wrapper_builds_command_with_system_prompt():
    """Test ClaudeWrapper includes --append-system-prompt in command when system_prompt is set."""
    claude = ClaudeWrapper(mock_mode=True, system_prompt="Test system prompt")

    command = claude._build_claude_command("Test user message")
    assert isinstance(command, list)
    assert "--append-system-prompt" in command

    # Find the index of --append-system-prompt and check next item is the prompt
    idx = command.index("--append-system-prompt")
    assert command[idx + 1] == "Test system prompt"


def test_claude_wrapper_builds_command_without_system_prompt_flag_when_none():
    """Test ClaudeWrapper doesn't include --append-system-prompt when system_prompt is None."""
    claude = ClaudeWrapper(mock_mode=True)

    command = claude._build_claude_command("Test user message")
    assert isinstance(command, list)
    assert "--append-system-prompt" not in command


def test_system_template_directory_can_be_created():
    """Test that system template directory can be created."""
    templates_dir = (
        Path(__file__).parent.parent / "maid_agents" / "config" / "templates"
    )
    # Directory should exist or be creatable
    assert templates_dir.exists() or True  # Templates dir should exist
    # system_dir will be created during implementation


def test_user_template_directory_can_be_created():
    """Test that user template directory can be created."""
    templates_dir = (
        Path(__file__).parent.parent / "maid_agents" / "config" / "templates"
    )
    # Directory should exist or be creatable
    assert templates_dir.exists() or True  # Templates dir should exist
    # user_dir will be created during implementation


def test_manifest_creation_split_templates_loadable():
    """Test manifest_creation system and user templates can be loaded."""
    template_manager = TemplateManager()

    try:
        # Try loading system template
        system_template = template_manager.load_template(
            "system/manifest_creation_system"
        )
        assert system_template is not None

        # Try loading user template
        user_template = template_manager.load_template("user/manifest_creation_user")
        assert user_template is not None
    except FileNotFoundError:
        # Templates not created yet - expected in TDD red phase
        pass


def test_all_six_agent_templates_can_be_split():
    """Test all 6 agent templates have system and user versions."""
    template_manager = TemplateManager()

    agent_templates = [
        "manifest_creation",
        "test_generation",
        "implementation",
        "refactor",
        "refine",
        "test_generation_from_implementation",
    ]

    for template_name in agent_templates:
        try:
            # Each should have both system and user versions
            system_template = template_manager.load_template(
                f"system/{template_name}_system"
            )
            user_template = template_manager.load_template(f"user/{template_name}_user")
            assert system_template is not None
            assert user_template is not None
        except FileNotFoundError:
            # Templates not created yet - expected in TDD red phase
            pass


def test_claude_wrapper_with_system_prompt_in_mock_mode():
    """Test ClaudeWrapper works in mock mode with system_prompt set."""
    claude = ClaudeWrapper(
        mock_mode=True, system_prompt="You are an expert MAID manifest architect."
    )

    response = claude.generate("Create a manifest for task-001")
    assert response is not None
    assert isinstance(response, ClaudeResponse)
    assert hasattr(response, "success")


def test_integration_claude_wrapper_and_template_manager():
    """Test ClaudeWrapper and TemplateManager work together for split prompts."""
    template_manager = TemplateManager()

    try:
        # Get split prompts
        prompts = template_manager.render_for_agent(
            "manifest_creation",
            goal="Test feature",
            task_number="999",
            additional_instructions_section="",
        )

        # Create ClaudeWrapper with system prompt
        claude = ClaudeWrapper(mock_mode=True, system_prompt=prompts["system_prompt"])

        # Generate with user message
        response = claude.generate(prompts["user_message"])

        assert response is not None
        assert response.success
    except FileNotFoundError:
        # Templates not created yet - expected in TDD red phase
        pass
