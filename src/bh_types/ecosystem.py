"""EcosystemState — canonical colony state schema.

Implements SAMAN-AI DESIGN.md EcosystemState TypedDict.
Adopted as the single source of truth for colony-wide state.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ConsensusStatus(str, Enum):
    PENDING = "pending"
    REACHED = "reached"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass(slots=True)
class EcosystemState:
    """Canonical state for the entire colony ecosystem.

    Fields per SAMAN-AI DESIGN.md:
    - session_id: unique session identifier
    - task_queue: pending tasks awaiting assignment
    - active_agents: currently running agent IDs
    - debate_rounds: number of debate rounds executed
    - consensus_reached: whether consensus was achieved
    - memory_context: current memory context snapshot
    - audit_log: immutable audit trail
    """

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_queue: list[str] = field(default_factory=list)
    active_agents: list[str] = field(default_factory=list)
    debate_rounds: int = 0
    consensus_reached: bool = False
    consensus_status: ConsensusStatus = ConsensusStatus.PENDING
    memory_context: dict[str, Any] = field(default_factory=dict)
    audit_log: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = time.time()

    def enqueue_task(self, task: str) -> None:
        """Add a task to the queue."""
        self.task_queue.append(task)
        self.touch()

    def dequeue_task(self) -> Optional[str]:
        """Remove and return the next task, or None if empty."""
        if self.task_queue:
            task = self.task_queue.pop(0)
            self.touch()
            return task
        return None

    def register_agent(self, agent_id: str) -> None:
        """Register an active agent."""
        if agent_id not in self.active_agents:
            self.active_agents.append(agent_id)
            self.touch()

    def deregister_agent(self, agent_id: str) -> None:
        """Remove an agent from active list."""
        if agent_id in self.active_agents:
            self.active_agents.remove(agent_id)
            self.touch()

    def increment_debate_round(self) -> None:
        """Increment debate round counter."""
        self.debate_rounds += 1
        self.touch()

    def set_consensus(self, reached: bool) -> None:
        """Set consensus status."""
        self.consensus_reached = reached
        self.consensus_status = ConsensusStatus.REACHED if reached else ConsensusStatus.FAILED
        self.touch()

    def append_audit(self, event: str, **kwargs: Any) -> None:
        """Append an immutable audit entry."""
        entry = {
            "timestamp": time.time(),
            "event": event,
            **kwargs,
        }
        self.audit_log.append(entry)
        self.touch()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "session_id": self.session_id,
            "task_queue": list(self.task_queue),
            "active_agents": list(self.active_agents),
            "debate_rounds": self.debate_rounds,
            "consensus_reached": self.consensus_reached,
            "consensus_status": self.consensus_status.value,
            "memory_context": dict(self.memory_context),
            "audit_log": list(self.audit_log),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EcosystemState":
        """Deserialize from dict."""
        state = cls(
            session_id=data.get("session_id", str(uuid.uuid4())),
            task_queue=list(data.get("task_queue", [])),
            active_agents=list(data.get("active_agents", [])),
            debate_rounds=data.get("debate_rounds", 0),
            consensus_reached=data.get("consensus_reached", False),
            memory_context=dict(data.get("memory_context", {})),
            audit_log=list(data.get("audit_log", [])),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )
        status_str = data.get("consensus_status", "pending")
        try:
            state.consensus_status = ConsensusStatus(status_str)
        except ValueError:
            state.consensus_status = ConsensusStatus.PENDING
        return state
