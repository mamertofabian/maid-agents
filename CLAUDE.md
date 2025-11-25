# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MAID Agents is a Claude Code automation layer for the MAID (Manifest-driven AI Development) methodology. It orchestrates TDD workflows using Claude Code's headless CLI mode across four phases:

1. **Phase 1: Goal Definition** - ManifestArchitect agent creates precise manifests
2. **Phase 2: Planning Loop** - TestDesigner agent generates behavioral tests
3. **Phase 3: Implementation** - Developer agent implements code to pass tests
4. **Phase 3.5: Refactoring** - Refactorer agent improves code quality

## Development Commands

### Testing
```bash
# Run all tests
make test
uv run python -m pytest tests/ -v

# Run specific test file
uv run python -m pytest tests/test_task_001_orchestrator_skeleton.py -v

# Run with coverage
uv run python -m pytest tests/ --cov=maid_agents --cov-report=html
```

### Code Quality
```bash
# Run all quality checks
make lint          # Check code quality with ruff
make lint-fix      # Auto-fix linting issues
make format        # Format code with black
```

### Manifest Validation
```bash
# Validate all manifests
make validate

# Validate specific manifest
uv run maid validate manifests/task-042.manifest.json --use-manifest-chain
```

### Installation
```bash
# Install package in editable mode
make install
uv pip install -e .

# Install with development dependencies
make install-dev
uv pip install -e ".[dev]"
```

## Architecture

### Core Components

**Orchestrator** (`maid_agents/core/orchestrator.py`):
- Central workflow coordinator with state machine (WorkflowState enum)
- Manages four workflow loops: planning, implementation, refinement, and refactoring
- Each loop runs iteratively until validation passes or max iterations reached
- Uses dependency injection for agents and validation runner (enables testing with mocks)
- Dry-run mode available for testing without file writes or API calls

**Agent System** (`maid_agents/agents/`):
- All agents inherit from `BaseAgent` abstract class
- Each agent wraps `ClaudeWrapper` to invoke Claude Code headless mode
- Agent types:
  - `ManifestArchitect`: Creates MAID manifests from goals
  - `TestDesigner`: Generates behavioral tests from manifests
  - `Developer`: Implements code to pass tests
  - `Refactorer`: Refactors code while maintaining test compliance
  - `Refiner`: Improves manifest and test quality
  - `TestGenerator`: Generates tests from existing implementation (reverse workflow)

**Claude Integration** (`maid_agents/claude/cli_wrapper.py`):
- Wraps Claude Code headless CLI with `--print --output-format=stream-json --verbose`
- Parses streaming JSON responses (tool_use, tool_result, text blocks)
- Mock mode available for testing without API calls
- Configurable timeout, model, and temperature
- Tool allowlist restricts Claude to safe operations (pytest, maid commands, linting)

**Template System** (`maid_agents/config/template_manager.py`):
- Loads prompt templates from `maid_agents/config/templates/*.txt`
- Uses Python's `string.Template` for variable substitution
- Templates cached for performance
- Key templates: manifest_creation, test_generation, implementation, refactor, refine

**Validation** (`maid_agents/core/validation_runner.py`):
- Runs `maid validate` for structural validation
- Runs `maid test` or manifest's `validationCommand` for behavioral tests
- Two validation modes: structural (manifest schema) and behavioral (tests use artifacts)

### Workflow Loops

Each loop follows a similar pattern:
1. Agent generates output (manifest/tests/code)
2. Files written to disk (skipped in dry_run mode)
3. Validation runs (structural and/or behavioral)
4. If validation fails, error feedback provided to next iteration
5. Loop continues until success or max iterations

**Planning Loop** (orchestrator.py:174-306):
- ManifestArchitect creates manifest with task number
- TestDesigner generates behavioral tests
- Behavioral validation ensures tests USE declared artifacts
- Iterates until both manifest and tests are valid

**Implementation Loop** (orchestrator.py:379-544):
- Developer generates code to pass tests
- Initial run expects failure (RED phase of TDD)
- Code written and tests rerun (GREEN phase)
- Manifest validation ensures compliance
- Systemic error detection prevents infinite loops on non-implementation issues

**Refinement Loop** (orchestrator.py:546-661):
- Refiner improves manifest and tests based on user goals
- Both structural and behavioral validation required
- Useful for quality gates and test coverage improvement

**Refactoring Loop** (orchestrator.py:663-783):
- Refactorer improves code quality while maintaining behavior
- Tests must continue passing (behavioral validation)
- Manifest compliance validated (structural validation)

### Error Handling

**Systemic Error Detection** (`orchestrator.py:785-856`):
- Detects errors that cannot be fixed by changing implementation/refactoring
- Patterns: test collection failures, import errors, timeouts, pytest config issues
- Prevents infinite loops by failing fast on systemic issues
- Returns tuple: (is_systemic, error_message)

**Error Categorization** (`orchestrator.py:912-1014`):
- Categories: network, filesystem, validation, parsing, configuration, resource, subprocess
- Each category has recovery guidance and user-friendly messages
- Recoverable vs fatal error distinction
- Used by `_handle_error()` for comprehensive error reporting

### Testing Conventions

**Test File Naming**:
- Tests named `test_task_XXX_*.py` matching manifest numbering
- Example: `test_task_001_orchestrator_skeleton.py` for task-001 manifest
- Enables traceability between manifests, implementation, and tests

**Test Structure**:
- Follow pytest conventions with fixtures and parametrization
- Use `docs/unit-testing-rules.md` for testing guidelines
- Mock external dependencies (Claude API, filesystem in some cases)
- Test behavior, not implementation details
- Use AAA pattern: Arrange, Act, Assert

**Pytest Configuration** (`pyproject.toml`):
- Test path: `tests/`
- Filters warnings for test class name collisions (TestDesigner, TestGenerator)
- These are agent classes, not test classes

### Configuration

**Config Files** (`maid_agents/config/`):
- `ccmaid.yaml` or `ccmaid.toml` for project configuration
- Config loader searches: ./.ccmaid.yaml, ~/.ccmaid.yaml
- Configuration schema includes: model, timeout, temperature, mock_mode
- CLI arguments override config file settings

**Task Numbering**:
- Manifests use sequential numbering: task-001, task-002, etc.
- `_get_next_task_number()` scans manifests/ directory for next available number
- Format: `task-{number:03d}.manifest.json` (zero-padded 3 digits)

## MAID Methodology Alignment

This codebase strictly follows MAID principles:

1. **Explicitness over Implicitness**: All changes declared in manifests with expectedArtifacts
2. **Test-Driven Validation**: Behavioral tests define success criteria
3. **Verifiable Chronology**: Sequential task numbering creates audit trail
4. **Validation Modes**: Behavioral (tests USE artifacts) vs Structural (manifest schema)
5. **Manifest Chain**: `--use-manifest-chain` flag for cross-manifest artifact resolution

## Key Implementation Details

### Claude CLI Invocation Pattern

```python
# Standard invocation in ClaudeWrapper
cmd = [
    "claude",
    "--headless",
    "--print",
    "--output-format=stream-json",
    "--verbose",
    f"--model={self.model}",
    f"--timeout={self.timeout}",
    prompt
]
```

The wrapper parses streaming JSON output and reconstructs responses from tool_use, tool_result, and text blocks.

### Template Variable Substitution

Templates use `$variable` syntax for substitution:
- `$goal`: User's high-level goal
- `$task_number`: Sequential task number
- `$manifest_path`: Path to manifest file
- `$test_errors`: Errors from test execution
- `$validation_feedback`: Feedback from validation failures

### Safe Path Validation

`_validate_safe_path()` (orchestrator.py:103-126) ensures all file operations are within project directory to prevent directory traversal attacks. Critical for security when generating file paths from AI responses.

### File Size Limits

`MAX_FILE_SIZE = 1_000_000` (1MB) prevents excessive code generation. Checked before writing files in implementation loop.

## Common Workflows

### Standard TDD Workflow
```bash
ccmaid run "Add user authentication to the API"
```
Executes: Planning loop → Implementation loop

### Separate Phases
```bash
ccmaid plan "Add user authentication"              # Phase 1-2
ccmaid implement manifests/task-042.manifest.json  # Phase 3
ccmaid refactor manifests/task-042.manifest.json   # Phase 3.5
```

### Reverse Workflow (Tests from Code)
```bash
maid snapshot path/to/existing/code.py                           # Create manifest
ccmaid generate-test manifests/task-NNN-code.manifest.json -i path/to/existing/code.py
```

### Quality Gate
```bash
ccmaid refine manifests/task-042.manifest.json --goal "Improve test coverage"
```

## Dependencies

**Runtime**:
- `maid-runner>=0.1.0` (external package for manifest validation and testing)
- `click>=8.0.0` (CLI framework)
- `rich>=13.0.0` (terminal formatting)

**Development**:
- `pytest>=8.4.2` (testing framework)
- `black>=25.1.0` (code formatting)
- `ruff>=0.13.0` (linting)

**External Tools**:
- Claude Code CLI (authenticated and installed)
- Python 3.12+

## Important Constraints

1. **Mock Mode Default**: `ClaudeWrapper` defaults to `mock_mode=True` for safety
2. **Dry Run Mode**: Orchestrator accepts `dry_run=True` to skip file writes (testing)
3. **Tool Allowlist**: ClaudeWrapper restricts allowed Bash commands for security
4. **Timeout Handling**: Default 300s timeout with systemic error detection for hangs
5. **Path Validation**: All paths validated against project directory before use

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
