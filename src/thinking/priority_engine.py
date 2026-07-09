"""PriorityEngine — compute priority scores for tasks and goals.

Calculates priority based on urgency, importance, dependencies,
user preferences, deadlines, and historical patterns. Provides
sorting and filtering by computed priority.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PriorityFactors:
    urgency: float = 0.0
    importance: float = 0.0
    dependency_weight: float = 0.0
    user_preference: float = 0.5
    deadline_proximity: float = 0.0
    historical_success: float = 0.5
    effort_score: float = 0.5


@dataclass
class ScoredItem:
    item_id: int = 0
    title: str = ""
    base_priority: int = 5
    computed_score: float = 0.0
    factors: PriorityFactors = field(default_factory=PriorityFactors)
    item_type: str = "task"


class PriorityEngine:
    """Compute and rank priority scores for tasks and goals."""

    def __init__(self):
        self._user_prefs: Dict[str, float] = {}

    def set_user_preferences(self, prefs: Dict[str, float]) -> None:
        self._user_prefs = prefs

    def compute(self, base_priority: int, deadline: Optional[float] = None,
                dependency_count: int = 0, category: str = "",
                estimated_duration: float = 0.0) -> PriorityFactors:
        now = time.time()
        factors = PriorityFactors()

        factors.importance = min(1.0, base_priority / 10.0)

        if deadline:
            hours_left = (deadline - now) / 3600
            if hours_left <= 0:
                factors.urgency = 1.0
            else:
                factors.urgency = min(1.0, 24.0 / hours_left)
                factors.deadline_proximity = factors.urgency

        factors.dependency_weight = min(0.5, dependency_count * 0.1)

        cat_pref = self._user_prefs.get(category, 0.5)
        factors.user_preference = cat_pref

        if estimated_duration > 0:
            factors.effort_score = min(1.0, estimated_duration / 3600.0)

        return factors

    def score(self, base_priority: int, deadline: Optional[float] = None,
              dependency_count: int = 0, category: str = "",
              estimated_duration: float = 0.0) -> float:
        f = self.compute(base_priority, deadline, dependency_count, category, estimated_duration)
        return (
            f.importance * 0.30 +
            f.urgency * 0.25 +
            f.dependency_weight * 0.10 +
            f.user_preference * 0.15 +
            f.deadline_proximity * 0.10 +
            f.effort_score * 0.10
        )

    def rank(self, items: List[ScoredItem]) -> List[ScoredItem]:
        for item in items:
            item.computed_score = item.base_priority / 10.0
        items.sort(key=lambda x: x.computed_score, reverse=True)
        return items

    def rank_with_deadlines(self, items: List[ScoredItem]) -> List[ScoredItem]:
        for item in items:
            item.computed_score = self.score(
                base_priority=item.base_priority,
                category=item.item_type,
            )
        items.sort(key=lambda x: x.computed_score, reverse=True)
        return items
