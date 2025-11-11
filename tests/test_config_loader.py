"""Tests for configuration file loader."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from maid_agents.config.config_loader import (
    CLIConfig,
    load_config,
    get_config_example,
    _merge_config,
)


def test_cli_config_defaults():
    """Test CLIConfig has correct default values."""
    config = CLIConfig()

    assert config.log_level == "INFO"
    assert config.mock_mode is False
    assert config.max_planning_iterations == 10
    assert config.max_implementation_iterations == 20
    assert config.max_refinement_iterations == 5
    assert config.manifest_dir == "manifests"
    assert config.test_dir == "tests"


def test_load_config_with_no_files():
    """Test load_config returns defaults when no config files exist."""
    import os

    # Run in temporary directory to avoid loading project's .ccmaid.toml
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            config = load_config()

            assert isinstance(config, CLIConfig)
            assert config.log_level == "INFO"
            assert config.mock_mode is False
        finally:
            os.chdir(original_cwd)


def test_merge_config_with_cli_section():
    """Test merging CLI section from TOML file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """
[cli]
log_level = "DEBUG"
mock_mode = true
"""
        )
        f.flush()
        config_path = Path(f.name)

    try:
        base_config = CLIConfig()
        merged_config = _merge_config(base_config, config_path)

        assert merged_config.log_level == "DEBUG"
        assert merged_config.mock_mode is True
    finally:
        config_path.unlink()


def test_merge_config_with_iterations_section():
    """Test merging iterations section from TOML file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """
[iterations]
max_planning_iterations = 15
max_implementation_iterations = 25
max_refinement_iterations = 8
"""
        )
        f.flush()
        config_path = Path(f.name)

    try:
        base_config = CLIConfig()
        merged_config = _merge_config(base_config, config_path)

        assert merged_config.max_planning_iterations == 15
        assert merged_config.max_implementation_iterations == 25
        assert merged_config.max_refinement_iterations == 8
    finally:
        config_path.unlink()


def test_merge_config_with_directories_section():
    """Test merging directories section from TOML file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """
[directories]
manifest_dir = "custom/manifests"
test_dir = "custom/tests"
"""
        )
        f.flush()
        config_path = Path(f.name)

    try:
        base_config = CLIConfig()
        merged_config = _merge_config(base_config, config_path)

        assert merged_config.manifest_dir == "custom/manifests"
        assert merged_config.test_dir == "custom/tests"
    finally:
        config_path.unlink()


def test_merge_config_with_complete_file():
    """Test merging complete config file with all sections."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """
[cli]
log_level = "WARNING"
mock_mode = true

[iterations]
max_planning_iterations = 12
max_implementation_iterations = 30
max_refinement_iterations = 10

[directories]
manifest_dir = "my_manifests"
test_dir = "my_tests"
"""
        )
        f.flush()
        config_path = Path(f.name)

    try:
        base_config = CLIConfig()
        merged_config = _merge_config(base_config, config_path)

        # CLI settings
        assert merged_config.log_level == "WARNING"
        assert merged_config.mock_mode is True

        # Iteration limits
        assert merged_config.max_planning_iterations == 12
        assert merged_config.max_implementation_iterations == 30
        assert merged_config.max_refinement_iterations == 10

        # Directories
        assert merged_config.manifest_dir == "my_manifests"
        assert merged_config.test_dir == "my_tests"
    finally:
        config_path.unlink()


def test_merge_config_with_invalid_file():
    """Test that invalid config file doesn't crash and uses defaults."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("invalid toml content {{{")
        f.flush()
        config_path = Path(f.name)

    try:
        base_config = CLIConfig()
        # Should not raise exception, just return base config
        merged_config = _merge_config(base_config, config_path)

        # Should still have defaults
        assert merged_config.log_level == "INFO"
        assert merged_config.mock_mode is False
    finally:
        config_path.unlink()


def test_merge_config_with_missing_file():
    """Test that missing config file doesn't crash."""
    base_config = CLIConfig()
    non_existent_path = Path("/tmp/nonexistent_ccmaid_config_12345.toml")

    # Should not raise exception
    merged_config = _merge_config(base_config, non_existent_path)

    # Should still have defaults
    assert merged_config.log_level == "INFO"
    assert merged_config.mock_mode is False


def test_get_config_example():
    """Test get_config_example returns valid TOML string."""
    example = get_config_example()

    assert isinstance(example, str)
    assert len(example) > 0
    assert "[cli]" in example
    assert "[iterations]" in example
    assert "[directories]" in example
    assert "log_level" in example
    assert "mock_mode" in example
    assert "max_planning_iterations" in example


def test_merge_config_partial_sections():
    """Test that partial sections don't override unspecified values."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """
[cli]
log_level = "ERROR"
# mock_mode not specified, should keep default
"""
        )
        f.flush()
        config_path = Path(f.name)

    try:
        base_config = CLIConfig()
        merged_config = _merge_config(base_config, config_path)

        # Specified value should be updated
        assert merged_config.log_level == "ERROR"
        # Unspecified value should keep default
        assert merged_config.mock_mode is False
    finally:
        config_path.unlink()
