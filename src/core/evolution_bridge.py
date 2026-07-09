"""
EvolutionBridge — Integrates all self-evolving modules into BH engine.

Wires together:
  1. SkillCrystallizer — crystallize trajectories into reusable skills
  2. SelfConsolidation — contrastive reflection + latent consolidation
  3. SwarmSkillsManager — multi-agent coordination engineering
  4. AgentContractManager — resource governance with circuit-breaking

This bridge connects to AgentLoop hooks so self-evolution happens
automatically during every agent execution cycle.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

from src.core.skill_crystallizer import SkillCrystallizer, ExecutionTrajectory, TrajectoryStep
from src.core.agent_contracts import AgentContractManager, AgentContract, ContractViolation

logger = logging.getLogger(__name__)


class EvolutionBridge:
    """
    Central integration point for all self-evolving subsystems.

    1. Hooks into AgentLoop:
       - pre_iteration: check contract, recall skills, reflect advice
       - post_iteration: record trajectory, crystallize if successful
       - on_tool_call: record cost to contract
       - on_error: record failure, trigger reflection

    2. Hooks into EcosystemOrchestrator:
       - sync: evolve swarm skills, consolidate memory
       - status: collect evolution stats

    3. Provides unified self-evolution lifecycle:
       execute -> record -> reflect -> consolidate -> crystallize -> evolve
    """

    def __init__(
        self,
        agent_id: str = "bh-agent",
        skill_crystallizer: Optional[SkillCrystallizer] = None,
        contract_manager: Optional[AgentContractManager] = None,
        swarm_skills: Any = None,
        self_consolidation: Any = None,
    ):
        self.agent_id = agent_id
        self._skill_crystallizer = skill_crystallizer or SkillCrystallizer()
        self._contract_manager = contract_manager or AgentContractManager()
        self._swarm_skills = swarm_skills
        self._self_consolidation = self_consolidation
        self._current_trajectory: Optional[ExecutionTrajectory] = None
        self._current_contract: Optional[AgentContract] = None
        self._evolution_count = 0

    # ── Agent Loop Hooks ─────────────────────────────────────────

    def create_pre_iteration_hook(self, task: str) -> callable:
        """Create a pre_iteration hook for AgentLoop."""
        self._current_trajectory = ExecutionTrajectory(task=task)

        # Create contract for this task
        self._current_contract = self._contract_manager.create_contract(
            agent_id=self.agent_id,
            cost_budget=0.5,
            token_budget=32000,
            max_duration=300.0,
        )

        async def pre_iteration_hook(iteration: int, messages: list) -> None:
            if not self._contract_manager.check_contract(self._current_contract.contract_id):
                logger.warning("Contract check failed at iteration %d", iteration)

            # Recall relevant skills
            if iteration == 1:
                skills = self._skill_crystallizer.recall(task)
                if skills:
                    logger.info("Recalled %d skills for task: %s", len(skills), task)

        return pre_iteration_hook

    def create_post_iteration_hook(self) -> callable:
        """Create a post_iteration hook for AgentLoop."""
        async def post_iteration_hook(iteration: int, response: str) -> None:
            if self._current_trajectory:
                self._current_trajectory.steps.append(TrajectoryStep(
                    action="llm_response",
                    input="",
                    output=response[:200],
                    duration=0.0,
                    success=True,
                ))

        return post_iteration_hook

    def create_on_tool_call_hook(self) -> callable:
        """Create an on_tool_call hook for AgentLoop."""
        async def on_tool_call_hook(tool_name: str, arguments: dict) -> None:
            if self._current_contract:
                self._contract_manager.record_cost(
                    self._current_contract.contract_id,
                    cost=0.001,
                    tokens=100,
                )

            if self._current_trajectory:
                self._current_trajectory.steps.append(TrajectoryStep(
                    action=tool_name,
                    input=str(arguments)[:200],
                    output="",
                    duration=0.0,
                    success=True,
                ))

        return on_tool_call_hook

    def create_on_error_hook(self) -> callable:
        """Create an on_error hook for AgentLoop."""
        async def on_error_hook(error: Exception) -> None:
            if self._current_trajectory:
                self._current_trajectory.steps.append(TrajectoryStep(
                    action="error",
                    input="",
                    output="",
                    duration=0.0,
                    success=False,
                    error=str(error)[:200],
                ))

            # Record failure in self-consolidation
            if self._self_consolidation:
                from src.memory.self_consolidation import Experience
                self._self_consolidation.record_experience(Experience(
                    task=self._current_trajectory.task if self._current_trajectory else "unknown",
                    action="error",
                    outcome="failure",
                    feedback=str(error)[:200],
                    success=False,
                ))

        return on_error_hook

    # ── Evolution Lifecycle ──────────────────────────────────────

    async def finish_task(self, task: str, success: bool, response: str) -> None:
        """Finalize a task execution — crystallize, reflect, consolidate."""
        if not self._current_trajectory:
            return

        self._current_trajectory.success = success
        self._current_trajectory.final_outcome = response[:200]

        # Complete contract
        if self._current_contract:
            self._contract_manager.complete_contract(
                self._current_contract.contract_id,
                result={"completed": success, "response": response[:200]},
            )

        # Crystallize successful trajectories into skills
        if success and self._current_trajectory.steps:
            skill = self._skill_crystallizer.crystallize(self._current_trajectory)
            if skill:
                logger.info("Crystallized skill: %s", skill.name)

        # Record trajectory for future learning
        self._skill_crystallizer.record_trajectory(self._current_trajectory)

        # Record in self-consolidation
        if self._self_consolidation:
            from src.memory.self_consolidation import Experience
            self._self_consolidation.record_experience(Experience(
                task=task,
                action="execute",
                outcome="success" if success else "failure",
                feedback=response[:200],
                success=success,
            ))

        self._current_trajectory = None
        self._current_contract = None

    async def evolve(self, force: bool = False) -> list[str]:
        """Run full evolution cycle across all subsystems."""
        actions: list[str] = []

        # Reflect on experiences
        if self._self_consolidation:
            insights = self._self_consolidation.reflect(force=force)
            if insights:
                actions.append(f"Reflected {len(insights)} new insights")
                for ins in insights:
                    logger.info("Insight: %s (confidence=%.2f)", ins.pattern, ins.confidence)

            consolidated = self._self_consolidation.consolidate(force=force)
            if consolidated:
                actions.append(f"Consolidated {len(consolidated)} latent memories")

        # Learn from failures
        failure_lessons = self._skill_crystallizer.learn_from_failures()
        if failure_lessons:
            actions.extend(failure_lessons)

        # Evolve swarm skills
        if self._swarm_skills and hasattr(self._swarm_skills, "evolve"):
            swarm_actions = self._swarm_skills.evolve(force=force)
            actions.extend(swarm_actions)

        self._evolution_count += 1
        if actions:
            logger.info("Evolution cycle #%d: %d actions", self._evolution_count, len(actions))

        return actions

    # ── Status & Stats ───────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        stats = {
            "evolution_count": self._evolution_count,
            "skill_crystallizer": self._skill_crystallizer.get_stats(),
            "contract_manager": self._contract_manager.get_stats(),
        }
        if self._self_consolidation:
            stats["self_consolidation"] = self._self_consolidation.get_stats()
        if self._swarm_skills and hasattr(self._swarm_skills, "get_stats"):
            stats["swarm_skills"] = self._swarm_skills.get_stats()
        return stats
