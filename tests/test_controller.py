from pathlib import Path

from chriscode.config import Settings
from chriscode.controller import Controller
from chriscode.ledger import JobLedger
from chriscode.models import ModelDecision, ModelUsage
from chriscode.tools import ToolRunner
from chriscode.verifier import UniversalVerifier
from chriscode.workspace import Workspace


class ScriptedModel:
    name = "scripted-test"

    def __init__(self, decisions):
        self.decisions = list(decisions)
        self.index = 0

    def decide(self, state):
        decision = self.decisions[self.index]
        self.index += 1
        return decision


def build_test_controller(tmp_path: Path, decisions):
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='fixture'\n",
        encoding="utf-8",
    )

    workspace = Workspace(tmp_path)
    tools = ToolRunner(workspace)
    ledger = JobLedger(tmp_path / ".chriscode" / "jobs")
    verifier = UniversalVerifier(workspace, tools)

    settings = Settings(
        max_iterations=10,
        max_paid_cost_usd=0.0,
        model_profile="scripted-test",
    )

    return Controller(
        settings,
        workspace,
        ledger,
        tools,
        verifier,
        ScriptedModel(decisions),
    )


def test_controller_executes_write_then_stop(tmp_path: Path):
    controller = build_test_controller(
        tmp_path,
        [
            ModelDecision(
                action="write_file",
                arguments={
                    "path": "example.py",
                    "content": "answer = 42\n",
                },
                reason="Create the requested file.",
                usage=ModelUsage(),
            ),
            ModelDecision(
                action="stop",
                arguments={"message": "Done."},
                reason="Requested change is complete.",
                usage=ModelUsage(),
            ),
        ],
    )

    result = controller.run("Create example.py")

    assert (tmp_path / "example.py").read_text(
        encoding="utf-8"
    ) == "answer = 42\n"

    assert result.status == "UNVERIFIED"


def test_controller_blocks_write_escape(tmp_path: Path):
    outside = tmp_path.parent / "controller_escape_test.txt"

    if outside.exists():
        outside.unlink()

    controller = build_test_controller(
        tmp_path,
        [
            ModelDecision(
                action="write_file",
                arguments={
                    "path": "../controller_escape_test.txt",
                    "content": "NOPE",
                },
                reason="Attempt escape.",
                usage=ModelUsage(),
            ),
            ModelDecision(
                action="stop",
                arguments={"message": "Stopped."},
                usage=ModelUsage(),
            ),
        ],
    )

    result = controller.run("Attempt escape")

    assert not outside.exists()
    assert result.status == "UNVERIFIED"
