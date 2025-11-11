"""Claude CLI Wrapper - Invokes Claude Code headless mode."""

import json
import logging
import subprocess
import time
from dataclasses import dataclass
from typing import Optional

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

    def __init__(
        self,
        mock_mode: bool = True,
        model: str = "claude-sonnet-4-5-20250929",
        timeout: int = 300,
        temperature: float = 0.0,
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

        # Log prompt (full at DEBUG level only)
        self.logger.info(
            f"🤖 Calling Claude ({self.model}, timeout={self.timeout}s, temp={self.temperature})"
        )
        self.logger.debug(f"Full prompt:\n{prompt}")

        if self.mock_mode:
            self.logger.warning("⚠️  MOCK MODE: Returning simulated response")
            # Return mock response for testing
            response = ClaudeResponse(
                success=True,
                result=f"Mock response for prompt: {prompt[:50]}...",
                error="",
                session_id="mock-session-123",
            )
            elapsed = time.time() - start_time
            self.logger.info(f"✅ Mock response returned ({elapsed:.2f}s)")
            return response

        # Real Claude invocation
        # Note: -p/--print flag is required for non-interactive output
        cmd = ["claude", "--print", prompt, "--output-format", "json"]
        self.logger.debug(f"Running command: {' '.join(cmd[:3])}...")

        try:
            with LogContext("Waiting for Claude response...", style="dim"):
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=self.timeout
                )

            elapsed = time.time() - start_time

            if result.returncode == 0:
                # Parse JSON response
                try:
                    data = json.loads(result.stdout)
                    response_text = data.get("result", "")
                    response_preview = (
                        response_text[:300] + "..."
                        if len(response_text) > 300
                        else response_text
                    )

                    self.logger.info(
                        f"✅ Claude response received ({elapsed:.2f}s, {len(response_text)} chars)"
                    )
                    self.logger.info(f"📄 Response preview: {response_preview}")
                    self.logger.debug(f"Full response:\n{response_text}")

                    return ClaudeResponse(
                        success=True,
                        result=response_text,
                        error="",
                        session_id=data.get("session_id"),
                    )
                except json.JSONDecodeError as e:
                    self.logger.warning(
                        f"Failed to parse JSON response, using plain text: {e}"
                    )
                    response_preview = (
                        result.stdout[:300] + "..."
                        if len(result.stdout) > 300
                        else result.stdout
                    )

                    self.logger.info(f"✅ Claude response received ({elapsed:.2f}s)")
                    self.logger.info(f"📄 Response preview: {response_preview}")
                    self.logger.debug(f"Full response:\n{result.stdout}")

                    # Fallback to plain text
                    return ClaudeResponse(
                        success=True, result=result.stdout, error="", session_id=None
                    )
            else:
                self.logger.error(f"❌ Claude CLI failed ({elapsed:.2f}s)")
                self.logger.error(f"Error: {result.stderr}")
                return ClaudeResponse(
                    success=False, result="", error=result.stderr, session_id=None
                )

        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            error_msg = "Claude CLI timed out after 300s"
            self.logger.error(f"❌ {error_msg}")
            return ClaudeResponse(
                success=False, result="", error=error_msg, session_id=None
            )
        except FileNotFoundError:
            elapsed = time.time() - start_time
            error_msg = "Claude CLI not found. Please install Claude Code."
            self.logger.error(f"❌ {error_msg}")
            return ClaudeResponse(
                success=False,
                result="",
                error=error_msg,
                session_id=None,
            )
        except Exception as e:
            elapsed = time.time() - start_time
            self.logger.error(f"❌ Unexpected error ({elapsed:.2f}s): {e}")
            return ClaudeResponse(
                success=False, result="", error=str(e), session_id=None
            )
