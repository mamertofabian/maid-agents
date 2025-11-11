"""Claude CLI Wrapper - Invokes Claude Code headless mode."""

import json
import logging
import selectors
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
        "Bash(python -m pytest:*)",
        "Bash(maid test:*)",
        "Bash(maid validate:*)",
        "Bash(black:*)",
        "Bash(make test)",
        "Bash(make lint)",
        "Bash(make lint-fix)",
        "Bash(make format)",
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
            "--model",
            self.model,
            "--output-format",
            "stream-json",
            "--verbose",
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
            Subprocess result with stdout containing streaming JSON (jsonl format)

        Raises:
            subprocess.TimeoutExpired: If command exceeds timeout
            FileNotFoundError: If claude command not found
        """
        with LogContext("Waiting for Claude response...", style="dim"):
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            stdout_lines = []
            stderr_lines = []
            start_time = time.time()

            selector = None
            try:
                selector = selectors.DefaultSelector()
                if process.stdout:
                    selector.register(process.stdout, selectors.EVENT_READ)

                while process.poll() is None:
                    elapsed = time.time() - start_time
                    if elapsed > self.timeout:
                        raise subprocess.TimeoutExpired(command, self.timeout)

                    events = selector.select(timeout=0.1)
                    for key, _ in events:
                        if key.fileobj == process.stdout:
                            line = process.stdout.readline()
                            if line:
                                line = line.rstrip()
                                stdout_lines.append(line)
                                self._log_streaming_message(line)

                while True:
                    if process.stdout:
                        line = process.stdout.readline()
                        if line:
                            line = line.rstrip()
                            stdout_lines.append(line)
                            self._log_streaming_message(line)
                        else:
                            break
                    else:
                        break

                if process.stderr:
                    remaining_stderr = process.stderr.read()
                    if remaining_stderr:
                        stderr_lines = remaining_stderr.splitlines()

                process.wait()

                return subprocess.CompletedProcess(
                    command,
                    process.returncode,
                    "\n".join(stdout_lines),
                    "\n".join(stderr_lines) if stderr_lines else "",
                )
            except subprocess.TimeoutExpired:
                if selector and process.stdout:
                    try:
                        selector.unregister(process.stdout)
                    except KeyError:
                        pass
                    selector.close()
                process.kill()
                process.wait()
                raise
            finally:
                if selector:
                    try:
                        selector.close()
                    except Exception:
                        pass

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
        """Parse Claude's streaming JSON output (jsonl format).

        Args:
            output: Raw output from Claude (jsonl format - one JSON object per line)
            elapsed_time: Time taken for the request

        Returns:
            Parsed ClaudeResponse
        """
        try:
            return self._parse_streaming_json_response(output, elapsed_time)
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.warning(
                f"Failed to parse streaming JSON response, using plain text: {e}"
            )
            return self._parse_plain_text_response(output, elapsed_time)

    def _parse_streaming_json_response(
        self, output: str, elapsed_time: float
    ) -> ClaudeResponse:
        """Parse streaming JSON (jsonl) formatted response from Claude.

        Args:
            output: JSONL string from Claude (one JSON object per line)
            elapsed_time: Time taken for the request

        Returns:
            ClaudeResponse with parsed data

        Raises:
            json.JSONDecodeError: If JSON parsing fails
            ValueError: If no result message found
        """
        lines = output.strip().split("\n")
        result_data = None
        session_id = None

        for line in lines:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                msg_type = data.get("type", "")

                if msg_type == "result":
                    result_data = data
                    session_id = data.get("session_id")
                elif msg_type == "init":
                    session_id = data.get("session_id", session_id)
            except json.JSONDecodeError:
                continue

        if not result_data:
            raise ValueError("No result message found in streaming output")

        response_text = result_data.get("result", "")
        self._log_successful_response(response_text, elapsed_time)

        return ClaudeResponse(
            success=True,
            result=response_text,
            error="",
            session_id=session_id,
        )

    def _log_streaming_message(self, line: str) -> None:
        """Log a streaming message from Claude.

        Args:
            line: A single JSON line from the stream
        """
        if not line.strip():
            return

        try:
            data = json.loads(line)
            msg_type = data.get("type", "")

            self.logger.debug(f"🔍 Message type: {msg_type}")
            if msg_type not in ["init", "user", "assistant", "result", "system"]:
                self.logger.debug(
                    f"🔍 Unknown message type structure: {json.dumps(data, indent=2)}"
                )

            if msg_type == "init":
                self.logger.debug("📡 Claude session initialized")
            elif msg_type == "system":
                subtype = data.get("subtype", "")
                if subtype == "init":
                    model = data.get("model", "unknown")
                    cwd = data.get("cwd", "")
                    tools_count = len(data.get("tools", []))
                    mcp_servers = data.get("mcp_servers", [])
                    mcp_count = len([s for s in mcp_servers if s.get("status") == "connected"])
                    self.logger.debug(
                        f"🔧 System init: model={model}, cwd={cwd}, "
                        f"tools={tools_count}, mcp_servers={mcp_count}"
                    )
            elif msg_type == "user":
                message = data.get("message", {})
                content = message.get("content", [])

                if content:
                    tool_calls = []
                    tool_results = []
                    text_parts = []

                    for item in content:
                        if item.get("type") == "tool_use":
                            tool_name = item.get("name", "unknown")
                            tool_input = item.get("input", {})

                            if isinstance(tool_input, dict):
                                if len(tool_input) == 1:
                                    key, value = next(iter(tool_input.items()))
                                    if isinstance(value, str) and len(value) < 100:
                                        tool_calls.append(f"{tool_name}({value})")
                                    else:
                                        tool_calls.append(
                                            f"{tool_name}({key}={self._format_tool_input(value)})"
                                        )
                                else:
                                    formatted_input = ", ".join(
                                        f"{k}={self._format_tool_input(v)}"
                                        for k, v in tool_input.items()
                                    )
                                    tool_calls.append(f"{tool_name}({formatted_input})")
                            else:
                                tool_calls.append(
                                    f"{tool_name}({self._format_tool_input(tool_input)})"
                                )
                        elif item.get("type") == "tool_result":
                            result_content = item.get("content", "")
                            is_error = item.get("is_error", False)

                            if result_content:
                                result_str = str(result_content)
                                first_line = result_str.split("\n")[0].strip()
                                if len(first_line) > 100:
                                    first_line = first_line[:97] + "..."

                                status = "❌" if is_error else "✅"
                                tool_results.append(
                                    f"{status} Tool result: {first_line}"
                                )
                        elif item.get("type") == "text":
                            text_parts.append(item.get("text", ""))

                    if tool_calls:
                        for tool_call in tool_calls:
                            self.logger.debug(f"🔧 {tool_call}")
                    if tool_results:
                        for tool_result in tool_results:
                            self.logger.debug(tool_result)
                    if text_parts:
                        text_content = " ".join(text_parts)
                        preview = self._create_preview(text_content)
                        self.logger.debug(f"👤 User: {preview}")
                    if not tool_calls and not tool_results and not text_parts:
                        self.logger.debug(
                            "👤 User message received (no recognized content)"
                        )
                else:
                    self.logger.debug("👤 Tool call received (no user message content)")
            elif msg_type == "assistant":
                message = data.get("message", {})
                content = message.get("content", [])
                usage = message.get("usage", {})

                if usage:
                    input_tokens = usage.get("input_tokens", 0)
                    output_tokens = usage.get("output_tokens", 0)
                    cache_read = usage.get("cache_read_input_tokens", 0)
                    cache_creation = usage.get("cache_creation_input_tokens", 0)
                    
                    token_info = f"📊 Tokens: in={input_tokens}"
                    if cache_read > 0:
                        token_info += f" (cache: {cache_read})"
                    if cache_creation > 0:
                        token_info += f" (new cache: {cache_creation})"
                    token_info += f", out={output_tokens}"
                    self.logger.debug(token_info)

                if content:
                    tool_calls = []
                    text_content = ""

                    for item in content:
                        if item.get("type") == "tool_use":
                            tool_name = item.get("name", "unknown")
                            tool_input = item.get("input", {})

                            if isinstance(tool_input, dict):
                                if len(tool_input) == 1:
                                    key, value = next(iter(tool_input.items()))
                                    if key == "file_path" and isinstance(value, str):
                                        tool_calls.append(f"{tool_name}({value})")
                                    elif key == "command" and isinstance(value, str):
                                        tool_calls.append(f"{tool_name}({value})")
                                    elif isinstance(value, str) and len(value) < 100:
                                        tool_calls.append(f"{tool_name}({value})")
                                    else:
                                        tool_calls.append(
                                            f"{tool_name}({key}={self._format_tool_input(value)})"
                                        )
                                else:
                                    if "command" in tool_input:
                                        command = tool_input.get("command", "")
                                        tool_calls.append(f"{tool_name}({command})")
                                    elif "file_path" in tool_input:
                                        file_path = tool_input.get("file_path", "")
                                        tool_calls.append(f"{tool_name}({file_path})")
                                    else:
                                        formatted_input = ", ".join(
                                            f"{k}={self._format_tool_input(v)}"
                                            for k, v in tool_input.items()
                                        )
                                        tool_calls.append(f"{tool_name}({formatted_input})")
                            else:
                                tool_calls.append(
                                    f"{tool_name}({self._format_tool_input(tool_input)})"
                                )
                        elif item.get("type") == "text":
                            text_content += item.get("text", "")

                    if tool_calls:
                        for tool_call in tool_calls:
                            self.logger.debug(f"🔧 {tool_call}")
                    if text_content:
                        preview = self._create_preview(text_content)
                        self.logger.info(f"💬 Claude: {preview}")
            elif msg_type == "result":
                stats = {
                    "cost": data.get("total_cost_usd"),
                    "duration": data.get("duration_ms"),
                    "turns": data.get("num_turns"),
                }
                self.logger.debug(f"📊 Final stats: {stats}")
        except json.JSONDecodeError:
            pass

    def _format_tool_input(self, value) -> str:
        """Format tool input value for display.

        Args:
            value: The tool input value to format

        Returns:
            Formatted string representation
        """
        if isinstance(value, str):
            if len(value) <= 80:
                return value
            return value[:77] + "..."
        elif isinstance(value, (dict, list)):
            json_str = json.dumps(value, separators=(",", ":"))
            if len(json_str) <= 80:
                return json_str
            return json_str[:77] + "..."
        else:
            return str(value)

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
