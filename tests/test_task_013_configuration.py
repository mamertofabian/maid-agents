"""Behavioral tests for Task-013: Configuration System."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from maid_agents.config.config_loader import CLIConfig, load_config, get_config_example


def test_cli_config_instantiation():
    """Test CLIConfig can be instantiated with defaults."""
    config = CLIConfig()
    assert config is not None
    assert isinstance(config, CLIConfig)


def test_cli_config_has_claude_settings():
    """Test CLIConfig has Claude-specific settings."""
    config = CLIConfig()

    # Claude settings
    assert hasattr(config, "claude_model")
    assert hasattr(config, "claude_timeout")
    assert hasattr(config, "claude_temperature")

    # Verify defaults
    assert config.claude_model == "claude-sonnet-4-5-20250929"
    assert config.claude_timeout == 300
    assert config.claude_temperature == 0.0


def test_cli_config_has_maid_settings():
    """Test CLIConfig has MAID-specific settings."""
    config = CLIConfig()

    # MAID settings
    assert hasattr(config, "manifest_dir")
    assert hasattr(config, "test_dir")
    assert hasattr(config, "max_planning_iterations")
    assert hasattr(config, "max_implementation_iterations")
    assert hasattr(config, "max_refinement_iterations")
    assert hasattr(config, "use_manifest_chain")

    # Verify defaults
    assert config.manifest_dir == "manifests"
    assert config.test_dir == "tests"
    assert config.max_planning_iterations == 10
    assert config.max_implementation_iterations == 20
    assert config.max_refinement_iterations == 5
    assert config.use_manifest_chain is True


def test_cli_config_has_cli_settings():
    """Test CLIConfig has CLI-specific settings."""
    config = CLIConfig()

    # CLI settings
    assert hasattr(config, "log_level")
    assert hasattr(config, "mock_mode")

    # Verify defaults
    assert config.log_level == "INFO"
    assert config.mock_mode is False


def test_load_config_function():
    """Test load_config() function returns CLIConfig."""
    config = load_config()

    assert config is not None
    assert isinstance(config, CLIConfig)

    # Should have all required attributes
    assert hasattr(config, "claude_model")
    assert hasattr(config, "manifest_dir")
    assert hasattr(config, "log_level")


def test_get_config_example_function():
    """Test get_config_example() returns valid TOML example."""
    example = get_config_example()

    assert example is not None
    assert isinstance(example, str)
    assert len(example) > 0

    # Should contain TOML sections
    assert "[cli]" in example
    assert "[claude]" in example
    assert "[iterations]" in example
    assert "[directories]" in example
    assert "[maid]" in example

    # Should contain key settings
    assert "log_level" in example
    assert "model" in example
    assert "timeout" in example
    assert "temperature" in example
    assert "manifest_dir" in example
    assert "use_manifest_chain" in example
