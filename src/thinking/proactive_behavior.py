"""ProactiveBehavior — initiate actions without user prompt.

Monitors goals, tasks, and context to determine when to proactively
suggest or execute actions. Uses triggers based on time, context
changes, goal states, and learned patterns.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProactiveAction:
    id: str = ""
    action_type: str = ""
    title: str = ""
    description: str = ""
    priority: int = 5
    source: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    expires_at: Optional[float] = None
    executed: bool = False


class ProactiveBehavior:
    """Determine when to take proactive actions."""

    def __init__(self):
        self._actions: List[ProactiveAction] = []
        self._last_check: float = 0.0
        self._check_interval: float = 300.0

    def set_check_interval(self, seconds: float) -> None:
        self._check_interval = max(30.0, seconds)

    def suggest_from_overdue_goals(self, goals: List[Any]) -> List[ProactiveAction]:
        actions: List[ProactiveAction] = []
        for goal in goals:
            action = ProactiveAction(
                id=f"overdue_goal_{goal.id}",
                action_type="reminder",
                title=f"Overdue goal: {goal.title}",
                description=goal.description[:200],
                priority=min(10, goal.priority + 2),
                source="overdue_goal",
                context={"goal_id": goal.id},
                created_at=time.time(),
            )
            actions.append(action)
        return actions

    def suggest_from_idle(self, idle_seconds: float, active_goals: List[Any]) -> List[ProactiveAction]:
        actions: List[ProactiveAction] = []
        if idle_seconds > 3600 and active_goals:
            for goal in active_goals[:3]:
                if goal.progress < 1.0:
                    action = ProactiveAction(
                        id=f"progress_goal_{goal.id}",
                        action_type="progress_check",
                        title=f"Check progress on: {goal.title}",
                        description=f"Goal progress is at {goal.progress:.0%}",
                        priority=4,
                        source="idle_progress",
                        context={"goal_id": goal.id, "idle_seconds": idle_seconds},
                        created_at=time.time(),
                    )
                    actions.append(action)
        return actions

    def suggest_from_context(self, context: str, keywords: Dict[str, int]) -> List[ProactiveAction]:
        actions: List[ProactiveAction] = []
        context_lower = context.lower()
        for keyword, priority in keywords.items():
            if keyword.lower() in context_lower:
                action = ProactiveAction(
                    id=f"context_{keyword}",
                    action_type="context_suggestion",
                    title=f"Found keyword: {keyword}",
                    description=f"Context triggered suggestion based on '{keyword}'",
                    priority=priority,
                    source="context_trigger",
                    context={"keyword": keyword},
                    created_at=time.time(),
                )
                actions.append(action)
        return actions

    def get_pending_actions(self, max_age: float = 3600.0) -> List[ProactiveAction]:
        now = time.time()
        return [
            a for a in self._actions
            if not a.executed
            and (a.expires_at is None or a.expires_at > now)
            and (now - a.created_at) < max_age
        ]

    def mark_executed(self, action_id: str) -> bool:
        for action in self._actions:
            if action.id == action_id:
                action.executed = True
                return True
        return False

    def clear_expired(self) -> int:
        now = time.time()
        before = len(self._actions)
        self._actions = [a for a in self._actions if a.expires_at is None or a.expires_at > now]
        return before - len(self._actions)
