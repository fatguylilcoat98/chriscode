from pathlib import Path
import subprocess

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

    (tmp_path / "test_fixture.py").write_text(
        "def test_fixture():\n    assert True\n",
        encoding="utf-8",
    )

    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
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

    assert result.status == "VERIFIED"


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
    assert result.status == "VERIFIED"


def test_model_stop_cannot_override_failing_tests(tmp_path: Path):
    controller = build_test_controller(
        tmp_path,
        [
            ModelDecision(
                action="stop",
                arguments={"message": "Everything is done."},
                reason="Model claims completion.",
                usage=ModelUsage(),
            ),
        ],
    )

    (tmp_path / "test_fixture.py").write_text(
        "def test_fixture():\n    assert False\n",
        encoding="utf-8",
    )

    result = controller.run("Pretend the broken task is complete")

    assert result.status == "FAILED"

class HistoryInspectingModel:
    name = "history-inspecting-test"

    def __init__(self):
        self.states = []
        self.index = 0

    def decide(self, state):
        self.states.append(state)

        decisions = [
            ModelDecision(
                action="list_files",
                arguments={},
                reason="Discover repository.",
                usage=ModelUsage(),
            ),
            ModelDecision(
                action="read_file",
                arguments={"path": "pyproject.toml"},
                reason="Inspect project metadata.",
                usage=ModelUsage(),
            ),
            ModelDecision(
                action="stop",
                arguments={"message": "Done."},
                reason="Enough evidence collected.",
                usage=ModelUsage(),
            ),
        ]

        decision = decisions[self.index]
        self.index += 1
        return decision


def test_controller_preserves_tool_history_across_turns(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='fixture'\n",
        encoding="utf-8",
    )

    (tmp_path / "test_fixture.py").write_text(
        "def test_fixture():\n    assert True\n",
        encoding="utf-8",
    )

    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    workspace = Workspace(tmp_path)
    tools = ToolRunner(workspace)
    ledger = JobLedger(tmp_path / ".chriscode" / "jobs")
    verifier = UniversalVerifier(workspace, tools)
    model = HistoryInspectingModel()

    controller = Controller(
        Settings(
            max_iterations=10,
            max_paid_cost_usd=0.0,
            model_profile="history-inspecting-test",
        ),
        workspace,
        ledger,
        tools,
        verifier,
        model,
    )

    result = controller.run("Inspect repository history")

    assert result.status == "VERIFIED"
    assert len(model.states) == 3

    third_turn_history = model.states[2]["history"]

    assert any(
        event.get("kind") == "tool_result"
        and event.get("action") == "list_files"
        and "pyproject.toml" in event.get("stdout", "")
        for event in third_turn_history
    )

    assert any(
        event.get("kind") == "tool_result"
        and event.get("action") == "read_file"
        and "[project]" in event.get("stdout", "")
        for event in third_turn_history
    )