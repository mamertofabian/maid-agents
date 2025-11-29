"""MAID Agents: Claude Code automation for Manifest-driven AI Development."""

try:
    from importlib.metadata import version
except ImportError:
    from importlib_metadata import version

__version__ = version("maid-agents")

__all__ = ["__version__"]
