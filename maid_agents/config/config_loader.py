"""Configuration file loader for ccmaid CLI.

Loads configuration from:
1. .ccmaid.toml (project-level, current directory)
2. ~/.ccmaid.toml (user-level, home directory)
3. Defaults (if no config files found)

CLI arguments always override config file values.
"""

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


_PROJECT_CONFIG_FILENAME = ".ccmaid.toml"

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

_SECTION_MAPPINGS: List[Tuple[str, Dict[str, str]]] = [
    ("cli", _CLI_FIELD_MAPPING),
    ("claude", _CLAUDE_FIELD_MAPPING),
    ("iterations", _ITERATIONS_FIELD_MAPPING),
    ("directories", _DIRECTORIES_FIELD_MAPPING),
    ("maid", _MAID_FIELD_MAPPING),
]


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
    """Load configuration from TOML files with cascading priority.

    Searches for configuration files in priority order (later overrides earlier):
    1. ~/.ccmaid.toml (user-level defaults)
    2. .ccmaid.toml (project-level overrides)

    Returns:
        CLIConfig instance with merged settings from all found config files.
        Missing files are silently ignored, falling back to defaults.
    """
    config = CLIConfig()

    for config_path in _get_config_paths():
        if config_path.exists():
            config = _merge_config(config, config_path)

    return config


def _merge_config(base_config: CLIConfig, config_path: Path) -> CLIConfig:
    """Merge TOML config file into base configuration.

    Reads TOML file and updates base_config with values from recognized sections.
    Invalid or unreadable files are silently ignored, preserving base_config.

    Args:
        base_config: Configuration to update with file values
        config_path: Path to TOML configuration file

    Returns:
        Updated CLIConfig with merged values, or unchanged base_config if file
        cannot be loaded.
    """
    toml_data = _load_toml_file(config_path)
    if toml_data is None:
        return base_config

    _apply_toml_sections(base_config, toml_data)
    return base_config


def _apply_toml_sections(config: CLIConfig, toml_data: Dict[str, Any]) -> None:
    """Apply all TOML sections to configuration object.

    Iterates through all section mappings and applies each one to the config.

    Args:
        config: Configuration object to update
        toml_data: Parsed TOML data containing sections
    """
    for section_name, field_mapping in _SECTION_MAPPINGS:
        _merge_section(config, toml_data, section_name, field_mapping)


def _get_config_paths() -> List[Path]:
    """Get configuration file paths in priority order.

    Returns:
        List of paths in load order: user config first, then project config.
        Project config overrides user config when both exist.
    """
    user_config = Path.home() / _PROJECT_CONFIG_FILENAME
    project_config = Path.cwd() / _PROJECT_CONFIG_FILENAME

    return [user_config, project_config]


def _load_toml_file(config_path: Path) -> Optional[Dict[str, Any]]:
    """Load and parse TOML configuration file.

    Handles all common errors gracefully, returning None for any failure.
    This ensures invalid config files don't break the application.

    Args:
        config_path: Path to TOML configuration file

    Returns:
        Dictionary with parsed TOML data, or None if file cannot be loaded
        (missing file, invalid TOML syntax, permission errors, etc.).
    """
    if not _is_readable_file(config_path):
        return None

    try:
        return _parse_toml_file(config_path)
    except (ValueError, tomllib.TOMLDecodeError):
        return None


def _is_readable_file(file_path: Path) -> bool:
    """Check if file exists and is readable.

    Args:
        file_path: Path to check

    Returns:
        True if file exists and can be opened for reading, False otherwise.
    """
    try:
        with open(file_path, "rb"):
            return True
    except OSError:
        return False


def _parse_toml_file(file_path: Path) -> Dict[str, Any]:
    """Parse TOML file content.

    Args:
        file_path: Path to TOML file to parse

    Returns:
        Dictionary with parsed TOML data.

    Raises:
        ValueError: If file content is invalid
        tomllib.TOMLDecodeError: If TOML syntax is invalid
    """
    with open(file_path, "rb") as toml_file:
        return tomllib.load(toml_file)


def _merge_section(
    config: CLIConfig,
    toml_data: Dict[str, Any],
    section_name: str,
    field_mapping: Dict[str, str],
) -> None:
    """Merge single TOML section into configuration object.

    Updates config attributes from values in the specified TOML section.
    Only processes fields defined in field_mapping. Missing sections or
    fields are silently ignored.

    Args:
        config: Configuration object to update
        toml_data: Complete parsed TOML data
        section_name: TOML section to process (e.g., "cli", "claude")
        field_mapping: Maps TOML keys to CLIConfig attribute names

    Example:
        toml_data = {"cli": {"log_level": "DEBUG"}}
        field_mapping = {"log_level": "log_level"}
        Result: config.log_level = "DEBUG"
    """
    section_data = toml_data.get(section_name, {})
    _apply_field_mappings(config, section_data, field_mapping)


def _apply_field_mappings(
    config: CLIConfig,
    section_data: Dict[str, Any],
    field_mapping: Dict[str, str],
) -> None:
    """Apply field mappings from section data to config object.

    Args:
        config: Configuration object to update
        section_data: Data from a single TOML section
        field_mapping: Maps section keys to config attribute names
    """
    for toml_key, config_attribute_name in field_mapping.items():
        if toml_key in section_data:
            value = section_data[toml_key]
            setattr(config, config_attribute_name, value)


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
