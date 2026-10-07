"""Genome evolution/mutation — self-improvable genome for BlackHornet."""

from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Genome:
    version: str = "1.0.0"
    mutation_rate: float = 0.05
    fitness: float = 0.85
    traits: dict = field(default_factory=lambda: {
        "scs_weight": {"prediction_accuracy": 0.4, "calibration": 0.3, "success_rate": 0.2, "self_correction": 0.1},
        "priority_formula": {"gap_weight": 1.0, "size_weight": 0.3, "impact_weight": 0.5, "dependency_weight": 0.2},
        "max_retries": 3,
        "council_min_personas": 3,
        "confidence_threshold": 0.7,
        "overclaim_penalty": 0.15,
        "learning_rate": 0.05,
    })
    mutations: list[dict] = field(default_factory=list)
    evolved_at: Optional[float] = None


class GenomeEngine:
    """Genome evolution — mutate traits when fitness is low."""

    GENOME_PATH: str = "data/omega/genome.json"

    def __init__(self) -> None:
        self.genome = Genome()
        self._load()

    def _load(self) -> None:
        path = self._resolve_path()
        if os.path.isfile(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                self.genome = Genome(**data)
            except Exception:
                pass

    def _save(self) -> None:
        path = self._resolve_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(asdict(self.genome), f, indent=2)

    def _resolve_path(self) -> str:
        base = os.environ.get("DHAHERLABS") or os.path.join(os.path.expanduser("~"), "dhaherlabs")
        return os.path.join(base, self.GENOME_PATH)

    def evaluate_fitness(self, scs_score: float, success_rate: float, project_avg: float) -> float:
        fitness = (project_avg / 100) * 0.4 + success_rate * 0.3 + scs_score * 0.3
        self.genome.fitness = round(fitness, 3)
        self._save()
        return self.genome.fitness

    def mutate(self) -> Optional[dict]:
        if self.genome.fitness >= 0.7:
            return None

        old_traits = dict(self.genome.traits)
        for key in self.genome.traits:
            if isinstance(self.genome.traits[key], dict):
                for subkey in self.genome.traits[key]:
                    if random.random() < self.genome.mutation_rate:
                        delta = random.uniform(-0.05, 0.05)
                        self.genome.traits[key][subkey] = round(max(0, min(1, self.genome.traits[key][subkey] + delta)), 3)
            elif isinstance(self.genome.traits[key], (int, float)):
                if random.random() < self.genome.mutation_rate:
                    delta = random.uniform(-0.1, 0.1)
                    self.genome.traits[key] = round(max(0.1, min(5, self.genome.traits[key] + delta)), 3)

        mutation = {
            "timestamp": time.time(),
            "old_traits": old_traits,
            "new_traits": dict(self.genome.traits),
            "fitness_before": self.genome.fitness,
        }
        self.genome.mutations.append(mutation)
        self.genome.evolved_at = time.time()
        minor = int(self.genome.version.split(".")[2]) + 1
        self.genome.version = f"1.0.{minor}"
        self._save()
        return mutation

    def status(self) -> dict:
        return {
            "version": self.genome.version,
            "fitness": self.genome.fitness,
            "trait_count": len(self.genome.traits),
            "mutation_count": len(self.genome.mutations),
            "last_evolved": self.genome.evolved_at,
            "needs_mutation": self.genome.fitness < 0.7,
        }
