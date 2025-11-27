# MAID Agents

**Automated AI coding orchestration with built-in validation.**

MAID Agents automates the complete development workflow: from idea to validated implementation using Claude Code.

## What Is This?

MAID Agents is an orchestration system that:
- **Plans** tasks using manifest-driven contracts
- **Generates** behavioral tests that exercise the code
- **Implements** code using Claude Code agents
- **Validates** using [MAID Runner](https://github.com/mamertofabian/maid-runner) before committing

Think of it as the "execution engine" that uses MAID Runner as its validation layer.

## How It Works

1. You describe what you want to build
2. ManifestArchitect agent generates a manifest (contract) with expected artifacts
3. TestDesigner agent generates behavioral tests
4. Developer agent implements the code via Claude Code
5. MAID Runner validates the implementation matches the contract
6. Iterate until validation passes

**All automated.** You just describe → review → approve.

## Status

🚧 **Alpha Release** - Functional but evolving based on feedback.

Built with the MAID methodology - this package dogfoods MAID itself! See `IMPLEMENTATION_SUMMARY.md` for details on the 16 tasks, 60 tests, and clean architecture.

## The Four Phases

MAID Agents automates the four phases of the MAID workflow:

1. **Phase 1: Goal Definition** - ManifestArchitect agent creates precise manifests
2. **Phase 2: Planning Loop** - TestDesigner agent generates behavioral tests
3. **Phase 3: Implementation** - Developer agent implements code to pass tests
4. **Phase 3.5: Refactoring** - Refactorer agent improves code quality

## How It Relates to MAID Runner

MAID Agents and MAID Runner work together as a complete system:

| Component | Role | What It Does |
|-----------|------|--------------|
| **MAID Runner** | Validation framework | Validates code matches contracts (manifests) |
| **MAID Agents** | Orchestration system | Automates planning, implementing, validating |

**Use MAID Runner standalone** for manual workflow with full control.

**Use MAID Agents** for automated workflow with Claude Code orchestration.

```
┌──────────────────────────────────────┐
│   You (Developer)                    │
│   "Add user authentication"          │
└──────────────────────────────────────┘
              │
              ▼
┌──────────────────────────────────────┐
│   MAID Agents (Orchestration)        │
│   - ManifestArchitect                │
│   - TestDesigner                     │
│   - Developer                        │
│   - Refactorer                       │
└──────────────────────────────────────┘
              │
              ├─► Creates manifests
              ├─► Generates tests
              ├─► Implements code
              │
              ▼
┌──────────────────────────────────────┐
│   MAID Runner (Validation)           │
│   ✓ Validates manifest schema        │
│   ✓ Validates behavioral tests       │
│   ✓ Validates implementation         │
└──────────────────────────────────────┘
              │
              ▼
┌──────────────────────────────────────┐
│   Your Codebase                      │
│   Fully validated implementation     │
└──────────────────────────────────────┘
```

## Installation

```bash
# Install from PyPI (when published)
pip install maid-agents

# Or install from source
git clone https://github.com/mamertofabian/maid-agents.git
cd maid-agents
uv pip install -e .

# Verify installation
ccmaid --version
```

## Prerequisites

- **maid-runner** package installed (`pip install maid-runner`)
- **Claude Code CLI** installed and authenticated
- **Python 3.12+**

## Usage

### Quick Start Example

The simplest way to use MAID Agents:

```bash
# Full automated workflow: manifest → tests → implementation → validation
ccmaid run "Add email validation to user registration"

# The agent will:
# 1. Create a manifest with expected artifacts
# 2. Generate behavioral tests
# 3. Implement the code
# 4. Validate everything with MAID Runner
# 5. Show you results for approval
```

### Standard MAID Workflow (Step-by-Step)

For more control, run phases individually:

```bash
# Phase 1-2: Create manifest and generate tests
ccmaid plan "Add user authentication to the API"
# Creates: manifests/task-042-user-auth.manifest.json
# Creates: tests/test_task_042_user_auth.py

# Phase 3: Implement the code
ccmaid implement manifests/task-042-user-auth.manifest.json
# Implements code to pass the tests
# Validates with MAID Runner

# Phase 3.5: Refactor for quality
ccmaid refactor manifests/task-042-user-auth.manifest.json
# Improves code quality while maintaining tests

# Optional: Refine tests/manifest
ccmaid refine manifests/task-042-user-auth.manifest.json --goal "Add edge cases"
```

### Reverse Workflow (Tests from Existing Code)

When working with existing code or after using `maid snapshot`:

```bash
# Step 1: Generate manifest from existing code
maid snapshot path/to/existing/code.py

# Step 2: Generate behavioral tests from implementation
ccmaid generate-test manifests/task-NNN-code.manifest.json -i path/to/existing/code.py

# Step 3: Validate the complete manifest
maid validate manifests/task-NNN-code.manifest.json
```

The `generate-test` command supports three modes:
- **Create new**: Generate tests from scratch when none exist
- **Enhance stub**: Fill in placeholder tests created by `maid snapshot`
- **Improve existing**: Enhance and complete existing tests

## Architecture

MAID Agents follows a clean, modular architecture built entirely using the MAID methodology:

```
maid_agents/
├── core/           # Orchestration engine
│   ├── orchestrator.py       # Main workflow coordinator
│   ├── validation_runner.py  # MAID Runner integration
│   └── context_builder.py    # Context preparation
├── agents/         # Specialized agents
│   ├── manifest_architect.py # Creates manifests
│   ├── test_designer.py      # Generates tests
│   ├── developer.py          # Implements code
│   ├── refactorer.py         # Improves quality
│   └── test_generator.py     # Reverse workflow
├── claude/         # Claude Code integration
│   └── cli_wrapper.py        # Claude CLI wrapper
├── config/         # Configuration
│   ├── config_loader.py      # Load .ccmaid.toml
│   └── templates/            # Prompt templates
└── cli/            # Command-line interface
    └── main.py               # ccmaid entrypoint
```

**Key Stats:**
- 16 manifests (one per task)
- 60 behavioral tests (100% passing)
- Built with MAID, validated by MAID

See `IMPLEMENTATION_SUMMARY.md` for complete architecture details.

## Configuration

Create `.ccmaid.toml` in your project root or `~/.ccmaid.toml` for global settings:

```toml
[cli]
log_level = "INFO"
mock_mode = false

[claude]
model = "claude-sonnet-4-5-20250929"
timeout = 1200
temperature = 0.0

[iterations]
max_planning_iterations = 10
max_implementation_iterations = 20

[maid]
use_manifest_chain = true
```

## Development

This package dogfoods the MAID methodology - it was built using MAID itself!

- All manifests are in `manifests/` (16 tasks)
- All behavioral tests in `tests/` (16 test files, 60 tests)
- Every feature was built following the MAID workflow

```bash
# Run tests
uv run pytest tests/ -v

# Format code
make format

# Lint code
make lint
```

## Roadmap

- [x] Core orchestration engine
- [x] Four specialized agents
- [x] Claude Code integration
- [x] CLI interface
- [ ] Proper documentation site
- [ ] Video tutorials
- [ ] IDE integrations (VS Code, etc.)
- [ ] Community templates library
- [ ] MCP server support

## Questions & Support

- **Discord**: Join the [AI Driven Coder community](https://aidrivencoder.com/discord)
- **Issues**: Report bugs or request features on [GitHub Issues](https://github.com/mamertofabian/maid-agents/issues)
- **Discussions**: Ask questions on [GitHub Discussions](https://github.com/mamertofabian/maid-agents/discussions)

## Contributing

See `CONTRIBUTING.md` for development guidelines. All changes must follow the MAID methodology.

## License

MIT License - See LICENSE file
