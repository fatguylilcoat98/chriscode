from __future__ import annotations

from dataclasses import dataclass

from .config import Settings
from .ledger import JobLedger
from .models import ModelAdapter
from .tools import ToolRunner
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

    def run(self, task: str) -> RunResult:
        job = self.ledger.create(task)
        job.status = "RUNNING"
        self.ledger.save(job)

        for iteration in range(1, self.settings.max_iterations + 1):
            job.iteration = iteration
            state = {
                "job_id": job.id,
                "task": task,
                "iteration": iteration,
                "git_status": self.workspace.status(),
            }

            decision = self.model.decide(state)
            job.model_calls += 1

            if decision.usage:
                job.input_tokens += decision.usage.input_tokens
                job.output_tokens += decision.usage.output_tokens
                job.paid_cost_usd += decision.usage.cost_usd

            job.add_event("model_decision", {
                "model": self.model.name,
                "action": decision.action,
                "arguments": decision.arguments,
                "reason": decision.reason,
            })
            self.ledger.save(job)

            if job.paid_cost_usd > self.settings.max_paid_cost_usd:
                job.status = "BUDGET_BLOCKED"
                job.add_event("budget_blocked", {})
                self.ledger.save(job)
                return RunResult(job.id, job.status, "Paid inference budget exceeded.")

            if decision.action == "stop":
                report = self.verifier.verify_foundation()
                job.status = report.verdict
                job.add_event("verification", {
                    "verdict": report.verdict,
                    "checks": [c.__dict__ for c in report.checks],
                })
                self.ledger.save(job)
                return RunResult(
                    job.id,
                    job.status,
                    decision.arguments.get("message", "Stopped."),
                )

            # Unknown actions fail closed in v0.1.
            job.status = "UNVERIFIED"
            job.add_event("unknown_action", {"action": decision.action})
            self.ledger.save(job)
            return RunResult(job.id, job.status, f"Unsupported action: {decision.action}")

        job.status = "UNVERIFIED"
        job.add_event("iteration_limit", {"limit": self.settings.max_iterations})
        self.ledger.save(job)
        return RunResult(job.id, job.status, "Iteration limit reached.")
