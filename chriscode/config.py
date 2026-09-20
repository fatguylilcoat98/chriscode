from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    max_iterations: int = 12
    max_paid_cost_usd: float = 0.0
    model_profile: str = "mock"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            max_iterations=int(os.getenv("CHRISCODE_MAX_ITERATIONS", "12")),
            max_paid_cost_usd=float(os.getenv("CHRISCODE_MAX_COST_USD", "0")),
            model_profile=os.getenv("CHRISCODE_MODEL", "mock"),
        )
