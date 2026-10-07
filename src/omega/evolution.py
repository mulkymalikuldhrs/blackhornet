"""Evolution — self-improvement through mutation, fitness tracking, and capability growth.

Separate from Genome (static traits). Evolution is the dynamic process:
  - Tracks fitness trends across sessions
  - Identifies weak dimensions and targets them for mutation
  - Orchestrates capability upgrades from research sources
  - Logs evolution history for audit
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class EvolutionEvent:
    timestamp: float
    event_type: str
    dimension: str
    description: str
    fitness_before: float
    fitness_after: float
    success: bool


class EvolutionEngine:
    """Self-improvement engine — tracks fitness, triggers mutations, grows capabilities."""

    EVOLUTION_PATH: str = "data/omega/evolution.json"

    def __init__(self) -> None:
        self._history: list[EvolutionEvent] = []
        self._load()

    def _load(self) -> None:
        path = self._resolve_path()
        if os.path.isfile(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                self._history = [EvolutionEvent(**e) for e in data.get("history", [])]
            except Exception:
                pass

    def _save(self) -> None:
        path = self._resolve_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump({"history": [asdict(e) for e in self._history[-200:]]}, f, indent=2)

    def _resolve_path(self) -> str:
        base = os.environ.get("DHAHERLABS") or os.path.join(os.path.expanduser("~"), "dhaherlabs")
        return os.path.join(base, self.EVOLUTION_PATH)

    def record(self, event_type: str, dimension: str, description: str, fitness_before: float, fitness_after: float, success: bool = True) -> EvolutionEvent:
        event = EvolutionEvent(
            timestamp=time.time(),
            event_type=event_type,
            dimension=dimension,
            description=description,
            fitness_before=fitness_before,
            fitness_after=fitness_after,
            success=success,
        )
        self._history.append(event)
        self._save()
        return event

    def fitness_trend(self, window: int = 10) -> dict:
        recent = self._history[-window:]
        if not recent:
            return {"trend": "stable", "avg_fitness": 0.85, "direction": 0}
        avg_before = sum(e.fitness_before for e in recent) / len(recent)
        avg_after = sum(e.fitness_after for e in recent) / len(recent)
        direction = avg_after - avg_before
        trend = "improving" if direction > 0.02 else "declining" if direction < -0.02 else "stable"
        return {"trend": trend, "avg_fitness_before": round(avg_before, 3), "avg_fitness_after": round(avg_after, 3), "direction": round(direction, 3)}

    def weak_dimensions(self) -> list[dict]:
        dims = {}
        for e in self._history:
            if e.event_type == "mutation":
                d = dims.setdefault(e.dimension, {"count": 0, "successes": 0, "failures": 0})
                d["count"] += 1
                if e.success:
                    d["successes"] += 1
                else:
                    d["failures"] += 1
        return [
            {"dimension": d, "count": v["count"], "success_rate": round(v["successes"] / max(v["count"], 1) * 100, 1)}
            for d, v in sorted(dims.items(), key=lambda x: x[1]["successes"] / max(x[1]["count"], 1))
        ]

    def evolve(self, current_fitness: float, scs_score: float, project_avg: float) -> dict:
        target_fitness = (scs_score + project_avg / 100) / 2
        needs_evolution = current_fitness < 0.7 or target_fitness > current_fitness * 1.1
        result = {
            "current_fitness": current_fitness,
            "target_fitness": round(target_fitness, 3),
            "needs_evolution": needs_evolution,
            "trend": self.fitness_trend(),
            "weak_dimensions": self.weak_dimensions(),
            "timestamp": time.time(),
        }
        if needs_evolution:
            from src.omega.genome import GenomeEngine
            genome = GenomeEngine()
            genome.evaluate_fitness(scs_score, current_fitness, project_avg)
            mutation = genome.mutate()
            result["mutation"] = mutation
            self.record("evolution", "genome", f"Fitness {current_fitness} → target {target_fitness}", current_fitness, target_fitness, mutation is not None)
        return result

    def history_summary(self, limit: int = 20) -> list[dict]:
        return [{"timestamp": e.timestamp, "type": e.event_type, "dimension": e.dimension, "description": e.description[:100], "success": e.success} for e in self._history[-limit:]]
