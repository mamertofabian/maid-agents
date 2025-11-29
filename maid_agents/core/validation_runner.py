"""Validation Runner - Wraps maid-runner CLI calls for manifest validation and test execution.

This module provides a clean interface to interact with the maid-runner CLI tool,
handling manifest validation and behavioral test execution with proper error handling
and result parsing.
"""

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional

# Constants for improved maintainability
DEFAULT_TIMEOUT_SECONDS = 300
MAID_CLI_COMMAND = "maid"
VALIDATION_SUBCOMMAND = "validate"
CHAIN_FLAG = "--use-manifest-chain"

# Error patterns for robust parsing
ERROR_INDICATORS = ["error", "✗", "failed", "exception"]
TEST_FAILURE_INDICATORS = ["FAILED", "ERROR", "XFAIL"]


@dataclass
class ValidationResult:
    """Result of a validation or test execution operation.

    Attributes:
        success: Whether the operation completed successfully
        stdout: Standard output from the command
        stderr: Standard error output from the command
        errors: List of parsed error messages for easier consumption
    """

    success: bool
    stdout: str
    stderr: str
    errors: List[str]


class ValidationRunner:
    """Wraps maid-runner CLI for validation operations.

    This class provides a clean Python interface to interact with the maid-runner
    command-line tool, handling both manifest validation and behavioral test execution.
    It includes proper error handling, timeout management, and output parsing.
    """

    def __init__(self):
        """Initialize validation runner.

        Currently no initialization is required, but this provides
        a consistent interface for future extensions.
        """
        pass

    def validate_manifest(
        self, manifest_path: str, use_chain: bool = False
    ) -> ValidationResult:
        """Run manifest validation using maid-runner CLI.

        Executes the maid validate command to check manifest structure and compliance.
        Optionally uses manifest chain validation for related manifests.

        Args:
            manifest_path: Path to the manifest file to validate
            use_chain: Whether to use manifest chain validation for related manifests

        Returns:
            ValidationResult containing success status, output, and parsed errors
        """
        command = self._build_validation_command(manifest_path, use_chain)
        return self._execute_command(
            command, error_parser=self._parse_validation_errors
        )

    def run_behavioral_tests(self, manifest_path: str) -> ValidationResult:
        """Execute behavioral tests specified in the manifest.

        Loads the manifest file, extracts the validation command (typically pytest),
        and executes it with proper environment setup for module imports.

        Args:
            manifest_path: Path to manifest file containing validationCommand

        Returns:
            ValidationResult with test execution status and parsed failures
        """
        validation_command = self._load_validation_command(manifest_path)
        if validation_command is None:
            return self._create_error_result(
                f"Manifest not found or invalid: {manifest_path}",
                ["File not found or invalid JSON"],
            )

        if not validation_command:
            return self._create_error_result(
                "No validationCommand in manifest", ["Missing validationCommand"]
            )

        environment = self._prepare_test_environment()
        return self._execute_command(
            validation_command,
            environment=environment,
            error_parser=self._parse_test_failures,
        )

    def _run_format(self) -> ValidationResult:
        """Run code formatting using make format.

        Executes 'make format' to automatically format code according to style guidelines.

        Returns:
            ValidationResult with formatting status
        """
        command = ["make", "format"]
        return self._execute_command(command)

    def _run_lint(self) -> ValidationResult:
        """Run linting checks using make lint.

        Executes 'make lint' to check for code quality issues.

        Returns:
            ValidationResult with linting status and any issues found
        """
        command = ["make", "lint"]
        return self._execute_command(
            command, error_parser=self._parse_validation_errors
        )

    def _build_validation_command(
        self, manifest_path: str, use_chain: bool
    ) -> List[str]:
        """Build the maid validate command with appropriate flags.

        Args:
            manifest_path: Path to manifest file
            use_chain: Whether to include chain validation flag

        Returns:
            List of command arguments ready for subprocess
        """
        command = [MAID_CLI_COMMAND, VALIDATION_SUBCOMMAND, manifest_path]
        if use_chain:
            command.append(CHAIN_FLAG)
        return command

    def _load_validation_command(self, manifest_path: str) -> Optional[List[str]]:
        """Load and extract validation command from manifest file.

        Args:
            manifest_path: Path to manifest file

        Returns:
            List of validation command arguments or None if error
        """
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
            command = manifest.get("validationCommand", [])
            # Normalize paths in the command to handle duplicate maid_agents/ prefix
            return self._normalize_command_paths(command)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def _normalize_command_paths(self, command: List[str]) -> List[str]:
        """Normalize file paths in a command by removing duplicate maid_agents/ prefix.

        Args:
            command: List of command arguments

        Returns:
            List with normalized paths
        """
        normalized = []
        for arg in command:
            # Check if this looks like a file path (not a flag/option)
            if arg and not arg.startswith("-") and "/" in arg:
                normalized_path = self._normalize_path(arg)
                normalized.append(normalized_path)
            else:
                normalized.append(arg)
        return normalized

    def _normalize_path(self, path: str) -> str:
        """Normalize file path by removing duplicate maid_agents/ prefix.

        Args:
            path: Original file path

        Returns:
            Normalized path with duplicate prefix removed
        """
        # Remove duplicate maid-agents/maid_agents/ prefix
        if path.startswith("maid-agents/maid_agents/"):
            return path.replace("maid-agents/maid_agents/", "maid_agents/", 1)
        # Also handle maid-agents/tests/ -> tests/ (test files are at root)
        if path.startswith("maid-agents/tests/") and not Path(path).exists():
            normalized = path.replace("maid-agents/tests/", "tests/", 1)
            if Path(normalized).exists():
                return normalized
        return path

    def _prepare_test_environment(self) -> Dict[str, str]:
        """Prepare environment variables for test execution.

        Sets up PYTHONPATH to ensure tests can import local modules.

        Returns:
            Dictionary of environment variables
        """
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd())
        return env

    def _execute_command(
        self,
        command: List[str],
        environment: Optional[Dict[str, str]] = None,
        error_parser: Optional[callable] = None,
    ) -> ValidationResult:
        """Execute a command and capture results with timeout handling.

        This is the central command execution method that handles subprocess
        management, timeout, and error capture in a consistent way.

        Args:
            command: List of command arguments to execute
            environment: Optional environment variables dict
            error_parser: Optional function to parse errors from output

        Returns:
            ValidationResult with execution status and output
        """
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=DEFAULT_TIMEOUT_SECONDS,
                env=environment,
            )

            success = result.returncode == 0
            errors = []

            if not success and error_parser:
                # Parse errors from appropriate output stream
                output_to_parse = (
                    result.stdout if "pytest" in str(command) else result.stderr
                )
                errors = error_parser(output_to_parse)

            return ValidationResult(
                success=success,
                stdout=result.stdout,
                stderr=result.stderr,
                errors=errors,
            )

        except subprocess.TimeoutExpired:
            return self._create_timeout_result()
        except Exception as e:
            return self._create_exception_result(e)

    def _create_error_result(
        self, error_message: str, errors: List[str]
    ) -> ValidationResult:
        """Create a ValidationResult for error conditions.

        Args:
            error_message: Error message for stderr
            errors: List of parsed error messages

        Returns:
            ValidationResult with error status
        """
        return ValidationResult(
            success=False, stdout="", stderr=error_message, errors=errors
        )

    def _create_timeout_result(self) -> ValidationResult:
        """Create a ValidationResult for timeout conditions.

        Returns:
            ValidationResult indicating timeout
        """
        return ValidationResult(
            success=False,
            stdout="",
            stderr=f"Command timed out after {DEFAULT_TIMEOUT_SECONDS} seconds",
            errors=["Timeout"],
        )

    def _create_exception_result(self, exception: Exception) -> ValidationResult:
        """Create a ValidationResult for unexpected exceptions.

        Args:
            exception: The exception that occurred

        Returns:
            ValidationResult with exception details
        """
        error_str = str(exception)
        return ValidationResult(
            success=False, stdout="", stderr=error_str, errors=[error_str]
        )

    def _parse_validation_errors(self, output: str) -> List[str]:
        """Parse error messages from validation command output.

        Looks for common error indicators and extracts relevant lines
        for easier error diagnosis.

        Args:
            output: Raw output string to parse

        Returns:
            List of error message strings
        """
        return self._extract_matching_lines(output, ERROR_INDICATORS)

    def _parse_test_failures(self, output: str) -> List[str]:
        """Parse test failure messages from pytest output.

        Extracts lines containing test failure indicators like FAILED or ERROR.

        Args:
            output: Raw pytest output to parse

        Returns:
            List of test failure message strings
        """
        return self._extract_matching_lines(output, TEST_FAILURE_INDICATORS)

    def _extract_matching_lines(self, text: str, indicators: List[str]) -> List[str]:
        """Extract lines containing any of the specified indicators.

        Generic line extraction method used by both error and test parsers.

        Args:
            text: Text to search through
            indicators: List of strings to search for (case-insensitive)

        Returns:
            List of matching lines, stripped of whitespace
        """
        if not text:
            return []

        matching_lines = []
        for line in text.split("\n"):
            line_lower = line.lower()
            if any(indicator.lower() in line_lower for indicator in indicators):
                stripped_line = line.strip()
                if stripped_line:  # Only add non-empty lines
                    matching_lines.append(stripped_line)

        return matching_lines

    def _parse_errors(self, stderr: str) -> List[str]:
        """Parse error messages from stderr.

        Legacy method maintained for API compatibility.
        Delegates to the improved _parse_validation_errors method.

        Args:
            stderr: Standard error output to parse

        Returns:
            List of error message strings
        """
        return self._parse_validation_errors(stderr)
