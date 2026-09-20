from __future__ import annotations

import argparse
from pathlib import Path

from .config import Settings
from .controller import Controller
from .ledger import JobLedger
from .models import MockModel
from .tools import ToolRunner
from .verifier import UniversalVerifier
from .workspace import Workspace


def build_controller(repo: Path) -> Controller:
    settings = Settings.from_env()
    workspace = Workspace(repo)
    ledger = JobLedger(repo / ".chriscode" / "jobs")
    tools = ToolRunner(workspace)
    verifier = UniversalVerifier(workspace, tools)
    model = MockModel()
    return Controller(settings, workspace, ledger, tools, verifier, model)


def main() -> None:
    parser = argparse.ArgumentParser(prog="chris-code")
    parser.add_argument("task", nargs="?", help="Coding task to run")
    parser.add_argument("--repo", default=".", help="Repository to work on")
    parser.add_argument("--doctor", action="store_true", help="Check the installation")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    controller = build_controller(repo)

    if args.doctor:
        controller.doctor()
        return

    if not args.task:
        parser.error("Provide a task or use --doctor.")

    result = controller.run(args.task)
    print(result.summary())


if __name__ == "__main__":
    main()
