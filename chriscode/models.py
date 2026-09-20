from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ModelUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


@dataclass
class ModelDecision:
    action: str
    arguments: dict
    reason: str = ""
    usage: ModelUsage | None = None


class ModelAdapter(Protocol):
    """Every local/API model must fit this interface."""

    name: str

    def decide(self, state: dict) -> ModelDecision:
        ...


class MockModel:
    """Safe placeholder. It proves plumbing without spending money."""

    name = "mock"

    def decide(self, state: dict) -> ModelDecision:
        return ModelDecision(
            action="stop",
            arguments={"message": "Mock model is connected; no code changes made."},
            reason="Foundation smoke test.",
            usage=ModelUsage(),
        )
