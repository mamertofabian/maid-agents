# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**⚠️ CRITICAL: This project dogfoods MAID v1.2. Every code change MUST follow the MAID workflow.**

## Project Overview

MAID Agents is a Claude Code automation layer for the MAID (Manifest-driven AI Development) methodology. It provides CLI tools and agents that automate the four phases of MAID workflow by invoking Claude Code in headless mode.

**📖 Important Reference:** When working with this project, always refer to `docs/maid_specs.md` for the complete MAID methodology specification and principles.

### Self-Improvement Architecture

**CRITICAL: This project uses itself to improve itself.**

Both tools are installed globally in miniconda and available system-wide:
- **maid-runner** (CLI: `maid`) - Validation engine for manifests
- **maid_agents** (CLI: `ccmaid`) - This package, the automation layer

**This means `ccmaid` can be used to develop `ccmaid` itself.** This self-referential architecture enables rapid iteration but has important implications:

⚠️ **Potential Gotchas:**
1. **Version Confusion** - Are you running the installed `ccmaid` or developing it?
2. **Infinite Recursion** - `ccmaid` could theoretically invoke itself recursively
3. **Bootstrap Paradox** - Changes to agents may affect their ability to develop themselves
4. **Debugging Complexity** - The tool being debugged might be the tool doing the debugging

**Best Practices:**
- When manually developing: Work directly in this codebase with tests
- When using `ccmaid` to develop `ccmaid`: Be explicit about which version you're running
- Always test changes to agents thoroughly before using them to develop themselves
- Use `--mock` mode when testing to avoid recursive API calls
- Be aware that agent behavior changes can affect subsequent development iterations

## Key Commands

### Development

```bash
# Install package in editable mode
uv pip install -e .

# Run tests
pytest tests/ -v

# Run specific task tests
pytest tests/test_task_018_agent_visibility.py -v

# Code quality
black maid_agents/        # Format code
ruff check maid_agents/   # Lint code
```

**Makefile Convenience Commands:**

The project includes a `Makefile` with convenient shortcuts for common development tasks:

```bash
# Show all available commands
make help

# Install package in editable mode
make install

# Install development dependencies
make install-dev

# Run all tests
make test

# Validate all manifests (with manifest chain)
make validate

# Run linting checks
make lint

# Run linting with auto-fix
make lint-fix

# Format code
make format
```

### Using ccmaid CLI

```bash
# Full workflow (all phases)
ccmaid run "Add user authentication to the API"

# Phase 1-2: Planning (manifest + tests)
ccmaid plan "Add user authentication" --max-iterations 10

# Phase 3: Implementation
ccmaid implement manifests/task-042.manifest.json --max-iterations 20

# Phase 3.5: Refactoring
ccmaid refactor manifests/task-042.manifest.json

# Phase 2 Quality Gate: Refinement
ccmaid refine manifests/task-042.manifest.json --goal "Improve test coverage"

# Generate tests from existing implementation (reverse workflow)
ccmaid generate-test manifests/task-042.manifest.json -i path/to/implementation.py

# Mock mode (for testing without API calls)
ccmaid --mock plan "Test feature"
```

**About `generate-test` Command:**

The `generate-test` command supports the reverse workflow where you have existing code and need to generate behavioral tests. This is particularly useful after using `maid snapshot` to create a manifest from existing code.

**Three modes of operation:**
1. **Create new**: Generate tests from scratch when none exist
2. **Enhance stub**: Fill in placeholder tests created by `maid snapshot`
3. **Improve existing**: Enhance and complete existing tests

**Typical workflow:**
```bash
# 1. Generate manifest from existing code (maid-runner)
maid snapshot ../other-repo/utils/formatter.py

# 2. Generate behavioral tests (maid_agents)
ccmaid generate-test manifests/task-NNN-formatter.manifest.json -i ../other-repo/utils/formatter.py

# 3. Validate complete manifest
maid validate manifests/task-NNN-formatter.manifest.json
```

### Using maid CLI

The `maid` command (from **maid-runner** package) provides validation and snapshot capabilities for MAID manifests:

```bash
# Validate a single manifest
maid validate manifests/task-042.manifest.json

# Validate with manifest chain (merges related manifests)
maid validate manifests/task-042.manifest.json --use-manifest-chain

# Validate all manifests in a directory
maid validate --manifest-dir manifests

# Behavioral validation (checks test usage of artifacts)
maid validate manifests/task-042.manifest.json --validation-mode behavioral

# Generate snapshot manifest from existing Python file
maid snapshot maid_agents/core/orchestrator.py

# Generate snapshot to specific directory
maid snapshot maid_agents/core/orchestrator.py --output-dir manifests

# Run validation commands from all manifests
maid test

# Run validation for a specific manifest
maid test --manifest task-042.manifest.json

# Run with verbose output
maid test --verbose

# Fail fast on first error
maid test --fail-fast
```

**Command Reference:**

- **`maid validate`**: Validates manifest structure and compliance
  - `--validation-mode {implementation,behavioral}`: Implementation checks definitions, behavioral checks test usage
  - `--use-manifest-chain`: Merge related manifests for validation (auto-enabled for directory validation)
  - `--quiet, -q`: Suppress success messages, only show errors
  - `--manifest-dir`: Validate all manifests in directory (mutually exclusive with manifest_path)

- **`maid snapshot`**: Generates MAID manifests from existing Python files
  - `--output-dir`: Directory to write manifest (default: `manifests`)
  - `--force`: Overwrite existing manifests without prompting

- **`maid test`**: Runs validation commands from manifests
  - `--manifest, -m`: Run validation for single manifest (filename relative to manifest-dir or absolute path)
  - `--manifest-dir`: Directory containing manifests (default: `manifests`)
  - `--fail-fast`: Stop execution on first failure
  - `--verbose, -v`: Show detailed command output
  - `--quiet, -q`: Only show summary (suppress per-manifest output)
  - `--timeout`: Command timeout in seconds (default: 300)

## Architecture

### Core Components

**MAIDOrchestrator** (`maid_agents/core/orchestrator.py`)
- Coordinates the complete MAID workflow
- Manages state machine: INIT → PLANNING → IMPLEMENTING → REFACTORING → COMPLETE
- Three main loops:
  - `run_planning_loop()`: Phase 1-2 (manifest + tests with validation)
  - `run_implementation_loop()`: Phase 3 (code generation until tests pass)
  - `run_refinement_loop()`: Phase 2 quality gate (manifest/test improvement)
- Uses `dry_run` mode for testing without file writes
- Path validation to prevent directory traversal attacks

**Agent System** (`maid_agents/agents/`)
- All agents inherit from `BaseAgent` abstract class
- **ManifestArchitect**: Creates MAID manifests from high-level goals
- **TestDesigner**: Generates behavioral tests from manifests (TDD approach)
- **Developer**: Implements code to pass tests
- **Refactorer**: Improves code quality (Phase 3.5)
- **Refiner**: Iteratively improves manifest and test quality
- Each agent wraps Claude Code CLI via `ClaudeWrapper`

**TestGenerator** (`maid_agents/core/test_generator.py`)
- Generates or enhances behavioral tests from existing implementations (reverse workflow)
- Detects existing test files and analyzes if they're stubs or complete
- Three operational modes: create new, enhance stub, improve existing
- Builds context-aware prompts with manifest, implementation, and existing tests
- Complements `maid snapshot` to complete the reverse engineering workflow

**ClaudeWrapper** (`maid_agents/claude/cli_wrapper.py`)
- Invokes Claude Code headless CLI: `claude --print <prompt> --output-format json`
- Supports `mock_mode` for testing without real API calls
- Returns `ClaudeResponse` dataclass with success/error status

**ValidationRunner** (`maid_agents/core/validation_runner.py`)
- Wraps `maid` CLI commands for validation
- `validate_manifest()`: Structural validation via `maid validate`
- `run_behavioral_tests()`: Executes pytest from manifest's `validationCommand`
- Parses validation errors for feedback loops

### Workflow Loops

**Planning Loop** (orchestrator.py:164-262)
1. ManifestArchitect creates manifest
2. TestDesigner generates tests
3. Behavioral validation (tests must USE artifacts)
4. Iterate until validation passes (max 10 iterations)

**Implementation Loop** (orchestrator.py:335-444)
1. Run tests (should fail - red phase)
2. Developer generates code
3. Write code to files
4. Run tests again
5. If pass, validate manifest compliance
6. Iterate until success (max 20 iterations)

**Refinement Loop** (orchestrator.py:446-533)
1. Refiner analyzes manifest and tests
2. Apply improvements
3. Structural validation
4. Behavioral validation
5. Iterate until both pass (max 5 iterations)

### MAID Workflow Integration

This codebase follows MAID methodology:
- All tasks have manifests in `manifests/task-*.manifest.json`
- All behavioral tests in `tests/test_task_*_*.py`
- Sequential task numbering (task-001, task-002, etc.)
- Validation enforced via `maid validate --use-manifest-chain`

## Configuration

**Settings** (`maid_agents/config/settings.py`)
- `ClaudeConfig`: Model, timeout, temperature
- `MAIDConfig`: Directory paths, iteration limits
- Defaults: claude-sonnet-4-5-20250929, 300s timeout, 0.0 temperature

## Key Design Patterns

**Mock Mode for Testing**
- All agents accept `ClaudeWrapper(mock_mode=True)` for testing
- Orchestrator uses `dry_run=True` to skip file writes
- Enables unit testing without API calls or file I/O

**Iterative Refinement with Feedback**
- Each loop collects validation errors
- Errors passed to next iteration as context
- Maximum iteration limits prevent infinite loops

**Path Safety**
- `_validate_safe_path()` prevents directory traversal
- All file operations resolve paths relative to project root
- MAX_FILE_SIZE (1MB) limit on generated code

**Agent Visibility** (Task-018)
- Agents must operate within manifest boundaries
- Only access files listed in manifest (creatable/editable/readonly)
- Prevents context leakage and ensures isolation

## MAID Compliance Notes

When making changes to this codebase:

1. **Always create manifests first** - Use sequential numbering
2. **Create tests before implementation** - Tests define success criteria
3. **Validate early and often** - Run `maid validate` before implementation
4. **Honor the chain** - Use `--use-manifest-chain` for validation
5. **Preserve public APIs** - All public methods/classes must be in manifests

## Task Completion Checklist

**⚠️ CRITICAL: Before declaring any task complete, you MUST run all of the following checks:**

```bash
# Code quality checks
make lint          # Check for linting errors
make format        # Format code (fixes formatting issues)
make test          # Run all tests

# MAID validation checks
maid validate      # Validate all manifests (or specific manifest)
maid test          # Run validation commands from manifests
```

**All checks must pass before a task is considered complete.** Do not skip any of these steps.

### Code Quality Standards

**🚫 Zero Tolerance for Workarounds and Band-Aid Solutions:**

- **Be honest about code quality** - If something is broken, fix it properly rather than patching it
- **No shortcuts** - Don't celebrate completion of broken or rotten code
- **Proper solutions only** - Take the time to implement correct, maintainable solutions
- **Address root causes** - Fix underlying issues, not just symptoms
- **Test thoroughly** - Ensure all tests pass and code behaves correctly

If you encounter issues during implementation:
1. **Stop and assess** - Understand the root cause
2. **Design properly** - Plan the correct solution
3. **Implement correctly** - Build it right the first time
4. **Validate completely** - Run all checks before declaring done

**Remember:** A task is only complete when the code is correct, tested, validated, and maintainable. Premature celebration of incomplete or broken code leads to technical debt and future problems.

## Testing Strategy

- **Unit tests**: Test individual agents with `mock_mode=True`
- **Integration tests**: Test orchestrator loops with `dry_run=True`
- **Behavioral tests**: Full workflow validation via pytest
- All tests follow naming: `test_task_NNN_description.py`

## Dependencies

- **maid-runner**: Core validation engine (sibling package)
- **click**: CLI framework
- **rich**: Terminal formatting
- **pytest**: Test framework
- **black**, **ruff**: Code quality tools

## CLI Entry Point

`ccmaid` command → `maid_agents/cli/main.py:main()` → MAIDOrchestrator or TestGenerator

All commands route through argparse subcommands:
- **run**: Full workflow via MAIDOrchestrator
- **plan**: Phase 1-2 via MAIDOrchestrator
- **implement**: Phase 3 via MAIDOrchestrator
- **refactor**: Phase 3.5 via MAIDOrchestrator
- **refine**: Phase 2 quality gate via MAIDOrchestrator
- **generate-test**: Reverse workflow via TestGenerator (new in task-019)
