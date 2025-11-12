"""Test Suite for Task 022: Passing Test Generation Feature.

This test suite validates that the TestGenerator agent now ensures generated
tests pass before returning success. It tests the validation loop and fix
iteration functionality.
"""

from unittest.mock import Mock, MagicMock, patch
from maid_agents.agents.test_generator import TestGenerator
from maid_agents.claude.cli_wrapper import ClaudeWrapper, ClaudeResponse
from maid_agents.core.validation_runner import ValidationResult


def test_test_generator_has_validation_runner():
    """Test that TestGenerator has a validation_runner attribute."""
    claude = ClaudeWrapper(mock_mode=True)
    generator = TestGenerator(claude=claude)

    assert hasattr(generator, "validation_runner")
    assert generator.validation_runner is not None


def test_generate_test_from_implementation_accepts_max_iterations():
    """Test that generate_test_from_implementation accepts max_iterations parameter."""
    claude = ClaudeWrapper(mock_mode=True)
    generator = TestGenerator(claude=claude)

    with patch("builtins.open", create=True) as mock_open:
        with patch("pathlib.Path.exists", return_value=False):
            # Mock file operations
            mock_open.return_value.__enter__.return_value.read.return_value = ""

            # This should not raise TypeError about unexpected argument
            result = generator.generate_test_from_implementation(
                manifest_path="test.manifest.json",
                implementation_path="test.py",
                max_iterations=3,
            )

            # We expect an error because files don't exist, but the parameter should be accepted
            assert "error" in result or "success" in result


def test_run_test_validation_loop_method_exists():
    """Test that _run_test_validation_loop method exists."""
    claude = ClaudeWrapper(mock_mode=True)
    generator = TestGenerator(claude=claude)

    assert hasattr(generator, "_run_test_validation_loop")
    assert callable(getattr(generator, "_run_test_validation_loop"))


def test_run_test_validation_loop_returns_expected_structure():
    """Test that _run_test_validation_loop returns dict with expected keys."""
    claude = ClaudeWrapper(mock_mode=True)
    generator = TestGenerator(claude=claude)

    # Mock the validation runner to return success immediately
    generator.validation_runner.run_behavioral_tests = Mock(
        return_value=ValidationResult(
            success=True, stdout="All tests passed", stderr="", errors=[]
        )
    )

    result = generator._run_test_validation_loop(
        manifest_path="test.manifest.json",
        test_path="tests/test_example.py",
        implementation_path="example.py",
        manifest_data={"expectedArtifacts": {}},
        max_iterations=5,
    )

    assert "success" in result
    assert "iterations" in result
    assert "error" in result
    assert result["success"] is True
    assert result["iterations"] == 1


def test_run_test_validation_loop_iterates_on_failure():
    """Test that validation loop iterates when tests fail."""
    claude = ClaudeWrapper(mock_mode=True)
    generator = TestGenerator(claude=claude)

    # Mock validation to fail twice, then succeed
    call_count = [0]

    def mock_run_tests(manifest_path):
        call_count[0] += 1
        if call_count[0] < 3:
            return ValidationResult(
                success=False,
                stdout="FAILED tests/test_example.py::test_something",
                stderr="AssertionError: expected True",
                errors=["FAILED tests/test_example.py::test_something"],
            )
        return ValidationResult(
            success=True, stdout="All tests passed", stderr="", errors=[]
        )

    generator.validation_runner.run_behavioral_tests = Mock(side_effect=mock_run_tests)

    # Mock the fix method to return success
    generator._fix_failing_tests_with_claude = Mock(
        return_value={"success": True, "error": None}
    )

    result = generator._run_test_validation_loop(
        manifest_path="test.manifest.json",
        test_path="tests/test_example.py",
        implementation_path="example.py",
        manifest_data={"expectedArtifacts": {}},
        max_iterations=5,
    )

    assert result["success"] is True
    assert result["iterations"] == 3
    assert call_count[0] == 3


def test_run_test_validation_loop_respects_max_iterations():
    """Test that validation loop stops at max iterations."""
    claude = ClaudeWrapper(mock_mode=True)
    generator = TestGenerator(claude=claude)

    # Mock validation to always fail
    generator.validation_runner.run_behavioral_tests = Mock(
        return_value=ValidationResult(
            success=False, stdout="FAILED", stderr="Error", errors=["FAILED"]
        )
    )

    # Mock fix to return success
    generator._fix_failing_tests_with_claude = Mock(
        return_value={"success": True, "error": None}
    )

    result = generator._run_test_validation_loop(
        manifest_path="test.manifest.json",
        test_path="tests/test_example.py",
        implementation_path="example.py",
        manifest_data={"expectedArtifacts": {}},
        max_iterations=3,
    )

    assert result["success"] is False
    assert result["iterations"] == 3
    assert "after 3 iterations" in result["error"]


def test_fix_failing_tests_with_claude_method_exists():
    """Test that _fix_failing_tests_with_claude method exists."""
    claude = ClaudeWrapper(mock_mode=True)
    generator = TestGenerator(claude=claude)

    assert hasattr(generator, "_fix_failing_tests_with_claude")
    assert callable(getattr(generator, "_fix_failing_tests_with_claude"))


def test_fix_failing_tests_with_claude_returns_expected_structure():
    """Test that _fix_failing_tests_with_claude returns dict with expected keys."""
    claude = ClaudeWrapper(mock_mode=True)
    generator = TestGenerator(claude=claude)

    # Create a temporary test file
    test_content = "def test_example():\n    assert True"

    with patch("builtins.open", create=True) as mock_open:
        # Mock file reading and writing
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.side_effect = [
            test_content,  # First read (current test)
            test_content + "\n# fixed",  # Second read (updated test)
        ]
        mock_open.return_value = mock_file

        result = generator._fix_failing_tests_with_claude(
            test_path="tests/test_example.py",
            test_errors="FAILED: AssertionError",
            manifest_data={"expectedArtifacts": {}},
            implementation_path="example.py",
        )

        assert "success" in result
        assert "error" in result


def test_fix_failing_tests_calls_claude_with_errors():
    """Test that fix method calls Claude with test errors."""
    mock_claude = Mock(spec=ClaudeWrapper)
    mock_claude.mock_mode = True
    mock_claude.model = "test-model"
    mock_claude.timeout = 300
    mock_claude.temperature = 0.0

    generator = TestGenerator(claude=mock_claude)

    test_content = "def test_example():\n    assert True"
    test_errors = "FAILED: AssertionError: expected True"

    with patch("builtins.open", create=True) as mock_open:
        # Mock file operations
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.side_effect = [
            test_content,  # First read (current test)
            test_content + "\n# fixed",  # Second read (updated test)
        ]
        mock_open.return_value = mock_file

        # Mock ClaudeWrapper instantiation and response
        with patch("maid_agents.agents.test_generator.ClaudeWrapper") as MockClaude:
            mock_instance = Mock()
            mock_instance.generate.return_value = ClaudeResponse(
                success=True, result="Fixed the test", error=""
            )
            MockClaude.return_value = mock_instance

            result = generator._fix_failing_tests_with_claude(
                test_path="tests/test_example.py",
                test_errors=test_errors,
                manifest_data={"expectedArtifacts": {}},
                implementation_path="example.py",
            )

            # Verify Claude was called
            assert mock_instance.generate.called
            call_args = mock_instance.generate.call_args[0][0]
            assert "failing" in call_args.lower()
            assert test_errors in call_args

            # Verify result structure
            assert "success" in result
            assert "error" in result


def test_error_result_includes_iterations():
    """Test that error results include iterations field."""
    claude = ClaudeWrapper(mock_mode=True)
    generator = TestGenerator(claude=claude)

    # Call _create_error_result
    result = generator._create_error_result("Test error")

    assert "iterations" in result
    assert result["iterations"] == 0
    assert result["success"] is False
    assert result["error"] == "Test error"
