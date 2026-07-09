"""BabyAGI — Task-Driven Autonomous Agent Loop.

Inspired by yoheinakajima/babyagi:
  - Task creation: generate subtasks from objective
  - Task prioritization: reorder by relevance and dependencies
  - Task execution: run each task with context from vector memory
  - Self-building: the simplest thing that builds itself
"""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BabyTask:
    id: str
    description: str
    priority: int
    status: str = "pending"
    result: str = ""
    dependencies: list[str] = field(default_factory=list)
    created_at: float = 0.0
    completed_at: float = 0.0


class BabyAGI:
    """BabyAGI-style autonomous task loop."""

    def __init__(self, objective: str = "") -> None:
        self.objective = objective
        self._tasks: list[BabyTask] = []
        self._completed: list[BabyTask] = []
        self._context: list[str] = []
        self._max_loops = 50

    def add_objective(self, objective: str) -> None:
        self.objective = objective
        self._tasks = []
        self._completed = []
        self._context = []
        initial = self._create_initial_tasks(objective)
        for t in initial:
            self.add_task(t)

    def add_task(self, description: str, priority: int = 5, dependencies: Optional[list[str]] = None) -> BabyTask:
        task = BabyTask(
            id=f"bt-{uuid.uuid4().hex[:8]}",
            description=description,
            priority=priority,
            dependencies=dependencies or [],
            created_at=time.time(),
        )
        self._tasks.append(task)
        return task

    def _create_initial_tasks(self, objective: str) -> list[str]:
        return [
            f"Analyze objective: {objective}",
            f"Research requirements for: {objective}",
            f"Design approach for: {objective}",
        ]

    def prioritize(self) -> None:
        self._tasks.sort(key=lambda t: (t.priority, len(t.dependencies)))

    def execute_next(self) -> Optional[BabyTask]:
        self.prioritize()
        ready = [t for t in self._tasks if all(d in [c.id for c in self._completed] for d in t.dependencies)]
        if not ready:
            return None
        task = ready[0]
        task.status = "running"
        task.result = f"Executed: {task.description[:100]}"
        task.status = "completed"
        task.completed_at = time.time()
        self._tasks.remove(task)
        self._completed.append(task)
        self._context.append(task.result)
        new_tasks = self._generate_tasks(task)
        for nt in new_tasks:
            self.add_task(nt, priority=max(1, task.priority - 1), dependencies=[task.id])
        return task

    def _generate_tasks(self, completed: BabyTask) -> list[str]:
        return [
            f"Review outcome: {completed.description[:50]}",
            f"Integrate: {completed.description[:50]}",
        ]

    def run_loop(self, max_steps: int = 10) -> list[BabyTask]:
        completed = []
        for _ in range(min(max_steps, self._max_loops)):
            task = self.execute_next()
            if task is None:
                break
            completed.append(task)
        return completed

    def status(self) -> dict:
        return {
            "objective": self.objective,
            "pending": len(self._tasks),
            "completed": len(self._completed),
            "context_size": len(self._context),
            "total_tasks": len(self._tasks) + len(self._completed),
        }
