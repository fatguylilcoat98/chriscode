from pathlib import Path

from chriscode.ledger import JobLedger
from chriscode.workspace import Workspace
from chriscode.tools import ToolRunner
from chriscode.verifier import UniversalVerifier


def test_ledger_persists(tmp_path: Path):
    ledger = JobLedger(tmp_path / "jobs")
    job = ledger.create("test task")
    assert (tmp_path / "jobs" / f"{job.id}.json").exists()


def test_verifier_detects_python_project(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    workspace = Workspace(tmp_path)
    verifier = UniversalVerifier(workspace, ToolRunner(workspace))
    assert "python" in verifier.detect()


def test_read_file_cannot_escape_repo(tmp_path: Path):
    workspace = Workspace(tmp_path)
    tools = ToolRunner(workspace)
    result = tools.read_file("../outside.txt")
    assert not result.ok
