"""Logging utilities for MAID Agents with colored output and progress tracking."""

import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.theme import Theme

# Global console instance for colored output
_console: Optional[Console] = None
_current_progress: Optional[Progress] = None
_log_context: dict = {}

# Custom theme for MAID Agents
_maid_theme = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "success": "bold green",
        "phase": "bold magenta",
        "agent": "bold blue",
        "file": "italic",
        "dim": "dim",
    }
)


def _get_console() -> Console:
    """Get or create global console instance."""
    global _console
    if _console is None:
        _console = Console(theme=_maid_theme)
    return _console


def setup_logging(level: str = "INFO") -> None:
    """Setup logging configuration for MAID Agents with rich formatting.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    console = _get_console()

    # Configure root logger with RichHandler
    logging.basicConfig(
        level=numeric_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                tracebacks_show_locals=True,
                show_path=False,
            )
        ],
    )

    # Get logger for maid_agents
    logger = logging.getLogger("maid_agents")
    logger.setLevel(numeric_level)

    console.print(
        f"[dim]Logging configured at {level} level - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]"
    )


def get_logger(name: str) -> logging.Logger:
    """Get logger for specific module.

    Args:
        name: Module name

    Returns:
        Configured logger instance
    """
    return logging.getLogger(f"maid_agents.{name}")


def log_phase_start(phase: str) -> None:
    """Log the start of a MAID phase with styled output.

    Args:
        phase: Phase name (e.g., "PLANNING", "IMPLEMENTATION", "REFACTORING")
    """
    console = _get_console()
    console.print()
    console.print(
        Panel.fit(
            f"[phase]Starting Phase: {phase}[/phase]",
            border_style="magenta",
        )
    )
    _log_context["current_phase"] = phase
    _log_context["phase_start_time"] = datetime.now()


def log_phase_end(phase: str, success: bool) -> None:
    """Log the end of a MAID phase with success/failure indication.

    Args:
        phase: Phase name
        success: Whether the phase completed successfully
    """
    console = _get_console()

    # Calculate duration
    duration = ""
    if "phase_start_time" in _log_context:
        elapsed = datetime.now() - _log_context["phase_start_time"]
        duration = f" (took {elapsed.total_seconds():.1f}s)"

    status = "[success]✓ SUCCESS[/success]" if success else "[error]✗ FAILED[/error]"
    console.print(
        Panel.fit(
            f"{status} - {phase}{duration}",
            border_style="green" if success else "red",
        )
    )
    console.print()

    # Clear context
    _log_context.pop("current_phase", None)
    _log_context.pop("phase_start_time", None)


def log_agent_action(
    agent_name: str, action: str, details: Optional[str] = None
) -> None:
    """Log an agent's action with colored formatting.

    Args:
        agent_name: Name of the agent
        action: Action being performed
        details: Optional additional details
    """
    console = _get_console()
    message = f"[agent]{agent_name}[/agent]: {action}"
    if details:
        message += f" [dim]({details})[/dim]"
    console.print(message)


def log_file_operation(operation: str, file_path: str) -> None:
    """Log file operations with styled output.

    Args:
        operation: Operation type (e.g., "Creating", "Editing", "Reading")
        file_path: Path to the file
    """
    console = _get_console()
    console.print(f"  [dim]{operation}[/dim] [file]{file_path}[/file]")


def log_validation_result(
    validation_type: str, passed: bool, errors: Optional[list] = None
) -> None:
    """Log validation results with colored pass/fail indicators.

    Args:
        validation_type: Type of validation (e.g., "Structural", "Behavioral")
        passed: Whether validation passed
        errors: Optional list of error messages
    """
    console = _get_console()

    if passed:
        console.print(f"  [success]✓[/success] {validation_type} validation passed")
    else:
        console.print(f"  [error]✗[/error] {validation_type} validation failed")
        if errors:
            for error in errors[:3]:  # Show first 3 errors
                console.print(f"    [error]•[/error] {error}")
            if len(errors) > 3:
                console.print(f"    [dim]... and {len(errors) - 3} more errors[/dim]")


def log_iteration(current: int, max_iterations: int, status: str) -> None:
    """Log iteration progress.

    Args:
        current: Current iteration number
        max_iterations: Maximum iterations allowed
        status: Status message for this iteration
    """
    console = _get_console()
    console.print(f"[dim]Iteration {current}/{max_iterations}:[/dim] {status}")


@contextmanager
def _spinner(message: str):
    """Context manager for showing a spinner during long operations (internal use).

    Args:
        message: Message to display with spinner

    Yields:
        Progress object for updating the message
    """
    console = _get_console()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        _task = progress.add_task(message, total=None)
        yield progress


class LogContext:
    """Context manager for grouping related log messages with indentation."""

    def __init__(self, title: str, style: str = "info"):
        """Initialize log context.

        Args:
            title: Title for the context section
            style: Style to apply (info, warning, error, success)
        """
        self.title = title
        self.style = style
        self.console = _get_console()

    def __enter__(self):
        """Enter context."""
        self.console.print(f"[{self.style}]▶ {self.title}[/{self.style}]")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        if exc_type is not None:
            self.console.print(f"[error]  ✗ Failed with {exc_type.__name__}[/error]")
        return False
