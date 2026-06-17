"""CuriosityDrive — generate exploration goals from knowledge gaps.

Identifies knowledge gaps, novel topics, and learning opportunities
to generate exploration goals. Uses concept map, skill extractor,
and feedback patterns to find areas for improvement.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExplorationGoal:
    topic: str = ""
    reason: str = ""
    priority: int = 3
    source: str = ""
    related_concepts: List[str] = field(default_factory=list)
    created_at: float = 0.0
    score: float = 0.0


class CuriosityDrive:
    """Generate exploration goals from knowledge gaps."""

    def __init__(self):
        self._explored_topics: Dict[str, float] = {}

    def mark_explored(self, topic: str, depth: float = 0.5) -> None:
        self._explored_topics[topic] = max(self._explored_topics.get(topic, 0.0), depth)

    def get_exploration_depth(self, topic: str) -> float:
        return self._explored_topics.get(topic, 0.0)

    def suggest_from_concept_map(self, concept_map: Any, min_confidence: float = 0.3) -> List[ExplorationGoal]:
        goals: List[ExplorationGoal] = []
        try:
            stats = concept_map.stats()
            if stats["concepts"] == 0:
                goals.append(ExplorationGoal(
                    topic="Build initial concept map",
                    reason="No concepts exist yet",
                    priority=5, source="curiosity",
                    score=0.8,
                ))
                return goals

            all_concepts = concept_map.search("")
            for concept in all_concepts or []:
                depth = self.get_exploration_depth(concept.name)
                if depth < min_confidence:
                    goals.append(ExplorationGoal(
                        topic=f"Explore: {concept.name}",
                        reason=f"Concept exists but exploration depth is low ({depth:.2f})",
                        priority=3, source="concept_map",
                        related_concepts=[concept.name],
                        score=1.0 - depth,
                    ))
        except Exception as e:
            logger.warning("Curiosity concept map suggestion failed: %s", e)
        return goals[:5]

    def suggest_from_skills(self, skill_extractor: Any, min_confidence: float = 0.3) -> List[ExplorationGoal]:
        goals: List[ExplorationGoal] = []
        try:
            top_skills = skill_extractor.get_top_skills(limit=10)
            for skill in top_skills:
                if skill.confidence < min_confidence:
                    goals.append(ExplorationGoal(
                        topic=f"Improve: {skill.name}",
                        reason=f"Skill confidence is low ({skill.confidence:.2f}), needs refinement",
                        priority=4, source="skill_gap",
                        related_concepts=[skill.name],
                        score=1.0 - skill.confidence,
                    ))
        except Exception as e:
            logger.warning("Curiosity skill suggestion failed: %s", e)
        return goals[:3]

    def suggest_from_novelty(self, recent_topics: List[str], known_topics: List[str]) -> List[ExplorationGoal]:
        goals: List[ExplorationGoal] = []
        known_set = set(t.lower() for t in known_topics)
        for topic in recent_topics:
            if topic.lower() not in known_set:
                goals.append(ExplorationGoal(
                    topic=f"Learn: {topic}",
                    reason=f"New topic encountered, not yet explored",
                    priority=3, source="novelty",
                    score=0.6,
                ))
        return goals[:3]

    def get_all_suggestions(self, concept_map: Any = None, skill_extractor: Any = None,
                            recent_topics: Optional[List[str]] = None,
                            known_topics: Optional[List[str]] = None) -> List[ExplorationGoal]:
        goals: List[ExplorationGoal] = []
        if concept_map:
            goals.extend(self.suggest_from_concept_map(concept_map))
        if skill_extractor:
            goals.extend(self.suggest_from_skills(skill_extractor))
        if recent_topics and known_topics:
            goals.extend(self.suggest_from_novelty(recent_topics, known_topics))
        goals.sort(key=lambda g: g.score, reverse=True)
        return goals[:10]
