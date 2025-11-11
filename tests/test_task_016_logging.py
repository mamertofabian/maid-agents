"""Behavioral tests for Task-016: Logging."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_logging_module_can_be_imported():
    """Test logging utils module can be imported."""
    try:
        from maid_agents.utils.logging import setup_logging

        assert callable(setup_logging)
    except ImportError:
        pytest.fail("Cannot import logging module")


def test_setup_logging_function():
    """Test setup_logging function exists and can be called."""
    from maid_agents.utils.logging import setup_logging

    # Call with INFO level
    result = setup_logging(level="INFO")
    assert result is None  # Function returns None


def test_setup_logging_with_different_levels():
    """Test setup_logging with different log levels."""
    from maid_agents.utils.logging import setup_logging

    # Test with DEBUG
    setup_logging(level="DEBUG")

    # Test with WARNING
    setup_logging(level="WARNING")

    # Should not raise errors
    assert True


def test_get_logger_function():
    """Test get_logger function returns a logger instance."""
    from maid_agents.utils.logging import get_logger
    import logging

    logger = get_logger("test_module")
    assert logger is not None
    assert isinstance(logger, logging.Logger)
    assert logger.name == "maid_agents.test_module"


def test_log_phase_start_function():
    """Test log_phase_start function exists and can be called."""
    from maid_agents.utils.logging import log_phase_start

    # Should not raise errors
    log_phase_start("TESTING")
    assert callable(log_phase_start)


def test_log_phase_end_function():
    """Test log_phase_end function exists and can be called."""
    from maid_agents.utils.logging import log_phase_end

    # Test with success
    log_phase_end("TESTING", success=True)

    # Test with failure
    log_phase_end("TESTING", success=False)

    assert callable(log_phase_end)


def test_log_context_class():
    """Test LogContext class exists and can be used as context manager."""
    from maid_agents.utils.logging import LogContext

    # Test using as context manager
    with LogContext("Test Context") as ctx:
        assert ctx is not None

    # Test with different styles
    with LogContext("Test Success", style="success"):
        pass

    with LogContext("Test Warning", style="warning"):
        pass


def test_log_agent_action_function():
    """Test log_agent_action helper function."""
    from maid_agents.utils.logging import log_agent_action

    # Should not raise errors
    log_agent_action("TestAgent", "doing something")
    log_agent_action("TestAgent", "doing something", details="extra info")


def test_log_file_operation_function():
    """Test log_file_operation helper function."""
    from maid_agents.utils.logging import log_file_operation

    # Should not raise errors
    log_file_operation("Creating", "test.py")
    log_file_operation("Editing", "/path/to/file.py")


def test_log_validation_result_function():
    """Test log_validation_result helper function."""
    from maid_agents.utils.logging import log_validation_result

    # Test passing validation
    log_validation_result("Structural", passed=True)

    # Test failing validation with errors
    log_validation_result("Behavioral", passed=False, errors=["Error 1", "Error 2"])


def test_log_iteration_function():
    """Test log_iteration helper function."""
    from maid_agents.utils.logging import log_iteration

    # Should not raise errors
    log_iteration(1, 10, "Starting iteration")
    log_iteration(5, 10, "Halfway done")


def test_spinner_function():
    """Test spinner context manager."""
    from maid_agents.utils.logging import _spinner

    # Test using as context manager
    with _spinner("Processing...") as progress:
        # Spinner should be running
        assert progress is not None
