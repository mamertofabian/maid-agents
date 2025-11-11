"""Behavioral tests for Task-015: Error Handling."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from maid_agents.core.orchestrator import MAIDOrchestrator


def test_handle_error_method_exists():
    """Test _handle_error method exists and has correct signature."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    # Call the method with a test exception
    error = Exception("Test error")
    result = orchestrator._handle_error(error)

    assert isinstance(result, dict)
    assert "error" in result
    assert "message" in result


def test_handle_error_with_different_exceptions():
    """Test _handle_error handles different exception types."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    # Test with ValueError
    result1 = orchestrator._handle_error(ValueError("Value error"))
    assert isinstance(result1, dict)

    # Test with RuntimeError
    result2 = orchestrator._handle_error(RuntimeError("Runtime error"))
    assert isinstance(result2, dict)


def test_handle_error_returns_required_fields():
    """Test _handle_error returns all required fields."""
    orchestrator = MAIDOrchestrator(dry_run=True)
    error = ValueError("Test validation error")

    result = orchestrator._handle_error(error)

    # Verify all required fields are present
    assert "error" in result
    assert "error_type" in result
    assert "category" in result
    assert "recoverable" in result
    assert "message" in result
    assert "suggestion" in result
    assert "stack_trace" in result


def test_handle_error_network_errors():
    """Test network error categorization."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    # Simulate network errors
    class TimeoutError(Exception):
        pass

    error = TimeoutError("Connection timed out")
    result = orchestrator._handle_error(error)

    assert result["category"] == "network"
    assert result["recoverable"] is True
    assert "network" in result["message"].lower() or "api" in result["message"].lower()
    assert len(result["suggestion"]) > 0


def test_handle_error_validation_errors():
    """Test validation error categorization."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    error = ValueError("Invalid manifest structure")
    result = orchestrator._handle_error(error)

    assert result["category"] == "validation"
    assert result["recoverable"] is True
    assert "validation" in result["message"].lower()


def test_handle_error_filesystem_errors():
    """Test filesystem error categorization."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    error = FileNotFoundError("File not found: test.py")
    result = orchestrator._handle_error(error)

    assert result["category"] == "filesystem"
    assert result["recoverable"] is True
    assert (
        "file" in result["message"].lower() or "filesystem" in result["message"].lower()
    )


def test_handle_error_import_errors():
    """Test import error categorization."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    error = ImportError("No module named 'pytest'")
    result = orchestrator._handle_error(error)

    assert result["category"] == "configuration"
    assert result["recoverable"] is False  # Import errors are not easily recoverable
    assert (
        "import" in result["message"].lower() or "module" in result["message"].lower()
    )


def test_handle_error_parsing_errors():
    """Test JSON/parsing error categorization."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    class JSONDecodeError(Exception):
        pass

    error = JSONDecodeError("Invalid JSON syntax")
    result = orchestrator._handle_error(error)

    assert result["category"] == "parsing"
    assert result["recoverable"] is True


def test_handle_error_subprocess_errors():
    """Test subprocess error categorization."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    class CalledProcessError(Exception):
        pass

    error = CalledProcessError("Command failed with exit code 1")
    result = orchestrator._handle_error(error)

    assert result["category"] == "subprocess"
    assert result["recoverable"] is True


def test_handle_error_unknown_errors():
    """Test unknown error categorization."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    class CustomWeirdError(Exception):
        pass

    error = CustomWeirdError("Something weird happened")
    result = orchestrator._handle_error(error)

    assert result["category"] == "unknown"
    assert result["recoverable"] is False


def test_handle_error_includes_stack_trace():
    """Test that error handler includes stack trace."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    try:
        raise ValueError("Test error for stack trace")
    except ValueError as e:
        result = orchestrator._handle_error(e)

    assert "stack_trace" in result
    assert len(result["stack_trace"]) > 0
    assert "Traceback" in result["stack_trace"]


def test_handle_error_error_type_extraction():
    """Test that error type is correctly extracted."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    error = KeyError("missing_key")
    result = orchestrator._handle_error(error)

    assert result["error_type"] == "KeyError"


def test_handle_error_message_not_empty():
    """Test that error messages are never empty."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    errors = [
        ValueError("Validation failed"),
        FileNotFoundError("Not found"),
        ImportError("Module missing"),
        RuntimeError("Runtime error"),
    ]

    for error in errors:
        result = orchestrator._handle_error(error)
        assert len(result["message"]) > 0
        assert len(result["suggestion"]) > 0


def test_handle_error_preserves_original_message():
    """Test that original error message is preserved."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    original_message = "This is a very specific error message"
    error = RuntimeError(original_message)
    result = orchestrator._handle_error(error)

    assert result["error"] == original_message


def test_categorize_error_method_exists():
    """Test _categorize_error helper method exists."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    error = ValueError("test")
    category, recoverable, message, suggestion = orchestrator._categorize_error(
        error, "ValueError", "test"
    )

    assert isinstance(category, str)
    assert isinstance(recoverable, bool)
    assert isinstance(message, str)
    assert isinstance(suggestion, str)


def test_handle_error_multiple_calls_consistent():
    """Test that handling the same error multiple times is consistent."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    error = ValueError("Consistent error")

    result1 = orchestrator._handle_error(error)
    result2 = orchestrator._handle_error(error)

    assert result1["category"] == result2["category"]
    assert result1["recoverable"] == result2["recoverable"]
    assert result1["error_type"] == result2["error_type"]
