"""Hermes Agent-inspired self-improving agent with closed learning loop."""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class Skill:
    name: str
    description: str
    code: str
    created_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0
    success_rate: float = 0.0

@dataclass
class Experience:
    task: str
    action: str
    outcome: str
    feedback: str
    timestamp: datetime = field(default_factory=datetime.now)

class SelfImprovingAgent:
    """Agent that improves by creating skills from experience."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.skills: Dict[str, Skill] = {}
        self.experiences: List[Experience] = []
        self.improvement_count = 0

    def record_experience(self, task: str, action: str, outcome: str, feedback: str):
        self.experiences.append(Experience(task=task, action=action, outcome=outcome, feedback=feedback))

    def create_skill(self, name: str, description: str, code: str) -> Skill:
        skill = Skill(name=name, description=description, code=code)
        self.skills[name] = skill
        self.improvement_count += 1
        logger.info(f"Agent {self.agent_id} created skill: {name}")
        return skill

    def use_skill(self, name: str, success: bool) -> Optional[Skill]:
        skill = self.skills.get(name)
        if not skill:
            return None
        skill.usage_count += 1
        total = skill.usage_count
        skill.success_rate = ((skill.success_rate * (total - 1)) + (1.0 if success else 0.0)) / total
        return skill

    def get_top_skills(self, n: int = 5) -> List[Skill]:
        return sorted(self.skills.values(), key=lambda s: s.success_rate, reverse=True)[:n]

    def learn_from_failures(self, threshold: float = 0.3) -> List[str]:
        """Analyze recent failures and suggest new skills to create."""
        recent = self.experiences[-20:] if len(self.experiences) > 20 else self.experiences
        failures = [e for e in recent if e.outcome == "failure"]
        suggestions = []
        if len(failures) > len(recent) * threshold:
            task_types = set(e.task.split(":")[0] if ":" in e.task else e.task for e in failures)
            for t in task_types:
                if t not in self.skills:
                    suggestions.append(f"Consider creating a '{t}' skill from {len(failures)} failure patterns")
        return suggestions
