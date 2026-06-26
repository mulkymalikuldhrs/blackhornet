"""SubAgent lifecycle manager — DeerFlow-inspired state machine.

State machine: PENDING → RUNNING → COMPLETED | FAILED | TIMEOUT
with retry support within RUNNING state.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class SubAgentState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


@dataclass
class SubAgent:
    id: str
    task: str
    max_retries: int = 3
    timeout: int = 300
    state: SubAgentState = SubAgentState.PENDING
    output: Any = None
    error: str = ""
    retry_count: int = 0
    _started_at: Optional[float] = None

    def start(self) -> None:
        self.state = SubAgentState.RUNNING
        self._started_at = time.time()

    def complete(self, output: Any) -> None:
        self.state = SubAgentState.COMPLETED
        self.output = output

    def fail(self, error: str) -> None:
        self.retry_count += 1
        self.error = error
        if self.retry_count > self.max_retries:
            self.state = SubAgentState.FAILED

    def is_timed_out(self) -> bool:
        if self._started_at is None:
            return False
        return time.time() - self._started_at > self.timeout
