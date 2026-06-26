"""Subagent lifecycle manager — DeerFlow-inspired state machine.

State machine: PENDING → RUNNING → COMPLETED | FAILED | TIMEOUT
with retry support within RUNNING state.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class SubagentState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


@dataclass
class Subagent:
    id: str
    task: str
    max_retries: int = 3
    timeout: int = 300
    state: SubagentState = SubagentState.PENDING
    output: Any = None
    error: str = ""
    retry_count: int = 0
    _started_at: Optional[float] = None

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {self.max_retries}")
        if self.timeout <= 0:
            raise ValueError(f"timeout must be > 0, got {self.timeout}")

    def start(self) -> None:
        if self.state != SubagentState.PENDING:
            raise ValueError(
                f"Cannot start from {self.state.value}; expected PENDING"
            )
        self.state = SubagentState.RUNNING
        self._started_at = time.time()

    def complete(self, output: Any) -> None:
        if self.state != SubagentState.RUNNING:
            raise ValueError(
                f"Cannot complete from {self.state.value}; expected RUNNING"
            )
        self.state = SubagentState.COMPLETED
        self.output = output

    def fail(self, error: str) -> None:
        if self.state != SubagentState.RUNNING:
            raise ValueError(
                f"Cannot fail from {self.state.value}; expected RUNNING"
            )
        self.retry_count += 1
        self.error = error
        if self.retry_count > self.max_retries:
            self.state = SubagentState.FAILED

    def is_timed_out(self) -> bool:
        if self._started_at is None:
            return False
        return time.time() - self._started_at > self.timeout
