from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys

from .workspace import Workspace


@dataclass
class ToolResult:
    ok: bool
    exit_code: int
    stdout: str
    stderr: str


class ToolRunner:
    """Deterministic tools. Models request capabilities, not arbitrary shell access."""

    def __init__(self, workspace: Workspace):
        self.workspace = workspace

    def _safe_path(self, relative_path: str) -> Path | None:
        path = (self.workspace.root / relative_path).resolve()

        if path != self.workspace.root and self.workspace.root not in path.parents:
            return None

        return path

    def read_file(self, relative_path: str, max_chars: int = 20000) -> ToolResult:
        path = self._safe_path(relative_path)

        if path is None:
            return ToolResult(False, 1, "", "Path escapes repository.")

        if not path.is_file():
            return ToolResult(False, 1, "", "File not found.")

        return ToolResult(
            True,
            0,
            path.read_text(encoding="utf-8")[:max_chars],
            "",
        )

    def write_file(self, relative_path: str, content: str) -> ToolResult:
        path = self._safe_path(relative_path)

        if path is None:
            return ToolResult(False, 1, "", "Path escapes repository.")

        if path == self.workspace.root:
            return ToolResult(False, 1, "", "Cannot write repository root.")

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

            return ToolResult(
                True,
                0,
                f"Wrote {relative_path}",
                "",
            )
        except OSError as exc:
            return ToolResult(False, 1, "", str(exc))

    def _run_process(
        self,
        command: list[str],
        timeout: int = 120,
    ) -> ToolResult:
        try:
            result = subprocess.run(
                command,
                cwd=self.workspace.root,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            return ToolResult(
                result.returncode == 0,
                result.returncode,
                result.stdout[-20000:],
                result.stderr[-20000:],
            )

        except subprocess.TimeoutExpired as exc:
            return ToolResult(
                False,
                124,
                exc.stdout or "",
                "Command timed out.",
            )

    def run_tests(self, timeout: int = 120) -> ToolResult:
        return self._run_process(
            [sys.executable, "-m", "pytest", "-q"],
            timeout=timeout,
        )
