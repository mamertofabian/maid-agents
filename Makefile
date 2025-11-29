# MAID Agents Development Makefile
# Convenience commands for development workflow

.PHONY: help install install-dev test lint lint-fix format type-check validate clean

# Unset VIRTUAL_ENV to let uv manage the virtual environment
SHELL := /bin/bash
.SHELLFLAGS := -c
export VIRTUAL_ENV :=

help:
	@echo "MAID Agents Development Commands:"
	@echo ""
	@echo "Setup:"
	@echo "  make install       - Install package in editable mode"
	@echo "  make install-dev   - Install package with dev dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run all tests"
	@echo "  make validate      - Validate all manifests"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          - Run linting checks (ruff)"
	@echo "  make lint-fix      - Run linting with auto-fix"
	@echo "  make format        - Format code (black)"
	@echo "  make type-check    - Run type checking (mypy)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean         - Clean build artifacts and cache files"

# Install package in editable mode
install:
	uv pip install -e .

# Install development dependencies
install-dev:
	uv pip install -e ".[dev]"

# Run all tests
test:
	uv run python -m pytest tests/ -v

# Code quality checks
lint:
	uv run ruff check maid_agents/ tests/

lint-fix:
	uv run ruff check --fix maid_agents/ tests/

format:
	uv run python -m black maid_agents/ tests/

# Type checking
type-check:
	uv run python -m mypy maid_agents/

# Validate all manifests
validate:
	@for manifest in manifests/task-*.manifest.json; do \
		echo "Validating $$manifest..."; \
		uv run maid validate $$manifest --quiet --use-manifest-chain || exit 1; \
	done
	@echo "✅ All manifests valid"

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
