from __future__ import annotations

from dataclasses import dataclass, field

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


def verdict_from_checks(checks: list[Check]) -> str:
    """
    Fail closed.

    Any FAIL        -> FAILED
    Else any
    UNVERIFIED      -> UNVERIFIED
    Else            -> VERIFIED
    """
    statuses = {check.status for check in checks}

    if "FAIL" in statuses:
        return "FAILED"

    if "UNVERIFIED" in statuses:
        return "UNVERIFIED"

    return "VERIFIED"


class UniversalVerifier:
    """Evidence, not model confidence, decides the final verdict."""

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
        detected = self.detect()

        checks = [
            Check(
                "repository",
                "PASS" if self.workspace.root.exists() else "FAIL",
            ),
            Check(
                "git",
                "PASS" if self.workspace.git_available() else "UNVERIFIED",
            ),
            Check(
                "project_detection",
                "PASS" if detected != ["unknown"] else "UNVERIFIED",
                ", ".join(detected),
            ),
        ]

        return VerificationReport(
            verdict=verdict_from_checks(checks),
            checks=checks,
        )

    def verify_task(self) -> VerificationReport:
        foundation = self.verify_foundation()
        checks = list(foundation.checks)
        detected = self.detect()

        if "python" in detected:
            test_result = self.tools.run_tests()

            checks.append(
                Check(
                    "python_tests",
                    "PASS" if test_result.ok else "FAIL",
                    (
                        test_result.stdout
                        if test_result.ok
                        else test_result.stderr or test_result.stdout
                    )[-4000:],
                )
            )
        else:
            checks.append(
                Check(
                    "task_tests",
                    "UNVERIFIED",
                    "No supported deterministic test runner detected.",
                )
            )

        return VerificationReport(
            verdict=verdict_from_checks(checks),
            checks=checks,
        )
