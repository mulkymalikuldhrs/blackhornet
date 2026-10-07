"""OWL/CAMEL-inspired dynamic role orchestration for multi-agent collaboration."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import uuid
import asyncio

from src.colony.types import TaskPriority
from src.core.workforce.task_planner import TaskPlanner, Plan


class RoleType(Enum):
    ANALYST = "analyst"
    CRITIC = "critic"
    EXECUTOR = "executor"
    PLANNER = "planner"
    RESEARCHER = "researcher"


@dataclass
class AgentRole:
    agent_id: str
    role: RoleType
    capabilities: List[str] = field(default_factory=list)
    assignment_id: str = ""

    def __post_init__(self):
        if not self.assignment_id:
            self.assignment_id = f"role-{uuid.uuid4().hex[:8]}"


@dataclass
class CollaborationRound:
    round_num: int
    contributions: Dict[str, str] = field(default_factory=dict)
    consensus: Optional[str] = None


class RoleOrchestrator:
    """Dynamically assigns roles to agents and manages collaboration rounds."""

    def __init__(self):
        self.roles: Dict[str, AgentRole] = {}
        self.rounds: List[CollaborationRound] = []
        self._lock = asyncio.Lock()
        self.state = type("State", (), {"active_tasks": {}})()
        async def _enqueue(self, *a, **k):
            return None
        self._task_queue = type("TaskQueue", (), {"enqueue": _enqueue})()

    def assign_role(self, agent_id: str, role: RoleType, capabilities: List[str] = None):
        self.roles[agent_id] = AgentRole(agent_id=agent_id, role=role, capabilities=capabilities or [])

    def get_agents_by_role(self, role: RoleType) -> List[AgentRole]:
        return [r for r in self.roles.values() if r.role == role]

    def run_collaboration(self, task: str, agent_fn: Callable[[str, str, RoleType], str], max_rounds: int = 3) -> List[CollaborationRound]:
        """Run collaboration rounds where agents contribute based on their roles."""
        for round_num in range(1, max_rounds + 1):
            round_data = CollaborationRound(round_num=round_num)
            for agent_role in self.roles.values():
                contribution = agent_fn(agent_role.agent_id, task, agent_role.role)
                round_data.contributions[agent_role.agent_id] = contribution
            self.rounds.append(round_data)
        return self.rounds

    def decompose_goal(self, goal: str) -> Plan:
        """Decompose a high-level goal into subtasks using TaskPlanner."""
        planner = TaskPlanner()
        return planner.decompose(goal)

    async def submit_plan(self, plan: Plan, priority: TaskPriority = TaskPriority.NORMAL) -> dict[str, str]:
        """Submit all pending subtasks from a plan to the task queue."""
        async with self._lock:
            submitted = {}
            for subtask in plan.pending():
                task_id = f"plan_{subtask.id}_{len(self.state.active_tasks)}"
                await self._task_queue.enqueue(task_id, subtask.description, priority)
                self.state.active_tasks[task_id] = subtask.description
                submitted[subtask.id] = task_id
            return submitted
