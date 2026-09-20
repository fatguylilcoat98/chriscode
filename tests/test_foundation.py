from pathlib import Path

from chriscode.ledger import JobLedger
from chriscode.workspace import Workspace
from chriscode.tools import ToolRunner
from chriscode.verifier import (
    Check,
    UniversalVerifier,
    verdict_from_checks,
)


def test_ledger_persists(tmp_path: Path):
    ledger = JobLedger(tmp_path / "jobs")
    job = ledger.create("test task")
    assert (tmp_path / "jobs" / f"{job.id}.json").exists()


def test_verifier_detects_python_project(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='x'\n",
        encoding="utf-8",
    )
    workspace = Workspace(tmp_path)
    verifier = UniversalVerifier(workspace, ToolRunner(workspace))
    assert "python" in verifier.detect()


def test_read_file_cannot_escape_repo(tmp_path: Path):
    workspace = Workspace(tmp_path)
    tools = ToolRunner(workspace)
    result = tools.read_file("../outside.txt")
    assert not result.ok


def test_verdict_verified_only_when_all_checks_pass():
    checks = [
        Check("one", "PASS"),
        Check("two", "PASS"),
    ]
    assert verdict_from_checks(checks) == "VERIFIED"


def test_verdict_unverified_when_evidence_is_missing():
    checks = [
        Check("one", "PASS"),
        Check("two", "UNVERIFIED"),
    ]
    assert verdict_from_checks(checks) == "UNVERIFIED"


def test_verdict_failed_beats_unverified():
    checks = [
        Check("one", "PASS"),
        Check("two", "UNVERIFIED"),
        Check("three", "FAIL"),
    ]
    assert verdict_from_checks(checks) == "FAILED"


def test_unknown_project_is_not_verified(tmp_path: Path):
    workspace = Workspace(tmp_path)
    verifier = UniversalVerifier(workspace, ToolRunner(workspace))
    report = verifier.verify_foundation()

    assert report.verdict == "UNVERIFIED"
    assert any(
        check.name == "project_detection"
        and check.status == "UNVERIFIED"
        for check in report.checks
    )

def test_write_file_inside_repo(tmp_path: Path):
    workspace = Workspace(tmp_path)
    tools = ToolRunner(workspace)

    result = tools.write_file(
        "src/example.py",
        "answer = 42\n",
    )

    assert result.ok
    assert (tmp_path / "src" / "example.py").read_text(
        encoding="utf-8"
    ) == "answer = 42\n"


def test_write_file_cannot_escape_repo(tmp_path: Path):
    workspace = Workspace(tmp_path)
    tools = ToolRunner(workspace)

    outside = tmp_path.parent / "chriscode_escape_test.txt"

    if outside.exists():
        outside.unlink()

    result = tools.write_file(
        "../chriscode_escape_test.txt",
        "YOU SHOULD NEVER SEE THIS",
    )

    assert not result.ok
    assert result.stderr == "Path escapes repository."
    assert not outside.exists()
