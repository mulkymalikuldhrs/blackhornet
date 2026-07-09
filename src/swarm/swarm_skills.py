"""
Swarm Skills — Portable self-evolving multi-agent coordination spec.
Inspired by "Swarm Skills: A Portable, Self-Evolving Multi-Agent System
Specification for Coordination Engineering" (arXiv:2605.10052).

Extends Anthropic Skills standard with multi-agent semantics:
  - Roles: agent role definitions with capabilities
  - Workflows: multi-step coordination patterns
  - Execution bounds: resource limits per coordination round
  - Self-evolution: automatic distillation of successful trajectories
    into new Swarm Skills + continuous patching based on E/U/F scores
"""
from __future__ import annotations

import json
import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class RoleType(str, Enum):
    PLANNER = "planner"
    RESEARCHER = "researcher"
    CODER = "coder"
    REVIEWER = "reviewer"
    ORCHESTRATOR = "orchestrator"
    ANALYST = "analyst"
    CRITIC = "critic"
    EXECUTOR = "executor"
    OBSERVER = "observer"
    CUSTOM = "custom"


@dataclass
class AgentRole:
    name: str
    role_type: RoleType = RoleType.CUSTOM
    system_prompt: str = ""
    capabilities: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    max_turns: int = 10
    temperature: float = 0.7


@dataclass
class WorkflowStep:
    step_id: int = 0
    role: str = ""
    action: str = ""
    input_template: str = ""
    expected_output: str = ""
    timeout: float = 60.0
    retry_count: int = 0
    depends_on: list[int] = field(default_factory=list)


@dataclass
class ExecutionBound:
    max_tokens: int = 32000
    max_cost: float = 0.5
    max_duration: float = 300.0
    max_agent_calls: int = 50
    max_rounds: int = 5


@dataclass
class SwarmSkillScore:
    effectiveness: float = 0.0
    utilization: float = 0.0
    freshness: float = 0.0

    @property
    def composite(self) -> float:
        return (self.effectiveness * 0.5 + self.utilization * 0.3 + self.freshness * 0.2)


@dataclass
class SwarmSkill:
    name: str
    description: str
    version: str = "1.0.0"
    roles: list[AgentRole] = field(default_factory=list)
    workflow: list[WorkflowStep] = field(default_factory=list)
    bounds: ExecutionBound = field(default_factory=ExecutionBound)
    tags: list[str] = field(default_factory=list)
    score: SwarmSkillScore = field(default_factory=SwarmSkillScore)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    execution_count: int = 0
    success_count: int = 0
    source_trajectories: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return self.success_count / max(self.execution_count, 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "roles": [
                {"name": r.name, "role_type": r.role_type.value, "capabilities": r.capabilities}
                for r in self.roles
            ],
            "workflow": [vars(s) for s in self.workflow],
            "bounds": vars(self.bounds),
            "tags": self.tags,
            "score": {
                "effectiveness": self.score.effectiveness,
                "utilization": self.score.utilization,
                "freshness": self.score.freshness,
                "composite": self.score.composite,
            },
            "execution_count": self.execution_count,
            "success_rate": self.success_rate,
        }


@dataclass
class CoordinationRecord:
    skill_name: str
    roles_used: list[str]
    steps_completed: int
    total_steps: int
    duration: float
    success: bool
    token_cost: float
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class SwarmSkillsManager:
    """
    Portable, self-evolving multi-agent coordination specification.

    Manages SwarmSkills as first-class distributable assets:
      - Roles define WHO participates
      - Workflows define WHAT they do
      - Bounds define CONSTRAINTS
      - Self-evolution automatically improves based on E/U/F scores
    """

    def __init__(
        self,
        auto_evolve: bool = True,
        evolution_interval: float = 3600.0,
        min_records_for_evolution: int = 10,
    ):
        self.auto_evolve = auto_evolve
        self.evolution_interval = evolution_interval
        self.min_records_for_evolution = min_records_for_evolution
        self._skills: dict[str, SwarmSkill] = {}
        self._records: list[CoordinationRecord] = []
        self._last_evolution: float = 0.0

    # ── Skill Management ─────────────────────────────────────────

    def register_skill(self, skill: SwarmSkill) -> None:
        """Register a swarm skill."""
        self._skills[skill.name] = skill
        logger.info("Swarm skill registered: %s v%s", skill.name, skill.version)

    def get_skill(self, name: str) -> Optional[SwarmSkill]:
        return self._skills.get(name)

    def list_skills(self, tag: Optional[str] = None) -> list[SwarmSkill]:
        if tag:
            return [s for s in self._skills.values() if tag in s.tags]
        return list(self._skills.values())

    # ── Coordination Recording ───────────────────────────────────

    def record_coordination(self, record: CoordinationRecord) -> None:
        """Record a coordination execution for evolution."""
        self._records.append(record)
        if len(self._records) > 10000:
            self._records = self._records[-5000:]

        skill = self._skills.get(record.skill_name)
        if skill:
            skill.execution_count += 1
            if record.success:
                skill.success_count += 1
            skill.updated_at = time.time()

    def record_execution(
        self,
        skill_name: str,
        roles_used: list[str],
        steps_completed: int,
        total_steps: int,
        duration: float,
        success: bool,
        token_cost: float = 0.0,
        error: Optional[str] = None,
    ) -> None:
        """Convenience method to record a coordination execution."""
        self.record_coordination(CoordinationRecord(
            skill_name=skill_name,
            roles_used=roles_used,
            steps_completed=steps_completed,
            total_steps=total_steps,
            duration=duration,
            success=success,
            token_cost=token_cost,
            error=error,
        ))

    # ── Self-Evolution ───────────────────────────────────────────

    def evolve(self, force: bool = False) -> list[str]:
        """
        Self-evolution loop: automatically improve swarm skills based
        on E/U/F scoring (Effectiveness, Utilization, Freshness).

        Steps:
          1. Score all skills on E/U/F dimensions
          2. Patch low-scoring skills (reduce steps, adjust roles)
          3. Create new skills from successful novel trajectories
          4. Archive skills with persistently low scores
        """
        if not self.auto_evolve and not force:
            return []

        if time.time() - self._last_evolution < self.evolution_interval and not force:
            return []

        self._last_evolution = time.time()
        actions: list[str] = []

        for skill in self._skills.values():
            self._update_scores(skill)
            action = self._evolve_skill(skill)
            if action:
                actions.append(action)

        # Create new skills from successful novel patterns
        new_skills = self._discover_new_skills()
        for ns in new_skills:
            self.register_skill(ns)
            actions.append(f"New swarm skill discovered: {ns.name}")

        logger.info("Swarm evolution: %d actions taken", len(actions))
        return actions

    def _update_scores(self, skill: SwarmSkill) -> None:
        """Recalculate E/U/F scores for a skill."""
        skill_records = [r for r in self._records if r.skill_name == skill.name]
        if not skill_records:
            return

        recent = skill_records[-50:] if len(skill_records) > 50 else skill_records

        # Effectiveness: success rate in recent executions
        if recent:
            skill.score.effectiveness = sum(1 for r in recent if r.success) / len(recent)

        # Utilization: how often this skill is used vs total
        total_execs = sum(1 for r in self._records if r.skill_name == skill.name)
        all_execs = len(self._records)
        skill.score.utilization = total_execs / max(all_execs, 1)

        # Freshness: how recently the skill was updated/used
        age_hours = (time.time() - skill.updated_at) / 3600
        skill.score.freshness = math.exp(-age_hours / 168)

    def _evolve_skill(self, skill: SwarmSkill) -> Optional[str]:
        """Apply evolution strategies to a single skill."""
        score = skill.score.composite

        if score < 0.3 and skill.execution_count > 5:
            # Low performer: reduce complexity
            if len(skill.workflow) > 3:
                skill.workflow = skill.workflow[:3]
                skill.version = self._bump_version(skill.version)
                return f"Patched {skill.name}: reduced workflow to {len(skill.workflow)} steps (score={score:.2f})"

        elif score < 0.5 and skill.execution_count > 3:
            # Moderate performer: adjust roles
            if len(skill.roles) > 2:
                skill.roles = skill.roles[:2]
                skill.version = self._bump_version(skill.version)
                return f"Optimized {skill.name}: reduced to {len(skill.roles)} roles (score={score:.2f})"

        elif score > 0.8 and skill.execution_count > 10:
            # High performer: increase bounds for more capacity
            skill.bounds.max_agent_calls = min(skill.bounds.max_agent_calls + 10, 200)
            skill.version = self._bump_version(skill.version)
            return f"Expanded {skill.name}: increased capacity (score={score:.2f})"

        return None

    def _discover_new_skills(self) -> list[SwarmSkill]:
        """Discover potential new skills from successful coordination records."""
        new_skills: list[SwarmSkill] = []

        successful = [r for r in self._records if r.success and r.skill_name not in self._skills]
        if len(successful) < self.min_records_for_evolution:
            return new_skills

        patterns: dict[str, list[CoordinationRecord]] = {}
        for r in successful:
            pattern_key = "+".join(sorted(r.roles_used))
            if pattern_key not in patterns:
                patterns[pattern_key] = []
            patterns[pattern_key].append(r)

        for pattern, records in patterns.items():
            if len(records) >= 3:
                skill_name = f"discovered:{pattern}"
                if skill_name not in self._skills:
                    skill = SwarmSkill(
                        name=skill_name,
                        description=f"Auto-discovered coordination: {pattern}",
                        roles=[
                            AgentRole(name=role) for role in pattern.split("+")
                        ],
                        workflow=[
                            WorkflowStep(step_id=i, role=role, action="process")
                            for i, role in enumerate(pattern.split("+"))
                        ],
                        execution_count=len(records),
                        success_count=len([r for r in records if r.success]),
                        source_trajectories=[str(r.timestamp) for r in records],
                    )
                    new_skills.append(skill)

        return new_skills

    # ── Coordination Execution ───────────────────────────────────

    def create_coordination_plan(
        self,
        task: str,
        required_roles: Optional[list[RoleType]] = None,
    ) -> Optional[SwarmSkill]:
        """
        Create or retrieve an optimal coordination plan for a task.
        Matches against existing skills, falls back to dynamic creation.
        """
        # Find best matching skill
        best_score = 0.0
        best_skill: Optional[SwarmSkill] = None

        for skill in self._skills.values():
            if skill.score.composite < 0.3:
                continue
            task_words = set(task.lower().split())
            skill_words = set(skill.description.lower().split())
            overlap = len(task_words & skill_words) / max(len(task_words | skill_words), 1)
            weighted = overlap * skill.score.composite
            if weighted > best_score:
                best_score = weighted
                best_skill = skill

        if best_skill and best_score > 0.3:
            return best_skill

        # Create new skill dynamically
        if not required_roles:
            required_roles = [RoleType.PLANNER, RoleType.EXECUTOR, RoleType.REVIEWER]

        dynamic_skill = SwarmSkill(
            name=f"dynamic:{hash(task) % 100000:05d}",
            description=f"Dynamic coordination for: {task[:100]}",
            roles=[AgentRole(name=r.value, role_type=r) for r in required_roles],
            workflow=[
                WorkflowStep(step_id=0, role=required_roles[0].value, action="plan"),
                WorkflowStep(step_id=1, role=required_roles[1].value, action="execute", depends_on=[0]),
            ],
            tags=["dynamic"],
        )
        return dynamic_skill

    # ── Helpers ──────────────────────────────────────────────────

    def _bump_version(self, version: str) -> str:
        parts = version.split(".")
        if len(parts) == 3:
            parts[2] = str(int(parts[2]) + 1)
        return ".".join(parts)

    def to_markdown(self, skill_name: str) -> str:
        """Export a swarm skill as markdown (SKILL.md compatible)."""
        skill = self._skills.get(skill_name)
        if not skill:
            return ""

        lines = [
            f"# {skill.name}",
            f"**Version:** {skill.version}",
            f"**Description:** {skill.description}",
            f"**Score:** E={skill.score.effectiveness:.2f} U={skill.score.utilization:.2f} F={skill.score.freshness:.2f}",
            "",
            "## Roles",
        ]
        for role in skill.roles:
            lines.append(f"- `{role.name}` ({role.role_type.value}): {', '.join(role.capabilities)}")

        lines.extend(["", "## Workflow"])
        for step in skill.workflow:
            deps = f" (after: {step.depends_on})" if step.depends_on else ""
            lines.append(f"  {step.step_id}. {step.role} → {step.action}{deps}")

        lines.extend(["", "## Bounds"])
        lines.append(f"- Max tokens: {skill.bounds.max_tokens}")
        lines.append(f"- Max cost: ${skill.bounds.max_cost}")
        lines.append(f"- Max duration: {skill.bounds.max_duration}s")
        lines.append(f"- Max agent calls: {skill.bounds.max_agent_calls}")

        return "\n".join(lines)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_skills": len(self._skills),
            "total_records": len(self._records),
            "last_evolution": self._last_evolution,
            "auto_evolve": self.auto_evolve,
            "avg_success_rate": (
                sum(s.success_rate for s in self._skills.values()) / max(len(self._skills), 1)
            ),
            "avg_composite_score": (
                sum(s.score.composite for s in self._skills.values()) / max(len(self._skills), 1)
            ),
        }
