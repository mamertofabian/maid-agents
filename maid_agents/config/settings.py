"""Configuration settings for MAID Agents.

DEPRECATED: This module is kept for backward compatibility and test purposes only.

The production configuration system now uses config_loader.CLIConfig which provides
a unified configuration for all MAID Agent settings including:
- Claude Code settings (model, timeout, temperature)
- Iteration limits
- Directory paths
- MAID-specific settings

For new code, please use:
    from maid_agents.config.config_loader import load_config, CLIConfig

The classes in this file (ClaudeConfig, MAIDConfig, AgentConfig) are maintained
only to satisfy the Task-013 manifest requirements and for testing purposes.
They are NOT used in the production codebase.
"""

import warnings
from dataclasses import dataclass

# Issue deprecation warning when this module is imported
warnings.warn(
    "maid_agents.config.settings is deprecated. Use config_loader.CLIConfig instead.",
    DeprecationWarning,
    stacklevel=2,
)


@dataclass
class ClaudeConfig:
    """Claude Code configuration."""

    model: str = "claude-sonnet-4-5-20250929"
    timeout: int = 300
    temperature: float = 0.0


@dataclass
class MAIDConfig:
    """MAID Agent configuration."""

    manifest_dir: str = "manifests"
    test_dir: str = "tests"
    max_planning_iterations: int = 10
    max_implementation_iterations: int = 20
    use_manifest_chain: bool = True


@dataclass
class AgentConfig:
    """Combined agent configuration."""

    claude: ClaudeConfig
    maid: MAIDConfig

    @classmethod
    def default(cls) -> "AgentConfig":
        """Create default configuration.

        Returns:
            AgentConfig with default settings
        """
        return cls(claude=ClaudeConfig(), maid=MAIDConfig())
