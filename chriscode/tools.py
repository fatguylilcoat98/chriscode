from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

from .workspace import Workspace


@dataclass
class ToolResult:
    ok: bool
    exit_code: int
    stdout: str
    stderr: str


class ToolRunner:
    """Deterministic tools. Models request actions; this layer executes them."""

    def __init__(self, workspace: Workspace):
        self.workspace = workspace

    def read_file(self, relative_path: str, max_chars: int = 20000) -> ToolResult:
        path = (self.workspace.root / relative_path).resolve()
        if self.workspace.root not in path.parents and path != self.workspace.root:
            return ToolResult(False, 1, "", "Path escapes repository.")
        if not path.is_file():
            return ToolResult(False, 1, "", "File not found.")
        return ToolResult(True, 0, path.read_text(encoding="utf-8")[:max_chars], "")

    def run(self, command: list[str], timeout: int = 120) -> ToolResult:
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
            return ToolResult(False, 124, exc.stdout or "", "Command timed out.")
