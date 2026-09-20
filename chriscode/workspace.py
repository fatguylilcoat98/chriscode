from __future__ import annotations

from pathlib import Path
import subprocess


class Workspace:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def git_available(self) -> bool:
        result = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True
        )
        return result.returncode == 0

    def status(self) -> str:
        if not self.git_available():
            return "NOT_A_GIT_REPOSITORY"
        result = subprocess.run(
            ["git", "-C", str(self.root), "status", "--short"],
            capture_output=True, text=True
        )
        return result.stdout.strip() or "CLEAN"
