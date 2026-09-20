from __future__ import annotations

from dataclasses import dataclass

from .config import Settings
from .ledger import JobLedger
from .models import ModelAdapter
from .tools import ToolRunner, ToolResult
from .verifier import UniversalVerifier
from .workspace import Workspace


@dataclass
class RunResult:
    job_id: str
    status: str
    message: str

    def summary(self) -> str:
        return f"Chris Code job {self.job_id}: {self.status}\n{self.message}"


class Controller:
    """The harness owns state. The model only proposes decisions."""

    def __init__(
        self,
        settings: Settings,
        workspace: Workspace,
        ledger: JobLedger,
        tools: ToolRunner,
        verifier: UniversalVerifier,
        model: ModelAdapter,
    ):
        self.settings = settings
        self.workspace = workspace
        self.ledger = ledger
        self.tools = tools
        self.verifier = verifier
        self.model = model

    def doctor(self) -> None:
        report = self.verifier.verify_foundation()

        print("Chris Code doctor")
        print(f"Repository: {self.workspace.root}")
        print(f"Git status: {self.workspace.status()}")

        for check in report.checks:
            print(f"[{check.status}] {check.name}: {check.detail}")

        print(f"Verdict: {report.verdict}")

    def _execute_tool_decision(self, action: str, arguments: dict) -> ToolResult:
        if action == "list_files":
            return self.tools.list_files()
        if action == "read_file":
            path = arguments.get("path")

            if not isinstance(path, str) or not path:
                return ToolResult(False, 1, "", "read_file requires path.")

            return self.tools.read_file(path)

        if action == "write_file":
            path = arguments.get("path")
            content = arguments.get("content")

            if not isinstance(path, str) or not path:
                return ToolResult(False, 1, "", "write_file requires path.")

            if not isinstance(content, str):
                return ToolResult(False, 1, "", "write_file requires string content.")

            return self.tools.write_file(path, content)

        if action == "run_tests":
            return self.tools.run_tests()

        return ToolResult(
            False,
            1,
            "",
            f"Unsupported action: {action}",
        )

    def run(self, task: str) -> RunResult:
        job = self.ledger.create(task)
        job.status = "RUNNING"
        self.ledger.save(job)

        last_tool_result: dict | None = None
        history: list[dict] = []

        for iteration in range(1, self.settings.max_iterations + 1):
            job.iteration = iteration

            state = {
                "job_id": job.id,
                "task": task,
                "iteration": iteration,
                "git_status": self.workspace.status(),
                "last_tool_result": last_tool_result,
                "history": history[-20:],
            }

            decision = self.model.decide(state)
            job.model_calls += 1

            if decision.usage:
                job.input_tokens += decision.usage.input_tokens
                job.output_tokens += decision.usage.output_tokens
                job.paid_cost_usd += decision.usage.cost_usd

            decision_event = {
                "kind": "model_decision",
                "model": self.model.name,
                "action": decision.action,
                "arguments": decision.arguments,
                "reason": decision.reason,
            }

            history.append(decision_event)

            job.add_event(
                "model_decision",
                {
                    "model": self.model.name,
                    "action": decision.action,
                    "arguments": decision.arguments,
                    "reason": decision.reason,
                },
            )
            self.ledger.save(job)

            if job.paid_cost_usd > self.settings.max_paid_cost_usd:
                job.status = "BUDGET_BLOCKED"
                job.add_event("budget_blocked", {})
                self.ledger.save(job)

                return RunResult(
                    job.id,
                    job.status,
                    "Paid inference budget exceeded.",
                )

            if decision.action == "stop":
                report = self.verifier.verify_task()
                job.status = report.verdict

                job.add_event(
                    "verification",
                    {
                        "verdict": report.verdict,
                        "checks": [c.__dict__ for c in report.checks],
                    },
                )
                self.ledger.save(job)

                return RunResult(
                    job.id,
                    job.status,
                    decision.arguments.get("message", "Stopped."),
                )

            if decision.action not in {
                "list_files",
                "read_file",
                "write_file",
                "run_tests",
            }:
                job.status = "UNVERIFIED"
                job.add_event(
                    "unknown_action",
                    {"action": decision.action},
                )
                self.ledger.save(job)

                return RunResult(
                    job.id,
                    job.status,
                    f"Unsupported action: {decision.action}",
                )

            tool_result = self._execute_tool_decision(
                decision.action,
                decision.arguments,
            )

            last_tool_result = {
                "action": decision.action,
                "ok": tool_result.ok,
                "exit_code": tool_result.exit_code,
                "stdout": tool_result.stdout,
                "stderr": tool_result.stderr,
            }

            history.append(
                {
                    "kind": "tool_result",
                    **last_tool_result,
                }
            )

            job.add_event("tool_result", last_tool_result)
            self.ledger.save(job)

        job.status = "UNVERIFIED"
        job.add_event(
            "iteration_limit",
            {"limit": self.settings.max_iterations},
        )
        self.ledger.save(job)

        return RunResult(
            job.id,
            job.status,
            "Iteration limit reached.",
        )
