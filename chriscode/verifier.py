from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .tools import ToolRunner
from .workspace import Workspace


@dataclass
class Check:
    name: str
    status: str
    detail: str = ""


@dataclass
class VerificationReport:
    verdict: str
    checks: list[Check] = field(default_factory=list)


class UniversalVerifier:
    """Universal shell; language-specific adapters will plug in here."""

    def __init__(self, workspace: Workspace, tools: ToolRunner):
        self.workspace = workspace
        self.tools = tools

    def detect(self) -> list[str]:
        root = self.workspace.root
        kinds = []
        if (root / "pyproject.toml").exists() or (root / "pytest.ini").exists():
            kinds.append("python")
        if (root / "package.json").exists():
            kinds.append("node")
        if (root / "Cargo.toml").exists():
            kinds.append("rust")
        if (root / "go.mod").exists():
            kinds.append("go")
        return kinds or ["unknown"]

    def verify_foundation(self) -> VerificationReport:
        checks = [
            Check("repository", "PASS" if self.workspace.root.exists() else "FAIL"),
            Check("git", "PASS" if self.workspace.git_available() else "UNVERIFIED"),
            Check("project_detection", "PASS", ", ".join(self.detect())),
        ]
        verdict = "VERIFIED" if all(c.status != "FAIL" for c in checks) else "FAILED"
        return VerificationReport(verdict, checks)
