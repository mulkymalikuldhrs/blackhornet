"""
Swarm Orchestrator
Integrates PSO ring topology, ABC role-switching, and stigmergic communication
into a unified cyberbee swarm system for BH agents.
"""
from typing import List, Dict, Optional, Any, Callable
try:
    import numpy as np
except ImportError:
    from ._numpy_shim import np
import logging

from .pso_swarm import RingPSOSwarm, SwarmState, Particle, Topology
from .abc_swarm import ABCSwarm, BeeRole, FoodSource
from .stigmergy import PheromoneField, PheromoneType, Pheromone

logger = logging.getLogger(__name__)

class SwarmOrchestrator:
    """
    Orchestrates the cyberbee swarm combining PSO + ABC + Stigmergy.

    How they work together:
    1. PSO provides rapid convergence via velocity-based optimization
    2. ABC provides diversity through role-switching and scout exploration
    3. Stigmergy enables indirect coordination without direct messaging
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        self.pso = RingPSOSwarm(
            n_particles=self.config.get("pso_particles", 20),
            dimensions=self.config.get("dimensions", 5),
            topology=Topology(self.config.get("topology", "ring")),
            w_start=self.config.get("w_start", 0.9),
            w_end=self.config.get("w_end", 0.4),
            c1=self.config.get("c1", 2.0),
            c2=self.config.get("c2", 2.0),
        )

        self.abc = ABCSwarm(
            n_employed=self.config.get("abc_employed", 15),
            n_onlookers=self.config.get("abc_onlookers", 15),
            n_scouts=self.config.get("abc_scouts", 5),
            dimensions=self.config.get("dimensions", 5),
            max_trials=self.config.get("abc_max_trials", 40),
        )

        self.pheromone_field = PheromoneField(
            evaporation_rate=self.config.get("evaporation_rate", 0.05),
            diffusion_rate=self.config.get("diffusion_rate", 0.1),
            dimensions=self.config.get("dimensions", 5),
        )

        self.initialized = False
        self.generation = 0

    def initialize(self, fitness_fn: Callable[[np.ndarray], float],
                   initial_positions: Optional[List[np.ndarray]] = None):
        """Initialize both swarms"""
        self.pso.initialize(fitness_fn, initial_positions)
        self.abc.initialize(fitness_fn, initial_positions)
        self.initialized = True
        logger.info("Swarm orchestrator initialized: PSO+ABC+Stigmergy")

    def step(self):
        """Execute one combined swarm iteration"""
        if not self.initialized:
            raise RuntimeError("Orchestrator not initialized")

        pso_state = self.pso.step()
        self.abc.step()

        if pso_state and pso_state.global_best_fitness > -1e6:
            self.pheromone_field.deposit(
                position=tuple(pso_state.global_best),
                type=PheromoneType.EXPLOIT,
                intensity=min(1.0, max(0.1, abs(pso_state.global_best_fitness) / 10.0)),
                depositor_id="pso_swarm",
                metadata={"fitness": float(pso_state.global_best_fitness), "generation": self.generation},
            )

        if self.abc.best_solution is not None:
            self.pheromone_field.deposit(
                position=tuple(self.abc.best_solution),
                type=PheromoneType.INFO,
                intensity=min(1.0, max(0.1, abs(self.abc.best_fitness) / 10.0)),
                depositor_id="abc_swarm",
                metadata={"fitness": float(self.abc.best_fitness), "generation": self.generation},
            )

        self.pheromone_field.evaporate(dt=1.0)
        self.pheromone_field.diffuse()

        self.generation += 1

    def sense_pheromones(self, position: np.ndarray) -> Dict[str, float]:
        """Sense pheromone field at a position"""
        pos = tuple(position)
        return {
            "exploit": self.pheromone_field.sense_strength(pos, PheromoneType.EXPLOIT),
            "explore": self.pheromone_field.sense_strength(pos, PheromoneType.EXPLORE),
            "danger": self.pheromone_field.sense_strength(pos, PheromoneType.DANGER),
            "total": self.pheromone_field.sense_strength(pos),
        }

    def get_best_solution(self) -> Dict[str, Any]:
        """Get the best solution from both swarms"""
        pso_best = None
        abc_best = None

        if self.pso.state:
            pso_best = {
                "position": self.pso.state.global_best,
                "fitness": self.pso.state.global_best_fitness,
                "source": "pso",
            }

        if self.abc.best_solution is not None:
            abc_best = {
                "position": self.abc.best_solution,
                "fitness": self.abc.best_fitness,
                "source": "abc",
            }

        candidates = [c for c in [pso_best, abc_best] if c]
        if not candidates:
            return {"position": None, "fitness": float('-inf')}

        return max(candidates, key=lambda c: c["fitness"])

    def get_state(self) -> Dict[str, Any]:
        """Get full swarm state"""
        return {
            "generation": self.generation,
            "pso": {
                "generation": self.pso.state.generation if self.pso.state else 0,
                "diversity": self.pso.state.diversity if self.pso.state else 0.0,
                "best_fitness": self.pso.state.global_best_fitness if self.pso.state else None,
            },
            "abc": {
                "generation": self.abc.generation,
                "bees": len(self.abc.bees),
                "food_sources": len(self.abc.food_sources),
                "best_fitness": self.abc.best_fitness,
                "role_distribution": self._get_role_distribution(),
            },
            "pheromone_field": self.pheromone_field.get_stats(),
        }

    def _get_role_distribution(self) -> Dict[str, int]:
        roles = {"employed": 0, "onlooker": 0, "scout": 0}
        for bee in self.abc.bees:
            roles[bee.role.value] += 1
        return roles
