"""PlanLayer — state machine for subagent plan stages.

States: IDLE → PLANNING → APPROVED → EXECUTING → COMPLETED | FAILED
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PlanLayerState(str, Enum):
    IDLE = "IDLE"
    PLANNING = "PLANNING"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PlanTransitionError(ValueError):
    """Raised on invalid state transition."""


_VALID_TRANSITIONS: Dict[PlanLayerState, set] = {
    PlanLayerState.IDLE: {PlanLayerState.PLANNING},
    PlanLayerState.PLANNING: {PlanLayerState.APPROVED, PlanLayerState.FAILED},
    PlanLayerState.APPROVED: {PlanLayerState.EXECUTING, PlanLayerState.FAILED},
    PlanLayerState.EXECUTING: {PlanLayerState.COMPLETED, PlanLayerState.FAILED},
    PlanLayerState.COMPLETED: set(),
    PlanLayerState.FAILED: set(),
}


@dataclass
class PlanStep:
    name: str
    status: PlanLayerState = PlanLayerState.IDLE
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    output: Any = None
    error: str = ""


@dataclass
class PlanLayer:
    """State machine tracking a plan through its lifecycle."""

    plan_id: str
    state: PlanLayerState = PlanLayerState.IDLE
    steps: List[PlanStep] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    _transitioned_at: Optional[float] = None

    def __post_init__(self) -> None:
        self._transitioned_at = time.time()

    def _transition(self, target: PlanLayerState) -> None:
        allowed = _VALID_TRANSITIONS.get(self.state, set())
        if target not in allowed:
            raise PlanTransitionError(
                f"Cannot transition from {self.state.value} to {target.value}; "
                f"allowed: {[s.value for s in allowed]}"
            )
        self.state = target
        self._transitioned_at = time.time()

    def plan(self) -> None:
        self._transition(PlanLayerState.PLANNING)

    def approve(self) -> None:
        self._transition(PlanLayerState.APPROVED)

    def execute(self) -> None:
        self._transition(PlanLayerState.EXECUTING)

    def complete(self, output: Any = None) -> None:
        self._transition(PlanLayerState.COMPLETED)

    def fail(self, error: str = "") -> None:
        self.state = PlanLayerState.FAILED
        self._transitioned_at = time.time()

    def add_step(self, name: str) -> PlanStep:
        step = PlanStep(name=name)
        self.steps.append(step)
        return step

    def elapsed(self) -> float:
        if self._transitioned_at is None:
            return 0.0
        return time.time() - self._transitioned_at

    @property
    def is_terminal(self) -> bool:
        return self.state in (PlanLayerState.COMPLETED, PlanLayerState.FAILED)

    @property
    def summary(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "state": self.state.value,
            "step_count": len(self.steps),
            "is_terminal": self.is_terminal,
            "elapsed_seconds": self.elapsed(),
        }
