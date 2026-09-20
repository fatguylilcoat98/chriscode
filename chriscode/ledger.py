from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json
import uuid


@dataclass
class JobRecord:
    id: str
    task: str
    status: str = "CREATED"
    iteration: int = 0
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    paid_cost_usd: float = 0.0
    events: list[dict] = field(default_factory=list)

    def add_event(self, kind: str, data: dict) -> None:
        self.events.append({
            "time": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "data": data,
        })


class JobLedger:
    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def create(self, task: str) -> JobRecord:
        job = JobRecord(id=uuid.uuid4().hex[:12], task=task)
        job.add_event("job_created", {"task": task})
        self.save(job)
        return job

    def save(self, job: JobRecord) -> None:
        target = self.directory / f"{job.id}.json"
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(job), indent=2), encoding="utf-8")
        temp.replace(target)
