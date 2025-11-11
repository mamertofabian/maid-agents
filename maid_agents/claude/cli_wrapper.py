"""Claude CLI Wrapper - Invokes Claude Code headless mode."""

import json
import logging
import subprocess
import time
from dataclasses import dataclass
from typing import Optional, List

from maid_agents.utils.logging import LogContext

logger = logging.getLogger(__name__)


@dataclass
class ClaudeResponse:
    """Response from Claude Code CLI."""

    success: bool
    result: str
    error: str
    session_id: Optional[str] = None


class ClaudeWrapper:
    """Wraps Claude Code headless CLI invocations."""

    # Constants
    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
    DEFAULT_TIMEOUT = 300
    DEFAULT_TEMPERATURE = 0.0
    MAX_PREVIEW_LENGTH = 300

    ALLOWED_TOOLS = [
        "Bash(pytest)",
        "Bash(maid test:*)",
        "Bash(maid validate:*)",
        "Bash(black)",
        "Bash(make)",
    ]

    def __init__(
        self,
        mock_mode: bool = True,
        model: str = DEFAULT_MODEL,
        timeout: int = DEFAULT_TIMEOUT,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> None:
        """Initialize Claude wrapper.

        Args:
            mock_mode: If True, returns mock responses without calling Claude
            model: Claude model to use (e.g., "claude-sonnet-4-5-20250929")
            timeout: Request timeout in seconds (default: 300)
            temperature: Sampling temperature 0.0-1.0 (default: 0.0 for deterministic)
        """
        self.mock_mode = mock_mode
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.logger = logger

    def generate(self, prompt: str) -> ClaudeResponse:
        """Generate response using Claude Code headless mode.

        Args:
            prompt: The prompt to send to Claude

        Returns:
            ClaudeResponse with result or error
        """
        start_time = time.time()
        self._log_request_start(prompt)

        if self.mock_mode:
            return self._generate_mock_response(prompt, start_time)

        return self._generate_real_response(prompt, start_time)

    def _log_request_start(self, prompt: str) -> None:
        """Log the start of a Claude request.

        Args:
            prompt: The prompt being sent
        """
        self.logger.info(
            f"🤖 Calling Claude ({self.model}, timeout={self.timeout}s, temp={self.temperature})"
        )
        self.logger.debug(f"Full prompt:\n{prompt}")

    def _generate_mock_response(self, prompt: str, start_time: float) -> ClaudeResponse:
        """Generate a mock response for testing.

        Args:
            prompt: The original prompt
            start_time: Request start time for elapsed calculation

        Returns:
            Mock ClaudeResponse
        """
        self.logger.warning("⚠️  MOCK MODE: Returning simulated response")

        mock_result = f"Mock response for prompt: {prompt[:50]}..."
        response = ClaudeResponse(
            success=True,
            result=mock_result,
            error="",
            session_id="mock-session-123",
        )

        elapsed_time = self._calculate_elapsed_time(start_time)
        self.logger.info(f"✅ Mock response returned ({elapsed_time:.2f}s)")

        return response

    def _generate_real_response(self, prompt: str, start_time: float) -> ClaudeResponse:
        """Generate a real response using Claude CLI.

        Args:
            prompt: The prompt to send to Claude
            start_time: Request start time for elapsed calculation

        Returns:
            Real ClaudeResponse from Claude
        """
        command = self._build_claude_command(prompt)
        self.logger.debug(f"Running command: {' '.join(command[:3])}...")

        try:
            result = self._execute_claude_command(command)
            return self._process_command_result(result, start_time)

        except subprocess.TimeoutExpired:
            return self._create_timeout_response(start_time)

        except FileNotFoundError:
            return self._create_not_found_response()

        except Exception as e:
            return self._create_unexpected_error_response(e, start_time)

    def _build_claude_command(self, prompt: str) -> List[str]:
        """Build the Claude CLI command with all necessary flags.

        Args:
            prompt: The prompt to include

        Returns:
            List of command arguments
        """
        return [
            "claude",
            "--print",
            prompt,
            "--output-format",
            "json",
            "--permission-mode",
            "acceptEdits",
            "--allowedTools",
            ",".join(self.ALLOWED_TOOLS),
        ]

    def _execute_claude_command(
        self, command: List[str]
    ) -> subprocess.CompletedProcess:
        """Execute the Claude command with proper context and timeout.

        Args:
            command: Command arguments list

        Returns:
            Subprocess result

        Raises:
            subprocess.TimeoutExpired: If command exceeds timeout
            FileNotFoundError: If claude command not found
        """
        with LogContext("Waiting for Claude response...", style="dim"):
            return subprocess.run(
                command, capture_output=True, text=True, timeout=self.timeout
            )

    def _process_command_result(
        self, result: subprocess.CompletedProcess, start_time: float
    ) -> ClaudeResponse:
        """Process the result from Claude CLI execution.

        Args:
            result: The subprocess result
            start_time: Request start time

        Returns:
            Processed ClaudeResponse
        """
        elapsed_time = self._calculate_elapsed_time(start_time)

        if result.returncode != 0:
            return self._create_error_response(result.stderr, elapsed_time)

        return self._parse_claude_output(result.stdout, elapsed_time)

    def _parse_claude_output(self, output: str, elapsed_time: float) -> ClaudeResponse:
        """Parse Claude's output, handling both JSON and plain text.

        Args:
            output: Raw output from Claude
            elapsed_time: Time taken for the request

        Returns:
            Parsed ClaudeResponse
        """
        try:
            return self._parse_json_response(output, elapsed_time)
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse JSON response, using plain text: {e}")
            return self._parse_plain_text_response(output, elapsed_time)

    def _parse_json_response(self, output: str, elapsed_time: float) -> ClaudeResponse:
        """Parse JSON formatted response from Claude.

        Args:
            output: JSON string from Claude
            elapsed_time: Time taken for the request

        Returns:
            ClaudeResponse with parsed data

        Raises:
            json.JSONDecodeError: If JSON parsing fails
        """
        data = json.loads(output)
        response_text = data.get("result", "")

        self._log_successful_response(response_text, elapsed_time)

        return ClaudeResponse(
            success=True,
            result=response_text,
            error="",
            session_id=data.get("session_id"),
        )

    def _parse_plain_text_response(
        self, output: str, elapsed_time: float
    ) -> ClaudeResponse:
        """Handle plain text response as fallback.

        Args:
            output: Plain text output from Claude
            elapsed_time: Time taken for the request

        Returns:
            ClaudeResponse with plain text result
        """
        self._log_successful_response(output, elapsed_time)

        return ClaudeResponse(success=True, result=output, error="", session_id=None)

    def _log_successful_response(self, response_text: str, elapsed_time: float) -> None:
        """Log details about a successful response.

        Args:
            response_text: The response content
            elapsed_time: Time taken for the request
        """
        response_preview = self._create_preview(response_text)

        self.logger.info(
            f"✅ Claude response received ({elapsed_time:.2f}s, {len(response_text)} chars)"
        )
        self.logger.info(f"📄 Response preview: {response_preview}")
        self.logger.debug(f"Full response:\n{response_text}")

    def _create_preview(self, text: str) -> str:
        """Create a truncated preview of text for logging.

        Args:
            text: Text to preview

        Returns:
            Truncated text with ellipsis if needed
        """
        if len(text) <= self.MAX_PREVIEW_LENGTH:
            return text
        return text[: self.MAX_PREVIEW_LENGTH] + "..."

    def _create_error_response(
        self, error_msg: str, elapsed_time: float
    ) -> ClaudeResponse:
        """Create an error response with logging.

        Args:
            error_msg: The error message
            elapsed_time: Time before error occurred

        Returns:
            Error ClaudeResponse
        """
        self.logger.error(f"❌ Claude CLI failed ({elapsed_time:.2f}s)")
        self.logger.error(f"Error: {error_msg}")

        return ClaudeResponse(
            success=False, result="", error=error_msg, session_id=None
        )

    def _create_timeout_response(self, start_time: float) -> ClaudeResponse:
        """Create a timeout error response.

        Args:
            start_time: Request start time

        Returns:
            Timeout error ClaudeResponse
        """
        elapsed_time = self._calculate_elapsed_time(start_time)
        error_msg = f"Claude CLI timed out after {elapsed_time:.2f}s"

        self.logger.error(f"❌ {error_msg}")

        return ClaudeResponse(
            success=False, result="", error=error_msg, session_id=None
        )

    def _create_not_found_response(self) -> ClaudeResponse:
        """Create a 'command not found' error response.

        Args:
            start_time: Request start time

        Returns:
            Not found error ClaudeResponse
        """
        error_msg = "Claude CLI not found. Please install Claude Code."

        self.logger.error(f"❌ {error_msg}")

        return ClaudeResponse(
            success=False, result="", error=error_msg, session_id=None
        )

    def _create_unexpected_error_response(
        self, exception: Exception, start_time: float
    ) -> ClaudeResponse:
        """Create an unexpected error response.

        Args:
            exception: The caught exception
            start_time: Request start time

        Returns:
            Unexpected error ClaudeResponse
        """
        elapsed_time = self._calculate_elapsed_time(start_time)

        self.logger.error(f"❌ Unexpected error ({elapsed_time:.2f}s): {exception}")

        return ClaudeResponse(
            success=False, result="", error=str(exception), session_id=None
        )

    def _calculate_elapsed_time(self, start_time: float) -> float:
        """Calculate elapsed time since start.

        Args:
            start_time: The start timestamp

        Returns:
            Elapsed time in seconds
        """
        return time.time() - start_time
