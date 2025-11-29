"""Main CLI entry point for CC MAID Agent."""

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from maid_agents.claude.cli_wrapper import ClaudeWrapper
from maid_agents.config.config_loader import load_config, get_config_example
from maid_agents.core.orchestrator import MAIDOrchestrator
from maid_agents.agents.test_generator import TestGenerator
from maid_agents.utils.logging import setup_logging

console = Console()


def _print_error(message: str, suggestion: str = None, details: str = None) -> None:
    """Print a formatted error message with optional suggestions.

    Args:
        message: The main error message
        suggestion: Optional suggestion for how to fix the issue
        details: Optional additional details
    """
    console.print(f"[bold red]❌ Error:[/bold red] {message}")

    if details:
        console.print(f"[dim]{details}[/dim]")

    if suggestion:
        console.print(f"[yellow]💡 Suggestion:[/yellow] {suggestion}")


def _print_success(message: str, details: dict = None) -> None:
    """Print a formatted success message.

    Args:
        message: The main success message
        details: Optional dictionary of details to display
    """
    console.print(f"[bold green]✅ {message}[/bold green]")

    if details:
        for key, value in details.items():
            console.print(f"  [cyan]{key}:[/cyan] {value}")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="ccmaid",
        description="Claude Code MAID Agent - Automates MAID workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full workflow with mock mode
  ccmaid --mock run "Add user authentication"

  # Create manifest and tests
  ccmaid plan "Add user authentication" --max-iterations 10

  # Implement from manifest
  ccmaid implement manifests/task-042.manifest.json

  # Refactor existing code
  ccmaid refactor manifests/task-042.manifest.json

  # Refine manifest and tests
  ccmaid refine manifests/task-042.manifest.json --goal "Improve test coverage"

  # Generate tests from existing implementation (reverse workflow)
  ccmaid generate-test manifests/task-042.manifest.json -i path/to/code.py

For more information, visit: https://github.com/mamertofabian/maid-agents
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version="ccmaid 0.1.0",
    )

    parser.add_argument(
        "--config-example",
        action="store_true",
        help="Print example configuration file and exit",
    )

    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock mode instead of real Claude CLI (overrides config file)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output (sets log level to DEBUG)",
    )

    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress non-essential output (sets log level to ERROR)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level explicitly (overrides -v/-q)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run subcommand
    run_parser = subparsers.add_parser(
        "run",
        help="Run full MAID workflow from goal",
    )
    run_parser.add_argument("goal", help="High-level goal description")

    # Plan subcommand
    plan_parser = subparsers.add_parser(
        "plan",
        help="Create manifest and tests (Phases 1-2)",
    )
    plan_parser.add_argument("goal", help="High-level goal description")
    plan_parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum planning iterations (default: from config or 10)",
    )
    plan_parser.add_argument(
        "--instructions",
        type=str,
        default="",
        help="Additional instructions or context to guide planning (optional)",
    )

    # Implement subcommand
    implement_parser = subparsers.add_parser(
        "implement",
        help="Implement from manifest (Phase 3)",
    )
    implement_parser.add_argument("manifest_path", help="Path to manifest file")
    implement_parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum implementation iterations (default: from config or 20)",
    )
    implement_parser.add_argument(
        "--no-retry",
        action="store_true",
        help="Disable automatic retries - fail immediately on first error",
    )
    implement_parser.add_argument(
        "--confirm-retry",
        action="store_true",
        help="Ask for confirmation before each retry iteration",
    )
    implement_parser.add_argument(
        "--fresh-start",
        action="store_true",
        help="Restore files to original state on each retry (default: build on previous attempt)",
    )
    implement_parser.add_argument(
        "--instructions",
        type=str,
        default="",
        help="Additional instructions or context to guide implementation (optional)",
    )

    # Refactor subcommand
    refactor_parser = subparsers.add_parser(
        "refactor",
        help="Refactor code to improve quality (Phase 3.5)",
    )
    refactor_parser.add_argument("manifest_path", help="Path to manifest file")
    refactor_parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum refactoring iterations (default: from config or 10)",
    )
    refactor_parser.add_argument(
        "--no-retry",
        action="store_true",
        help="Disable automatic retries - fail immediately on first error",
    )
    refactor_parser.add_argument(
        "--confirm-retry",
        action="store_true",
        help="Ask for confirmation before each retry iteration",
    )
    refactor_parser.add_argument(
        "--fresh-start",
        action="store_true",
        help="Restore files to original state on each retry (default: build on previous attempt)",
    )
    refactor_parser.add_argument(
        "--instructions",
        type=str,
        default="",
        help="Additional instructions or context to guide refactoring (optional)",
    )

    # Refine subcommand
    refine_parser = subparsers.add_parser(
        "refine",
        help="Refine manifest and tests with validation loop (Phase 2 quality gate)",
    )
    refine_parser.add_argument("manifest_path", help="Path to manifest file")
    refine_parser.add_argument(
        "--goal",
        required=True,
        help="Refinement goals/objectives",
    )
    refine_parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum refinement iterations (default: from config or 5)",
    )
    refine_parser.add_argument(
        "--instructions",
        type=str,
        default="",
        help="Additional instructions or context to guide refinement (optional)",
    )

    # Generate-test subcommand
    generate_test_parser = subparsers.add_parser(
        "generate-test",
        help="Generate or enhance behavioral tests from existing implementation",
    )
    generate_test_parser.add_argument("manifest_path", help="Path to manifest file")
    generate_test_parser.add_argument(
        "-i",
        "--implementation",
        required=True,
        help="Path to existing implementation file",
    )
    generate_test_parser.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        help="Maximum iterations for fixing failing tests (default: 5)",
    )

    args = parser.parse_args()

    # Handle --config-example flag
    if hasattr(args, "config_example") and args.config_example:
        console.print(
            Panel(
                get_config_example(),
                title="📄 Example .ccmaid.toml Configuration",
                border_style="cyan",
            )
        )
        console.print(
            "\n[dim]Save this as .ccmaid.toml in your project root or ~/.ccmaid.toml for user defaults[/dim]"
        )
        sys.exit(0)

    # Load configuration from files (project > user > defaults)
    config = load_config()

    # Determine log level: CLI args override config file
    if args.log_level:
        log_level = args.log_level
    elif args.verbose:
        log_level = "DEBUG"
    elif args.quiet:
        log_level = "ERROR"
    else:
        log_level = config.log_level  # Use config file default

    setup_logging(level=log_level)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Determine mock mode: CLI flag overrides config file
    mock_mode = args.mock if args.mock else config.mock_mode

    # Create Claude wrapper with config values and orchestrator
    claude = ClaudeWrapper(
        mock_mode=mock_mode,
        model=config.claude_model,
        timeout=config.claude_timeout,
        temperature=config.claude_temperature,
    )
    orchestrator = MAIDOrchestrator(claude=claude)

    if args.command == "run":
        if not args.quiet:
            console.print(
                Panel(
                    f"[bold]Running full MAID workflow[/bold]\n[dim]Goal:[/dim] {args.goal}",
                    title="🚀 MAID Agent",
                    border_style="blue",
                )
            )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Running workflow...", total=None)
            result = orchestrator.run_full_workflow(args.goal)

        if result.success:
            _print_success(
                result.message,
                details={
                    "Manifest": result.manifest_path,
                },
            )
            sys.exit(0)
        else:
            _print_error(
                result.message,
                suggestion="Try running with --verbose to see detailed logs, or use --mock for testing",
            )
            sys.exit(1)

    elif args.command == "plan":
        # Use config default if --max-iterations not specified
        max_iterations = (
            args.max_iterations
            if args.max_iterations is not None
            else config.max_planning_iterations
        )

        if not args.quiet:
            console.print(
                Panel(
                    f"[bold]Creating MAID manifest and tests[/bold]\n[dim]Goal:[/dim] {args.goal}",
                    title="📋 Planning Phase",
                    border_style="cyan",
                )
            )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Planning...", total=None)
            result = orchestrator.run_planning_loop(
                goal=args.goal,
                max_iterations=max_iterations,
                instructions=args.instructions,
            )

        if result["success"]:
            _print_success(
                f"Planning complete in {result['iterations']} iteration(s)",
                details={
                    "Manifest": result["manifest_path"],
                    "Tests": ", ".join(result["test_paths"]),
                },
            )
            sys.exit(0)
        else:
            _print_error(
                f"Planning failed after {result['iterations']} iteration(s)",
                details=result.get("error"),
                suggestion="Try increasing --max-iterations or refining the goal description",
            )
            sys.exit(1)

    elif args.command == "implement":
        # Import RetryMode and ErrorContextMode here to avoid circular imports
        from maid_agents.core.orchestrator import RetryMode, ErrorContextMode

        # Use config default if --max-iterations not specified
        max_iterations = (
            args.max_iterations
            if args.max_iterations is not None
            else config.max_implementation_iterations
        )

        # Determine retry mode from flags
        if args.no_retry and args.confirm_retry:
            _print_error(
                "Cannot use both --no-retry and --confirm-retry",
                suggestion="Choose one retry mode or use neither for default behavior",
            )
            sys.exit(1)
        elif args.no_retry:
            retry_mode = RetryMode.DISABLED
        elif args.confirm_retry:
            retry_mode = RetryMode.CONFIRM
        else:
            retry_mode = RetryMode.DISABLED  # Default

        # Determine error context mode from flags
        error_context_mode = (
            ErrorContextMode.FRESH_START
            if args.fresh_start
            else ErrorContextMode.INCREMENTAL
        )

        manifest_path = args.manifest_path
        if not Path(manifest_path).exists():
            _print_error(
                f"Manifest not found: {manifest_path}",
                suggestion='Make sure the manifest exists. Try running: ccmaid plan "<your goal>" first',
            )
            sys.exit(1)

        if not args.quiet:
            retry_info = f"[dim]Retry mode:[/dim] {retry_mode.value}, [dim]Error context:[/dim] {error_context_mode.value}"
            console.print(
                Panel(
                    f"[bold]Implementing code from manifest[/bold]\n[dim]Manifest:[/dim] {manifest_path}\n{retry_info}",
                    title="⚙️ Implementation Phase",
                    border_style="green",
                )
            )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Implementing...", total=None)
            result = orchestrator.run_implementation_loop(
                manifest_path=manifest_path,
                max_iterations=max_iterations,
                retry_mode=retry_mode,
                error_context_mode=error_context_mode,
                instructions=args.instructions,
            )

        if result["success"]:
            _print_success(
                f"Implementation complete in {result['iterations']} iteration(s)",
                details={
                    "Files modified": ", ".join(result["files_modified"]),
                },
            )
            sys.exit(0)
        else:
            _print_error(
                f"Implementation failed after {result['iterations']} iteration(s)",
                details=result.get("error"),
                suggestion="Review test failures and consider increasing --max-iterations or refining the manifest",
            )
            sys.exit(1)

    elif args.command == "refactor":
        # Import RetryMode and ErrorContextMode here to avoid circular imports
        from maid_agents.core.orchestrator import RetryMode, ErrorContextMode

        # Use config default if --max-iterations not specified
        max_iterations = (
            args.max_iterations
            if args.max_iterations is not None
            else getattr(config, "max_refactoring_iterations", 10)
        )

        # Determine retry mode from flags
        if args.no_retry and args.confirm_retry:
            _print_error(
                "Cannot use both --no-retry and --confirm-retry",
                suggestion="Choose one retry mode or use neither for default behavior",
            )
            sys.exit(1)
        elif args.no_retry:
            retry_mode = RetryMode.DISABLED
        elif args.confirm_retry:
            retry_mode = RetryMode.CONFIRM
        else:
            retry_mode = RetryMode.DISABLED  # Default

        # Determine error context mode from flags
        error_context_mode = (
            ErrorContextMode.FRESH_START
            if args.fresh_start
            else ErrorContextMode.INCREMENTAL
        )

        manifest_path = args.manifest_path
        if not Path(manifest_path).exists():
            _print_error(
                f"Manifest not found: {manifest_path}",
                suggestion="Ensure the manifest file exists and the path is correct",
            )
            sys.exit(1)

        if not args.quiet:
            retry_info = f"[dim]Retry mode:[/dim] {retry_mode.value}, [dim]Error context:[/dim] {error_context_mode.value}"
            console.print(
                Panel(
                    f"[bold]Refactoring code for quality improvements[/bold]\n[dim]Manifest:[/dim] {manifest_path}\n{retry_info}",
                    title="✨ Refactoring Phase",
                    border_style="magenta",
                )
            )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Refactoring...", total=None)
            result = orchestrator.run_refactoring_loop(
                manifest_path=manifest_path,
                max_iterations=max_iterations,
                retry_mode=retry_mode,
                error_context_mode=error_context_mode,
                instructions=args.instructions,
            )

        if result["success"]:
            console.print(
                f"[bold green]✅ Refactoring complete in {result['iterations']} iteration(s)![/bold green]"
            )
            improvements = result.get("improvements", [])
            if improvements:
                console.print(f"  [cyan]Improvements:[/cyan] ({len(improvements)})")
                for i, improvement in enumerate(improvements, 1):
                    console.print(f"    {i}. {improvement}")
            files_written = result.get("files_written", [])
            if files_written:
                console.print(
                    f"  [cyan]Files written:[/cyan] {', '.join(files_written)}"
                )
            sys.exit(0)
        else:
            _print_error(
                f"Refactoring failed after {result['iterations']} iteration(s)",
                details=result.get("error"),
                suggestion="Check if all tests are passing before refactoring, or increase --max-iterations",
            )
            sys.exit(1)

    elif args.command == "refine":
        # Use config default if --max-iterations not specified
        max_iterations = (
            args.max_iterations
            if args.max_iterations is not None
            else config.max_refinement_iterations
        )

        manifest_path = args.manifest_path
        if not Path(manifest_path).exists():
            _print_error(
                f"Manifest not found: {manifest_path}",
                suggestion="Ensure the manifest file exists and the path is correct",
            )
            sys.exit(1)

        if not args.quiet:
            console.print(
                Panel(
                    f"[bold]Refining manifest and tests[/bold]\n[dim]Manifest:[/dim] {manifest_path}\n[dim]Goal:[/dim] {args.goal}",
                    title="🔍 Refinement Phase",
                    border_style="yellow",
                )
            )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Refining...", total=None)
            result = orchestrator.run_refinement_loop(
                manifest_path=manifest_path,
                refinement_goal=args.goal,
                max_iterations=max_iterations,
                instructions=args.instructions,
            )

        if result["success"]:
            console.print(
                f"[bold green]✅ Refinement complete in {result['iterations']} iteration(s)![/bold green]"
            )
            improvements = result.get("improvements", [])
            if improvements:
                console.print(f"  [cyan]Improvements:[/cyan] ({len(improvements)})")
                for i, improvement in enumerate(improvements, 1):
                    console.print(f"    {i}. {improvement}")
            sys.exit(0)
        else:
            _print_error(
                f"Refinement failed after {result['iterations']} iteration(s)",
                details=result.get("error"),
                suggestion="Try a more specific refinement goal or increase --max-iterations",
            )
            sys.exit(1)

    elif args.command == "generate-test":
        manifest_path = args.manifest_path
        implementation_path = args.implementation

        # Validate paths exist
        if not Path(manifest_path).exists():
            _print_error(
                f"Manifest not found: {manifest_path}",
                suggestion="Ensure the manifest file exists and the path is correct",
            )
            sys.exit(1)

        if not Path(implementation_path).exists():
            _print_error(
                f"Implementation file not found: {implementation_path}",
                suggestion="Ensure the implementation file exists and the path is correct",
            )
            sys.exit(1)

        if not args.quiet:
            console.print(
                Panel(
                    f"[bold]Generating behavioral tests from implementation[/bold]\n"
                    f"[dim]Manifest:[/dim] {manifest_path}\n"
                    f"[dim]Implementation:[/dim] {implementation_path}",
                    title="🧪 Test Generation",
                    border_style="cyan",
                )
            )

        # Create test generator
        claude = ClaudeWrapper(
            mock_mode=mock_mode,
            model=config.claude_model,
            timeout=config.claude_timeout,
            temperature=config.claude_temperature,
        )
        generator = TestGenerator(claude=claude)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Generating tests...", total=None)
            result = generator.generate_test_from_implementation(
                manifest_path=manifest_path,
                implementation_path=implementation_path,
                max_iterations=args.max_iterations,
            )

        if result["success"]:
            mode = result.get("mode", "created")
            iterations = result.get("iterations", 0)
            _print_success(
                f"Test generation complete ({mode})",
                details={
                    "Test file": result["test_path"],
                    "Mode": mode,
                    "Iterations": iterations,
                    "Status": "All tests passing ✓",
                },
            )
            sys.exit(0)
        else:
            iterations = result.get("iterations", 0)
            _print_error(
                f"Test generation failed after {iterations} iteration(s)",
                details=result.get("error"),
                suggestion="Check that the manifest and implementation file are valid, or increase --max-iterations",
            )
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
