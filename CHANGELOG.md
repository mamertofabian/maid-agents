# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-11-27

### Added

#### Core Orchestration
- MAIDOrchestrator with workflow state management
- Planning loop orchestration (Phase 1-2)
- Implementation loop orchestration (Phase 3)
- Refactoring loop (Phase 3.5)
- Refinement loop for quality improvement
- ValidationRunner for MAID Runner integration
- ContextBuilder for manifest context preparation
- File backup and restore system for safe iterations

#### Specialized Agents
- **ManifestArchitect** - Creates precise task manifests with expected artifacts
- **TestDesigner** - Generates behavioral tests from manifests
- **Developer** - Implements code to pass tests via Claude Code
- **Refactorer** - Improves code quality while maintaining tests
- **Refiner** - Enhances tests and manifests iteratively
- **TestGenerator** - Reverse workflow: generates tests from existing code

#### Claude Code Integration
- ClaudeWrapper for headless CLI mode execution
- Claude Code API settings management
- Mock mode for testing without API calls
- Timeout and temperature configuration
- Response parsing and error handling

#### CLI Commands
- `ccmaid run <goal>` - Full automated MAID workflow
- `ccmaid plan <goal>` - Create manifest and generate tests (Phase 1-2)
- `ccmaid implement <manifest>` - Implement code from manifest (Phase 3)
- `ccmaid refactor <manifest>` - Improve code quality (Phase 3.5)
- `ccmaid refine <manifest>` - Enhance tests/manifest iteratively
- `ccmaid generate-test <manifest>` - Generate tests from existing code

#### Configuration System
- `.ccmaid.toml` configuration file support
- AgentConfig for agent-specific settings
- ClaudeConfig for Claude Code API settings
- MAIDConfig for MAID methodology settings
- Template manager for prompt customization
- User and system prompt separation

#### Prompt Templates
- Manifest creation templates (system + user)
- Test generation templates (system + user)
- Implementation templates (system + user)
- Refactoring templates (system + user)
- Refinement templates (system + user)
- Test generation from implementation templates
- Template variable system

#### Error Handling & Logging
- Comprehensive error handling throughout
- Rich console logging with color coding
- Structured logging utilities
- Debug mode support
- Detailed error messages with context

### Architecture

#### Clean Modular Design
- **core/** - Orchestration engine (orchestrator, validation_runner, context_builder)
- **agents/** - Specialized agents (manifest_architect, test_designer, developer, refactorer, refiner, test_generator)
- **claude/** - Claude Code integration (cli_wrapper)
- **config/** - Configuration system (config_loader, template_manager, templates/)
- **cli/** - Command-line interface (main)
- **utils/** - Logging and utilities

#### Testing
- 60 behavioral tests (100% passing)
- 16 individual test files (one per task)
- Unit testing for all core components
- Mock mode for testing without API calls
- Pytest-based test suite

#### Development Methodology
- Built using MAID methodology (dogfooding)
- 16 task manifests (chronologically ordered)
- Complete MAID compliance throughout
- Test-driven development approach
- Clean git history with sequential tasks

### Initial Release Notes

This is the first public release of MAID Agents, providing automated orchestration for the Manifest-driven AI Development (MAID) methodology using Claude Code.

**Key Features:**
- Automates the complete MAID workflow from idea to validated implementation
- Uses Claude Code in headless mode for AI-powered development
- Integrates with MAID Runner for validation
- Supports both standard TDD workflow and reverse workflow (tests from code)
- Configurable via `.ccmaid.toml` files
- Extensible template system for custom prompts

**Design Philosophy:**
- Orchestration layer on top of MAID Runner (validation)
- Claude Code as the AI execution engine
- Full automation with human approval checkpoints
- Clean separation of concerns
- Tool-agnostic at validation layer

**Requirements:**
- Python 3.12 or higher
- maid-runner >= 0.1.0
- Claude Code CLI installed and authenticated
- click >= 8.0.0
- rich >= 13.0.0

**Development:**
- black >= 25.1.0 (for code formatting)
- ruff >= 0.13.0 (for linting)
- pytest >= 8.4.2 (for running tests)

**Metrics:**
- 16 manifests (one per task)
- 60 tests (100% passing)
- 15+ Python modules
- 19 prompt template files
- Alpha release status

[0.1.0]: https://github.com/mamertofabian/maid-agents/releases/tag/v0.1.0
