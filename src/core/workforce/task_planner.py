"""Task Planner — SamanAI §3.3 WORKFORCE layer.

Goal decomposer and memory router for workforce agents.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SubTask:
    id: str
    description: str
    role: str
    dependencies: list[str] = field(default_factory=list)
    priority: float = 1.0
    completed: bool = False


@dataclass(slots=True)
class Plan:
    goal: str
    subtasks: list[SubTask] = field(default_factory=list)
    memory_route: dict[str, list[str]] = field(default_factory=dict)

    def mark_complete(self, task_id: str) -> bool:
        for t in self.subtasks:
            if t.id == task_id:
                t.completed = True
                return True
        return False

    def pending(self) -> list[SubTask]:
        return [t for t in self.subtasks if not t.completed]


class TaskPlanner:
    """Decomposes high-level goals into executable subtasks."""

    def __init__(self, max_subtasks: int = 10) -> None:
        self.max_subtasks = max_subtasks

    def decompose(self, goal: str, context: Optional[dict] = None) -> Plan:
        # Minimal heuristic decomposition; wire to LLM later
        subtasks = [
            SubTask(id="t1", description=f"Research: {goal[:80]}", role="researcher", priority=1.0),
            SubTask(id="t2", description=f"Plan: {goal[:80]}", role="orchestrator", priority=0.9),
            SubTask(id="t3", description=f"Execute: {goal[:80]}", role="coder", priority=0.8),
            SubTask(id="t4", description=f"Review: {goal[:80]}", role="critic", priority=0.7),
        ]
        plan = Plan(goal=goal, subtasks=subtasks[: self.max_subtasks])
        plan.memory_route = {
            "researcher": ["research:findings"],
            "orchestrator": ["plan:structure"],
            "coder": ["code:changes"],
            "critic": ["review:issues"],
        }
        return plan

    def route_memory(self, plan: Plan, role: str) -> list[str]:
        return plan.memory_route.get(role, [])


__all__ = ["TaskPlanner", "Plan", "SubTask"]
