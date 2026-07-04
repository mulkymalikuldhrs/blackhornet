"""
Skill Crystallizer — Self-evolving skill system for BlackHornet agents.
Inspired by GenericAgent (arXiv:2604.17091), EvolveR (arXiv:2510.16079),
and Recursive Knowledge Crystallization (Tanaike, 2026).

Mechanism:
  1. Agent executes a novel task -> trajectory is recorded
  2. Trajectory is distilled into a reusable Skill (markdown + code)
  3. Skill is stored in local filesystem + memory
  4. On similar future tasks, skill is recalled and adapted
  5. Skills self-optimize through usage tracking and failure analysis
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


SKILLS_DIR = Path(os.environ.get("BH_SKILLS_DIR", "data/skills"))


@dataclass
class Skill:
    name: str
    description: str
    code: str
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    usage_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    version: int = 1
    source_trajectory: str = ""
    confidence: float = 0.0
    min_similarity: float = 0.6

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        return self.success_count / max(total, 1)

    @property
    def skill_hash(self) -> str:
        return hashlib.md5(self.name.encode()).hexdigest()[:12]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "code": self.code,
            "category": self.category,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "version": self.version,
            "confidence": self.confidence,
            "success_rate": self.success_rate,
            "skill_hash": self.skill_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Skill:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class TrajectoryStep:
    action: str
    input: str
    output: str
    duration: float
    success: bool
    error: Optional[str] = None


@dataclass
class ExecutionTrajectory:
    task: str
    steps: list[TrajectoryStep] = field(default_factory=list)
    final_outcome: str = ""
    total_duration: float = 0.0
    success: bool = False
    timestamp: float = field(default_factory=time.time)


class SkillCrystallizer:
    """
    Self-evolving skill system that crystallizes execution trajectories
    into reusable skills. Core pattern from GenericAgent + EvolveR.

    The agent performs a task -> trajectory is recorded ->
    trajectory is distilled into a Skill -> stored + indexed ->
    recalled on similar future tasks.
    """

    def __init__(
        self,
        skills_dir: str | Path = SKILLS_DIR,
        auto_save: bool = True,
        min_trajectory_success: float = 0.7,
    ):
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.auto_save = auto_save
        self.min_trajectory_success = min_trajectory_success
        self._skills: dict[str, Skill] = {}
        self._trajectories: list[ExecutionTrajectory] = []
        self._load_all()

    # ── Skill Lifecycle ──────────────────────────────────────────

    def crystallize(
        self,
        trajectory: ExecutionTrajectory,
        name: Optional[str] = None,
        category: str = "general",
        tags: Optional[list[str]] = None,
    ) -> Optional[Skill]:
        """
        Crystallize an execution trajectory into a reusable Skill.

        Steps:
          1. Validate trajectory quality
          2. Distill trajectory into abstract code + description
          3. Create or update Skill
          4. Persist to filesystem
        """
        if not trajectory.steps:
            logger.warning("Cannot crystallize: empty trajectory")
            return None

        success_ratio = sum(1 for s in trajectory.steps if s.success) / len(trajectory.steps)
        if success_ratio < self.min_trajectory_success:
            logger.info(
                "Trajectory quality too low for crystallization: %.2f < %.2f",
                success_ratio, self.min_trajectory_success,
            )
            return None

        skill_name = name or self._generate_skill_name(trajectory.task)
        description = self._distill_description(trajectory)
        code = self._distill_code(trajectory)

        if skill_name in self._skills:
            existing = self._skills[skill_name]
            existing.code = self._merge_code(existing.code, code)
            existing.description = description
            existing.updated_at = time.time()
            existing.version += 1
            existing.tags = list(set(existing.tags + (tags or [])))
            skill = existing
            logger.info("Skill updated: %s (v%d)", skill_name, existing.version)
        else:
            skill = Skill(
                name=skill_name,
                description=description,
                code=code,
                category=category,
                tags=tags or [],
                source_trajectory=trajectory.task,
                confidence=success_ratio,
            )
            self._skills[skill_name] = skill
            logger.info("Skill created: %s (confidence=%.2f)", skill_name, success_ratio)

        if self.auto_save:
            self._save_skill(skill)

        return skill

    def recall(self, task: str, min_confidence: float = 0.3) -> list[Skill]:
        """
        Recall relevant skills for a given task.
        Uses keyword matching + confidence threshold.

        Returns skills sorted by relevance (confidence * success_rate).
        """
        task_lower = task.lower()
        task_words = set(task_lower.split())

        scored: list[tuple[float, Skill]] = []
        for skill in self._skills.values():
            if skill.confidence < min_confidence:
                continue

            score = 0.0
            skill_text = f"{skill.name} {skill.description}".lower()

            for word in task_words:
                if word in skill_text:
                    score += 1.0
                if word in skill.name.lower():
                    score += 2.0
                if word in (t.lower() for t in skill.tags):
                    score += 1.5

            if score > 0:
                relevance = (score / max(len(task_words), 1)) * skill.success_rate
                scored.append((relevance, skill))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored]

    def record_usage(self, skill_name: str, success: bool) -> None:
        """Record a usage attempt for a skill."""
        skill = self._skills.get(skill_name)
        if not skill:
            return
        skill.usage_count += 1
        if success:
            skill.success_count += 1
        else:
            skill.fail_count += 1
        skill.confidence = skill.success_rate
        skill.updated_at = time.time()
        if self.auto_save:
            self._save_skill(skill)

    def record_trajectory(self, trajectory: ExecutionTrajectory) -> None:
        """Record an execution trajectory for future crystallization."""
        self._trajectories.append(trajectory)
        if len(self._trajectories) > 1000:
            self._trajectories = self._trajectories[-500:]

    def learn_from_failures(self) -> list[str]:
        """Analyze recent failures and suggest skill improvements."""
        recent = self._trajectories[-50:] if len(self._trajectories) > 50 else self._trajectories
        failures = [t for t in recent if not t.success]
        if not failures:
            return []

        suggestions = []
        failure_tasks = set(t.task for t in failures)
        for task in failure_tasks:
            matched = self.recall(task, min_confidence=0.0)
            for skill in matched:
                if skill.fail_count > skill.success_count:
                    suggestions.append(
                        f"Skill '{skill.name}' needs revision: "
                        f"{skill.fail_count} failures vs {skill.success_count} successes"
                    )
        return suggestions

    # ── Persistence ──────────────────────────────────────────────

    def _save_skill(self, skill: Skill) -> None:
        """Save a skill as a markdown + json file pair."""
        skill_dir = self.skills_dir / skill.category
        skill_dir.mkdir(parents=True, exist_ok=True)

        md_path = skill_dir / f"{skill.skill_hash}.md"
        json_path = skill_dir / f"{skill.skill_hash}.json"

        md_content = self._skill_to_markdown(skill)
        md_path.write_text(md_content)

        json_path.write_text(json.dumps(skill.to_dict(), indent=2, default=str))

    def _load_all(self) -> None:
        """Load all skills from the skills directory."""
        if not self.skills_dir.exists():
            return
        for json_path in self.skills_dir.rglob("*.json"):
            try:
                data = json.loads(json_path.read_text())
                skill = Skill.from_dict(data)
                self._skills[skill.name] = skill
            except Exception as e:
                logger.warning("Failed to load skill %s: %s", json_path, e)
        logger.info("Loaded %d skills from %s", len(self._skills), self.skills_dir)

    # ── Helpers ──────────────────────────────────────────────────

    def _generate_skill_name(self, task: str) -> str:
        """Generate a skill name from task description."""
        words = task.lower().split()[:6]
        return "_".join(w for w in words if w.isalpha())[:64]

    def _distill_description(self, trajectory: ExecutionTrajectory) -> str:
        """Distill trajectory into a concise description."""
        steps_desc = []
        for s in trajectory.steps[:5]:
            status = "✓" if s.success else "✗"
            steps_desc.append(f"{status} {s.action}: {s.input[:100]}")
        return "\n".join(steps_desc)

    def _distill_code(self, trajectory: ExecutionTrajectory) -> str:
        """Extract executable code pattern from trajectory."""
        code_parts = []
        for step in trajectory.steps:
            if step.action in ("code_run", "file_write", "execute") and step.success:
                code_parts.append(f"# Step: {step.action}\n{step.output[:500]}")
        return "\n\n".join(code_parts)

    def _merge_code(self, existing: str, new: str) -> str:
        """Merge new code into existing skill code."""
        if new not in existing:
            return f"{existing}\n\n# --- merged ---\n\n{new}"
        return existing

    def _skill_to_markdown(self, skill: Skill) -> str:
        """Convert skill to markdown format (compatible with SKILL.md spec)."""
        return f"""# {skill.name}

**Description:** {skill.description}
**Category:** {skill.category}
**Version:** {skill.version}
**Confidence:** {skill.confidence:.2f}
**Success Rate:** {skill.success_rate:.2f}
**Usage:** {skill.usage_count} times
**Tags:** {', '.join(skill.tags)}

## Code

```python
{skill.code}
```

## Metadata

- Created: {time.ctime(skill.created_at)}
- Updated: {time.ctime(skill.updated_at)}
- Source: {skill.source_trajectory}
"""

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_skills": len(self._skills),
            "total_trajectories": len(self._trajectories),
            "categories": len(set(s.category for s in self._skills.values())),
            "avg_confidence": sum(s.confidence for s in self._skills.values()) / max(len(self._skills), 1),
            "avg_success_rate": sum(s.success_rate for s in self._skills.values()) / max(len(self._skills), 1),
        }

    def get_top_skills(self, n: int = 10) -> list[Skill]:
        return sorted(self._skills.values(), key=lambda s: s.confidence, reverse=True)[:n]

    def get_skills_by_category(self, category: str) -> list[Skill]:
        return [s for s in self._skills.values() if s.category == category]
