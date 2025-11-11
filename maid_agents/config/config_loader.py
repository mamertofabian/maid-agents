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


@dataclass
class CLIConfig:
    """CLI configuration from file or defaults."""

    # CLI settings
    log_level: str = "INFO"
    mock_mode: bool = False

    # Iteration limits
    max_planning_iterations: int = 10
    max_implementation_iterations: int = 20
    max_refinement_iterations: int = 5

    # Directories
    manifest_dir: str = "manifests"
    test_dir: str = "tests"


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

    # Try user-level config first
    user_config_path = Path.home() / ".ccmaid.toml"
    if user_config_path.exists():
        config = _merge_config(config, user_config_path)

    # Try project-level config (overrides user config)
    project_config_path = Path.cwd() / ".ccmaid.toml"
    if project_config_path.exists():
        config = _merge_config(config, project_config_path)

    return config


def _merge_config(base_config: CLIConfig, config_path: Path) -> CLIConfig:
    """Merge TOML config file into base config.

    Args:
        base_config: Existing configuration
        config_path: Path to TOML config file

    Returns:
        Updated CLIConfig with values from file
    """
    try:
        with open(config_path, "rb") as f:
            toml_data = tomllib.load(f)

        # Extract CLI settings
        cli_section = toml_data.get("cli", {})
        if "log_level" in cli_section:
            base_config.log_level = cli_section["log_level"]
        if "mock_mode" in cli_section:
            base_config.mock_mode = cli_section["mock_mode"]

        # Extract iteration limits
        iterations = toml_data.get("iterations", {})
        if "max_planning_iterations" in iterations:
            base_config.max_planning_iterations = iterations["max_planning_iterations"]
        if "max_implementation_iterations" in iterations:
            base_config.max_implementation_iterations = iterations[
                "max_implementation_iterations"
            ]
        if "max_refinement_iterations" in iterations:
            base_config.max_refinement_iterations = iterations[
                "max_refinement_iterations"
            ]

        # Extract directories
        dirs = toml_data.get("directories", {})
        if "manifest_dir" in dirs:
            base_config.manifest_dir = dirs["manifest_dir"]
        if "test_dir" in dirs:
            base_config.test_dir = dirs["test_dir"]

    except Exception:
        # Silently ignore config file errors and use defaults
        # We could log this if logging is already setup
        pass

    return base_config


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

[iterations]
# Maximum iterations for each phase
max_planning_iterations = 10
max_implementation_iterations = 20
max_refinement_iterations = 5

[directories]
# Default directories for manifests and tests
manifest_dir = "manifests"
test_dir = "tests"
"""
