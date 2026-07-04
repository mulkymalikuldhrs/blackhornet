"""ORCA — Parallel Agent Orchestration System.

Inspired by stablyai/orca (parallel agent IDE architecture):
  - Multiple agents running in isolated worktrees
  - Parallel task execution with result comparison
  - Agent race: same prompt → multiple agents → best result wins
  - Worktree isolation for concurrent modifications
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class AgentWorktree:
    id: str
    name: str
    path: str
    agent_type: str
    status: str = "idle"
    created_at: float = 0.0
    last_active: float = 0.0


@dataclass
class ParallelTask:
    id: str
    prompt: str
    agents: list[str]
    results: dict = field(default_factory=dict)
    best_result: Optional[str] = None
    status: str = "pending"
    created_at: float = 0.0
    completed_at: float = 0.0


class OrcaOrchestrator:
    """ORCA-style parallel agent orchestrator."""

    def __init__(self) -> None:
        self._worktrees: dict[str, AgentWorktree] = {}
        self._tasks: list[ParallelTask] = []
        self._base_dir = self._detect_base()

    def _detect_base(self) -> str:
        base = os.environ.get("DHAHERLABS", "/sdcard/dhaherlabs")
        worktrees = os.path.join(base, "worktrees")
        os.makedirs(worktrees, exist_ok=True)
        return worktrees

    def create_worktree(self, name: str, agent_type: str = "coder") -> AgentWorktree:
        wt_id = f"wt-{uuid.uuid4().hex[:8]}"
        wt_path = os.path.join(self._base_dir, name or wt_id)
        os.makedirs(wt_path, exist_ok=True)
        worktree = AgentWorktree(
            id=wt_id,
            name=name or wt_id,
            path=wt_path,
            agent_type=agent_type,
            status="ready",
            created_at=time.time(),
            last_active=time.time(),
        )
        self._worktrees[wt_id] = worktree
        return worktree

    def list_worktrees(self) -> list[AgentWorktree]:
        return list(self._worktrees.values())

    def get_worktree(self, worktree_id: str) -> Optional[AgentWorktree]:
        return self._worktrees.get(worktree_id)

    def race(self, prompt: str, agent_types: Optional[list[str]] = None, timeout: float = 60.0) -> ParallelTask:
        if agent_types is None:
            agent_types = ["coder", "planner", "researcher"]
        task = ParallelTask(
            id=f"task-{uuid.uuid4().hex[:8]}",
            prompt=prompt,
            agents=agent_types,
            status="running",
            created_at=time.time(),
        )
        self._tasks.append(task)
        results = {}
        for at in agent_types:
            wt = self.create_worktree(f"race-{at}-{task.id[:4]}", at)
            result = self._execute_in_worktree(wt, prompt, timeout)
            results[at] = result
        task.results = results
        best = max(results.values(), key=lambda r: len(r) if r else 0) if results else ""
        task.best_result = best
        task.status = "completed"
        task.completed_at = time.time()
        return task

    def _execute_in_worktree(self, worktree: AgentWorktree, prompt: str, timeout: float) -> str:
        start = time.time()
        worktree.status = "busy"
        try:
            result = f"[{worktree.agent_type}] Simulated execution of: {prompt[:50]}... (took {time.time() - start:.1f}s)"
            worktree.last_active = time.time()
            worktree.status = "ready"
            return result
        except Exception as e:
            worktree.status = "error"
            return f"Error: {e}"

    def fan_out(self, prompt: str, count: int = 3) -> list[str]:
        results = []
        for i in range(count):
            wt = self.create_worktree(f"fan-{i}-{uuid.uuid4().hex[:4]}")
            result = self._execute_in_worktree(wt, f"{prompt} (variant {i+1})", 30)
            results.append(result)
        return results

    def task_history(self, limit: int = 10) -> list[ParallelTask]:
        return self._tasks[-limit:]

    def stats(self) -> dict:
        return {
            "worktrees": len(self._worktrees),
            "tasks_completed": sum(1 for t in self._tasks if t.status == "completed"),
            "tasks_running": sum(1 for t in self._tasks if t.status == "running"),
            "agents_types": list(set(w.agent_type for w in self._worktrees.values())),
        }
