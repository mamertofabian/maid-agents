"""MAID Orchestrator - Coordinates the MAID workflow phases.

This module provides the core orchestration logic for executing the MAID workflow.
"""

import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from maid_agents.agents.manifest_architect import ManifestArchitect
from maid_agents.agents.refiner import Refiner
from maid_agents.agents.refactorer import Refactorer
from maid_agents.agents.test_designer import TestDesigner
from maid_agents.claude.cli_wrapper import ClaudeWrapper
from maid_agents.core.validation_runner import ValidationRunner
from maid_agents.utils.logging import (
    LogContext,
    log_agent_action,
    log_file_operation,
    log_iteration,
    log_phase_end,
    log_phase_start,
    log_validation_result,
)

logger = logging.getLogger(__name__)

# Maximum file size for generated code (1MB)
MAX_FILE_SIZE = 1_000_000


class WorkflowState(Enum):
    """Workflow state machine states."""

    INIT = "init"
    PLANNING = "planning"
    IMPLEMENTING = "implementing"
    REFACTORING = "refactoring"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class WorkflowResult:
    """Result of workflow execution."""

    success: bool
    manifest_path: str
    message: str


class MAIDOrchestrator:
    """Orchestrates the complete MAID workflow."""

    def __init__(
        self,
        claude: Optional[ClaudeWrapper] = None,
        manifest_architect: Optional[ManifestArchitect] = None,
        test_designer: Optional[TestDesigner] = None,
        validation_runner: Optional[ValidationRunner] = None,
        dry_run: bool = False,
    ):
        """Initialize orchestrator.

        Args:
            claude: Claude wrapper (creates default if None)
            manifest_architect: Manifest architect agent (creates default if None)
            test_designer: Test designer agent (creates default if None)
            validation_runner: Validation runner (creates default if None)
            dry_run: If True, skip all file write operations (for testing)
        """
        self._state = WorkflowState.INIT
        self.dry_run = dry_run

        # Create default Claude wrapper if not provided
        if claude is None:
            if dry_run:
                # In dry_run mode, mock is appropriate for testing
                claude = ClaudeWrapper(mock_mode=True)
                logger.info(
                    "🧪 TEST MODE: Using mock Claude wrapper (dry_run=True). "
                    "No real API calls will be made."
                )
            else:
                # In production mode, require explicit Claude instance
                raise ValueError(
                    "Production mode requires explicit Claude instance. "
                    "Pass a ClaudeWrapper with mock_mode=False to __init__(), "
                    "or use dry_run=True for testing without API calls."
                )

        # Store Claude wrapper for use by dynamically created agents
        self.claude = claude

        # Create agents with provided or default Claude wrapper
        self.manifest_architect = manifest_architect or ManifestArchitect(claude)
        self.test_designer = test_designer or TestDesigner(claude)
        self.validation_runner = validation_runner or ValidationRunner()

    def _validate_safe_path(self, path: str) -> Path:
        """Validate that a path is safe and within the project directory.

        Args:
            path: Path string to validate

        Returns:
            Resolved Path object

        Raises:
            ValueError: If path is outside project directory
        """
        resolved_path = Path(path).resolve()
        project_dir = Path.cwd().resolve()

        try:
            # Check if the path is relative to the project directory
            resolved_path.relative_to(project_dir)
            return resolved_path
        except ValueError:
            raise ValueError(
                f"Path '{path}' is outside project directory. "
                f"Only paths within {project_dir} are allowed."
            )

    def run_full_workflow(self, goal: str) -> WorkflowResult:
        """Execute complete MAID workflow from goal to integration.

        Args:
            goal: High-level goal description

        Returns:
            WorkflowResult with status and manifest path
        """
        # Phase 1-2: Planning Loop (manifest + tests)
        planning_result = self.run_planning_loop(goal=goal)

        if not planning_result["success"]:
            return WorkflowResult(
                success=False,
                manifest_path="",
                message=f"Planning failed: {planning_result['error']}",
            )

        manifest_path = planning_result["manifest_path"]

        # Phase 3: Implementation Loop (code generation)
        impl_result = self.run_implementation_loop(manifest_path=manifest_path)

        if not impl_result["success"]:
            return WorkflowResult(
                success=False,
                manifest_path=manifest_path,
                message=f"Implementation failed: {impl_result['error']}",
            )

        # Success! Workflow complete
        return WorkflowResult(
            success=True,
            manifest_path=manifest_path,
            message=f"Workflow complete! Manifest: {manifest_path}",
        )

    def get_workflow_state(self) -> WorkflowState:
        """Get current workflow state.

        Returns:
            Current WorkflowState
        """
        return self._state

    def run_planning_loop(self, goal: str, max_iterations: int = 10) -> dict:
        """Execute planning loop: manifest creation + test generation with validation.

        Args:
            goal: High-level goal description
            max_iterations: Maximum planning iterations

        Returns:
            Dict with planning loop results
        """
        self._state = WorkflowState.PLANNING
        log_phase_start("PLANNING")

        # Determine next task number by counting existing manifests
        task_number = self._get_next_task_number()
        logger.info(f"Planning task-{task_number:03d}: {goal}")

        iteration = 0
        last_error = None

        while iteration < max_iterations:
            iteration += 1
            log_iteration(iteration, max_iterations, "Creating manifest and tests")

            # Step 1: Create manifest using ManifestArchitect
            with LogContext(
                f"Step 1: Creating manifest (task-{task_number:03d})", style="info"
            ):
                log_agent_action(
                    "ManifestArchitect", "creating manifest", details=goal[:50]
                )
                manifest_result = self.manifest_architect.create_manifest(
                    goal=goal, task_number=task_number
                )

                if not manifest_result["success"]:
                    last_error = f"Manifest creation failed: {manifest_result['error']}"
                    logger.error(last_error)
                    continue

                manifest_path = manifest_result["manifest_path"]
                manifest_data = manifest_result["manifest_data"]

            # Save manifest to disk (skip in dry_run mode)
            manifest_file = Path(manifest_path)
            if not self.dry_run:
                try:
                    manifest_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(manifest_file, "w") as f:
                        json.dump(manifest_data, f, indent=2)
                    log_file_operation("Created", str(manifest_file))
                except Exception as e:
                    last_error = f"Failed to save manifest: {e}"
                    logger.error(last_error)
                    continue

            # Step 2: Create tests using TestDesigner
            with LogContext("Step 2: Creating behavioral tests", style="info"):
                log_agent_action(
                    "TestDesigner", "generating tests", details=str(manifest_file)
                )
                test_result = self.test_designer.create_tests(
                    manifest_path=str(manifest_file)
                )

                if not test_result["success"]:
                    last_error = f"Test generation failed: {test_result['error']}"
                    logger.error(last_error)
                    continue

                test_paths = test_result["test_paths"]
                test_code = test_result["test_code"]

            # Save test files to disk (skip in dry_run mode)
            if not self.dry_run:
                try:
                    for test_path in test_paths:
                        test_file = Path(test_path)
                        test_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(test_file, "w") as f:
                            f.write(test_code)
                        log_file_operation("Created", str(test_file))
                except Exception as e:
                    last_error = f"Failed to save test files: {e}"
                    logger.error(last_error)
                    continue

            # Step 3: Run behavioral validation
            with LogContext("Step 3: Running behavioral validation", style="info"):
                # Validate that tests USE the declared artifacts (behavioral mode)
                # With the validator fix, this now works without implementation file existing
                validation_result = self._validate_behavioral_tests(
                    manifest_path=str(manifest_file)
                )

                log_validation_result(
                    "Behavioral",
                    passed=validation_result["success"],
                    errors=(
                        [validation_result.get("error")]
                        if not validation_result["success"]
                        else None
                    ),
                )

            if validation_result["success"]:
                # Planning loop succeeded!
                log_phase_end("PLANNING", success=True)
                return {
                    "success": True,
                    "manifest_path": str(manifest_file),
                    "test_paths": [str(p) for p in test_paths],
                    "iterations": iteration,
                    "error": None,
                }
            else:
                # Validation failed - prepare error feedback for next iteration
                last_error = (
                    f"Behavioral validation failed: {validation_result['error']}"
                )
                logger.warning(f"Iteration {iteration} failed, retrying...")
                continue

        # Max iterations reached without success
        error_msg = f"Planning loop failed after {max_iterations} iterations. Last error: {last_error}"
        logger.error(error_msg)
        log_phase_end("PLANNING", success=False)
        return {
            "success": False,
            "manifest_path": None,
            "test_paths": [],
            "iterations": iteration,
            "error": error_msg,
        }

    def _validate_behavioral_tests(self, manifest_path: str) -> dict:
        """Run behavioral validation on tests to ensure they USE declared artifacts.

        Args:
            manifest_path: Path to manifest file

        Returns:
            Dict with success status and error message
        """
        import subprocess

        # Validate path before using it in subprocess
        try:
            validated_path = self._validate_safe_path(manifest_path)
        except ValueError as e:
            return {"success": False, "error": str(e)}

        # Run maid validate with behavioral mode
        # This validates tests USE artifacts without requiring implementation to exist
        cmd = [
            "maid",
            "validate",
            str(validated_path),
            "--validation-mode",
            "behavioral",
            "--use-manifest-chain",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                return {"success": True, "error": None}
            else:
                return {
                    "success": False,
                    "error": f"{result.stderr}\n{result.stdout}",
                }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Behavioral validation timed out"}
        except Exception as e:
            return {"success": False, "error": f"Validation error: {e}"}

    def _get_next_task_number(self) -> int:
        """Determine next task number by counting existing manifests.

        Returns:
            Next available task number
        """
        manifests_dir = Path("manifests")
        if not manifests_dir.exists():
            return 1

        # Find all task-*.manifest.json files
        manifest_files = list(manifests_dir.glob("task-*.manifest.json"))

        if not manifest_files:
            return 1

        # Extract task numbers and find max
        task_numbers = []
        for manifest_file in manifest_files:
            # Extract number from filename like "task-042.manifest.json"
            try:
                num_str = manifest_file.stem.split("-")[1].split(".")[0]
                task_numbers.append(int(num_str))
            except (IndexError, ValueError):
                continue

        return max(task_numbers) + 1 if task_numbers else 1

    def run_implementation_loop(
        self, manifest_path: str, max_iterations: int = 20
    ) -> dict:
        """Execute implementation loop: code generation until tests pass.

        Args:
            manifest_path: Path to manifest file
            max_iterations: Maximum implementation iterations

        Returns:
            Dict with implementation loop results
        """
        self._state = WorkflowState.IMPLEMENTING
        log_phase_start("IMPLEMENTATION")
        logger.info(f"Implementing manifest: {manifest_path}")

        # Step 1: Run tests initially (should fail - red phase of TDD)
        with LogContext(
            "Step 1: Running tests (expecting failure - RED phase)", style="info"
        ):
            test_result = self.validation_runner.run_behavioral_tests(manifest_path)
            log_validation_result("Initial Tests", passed=test_result.success)

        test_errors = test_result.stderr if not test_result.success else ""

        iteration = 0
        last_error = None

        while iteration < max_iterations:
            iteration += 1
            log_iteration(iteration, max_iterations, "Generating code to pass tests")

            # Step 2: Generate code using Developer agent
            # Pass test errors from previous iteration (if any)
            with LogContext("Step 2: Generating implementation code", style="info"):
                from maid_agents.agents.developer import Developer

                developer = Developer(self.claude)
                log_agent_action(
                    "Developer",
                    "generating code",
                    details=f"fixing {len(test_errors[:200])}+ char errors",
                )
                impl_result = developer.implement(
                    manifest_path=manifest_path, test_errors=test_errors
                )

                if not impl_result["success"]:
                    last_error = f"Code generation failed: {impl_result['error']}"
                    logger.error(last_error)
                    continue

            # Step 3: Write generated code to files
            generated_code = impl_result.get("code", "")
            files_modified = impl_result.get("files_modified", [])

            if not generated_code:
                last_error = "No code generated"
                logger.warning(last_error)
                continue

            if not files_modified:
                last_error = "No files to modify"
                logger.warning(last_error)
                continue

            # Write code to the target file(s) (skip in dry_run mode)
            # Developer returns single code block for the primary file
            if not self.dry_run:
                try:
                    # Check file size before writing
                    if len(generated_code) > MAX_FILE_SIZE:
                        last_error = (
                            f"Generated code exceeds maximum file size "
                            f"({len(generated_code)} > {MAX_FILE_SIZE} bytes)"
                        )
                        logger.error(last_error)
                        continue

                    # Validate path before writing
                    target_file = self._validate_safe_path(files_modified[0])
                    target_file.parent.mkdir(parents=True, exist_ok=True)

                    with open(target_file, "w") as f:
                        f.write(generated_code)

                    log_file_operation("Updated", str(target_file))

                except ValueError as e:
                    last_error = f"Invalid path {files_modified[0]}: {e}"
                    logger.error(last_error)
                    continue
                except Exception as e:
                    last_error = f"Failed to write code to {files_modified[0]}: {e}"
                    logger.error(last_error)
                    continue

            # Step 4: Run tests again
            with LogContext(
                "Step 3: Running tests (expecting success - GREEN phase)", style="info"
            ):
                test_result = self.validation_runner.run_behavioral_tests(manifest_path)
                log_validation_result(
                    "Implementation Tests", passed=test_result.success
                )

            # Check for systemic errors that cannot be fixed by changing implementation
            if not test_result.success:
                test_output = f"{test_result.stdout}\n{test_result.stderr}"
                is_systemic, systemic_msg = self._is_systemic_error(test_output)
                if is_systemic:
                    # Bail out immediately - this is not an implementation issue
                    error_msg = f"Systemic error detected (cannot be fixed by changing implementation):\n{systemic_msg}"
                    logger.error(error_msg)
                    log_phase_end("IMPLEMENTATION", success=False)
                    return {
                        "success": False,
                        "iterations": iteration,
                        "error": error_msg,
                    }

            if test_result.success:
                # Tests pass! Now validate manifest compliance
                with LogContext(
                    "Step 4: Validating manifest compliance", style="success"
                ):
                    validation_result = self.validation_runner.validate_manifest(
                        manifest_path, use_chain=True
                    )
                    log_validation_result(
                        "Manifest Compliance", passed=validation_result.success
                    )

                if validation_result.success:
                    # Success! Tests pass and manifest validates
                    logger.info(f"Implementation complete in {iteration} iteration(s)!")
                    log_phase_end("IMPLEMENTATION", success=True)
                    return {
                        "success": True,
                        "iterations": iteration,
                        "files_modified": files_modified,
                        "error": None,
                    }
                else:
                    # Tests pass but manifest validation fails
                    last_error = (
                        f"Manifest validation failed: {validation_result.stderr}"
                    )
                    logger.warning(f"Iteration {iteration} failed, retrying...")
                    continue
            else:
                # Tests still failing - extract errors for next iteration
                test_errors = f"{test_result.stdout}\n{test_result.stderr}"
                last_error = f"Tests failed: {'; '.join(test_result.errors)}"
                logger.warning(f"Iteration {iteration} failed, retrying...")
                continue

        # Max iterations reached without success
        error_msg = f"Implementation loop failed after {max_iterations} iterations. Last error: {last_error}"
        logger.error(error_msg)
        log_phase_end("IMPLEMENTATION", success=False)
        return {
            "success": False,
            "iterations": iteration,
            "error": error_msg,
        }

    def run_refinement_loop(
        self, manifest_path: str, refinement_goal: str, max_iterations: int = 5
    ) -> dict:
        """Execute refinement loop: refine manifest and tests with validation.

        Args:
            manifest_path: Path to manifest file to refine
            refinement_goal: User's refinement objectives/goals
            max_iterations: Maximum refinement iterations

        Returns:
            Dict with refinement loop results
        """
        log_phase_start("REFINEMENT")
        logger.info(f"Refining manifest: {manifest_path}")
        logger.info(f"Goal: {refinement_goal}")

        # Lazy-initialize refiner if needed
        if not hasattr(self, "refiner"):
            self.refiner = Refiner(self.claude)

        iteration = 0
        last_error = ""

        while iteration < max_iterations:
            iteration += 1
            log_iteration(iteration, max_iterations, "Refining manifest and tests")

            # Step 1: Refine manifest and tests
            with LogContext(
                "Step 1: Analyzing and improving manifest/tests", style="info"
            ):
                log_agent_action(
                    "Refiner",
                    "analyzing manifest and tests",
                    details=refinement_goal[:50],
                )
                refine_result = self.refiner.refine(
                    manifest_path=manifest_path,
                    refinement_goal=refinement_goal,
                    validation_feedback=last_error,
                )

                if not refine_result["success"]:
                    last_error = f"Refinement failed: {refine_result['error']}"
                    logger.error(last_error)
                    continue

            manifest_data = refine_result["manifest_data"]
            test_code_dict = refine_result["test_code"]

            # Step 2: Write refined files to disk (skip in dry_run mode)
            if not self.dry_run:
                try:
                    # Write manifest
                    manifest_file = Path(manifest_path)
                    manifest_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(manifest_file, "w") as f:
                        json.dump(manifest_data, f, indent=2)
                    log_file_operation("Updated", str(manifest_file))

                    # Write test files
                    for test_path, test_code in test_code_dict.items():
                        test_file = Path(test_path)
                        test_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(test_file, "w") as f:
                            f.write(test_code)
                        log_file_operation("Updated", str(test_file))

                except Exception as e:
                    last_error = f"Failed to write refined files: {e}"
                    logger.error(last_error)
                    continue

            # Step 3: Structural validation
            with LogContext("Step 2: Running structural validation", style="info"):
                validation_result = self.validation_runner.validate_manifest(
                    manifest_path, use_chain=True
                )
                log_validation_result("Structural", passed=validation_result.success)

            if not validation_result.success:
                last_error = f"Structural validation failed: {validation_result.stderr}"
                logger.warning(f"Iteration {iteration} failed, retrying...")
                continue

            # Step 4: Behavioral test validation
            with LogContext("Step 3: Running behavioral validation", style="info"):
                behavioral_result = self._validate_behavioral_tests(manifest_path)
                log_validation_result("Behavioral", passed=behavioral_result["success"])

            if behavioral_result["success"]:
                # Refinement complete - both validations pass!
                logger.info(f"Refinement complete in {iteration} iteration(s)!")
                log_phase_end("REFINEMENT", success=True)
                return {
                    "success": True,
                    "iterations": iteration,
                    "improvements": refine_result.get("improvements", []),
                    "error": None,
                }
            else:
                # Behavioral validation failed - provide feedback for next iteration
                last_error = behavioral_result["output"]
                logger.warning(f"Iteration {iteration} failed, retrying...")
                continue

        # Max iterations reached without success
        error_msg = f"Refinement loop failed after {max_iterations} iterations. Last error: {last_error}"
        logger.error(error_msg)
        log_phase_end("REFINEMENT", success=False)
        return {
            "success": False,
            "iterations": iteration,
            "error": error_msg,
        }

    def run_refactoring_loop(
        self, manifest_path: str, max_iterations: int = 10
    ) -> dict:
        """Execute refactoring loop: refactor code with validation and testing.

        Args:
            manifest_path: Path to manifest file to refactor
            max_iterations: Maximum refactoring iterations

        Returns:
            Dict with refactoring loop results
        """
        self._state = WorkflowState.REFACTORING
        log_phase_start("REFACTORING")
        logger.info(f"Refactoring code for manifest: {manifest_path}")

        # Lazy-initialize refactorer if needed
        if not hasattr(self, "refactorer"):
            self.refactorer = Refactorer(self.claude)

        iteration = 0
        last_error = ""

        while iteration < max_iterations:
            iteration += 1
            log_iteration(iteration, max_iterations, "Refactoring code")

            # Step 1: Refactor code
            with LogContext("Step 1: Refactoring code", style="info"):
                log_agent_action(
                    "Refactorer",
                    "refactoring code",
                    details=manifest_path,
                )
                refactor_result = self.refactorer.refactor(
                    manifest_path=manifest_path,
                    validation_feedback=last_error if last_error else "",
                )

                if not refactor_result["success"]:
                    # Check if error is systemic (e.g., timeout)
                    error_msg = refactor_result.get("error", "Unknown error")
                    is_systemic, systemic_msg = self._is_systemic_error(error_msg)
                    if is_systemic:
                        error_msg = f"Systemic error detected (cannot be fixed by refactoring):\n{systemic_msg}"
                        logger.error(error_msg)
                        log_phase_end("REFACTORING", success=False)
                        return {
                            "success": False,
                            "iterations": iteration,
                            "error": error_msg,
                        }
                    last_error = f"Refactoring failed: {error_msg}"
                    logger.error(last_error)
                    continue

            improvements = refactor_result.get("improvements", [])

            # Step 2: Structural validation (maid validate)
            with LogContext("Step 2: Running structural validation", style="info"):
                validation_result = self.validation_runner.validate_manifest(
                    manifest_path, use_chain=True
                )
                log_validation_result("Structural", passed=validation_result.success)

            if not validation_result.success:
                last_error = f"Structural validation failed:\n{validation_result.stderr}\n{validation_result.stdout}"
                logger.warning(f"Iteration {iteration} failed, retrying...")
                continue

            # Step 3: Behavioral test validation (maid test / validationCommand)
            with LogContext("Step 3: Running behavioral tests", style="info"):
                test_result = self.validation_runner.run_behavioral_tests(manifest_path)
                log_validation_result("Behavioral", passed=test_result.success)

            # Check for systemic errors that cannot be fixed by refactoring
            if not test_result.success:
                test_output = f"{test_result.stdout}\n{test_result.stderr}"
                is_systemic, systemic_msg = self._is_systemic_error(test_output)
                if is_systemic:
                    # Bail out immediately - this is not a refactoring issue
                    error_msg = f"Systemic error detected (cannot be fixed by refactoring):\n{systemic_msg}"
                    logger.error(error_msg)
                    log_phase_end("REFACTORING", success=False)
                    return {
                        "success": False,
                        "iterations": iteration,
                        "error": error_msg,
                    }

            if test_result.success:
                # Refactoring complete - both validations pass!
                logger.info(f"Refactoring complete in {iteration} iteration(s)!")
                log_phase_end("REFACTORING", success=True)
                return {
                    "success": True,
                    "iterations": iteration,
                    "improvements": improvements,
                    "files_written": refactor_result.get("files_written", []),
                    "error": None,
                }
            else:
                # Tests failed - provide comprehensive feedback for next iteration
                test_output = f"{test_result.stdout}\n{test_result.stderr}".strip()
                if test_result.errors:
                    error_summary = "\n".join(test_result.errors)
                    last_error = f"Tests failed:\n{error_summary}\n\nFull test output:\n{test_output}"
                else:
                    last_error = f"Tests failed. Full test output:\n{test_output}"
                logger.warning(f"Iteration {iteration} failed, retrying...")
                continue

        # Max iterations reached without success
        error_msg = f"Refactoring loop failed after {max_iterations} iterations. Last error: {last_error}"
        logger.error(error_msg)
        log_phase_end("REFACTORING", success=False)
        return {
            "success": False,
            "iterations": iteration,
            "error": error_msg,
        }

    def _is_systemic_error(self, test_output: str) -> tuple[bool, str]:
        """Detect if test failure is due to systemic issues, not implementation.

        Systemic errors include test framework failures, import errors, missing files,
        etc. that cannot be fixed by changing the implementation code.

        Args:
            test_output: Combined stdout and stderr from test execution

        Returns:
            Tuple of (is_systemic, error_message)
        """
        # Patterns that indicate systemic issues, not implementation problems
        systemic_patterns = [
            (
                "ERROR collecting",
                "Test collection failed - check test file imports and syntax",
            ),
            (
                "ModuleNotFoundError",
                "Module import failed - check PYTHONPATH or missing dependencies",
            ),
            ("ImportError", "Import failed - check module availability"),
            ("INTERNALERROR", "pytest internal error - check test framework setup"),
            ("SyntaxError", "Syntax error in test file - fix test file syntax"),
            ("pytest: error:", "pytest configuration error - check pytest setup"),
            (
                "No module named 'pytest'",
                "pytest not installed - install test framework",
            ),
            (
                "file or directory not found",
                "Test file not found - check test file path in manifest",
            ),
            (
                "ERROR: file or directory not found",
                "Test file not found - check test file path in manifest",
            ),
            (
                "no tests ran",
                "No tests found - check test file path and test discovery",
            ),
            (
                "timed out",
                "Operation timed out - check network connection or increase timeout",
            ),
            (
                "Claude CLI timed out",
                "Claude API timed out - check network connection or increase timeout",
            ),
            (
                "TimeoutExpired",
                "Command timed out - check system resources or increase timeout",
            ),
        ]

        for pattern, message in systemic_patterns:
            if pattern in test_output:
                return (
                    True,
                    f"Systemic error detected: {message}\n\nFull output:\n{test_output[:500]}",
                )

        return False, ""

    def _handle_error(self, error: Exception) -> dict:
        """Handle errors during workflow execution with categorization and recovery suggestions.

        Provides comprehensive error handling with:
        - Error categorization (transient vs permanent, recoverable vs fatal)
        - Context preservation (stack trace, operation context)
        - User-friendly messages with actionable suggestions
        - Integration with logging system

        Args:
            error: Exception that occurred

        Returns:
            Dict with comprehensive error information:
            - error: Original error message
            - error_type: Exception class name
            - category: Error category (transient, permanent, validation, configuration, etc.)
            - recoverable: Boolean indicating if error is recoverable
            - message: User-friendly error message
            - suggestion: Actionable suggestion for resolution
            - stack_trace: Full stack trace for debugging
        """
        import traceback

        error_type = type(error).__name__
        error_message = str(error)
        stack_trace = traceback.format_exc()

        # Categorize error and determine if recoverable
        category, recoverable, user_message, suggestion = self._categorize_error(
            error, error_type, error_message
        )

        # Log error with appropriate level
        if recoverable:
            logger.warning(
                f"Recoverable {category} error: {error_type}: {error_message}"
            )
        else:
            logger.error(
                f"Fatal {category} error: {error_type}: {error_message}",
                exc_info=True,
            )

        return {
            "error": error_message,
            "error_type": error_type,
            "category": category,
            "recoverable": recoverable,
            "message": user_message,
            "suggestion": suggestion,
            "stack_trace": stack_trace,
        }

    def _categorize_error(
        self, error: Exception, error_type: str, error_message: str
    ) -> tuple[str, bool, str, str]:
        """Categorize error and provide recovery guidance.

        Args:
            error: The exception object
            error_type: Name of exception class
            error_message: String representation of error

        Returns:
            Tuple of (category, recoverable, user_message, suggestion)
        """
        # Network/API errors - typically transient
        if any(
            keyword in error_type
            for keyword in ["Timeout", "Connection", "Network", "HTTP"]
        ):
            return (
                "network",
                True,
                "Network or API error occurred",
                "Check your internet connection and API credentials. This error is often transient - try again.",
            )

        # File I/O errors - may be recoverable
        if any(
            keyword in error_type
            for keyword in ["FileNotFound", "Permission", "IOError", "OSError"]
        ):
            return (
                "filesystem",
                True,
                f"File system error: {error_message}",
                "Check file paths, permissions, and disk space. Ensure all required directories exist.",
            )

        # Validation errors - user input issue
        if any(
            keyword in error_type
            for keyword in [
                "Validation",
                "Schema",
                "ValueError",
                "KeyError",
                "AttributeError",
            ]
        ):
            return (
                "validation",
                True,
                f"Validation error: {error_message}",
                "Review the manifest structure and ensure all required fields are present with correct types.",
            )

        # JSON/parsing errors
        if any(
            keyword in error_type for keyword in ["JSON", "Parse", "Decode", "Syntax"]
        ):
            return (
                "parsing",
                True,
                f"Parsing error: {error_message}",
                "Check for malformed JSON or syntax errors in generated files. Review Claude's output.",
            )

        # Import/module errors - configuration issue
        if "Import" in error_type or "ModuleNotFound" in error_type:
            return (
                "configuration",
                False,
                f"Module import error: {error_message}",
                "Install missing dependencies with 'uv pip install -e .' or check your Python environment.",
            )

        # Memory errors - resource issue
        if any(keyword in error_type for keyword in ["Memory", "Resource"]):
            return (
                "resource",
                False,
                "System resource error occurred",
                "Check available memory and disk space. Consider reducing batch sizes or complexity.",
            )

        # Subprocess/command errors
        if any(
            keyword in error_type
            for keyword in ["CalledProcess", "Subprocess", "Command"]
        ):
            return (
                "subprocess",
                True,
                f"Command execution error: {error_message}",
                "Check command syntax and availability. Review pytest configuration and test file paths.",
            )

        # Default: Unknown error
        return (
            "unknown",
            False,
            f"Unexpected error: {error_type}: {error_message}",
            "Review the stack trace for details. This may require code changes or debugging.",
        )
