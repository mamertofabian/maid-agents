"""Claude CLI Wrapper - Invokes Claude Code headless mode."""

import json
import logging
import selectors
import subprocess
import time
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple

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
    DEFAULT_MODEL = "opus"
    DEFAULT_TIMEOUT = 300
    DEFAULT_TEMPERATURE = 0.0
    MAX_PREVIEW_LENGTH = 300

    ALLOWED_TOOLS = [
        "Bash(python -m pytest:*)",
        "Bash(python tests/:*)",
        "Bash(maid init:*)Bash(maid test:*)",
        "Bash(maid validate:*)",
        "Bash(maid schema:*)",
        "Bash(maid snapshot:*)",
        "Bash(maid generate-stubs:*)",
        "Bash(maid manifests:*)",
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
        system_prompt: Optional[str] = None,
    ) -> None:
        """Initialize Claude wrapper.

        Args:
            mock_mode: If True, returns mock responses without calling Claude
            model: Claude model to use (e.g., "opus")
            timeout: Request timeout in seconds (default: 300)
            temperature: Sampling temperature 0.0-1.0 (default: 0.0 for deterministic)
            system_prompt: Additional system prompt to append (uses --append-system-prompt)
        """
        self.mock_mode = mock_mode
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.system_prompt = system_prompt
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
        prompt_preview = self._create_preview(prompt)
        self.logger.debug(f"Prompt preview: {prompt_preview}")

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
        self._log_command_preview(command)

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
        command = [
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

        # Add system prompt if provided
        if self.system_prompt:
            command.extend(["--append-system-prompt", self.system_prompt])
            self.logger.debug(
                f"Using custom system prompt ({len(self.system_prompt)} chars)"
            )

        return command

    def _log_command_preview(self, command: List[str]) -> None:
        """Log a preview of the command being executed.

        Args:
            command: The command arguments list
        """
        command_preview_parts = [
            self._create_preview(part) if len(part) > 100 else part
            for part in command[:5]
        ]
        command_preview = " ".join(command_preview_parts)
        if len(command) > 5:
            command_preview += "..."
        self.logger.debug(f"Command preview: {command_preview}")

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

            stdout_lines, stderr_lines = self._capture_process_output(process, command)

            return subprocess.CompletedProcess(
                command,
                process.returncode,
                "\n".join(stdout_lines),
                "\n".join(stderr_lines) if stderr_lines else "",
            )

    def _capture_process_output(
        self, process: subprocess.Popen, command: List[str]
    ) -> Tuple[List[str], List[str]]:
        """Capture stdout and stderr from running process with timeout.

        Args:
            process: The running subprocess
            command: Original command for timeout error

        Returns:
            Tuple of (stdout_lines, stderr_lines)

        Raises:
            subprocess.TimeoutExpired: If process exceeds timeout
        """
        stdout_lines = []
        stderr_lines = []
        start_time = time.time()
        selector = None

        try:
            selector = selectors.DefaultSelector()
            if process.stdout:
                selector.register(process.stdout, selectors.EVENT_READ)

            self._stream_output_with_timeout(
                process, selector, stdout_lines, start_time, command
            )
            self._collect_remaining_output(process, stdout_lines, stderr_lines)

            return stdout_lines, stderr_lines

        except subprocess.TimeoutExpired:
            self._cleanup_timed_out_process(process, selector)
            raise
        finally:
            self._close_selector(selector)

    def _stream_output_with_timeout(
        self,
        process: subprocess.Popen,
        selector: selectors.DefaultSelector,
        stdout_lines: List[str],
        start_time: float,
        command: List[str],
    ) -> None:
        """Stream output from process while checking timeout.

        Args:
            process: The running subprocess
            selector: Selector for non-blocking reads
            stdout_lines: List to append stdout lines to
            start_time: Time when process started
            command: Original command for timeout error

        Raises:
            subprocess.TimeoutExpired: If timeout exceeded
        """
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

    def _collect_remaining_output(
        self,
        process: subprocess.Popen,
        stdout_lines: List[str],
        stderr_lines: List[str],
    ) -> None:
        """Collect any remaining output after process completes.

        Args:
            process: The completed subprocess
            stdout_lines: List to append stdout lines to
            stderr_lines: List to append stderr lines to
        """
        while process.stdout:
            line = process.stdout.readline()
            if not line:
                break
            line = line.rstrip()
            stdout_lines.append(line)
            self._log_streaming_message(line)

        if process.stderr:
            remaining_stderr = process.stderr.read()
            if remaining_stderr:
                stderr_lines.extend(remaining_stderr.splitlines())

        process.wait()

    def _cleanup_timed_out_process(
        self, process: subprocess.Popen, selector: Optional[selectors.DefaultSelector]
    ) -> None:
        """Clean up a process that timed out.

        Args:
            process: The timed out subprocess
            selector: The selector to unregister from
        """
        if selector and process.stdout:
            try:
                selector.unregister(process.stdout)
            except KeyError:
                pass
            selector.close()
        process.kill()
        process.wait()

    def _close_selector(self, selector: Optional[selectors.DefaultSelector]) -> None:
        """Safely close a selector.

        Args:
            selector: The selector to close
        """
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

            if msg_type == "system":
                self._log_system_message(data)
            elif msg_type == "init":
                self._log_init_message()
            elif msg_type == "user":
                self._log_user_message(data)
            elif msg_type == "assistant":
                self._log_assistant_message(data)
            elif msg_type == "result":
                self._log_result_message(data)
            else:
                self._log_unknown_message(data, msg_type)

        except json.JSONDecodeError:
            pass

    def _log_system_message(self, data: Dict[str, Any]) -> None:
        """Log system initialization message.

        Args:
            data: The parsed JSON message data
        """
        subtype = data.get("subtype", "")
        if subtype == "init":
            model = data.get("model", "unknown")
            tools = data.get("tools", [])
            mcp_servers = data.get("mcp_servers", [])
            connected_mcp = [s for s in mcp_servers if s.get("status") == "connected"]
            cwd = data.get("cwd", "")

            self.logger.info(
                f"🚀 Claude session: model={model}, tools={len(tools)}, "
                f"mcp={len(connected_mcp)}, cwd={cwd}"
            )

    def _log_init_message(self) -> None:
        """Log initialization message."""
        self.logger.debug("📡 Claude session initialized")

    def _log_user_message(self, data: Dict[str, Any]) -> None:
        """Log user message with tool calls and results.

        Args:
            data: The parsed JSON message data
        """
        message = data.get("message", {})
        content = message.get("content", [])

        if not content:
            self.logger.debug("👤 Tool call received (no user message content)")
            return

        tool_calls, tool_results, text_parts = self._parse_message_content(content)

        self._log_tool_calls(tool_calls)
        self._log_tool_results(tool_results)
        self._log_text_content(text_parts, "👤 User")

        if not tool_calls and not tool_results and not text_parts:
            self.logger.debug("👤 User message received (no recognized content)")

    def _log_assistant_message(self, data: Dict[str, Any]) -> None:
        """Log assistant message with tool calls, text, and token usage.

        Args:
            data: The parsed JSON message data
        """
        message = data.get("message", {})
        content = message.get("content", [])
        usage = message.get("usage", {})

        if not content:
            return

        tool_calls, _, text_parts = self._parse_message_content(content)

        self._log_tool_calls(tool_calls)
        self._log_text_content(text_parts, "💬 Claude")
        self._log_token_usage(usage)

    def _log_result_message(self, data: Dict[str, Any]) -> None:
        """Log final result statistics.

        Args:
            data: The parsed JSON message data
        """
        stats = {
            "cost": data.get("total_cost_usd"),
            "duration": data.get("duration_ms"),
            "turns": data.get("num_turns"),
        }
        self.logger.debug(f"📊 Final stats: {stats}")

    def _log_token_usage(self, usage: Dict[str, Any]) -> None:
        """Log token usage information.

        Args:
            usage: Usage dictionary from message
        """
        if not usage:
            return

        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        cache_read = usage.get("cache_read_input_tokens", 0)
        cache_creation = usage.get("cache_creation_input_tokens", 0)

        if input_tokens == 0 and output_tokens == 0:
            return

        token_info = f"📊 Tokens: in={input_tokens}"
        if cache_read > 0:
            token_info += f" (cache: {cache_read})"
        if cache_creation > 0:
            token_info += f" (new: {cache_creation})"
        token_info += f", out={output_tokens}"

        self.logger.debug(token_info)

    def _log_unknown_message(self, data: Dict[str, Any], msg_type: str) -> None:
        """Log unknown message type with preview.

        Args:
            data: The parsed JSON message data
            msg_type: The message type string
        """
        json_str = json.dumps(data, separators=(",", ":"))
        preview = self._create_preview(json_str)
        self.logger.debug(f"🔍 Unknown message type '{msg_type}': {preview}")

    def _parse_message_content(
        self, content: List[Dict[str, Any]]
    ) -> Tuple[List[str], List[str], List[str]]:
        """Parse message content into tool calls, tool results, and text.

        Args:
            content: List of content items from message

        Returns:
            Tuple of (tool_calls, tool_results, text_parts)
        """
        tool_calls = []
        tool_results = []
        text_parts = []

        for item in content:
            item_type = item.get("type")

            if item_type == "tool_use":
                tool_call = self._format_tool_use(item)
                tool_calls.append(tool_call)
            elif item_type == "tool_result":
                tool_result = self._format_tool_result(item)
                if tool_result:
                    tool_results.append(tool_result)
            elif item_type == "text":
                text_parts.append(item.get("text", ""))

        return tool_calls, tool_results, text_parts

    def _format_tool_use(self, item: Dict[str, Any]) -> str:
        """Format a tool_use item for logging.

        Args:
            item: The tool_use content item

        Returns:
            Formatted tool call string
        """
        tool_name = item.get("name", "unknown")
        tool_input = item.get("input", {})

        if not isinstance(tool_input, dict):
            return f"{tool_name}({self._format_tool_input(tool_input)})"

        # Special handling for common tools
        if tool_name == "Bash" and "command" in tool_input:
            cmd = tool_input["command"]
            if len(cmd) <= 80:
                return f"{tool_name}({cmd})"
            return f"{tool_name}({cmd[:77]}...)"

        if tool_name == "Read" and "file_path" in tool_input:
            return f"{tool_name}({tool_input['file_path']})"

        if tool_name == "Write" and "file_path" in tool_input:
            return f"{tool_name}({tool_input['file_path']})"

        if tool_name == "Edit" and "file_path" in tool_input:
            return f"{tool_name}({tool_input['file_path']})"

        if tool_name == "MultiEdit" and "file_paths" in tool_input:
            paths = tool_input.get("file_paths", [])
            if isinstance(paths, list) and len(paths) <= 3:
                return f"{tool_name}({', '.join(paths)})"
            return f"{tool_name}({len(paths)} files)"

        if len(tool_input) == 1:
            key, value = next(iter(tool_input.items()))
            if isinstance(value, str) and len(value) < 100:
                return f"{tool_name}({value})"
            return f"{tool_name}({key}={self._format_tool_input(value)})"

        formatted_input = ", ".join(
            f"{k}={self._format_tool_input(v)}" for k, v in list(tool_input.items())[:2]
        )
        if len(tool_input) > 2:
            formatted_input += f", ... ({len(tool_input) - 2} more)"
        return f"{tool_name}({formatted_input})"

    def _format_tool_result(self, item: Dict[str, Any]) -> Optional[str]:
        """Format a tool_result item for logging.

        Args:
            item: The tool_result content item

        Returns:
            Formatted tool result string, or None if no content
        """
        result_content = item.get("content", "")
        if not result_content:
            return None

        is_error = item.get("is_error", False)
        result_str = str(result_content)

        # Extract first meaningful line (skip empty lines)
        lines = result_str.split("\n")
        first_line = ""
        for line in lines[:3]:
            stripped = line.strip()
            if stripped:
                first_line = stripped
                break

        if not first_line:
            first_line = result_str[:50].strip() if result_str else ""

        if len(first_line) > 80:
            first_line = first_line[:77] + "..."

        status = "❌" if is_error else "✅"
        return f"{status} {first_line}"

    def _log_tool_calls(self, tool_calls: List[str]) -> None:
        """Log tool calls.

        Args:
            tool_calls: List of formatted tool call strings
        """
        for tool_call in tool_calls:
            self.logger.info(f"🔧 {tool_call}")

    def _log_tool_results(self, tool_results: List[str]) -> None:
        """Log tool results.

        Args:
            tool_results: List of formatted tool result strings
        """
        for tool_result in tool_results:
            self.logger.info(tool_result)

    def _log_text_content(self, text_parts: List[str], prefix: str) -> None:
        """Log text content with preview.

        Args:
            text_parts: List of text strings
            prefix: Prefix for log message (e.g., "👤 User" or "💬 Claude")
        """
        if not text_parts:
            return

        text_content = " ".join(text_parts)
        preview = self._create_preview(text_content)

        if prefix.startswith("💬"):
            self.logger.info(f"{prefix}: {preview}")
        else:
            self.logger.debug(f"{prefix}: {preview}")

    def _format_tool_input(self, value: Any) -> str:
        """Format tool input value for display.

        Args:
            value: The tool input value to format

        Returns:
            Formatted string representation
        """
        if isinstance(value, str):
            return value if len(value) <= 80 else value[:77] + "..."

        if isinstance(value, (dict, list)):
            json_str = json.dumps(value, separators=(",", ":"))
            return json_str if len(json_str) <= 80 else json_str[:77] + "..."

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
