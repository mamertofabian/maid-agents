"""Configuration file loader for ccmaid CLI.

Loads configuration from:
1. .ccmaid.toml (project-level, current directory)
2. ~/.ccmaid.toml (user-level, home directory)
3. Defaults (if no config files found)

CLI arguments always override config file values.
"""

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # Python 3.10 and earlier

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional


_CLI_FIELD_MAPPING = {
    "log_level": "log_level",
    "mock_mode": "mock_mode",
}

_CLAUDE_FIELD_MAPPING = {
    "model": "claude_model",
    "timeout": "claude_timeout",
    "temperature": "claude_temperature",
}

_ITERATIONS_FIELD_MAPPING = {
    "max_planning_iterations": "max_planning_iterations",
    "max_implementation_iterations": "max_implementation_iterations",
    "max_refinement_iterations": "max_refinement_iterations",
}

_DIRECTORIES_FIELD_MAPPING = {
    "manifest_dir": "manifest_dir",
    "test_dir": "test_dir",
}

_MAID_FIELD_MAPPING = {
    "use_manifest_chain": "use_manifest_chain",
}


@dataclass
class CLIConfig:
    """CLI configuration from file or defaults.

    This unified configuration replaces the separate AgentConfig/ClaudeConfig/MAIDConfig
    from settings.py to provide a single source of truth for all ccmaid settings.
    """

    # CLI settings
    log_level: str = "INFO"
    mock_mode: bool = False

    # Claude Code settings
    claude_model: str = "claude-sonnet-4-5-20250929"
    claude_timeout: int = 300
    claude_temperature: float = 0.0

    # Iteration limits
    max_planning_iterations: int = 10
    max_implementation_iterations: int = 20
    max_refinement_iterations: int = 5

    # Directories
    manifest_dir: str = "manifests"
    test_dir: str = "tests"

    # MAID settings
    use_manifest_chain: bool = True


def load_config() -> CLIConfig:
    """Load configuration from TOML files.

    Search order:
    1. .ccmaid.toml in current directory (project config)
    2. ~/.ccmaid.toml in home directory (user config)
    3. Defaults if no config found

    Returns:
        CLIConfig with merged settings (project overrides user overrides defaults)
    """
    config = CLIConfig()

    for config_path in _get_config_paths():
        if config_path.exists():
            config = _merge_config(config, config_path)

    return config


def _merge_config(base_config: CLIConfig, config_path: Path) -> CLIConfig:
    """Merge TOML config file into base config.

    Args:
        base_config: Existing configuration
        config_path: Path to TOML config file

    Returns:
        Updated CLIConfig with values from file
    """
    toml_data = _load_toml_file(config_path)
    if toml_data is None:
        return base_config

    _merge_section(base_config, toml_data, "cli", _CLI_FIELD_MAPPING)
    _merge_section(base_config, toml_data, "claude", _CLAUDE_FIELD_MAPPING)
    _merge_section(base_config, toml_data, "iterations", _ITERATIONS_FIELD_MAPPING)
    _merge_section(base_config, toml_data, "directories", _DIRECTORIES_FIELD_MAPPING)
    _merge_section(base_config, toml_data, "maid", _MAID_FIELD_MAPPING)

    return base_config


def _get_config_paths() -> List[Path]:
    """Get list of config file paths in search order.

    Returns:
        List of paths to check (user config, then project config)
    """
    return [
        Path.home() / ".ccmaid.toml",
        Path.cwd() / ".ccmaid.toml",
    ]


def _load_toml_file(config_path: Path) -> Optional[Dict[str, Any]]:
    """Load TOML file and return parsed data.

    Args:
        config_path: Path to TOML config file

    Returns:
        Parsed TOML data as dictionary, or None if loading failed
    """
    try:
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    except (OSError, ValueError, tomllib.TOMLDecodeError):
        return None


def _merge_section(
    config: CLIConfig,
    toml_data: Dict[str, Any],
    section_name: str,
    field_mapping: Dict[str, str],
) -> None:
    """Merge a TOML section into config object.

    Args:
        config: Configuration object to update
        toml_data: Parsed TOML data
        section_name: Name of TOML section (e.g., "cli", "claude")
        field_mapping: Mapping from TOML keys to config attribute names
    """
    section_data = toml_data.get(section_name, {})
    for toml_key, config_attr in field_mapping.items():
        if toml_key in section_data:
            setattr(config, config_attr, section_data[toml_key])


def get_config_example() -> str:
    """Get example config file content.

    Returns:
        Example .ccmaid.toml content as string
    """
    return """# ccmaid Configuration File
# Place this file as .ccmaid.toml in your project root or ~/.ccmaid.toml for user defaults

[cli]
# Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
log_level = "INFO"

# Use mock mode by default (useful for testing without API calls)
mock_mode = false

[claude]
# Claude Code API settings
model = "claude-sonnet-4-5-20250929"
timeout = 300  # seconds
temperature = 0.0  # 0.0 = deterministic, 1.0 = creative

[iterations]
# Maximum iterations for each phase
max_planning_iterations = 10
max_implementation_iterations = 20
max_refinement_iterations = 5

[directories]
# Default directories for manifests and tests
manifest_dir = "manifests"
test_dir = "tests"

[maid]
# Use manifest chain for validation (recommended)
use_manifest_chain = true
"""
