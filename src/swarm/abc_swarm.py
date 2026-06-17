"""
Artificial Bee Colony with Dynamic Role-Switching
Implements ABC algorithm where bees dynamically switch between employed, onlooker,
and scout roles based on performance and food source quality.
"""
from typing import List, Tuple, Dict, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
try:
    import numpy as np
except ImportError:
    from ._numpy_shim import np
import random
import logging

logger = logging.getLogger(__name__)

class BeeRole(Enum):
    EMPLOYED = "employed"
    ONLOOKER = "onlooker"
    SCOUT = "scout"

@dataclass
class FoodSource:
    position: np.ndarray
    fitness: float = 0.0
    nectar_amount: float = 0.0
    trial_limit: int = 0
    is_exhausted: bool = False

@dataclass
class Bee:
    id: int
    role: BeeRole
    food_source_index: Optional[int] = None
    specialization: Optional[str] = None
    performance: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class ABCSwarm:
    """
    Artificial Bee Colony with dynamic role-switching.

    Bee roles:
    - EMPLOYED: Exploits assigned food source, shares info via waggle dance
    - ONLOOKER: Evaluates employed bee info, selects sources probabilistically
    - SCOUT: Abandons exhausted sources, searches randomly

    Reference: Karaboga (2005), "An idea based on honey bee swarm for numerical optimization"
    """

    def __init__(self,
                 n_employed: int = 20,
                 n_onlookers: int = 20,
                 n_scouts: int = 5,
                 dimensions: int = 3,
                 max_trials: int = 50,
                 bounds: Optional[List[Tuple[float, float]]] = None,
                 seed: Optional[int] = None,
                 role_switch_threshold: float = 0.3):
        self.n_employed = n_employed
        self.n_onlookers = n_onlookers
        self.n_scouts = n_scouts
        self.dimensions = dimensions
        self.max_trials = max_trials
        self.bounds = bounds or [(0.0, 1.0)] * dimensions
        self.role_switch_threshold = role_switch_threshold
        self.rng = random.Random(seed)

        self.food_sources: List[FoodSource] = []
        self.bees: List[Bee] = []
        self.best_solution: Optional[np.ndarray] = None
        self.best_fitness: float = float('-inf')
        self.generation: int = 0
        self.fitness_function: Optional[Callable] = None
        self.convergence_history: List[float] = []

    def initialize(self, fitness_fn: Callable[[np.ndarray], float],
                   initial_sources: Optional[List[np.ndarray]] = None):
        """Initialize the bee colony"""
        self.fitness_function = fitness_fn

        self.food_sources = []
        for i in range(self.n_employed):
            if initial_sources and i < len(initial_sources):
                pos = np.array(initial_sources[i], dtype=float)
            else:
                pos = np.array([self.rng.uniform(low, high) for low, high in self.bounds])
            fitness = fitness_fn(pos)
            self.food_sources.append(FoodSource(
                position=pos,
                fitness=fitness,
                nectar_amount=self._compute_nectar(fitness),
            ))
            if fitness > self.best_fitness:
                self.best_fitness = fitness
                self.best_solution = pos.copy()

        self.bees = []
        for i in range(self.n_employed):
            self.bees.append(Bee(id=i, role=BeeRole.EMPLOYED, food_source_index=i))
        for i in range(self.n_onlookers):
            self.bees.append(Bee(id=self.n_employed + i, role=BeeRole.ONLOOKER))
        for i in range(self.n_scouts):
            self.bees.append(Bee(id=self.n_employed + self.n_onlookers + i, role=BeeRole.SCOUT))

    def _compute_nectar(self, fitness: float) -> float:
        """Convert fitness to nectar amount (higher fitness = more nectar)"""
        return 1.0 / (1.0 + abs(fitness)) if fitness < 0 else 1.0 + abs(fitness)

    def step(self):
        """Execute one ABC iteration"""
        self._employed_phase()
        self._onlooker_phase()
        self._scout_phase()
        self._role_switching()

        self.generation += 1
        self.convergence_history.append(self.best_fitness)

    def _employed_phase(self):
        """Employed bees search around their food source"""
        employed_bees = [b for b in self.bees if b.role == BeeRole.EMPLOYED]
        for bee in employed_bees:
            if bee.food_source_index is None:
                continue
            source = self.food_sources[bee.food_source_index]

            new_pos = source.position.copy()
            d = self.rng.randint(0, self.dimensions - 1)
            phi = self.rng.uniform(-1, 1)

            other = self.rng.choice([s for s in self.food_sources if s is not source])
            new_pos[d] = source.position[d] + phi * (source.position[d] - other.position[d])

            low, high = self.bounds[d]
            new_pos[d] = np.clip(new_pos[d], low, high)

            new_fitness = self.fitness_function(new_pos)
            new_nectar = self._compute_nectar(new_fitness)

            if new_fitness > source.fitness:
                source.position = new_pos
                source.fitness = new_fitness
                source.nectar_amount = new_nectar
                source.trial_limit = 0
                bee.performance += 1.0
                if new_fitness > self.best_fitness:
                    self.best_fitness = new_fitness
                    self.best_solution = new_pos.copy()
            else:
                source.trial_limit += 1
                bee.performance -= 0.5

    def _onlooker_phase(self):
        """Onlooker bees probabilistically select food sources"""
        if not self.food_sources:
            return

        total_nectar = sum(s.nectar_amount for s in self.food_sources)
        if total_nectar <= 0:
            probabilities = [1.0 / len(self.food_sources)] * len(self.food_sources)
        else:
            probabilities = [s.nectar_amount / total_nectar for s in self.food_sources]

        onlooker_bees = [b for b in self.bees if b.role == BeeRole.ONLOOKER]
        for bee in onlooker_bees:
            idx = self.rng.choices(range(len(self.food_sources)), weights=probabilities, k=1)[0]
            source = self.food_sources[idx]

            new_pos = source.position.copy()
            d = self.rng.randint(0, self.dimensions - 1)
            phi = self.rng.uniform(-1, 1)
            other = self.rng.choice([s for s in self.food_sources if s is not source])
            new_pos[d] = source.position[d] + phi * (source.position[d] - other.position[d])

            low, high = self.bounds[d]
            new_pos[d] = np.clip(new_pos[d], low, high)

            new_fitness = self.fitness_function(new_pos)
            if new_fitness > source.fitness:
                source.position = new_pos
                source.fitness = new_fitness
                source.nectar_amount = self._compute_nectar(new_fitness)
                source.trial_limit = 0
                if new_fitness > self.best_fitness:
                    self.best_fitness = new_fitness
                    self.best_solution = new_pos.copy()
                bee.performance += 1.0
            else:
                bee.performance -= 0.5

    def _scout_phase(self):
        """Scout bees abandon exhausted sources"""
        exhausted_indices = [
            i for i, s in enumerate(self.food_sources)
            if s.trial_limit >= self.max_trials
        ]

        scout_bees = [b for b in self.bees if b.role == BeeRole.SCOUT]
        scout_idx = 0

        for src_idx in exhausted_indices:
            if scout_idx >= len(scout_bees):
                break

            new_pos = np.array([self.rng.uniform(low, high) for low, high in self.bounds])
            new_fitness = self.fitness_function(new_pos)

            self.food_sources[src_idx] = FoodSource(
                position=new_pos,
                fitness=new_fitness,
                nectar_amount=self._compute_nectar(new_fitness),
            )

            scout_bees[scout_idx].role = BeeRole.EMPLOYED
            scout_bees[scout_idx].food_source_index = src_idx
            scout_idx += 1

    def _role_switching(self):
        """Dynamic role-switching based on performance"""
        for bee in self.bees:
            if bee.role == BeeRole.EMPLOYED and bee.performance < -self.role_switch_threshold * 5:
                bee.role = BeeRole.SCOUT
                bee.food_source_index = None
                bee.performance = 0.0
                logger.debug(f"Bee {bee.id}: EMPLOYED -> SCOUT")

            elif bee.role == BeeRole.ONLOOKER and bee.performance > self.role_switch_threshold * 3:
                if self.food_sources:
                    best_idx = max(range(len(self.food_sources)),
                                   key=lambda i: self.food_sources[i].fitness)
                    bee.role = BeeRole.EMPLOYED
                    bee.food_source_index = best_idx
                    bee.performance = 0.0
                    logger.debug(f"Bee {bee.id}: ONLOOKER -> EMPLOYED")

    def optimize(self, n_iterations: int = 100) -> Dict[str, Any]:
        """Run full ABC optimization"""
        for i in range(n_iterations):
            self.step()

        return {
            "best_solution": self.best_solution,
            "best_fitness": self.best_fitness,
            "generations": self.generation,
            "convergence_history": self.convergence_history,
            "final_food_sources": [(s.position, s.fitness) for s in self.food_sources],
        }
