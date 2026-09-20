from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class ModelUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


@dataclass
class ModelDecision:
    action: str
    arguments: dict[str, Any]
    reason: str = ""
    usage: ModelUsage | None = None


class ModelAdapter(Protocol):
    name: str

    def decide(self, state: dict[str, Any]) -> ModelDecision:
        ...


class MockModel:
    name = "mock"

    def decide(self, state: dict[str, Any]) -> ModelDecision:
        return ModelDecision(
            action="stop",
            arguments={
                "message": "Mock model is connected; no code changes made."
            },
            reason="Foundation smoke test.",
            usage=ModelUsage(),
        )


class GroqModel:
    """
    Minimal Groq adapter.

    The model proposes exactly one action per turn.
    Chris Code remains responsible for executing tools and verification.
    """

    endpoint = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(
        self,
        model: str = "qwen/qwen3.6-27b",
        api_key: str | None = None,
        timeout: int = 60,
    ):
        self.model = model
        self.name = f"groq:{model}"
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.timeout = timeout

        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY is not set.")

    def _system_prompt(self) -> str:
        return """
You are the proposal model inside Chris Code.

You do NOT directly execute tools.
You propose exactly ONE action per response.

Allowed actions:

1. read_file
   arguments:
   {"path": "relative/path"}

2. write_file
   arguments:
   {
     "path": "relative/path",
     "content": "complete replacement file content"
   }

3. run_tests
   arguments:
   {}

4. stop
   arguments:
   {"message": "short completion message"}

Return ONLY valid JSON with exactly this structure:

{
  "action": "read_file|write_file|run_tests|stop",
  "arguments": {},
  "reason": "brief reason"
}

Rules:

- Paths must be relative to the repository.
- Never request shell commands.
- Never request network access.
- Never request paths outside the repository.
- Use read_file before modifying a file unless its complete contents
  are already present in tool evidence.
- After changing code, run tests.
- Do not claim success merely because you wrote code.
- Stop only when the available tool evidence supports stopping.
- If tests fail, inspect evidence and continue working.
- Return JSON only. No markdown fences. No commentary outside JSON.
""".strip()

    def decide(self, state: dict[str, Any]) -> ModelDecision:
        body = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": self._system_prompt(),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        state,
                        ensure_ascii=False,
                        indent=2,
                    ),
                },
            ],
        }

        request = Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "ChrisCode/0.1",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(
                    response.read().decode("utf-8")
                )

        except HTTPError as exc:
            detail = exc.read().decode(
                "utf-8",
                errors="replace",
            )
            raise RuntimeError(
                f"Groq HTTP {exc.code}: {detail}"
            ) from exc

        except URLError as exc:
            raise RuntimeError(
                f"Groq connection failed: {exc.reason}"
            ) from exc

        try:
            raw = payload["choices"][0]["message"]["content"]
            parsed = json.loads(raw)

            action = parsed["action"]
            arguments = parsed.get("arguments", {})
            reason = parsed.get("reason", "")

        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                f"Invalid Groq decision payload: {payload!r}"
            ) from exc

        allowed = {
            "read_file",
            "write_file",
            "run_tests",
            "stop",
        }

        if action not in allowed:
            raise RuntimeError(
                f"Groq proposed unsupported action: {action!r}"
            )

        if not isinstance(arguments, dict):
            raise RuntimeError(
                "Groq decision arguments must be an object."
            )

        usage_data = payload.get("usage", {})

        usage = ModelUsage(
            input_tokens=int(
                usage_data.get("prompt_tokens", 0) or 0
            ),
            output_tokens=int(
                usage_data.get("completion_tokens", 0) or 0
            ),
            cost_usd=0.0,
        )

        return ModelDecision(
            action=action,
            arguments=arguments,
            reason=str(reason),
            usage=usage,
        )
