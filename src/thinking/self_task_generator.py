"""SelfTaskGenerator — generate self-assigned tasks from goals and context.

Creates actionable tasks from high-level goals, curiosity suggestions,
maintenance needs, and learning objectives. Integrates with GoalManager,
TaskScheduler, and CuriosityDrive.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TaskProposal:
    title: str = ""
    description: str = ""
    priority: int = 5
    task_type: str = ""
    source: str = ""
    source_id: int = 0
    estimated_duration: float = 0.0
    tags: List[str] = field(default_factory=list)


class SelfTaskGenerator:
    """Generate tasks from goals, curiosity, and maintenance needs."""

    def __init__(self):
        self._generated_count: int = 0

    def from_goal(self, goal: Any) -> Optional[TaskProposal]:
        if not goal:
            return None
        if goal.state != "active":
            return None
        return TaskProposal(
            title=f"Work on goal: {goal.title}",
            description=goal.description[:500],
            priority=goal.priority,
            task_type="goal_step",
            source="goal",
            source_id=goal.id,
            estimated_duration=1800.0,
            tags=[goal.category] if goal.category else [],
        )

    def from_exploration(self, exp_goal: Any) -> Optional[TaskProposal]:
        if not exp_goal:
            return None
        return TaskProposal(
            title=exp_goal.topic,
            description=f"Exploration suggested by {exp_goal.source}: {exp_goal.reason}",
            priority=exp_goal.priority,
            task_type="exploration",
            source=exp_goal.source,
            estimated_duration=900.0,
            tags=exp_goal.related_concepts,
        )

    def from_maintenance(self, memory_system: Any) -> List[TaskProposal]:
        proposals: List[TaskProposal] = []
        try:
            stats = memory_system.stats()
            consolidation_age = stats.get("last_consolidation", 0)
            forgetting_age = stats.get("last_forgetting", 0)
            now = time.time()

            if consolidation_age and (now - consolidation_age) > 7200:
                proposals.append(TaskProposal(
                    title="Run memory consolidation",
                    description=f"Last consolidation was {(now - consolidation_age) / 3600:.1f}h ago",
                    priority=4, task_type="maintenance",
                    source="memory_system", estimated_duration=60.0,
                    tags=["maintenance", "memory"],
                ))

            if forgetting_age and (now - forgetting_age) > 14400:
                proposals.append(TaskProposal(
                    title="Run forgetting cycle",
                    description=f"Last forgetting was {(now - forgetting_age) / 3600:.1f}h ago",
                    priority=3, task_type="maintenance",
                    source="memory_system", estimated_duration=30.0,
                    tags=["maintenance", "memory"],
                ))
        except Exception as e:
            logger.warning("Maintenance task generation failed: %s", e)
        return proposals

    def from_learning(self, skill_extractor: Any, limit: int = 3) -> List[TaskProposal]:
        proposals: List[TaskProposal] = []
        try:
            low_conf_skills = skill_extractor.search("", limit=50)
            low_conf_skills.sort(key=lambda s: s.confidence)
            for skill in low_conf_skills[:limit]:
                if skill.confidence < 0.5:
                    proposals.append(TaskProposal(
                        title=f"Practice skill: {skill.name}",
                        description=f"Skill confidence is {skill.confidence:.2f}, needs practice",
                        priority=3, task_type="learning",
                        source="skill_extractor", source_id=skill.id,
                        estimated_duration=1800.0,
                        tags=[skill.category, "learning"],
                    ))
        except Exception as e:
            logger.warning("Learning task generation failed: %s", e)
        return proposals

    def generate_all(self, active_goals: List[Any], exploration_goals: List[Any],
                     memory_system: Any = None, skill_extractor: Any = None) -> List[TaskProposal]:
        proposals: List[TaskProposal] = []
        seen_titles: set = set()

        for goal in active_goals:
            t = self.from_goal(goal)
            if t and t.title not in seen_titles:
                proposals.append(t)
                seen_titles.add(t.title)

        for eg in exploration_goals:
            t = self.from_exploration(eg)
            if t and t.title not in seen_titles:
                proposals.append(t)
                seen_titles.add(t.title)

        if memory_system:
            for t in self.from_maintenance(memory_system):
                if t.title not in seen_titles:
                    proposals.append(t)
                    seen_titles.add(t.title)

        if skill_extractor:
            for t in self.from_learning(skill_extractor):
                if t.title not in seen_titles:
                    proposals.append(t)
                    seen_titles.add(t.title)

        proposals.sort(key=lambda p: p.priority, reverse=True)
        self._generated_count = len(proposals)
        return proposals
