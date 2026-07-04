"""BlackHornet Ω — Autonomous AGI Engine.

Lord Omega v5.0 founding pillars embedded into BlackHornet:
  - Constitution (AI-Engineering-OS)
  - Self-Confidence System (SCS)
  - Multi-Perspective Council (15 personas)
  - Predictive Superconsciousness (L9 Oracle)
  - Second Brain (L0 Permanent Memory)
  - Genome Evolution/Mutation
  - 100/100/100 Scoring
  - Ecosystem Sync Pipeline
"""

from __future__ import annotations

import time
from typing import Any, Optional

from src.config.logging_config import get_logger

logger = get_logger("omega")


class OmegaEngine:
    """Lord Omega v5.0 engine — autonomous loop, boot sequence, self-evolution."""

    def __init__(self) -> None:
        self._running = False
        self._booted = False
        self._started_at: Optional[float] = None
        self._loop_count = 0

    def boot(self) -> dict:
        """Boot sequence — auto-path, auto-recall, auto-score, auto-evolve."""
        from src.omega.constitution import Constitution
        from src.omega.brain import SecondBrain
        from src.omega.score import ProjectScorer
        from src.omega.scs import SelfConfidenceSystem

        self._started_at = time.time()
        constitution = Constitution()
        brain = SecondBrain()
        scorer = ProjectScorer()
        scs = SelfConfidenceSystem()

        boot_report = {
            "timestamp": time.time(),
            "omega_version": "5.0",
            "constitution": constitution.validate(),
            "brain_recall": brain.recall_recent(limit=5),
            "scores": scorer.current(),
            "scs": scs.status(),
        }
        self._booted = True
        logger.info("omega_boot_complete scs=%s", boot_report.get("scs", {}).get("score"))
        return boot_report

    def _run_agent_cycle(self, objective: str) -> dict:
        """Plan with BabyAGI, execute with ORCA fan-out."""
        from src.agents.babyagi import BabyAGI
        from src.agents.orca import OrcaOrchestrator

        baby = BabyAGI(objective)
        baby.add_objective(objective)
        planned = baby.run_loop(max_steps=5)
        task_descriptions = [t.description for t in planned]

        orca = OrcaOrchestrator()
        fan_results = orca.fan_out(objective, count=min(len(task_descriptions), 3))

        return {
            "objective": objective,
            "tasks_planned": len(planned),
            "tasks": task_descriptions[:3],
            "execution_results": fan_results,
        }

    def main_loop(self) -> dict:
        """Autonomous loop iteration: SCAN → SCORE → PRIORITIZE → PLAN → ACT → VERIFY → LOG → SAVE → SYNC."""
        from src.omega.brain import SecondBrain
        from src.omega.score import ProjectScorer
        from src.omega.council import Council
        from src.omega.sync import EcosystemSync

        brain = SecondBrain()
        scorer = ProjectScorer()
        council = Council()
        sync = EcosystemSync()

        self._loop_count += 1
        loop_report: dict[str, Any] = {"loop": self._loop_count, "timestamp": time.time()}

        try:
            loop_report["scan"] = brain.scan_ecosystem()
            loop_report["score"] = scorer.evaluate_all()
            loop_report["priority"] = scorer.priority_queue()
            council_result = council.convene(
                context=f"Loop #{self._loop_count}: advance worst project",
                personas=["CTO", "Quality Dictator", "Skeptic"],
            )
            loop_report["council"] = council_result

            priority_q = loop_report.get("priority", [])
            target = priority_q[0]["name"] if priority_q else "blackhornet"
            loop_report["agent_cycle"] = self._run_agent_cycle(f"Advance {target} — close score gaps")

            sync.run()
            brain.auto_capture("session", f"Loop #{self._loop_count} completed — agents focused on {target}")
        except Exception as e:
            logger.error("omega_loop_error loop=%d err=%s", self._loop_count, e)

        return loop_report

    def start(self) -> bool:
        if self._running:
            return True
        self._running = True
        boot_report = self.boot()
        logger.info("omega_started boot=%s", boot_report)
        return True

    def stop(self) -> None:
        self._running = False
        logger.info("omega_stopped loops=%d uptime=%.1fs", self._loop_count, (time.time() - (self._started_at or time.time())))

    @property
    def is_running(self) -> bool:
        return self._running

    def stats(self) -> dict:
        return {
            "booted": self._booted,
            "running": self._running,
            "loop_count": self._loop_count,
            "uptime_seconds": (time.time() - (self._started_at or time.time())) if self._started_at else 0,
            "started_at": self._started_at,
        }
