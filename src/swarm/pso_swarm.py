"""
PSO Ring Topology Swarm
Implements particle swarm optimization with ring (lbest) topology where each particle
only communicates with its immediate neighbors. This prevents premature convergence
and maintains swarm diversity.
"""
from typing import List, Tuple, Dict, Optional, Any, Callable
from dataclasses import dataclass, field
try:
    import numpy as np
except ImportError:
    from ._numpy_shim import np
import random
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class Topology(Enum):
    RING = "ring"            # lbest — each particle talks to immediate neighbors
    STAR = "star"            # gbest — all particles talk to global best
    WHEEL = "wheel"          # central hub relays information
    VON_NEUMANN = "von_neumann"  # 2D grid topology

@dataclass
class Particle:
    id: int
    position: np.ndarray
    velocity: np.ndarray
    personal_best: np.ndarray
    personal_best_fitness: float = float('-inf')
    current_fitness: float = float('-inf')
    neighbors: List[int] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SwarmState:
    particles: List[Particle]
    global_best: np.ndarray
    global_best_fitness: float
    generation: int = 0
    diversity: float = 0.0
    convergence_rate: float = 0.0

class RingPSOSwarm:
    """
    Particle Swarm Optimization with configurable topology.

    Key features:
    - Ring topology (default) for diversity preservation
    - Adaptive inertia weight (w) that decreases over time
    - Velocity clamping to prevent explosion
    - Fitness-based personal/global best tracking
    - Convergence monitoring

    Reference: Kennedy & Eberhart (1995), "Particle Swarm Optimization"
    """

    def __init__(self,
                 n_particles: int = 30,
                 dimensions: int = 3,
                 topology: Topology = Topology.RING,
                 w_start: float = 0.9,   # Initial inertia weight
                 w_end: float = 0.4,     # Final inertia weight
                 c1: float = 2.0,        # Cognitive coefficient (personal best)
                 c2: float = 2.0,        # Social coefficient (neighborhood best)
                 max_velocity: float = 0.5,
                 bounds: Optional[List[Tuple[float, float]]] = None,
                 seed: Optional[int] = None):
        self.n_particles = n_particles
        self.dimensions = dimensions
        self.topology = topology
        self.w_start = w_start
        self.w_end = w_end
        self.c1 = c1
        self.c2 = c2
        self.max_velocity = max_velocity
        self.bounds = bounds or [(0.0, 1.0)] * dimensions
        self.rng = random.Random(seed)
        self.state: Optional[SwarmState] = None
        self.fitness_function: Optional[Callable] = None
        self._generation = 0

    def initialize(self, fitness_fn: Callable[[np.ndarray], float],
                   initial_positions: Optional[List[np.ndarray]] = None):
        """Initialize swarm with particles at random positions"""
        particles = []
        for i in range(self.n_particles):
            if initial_positions and i < len(initial_positions):
                pos = np.array(initial_positions[i], dtype=float)
            else:
                pos = np.array([
                    self.rng.uniform(low, high)
                    for low, high in self.bounds
                ])
            vel = np.random.uniform(-self.max_velocity/2, self.max_velocity/2, self.dimensions)
            fitness = fitness_fn(pos)
            particles.append(Particle(
                id=i, position=pos, velocity=vel,
                personal_best=pos.copy(), personal_best_fitness=fitness,
                current_fitness=fitness
            ))

        self._assign_neighbors(particles)

        gbest_idx = max(range(len(particles)), key=lambda i: particles[i].personal_best_fitness)
        gbest = particles[gbest_idx].personal_best.copy()

        self.state = SwarmState(
            particles=particles,
            global_best=gbest,
            global_best_fitness=particles[gbest_idx].personal_best_fitness,
        )
        self.fitness_function = fitness_fn

    def _assign_neighbors(self, particles: List[Particle]):
        """Assign neighbors based on topology"""
        n = len(particles)
        if self.topology == Topology.RING:
            for i in range(n):
                particles[i].neighbors = [
                    (i - 1) % n,
                    (i + 1) % n,
                ]
        elif self.topology == Topology.STAR:
            for i in range(n):
                particles[i].neighbors = [j for j in range(n) if j != i]
        elif self.topology == Topology.WHEEL:
            for i in range(n):
                if i == 0:
                    particles[i].neighbors = list(range(1, n))
                else:
                    particles[i].neighbors = [0]
        elif self.topology == Topology.VON_NEUMANN:
            grid_size = int(np.ceil(np.sqrt(n)))
            for i in range(n):
                row, col = divmod(i, grid_size)
                neighbors = []
                for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
                    nr, nc = (row + dr) % grid_size, (col + dc) % grid_size
                    ni = nr * grid_size + nc
                    if ni < n and ni != i:
                        neighbors.append(ni)
                particles[i].neighbors = neighbors

    def step(self) -> SwarmState:
        """Execute one PSO iteration"""
        if self.state is None or self.fitness_function is None:
            raise ValueError("Swarm not initialized. Call initialize() first.")

        w = self._current_inertia()

        for particle in self.state.particles:
            if self.topology == Topology.STAR:
                neighbor_best = self.state.global_best
            else:
                neighbor_best = self._neighborhood_best(particle)

            r1, r2 = np.random.rand(self.dimensions), np.random.rand(self.dimensions)

            cognitive = self.c1 * r1 * (particle.personal_best - particle.position)
            social = self.c2 * r2 * (neighbor_best - particle.position)
            particle.velocity = (w * particle.velocity + cognitive + social)

            particle.velocity = np.clip(particle.velocity, -self.max_velocity, self.max_velocity)

            particle.position = particle.position + particle.velocity

            for d in range(self.dimensions):
                low, high = self.bounds[d]
                particle.position[d] = np.clip(particle.position[d], low, high)

            particle.current_fitness = self.fitness_function(particle.position)

            if particle.current_fitness > particle.personal_best_fitness:
                particle.personal_best = particle.position.copy()
                particle.personal_best_fitness = particle.current_fitness

                if particle.current_fitness > self.state.global_best_fitness:
                    self.state.global_best = particle.position.copy()
                    self.state.global_best_fitness = particle.current_fitness

        self.state.generation += 1
        self.state.diversity = self._compute_diversity()
        self.state.convergence_rate = self._compute_convergence_rate()

        return self.state

    def _current_inertia(self) -> float:
        """Linearly decreasing inertia weight"""
        if self.state is None:
            return self.w_start
        return self.w_start - (self.w_start - self.w_end) * min(self.state.generation / 100, 1)

    def _neighborhood_best(self, particle: Particle) -> np.ndarray:
        """Find best particle in neighborhood"""
        best_fitness = particle.personal_best_fitness
        best_pos = particle.personal_best.copy()
        for ni in particle.neighbors:
            n_particle = self.state.particles[ni]
            if n_particle.personal_best_fitness > best_fitness:
                best_fitness = n_particle.personal_best_fitness
                best_pos = n_particle.personal_best.copy()
        return best_pos

    def _compute_diversity(self) -> float:
        """Compute swarm diversity (average distance to centroid)"""
        if self.state is None or len(self.state.particles) < 2:
            return 0.0
        positions = np.array([p.position for p in self.state.particles])
        centroid = np.mean(positions, axis=0)
        distances = np.linalg.norm(positions - centroid, axis=1)
        return float(np.mean(distances))

    def _compute_convergence_rate(self) -> float:
        """Compute convergence rate (improvement per generation)"""
        if self.state is None or self.state.generation < 2:
            return 1.0
        return float(self.state.global_best_fitness / max(abs(self.state.global_best_fitness), 1e-10))

    def optimize(self, n_iterations: int = 100, early_stop_patience: int = 20) -> SwarmState:
        """Run full optimization"""
        best_fitness_history = []
        no_improve = 0

        for i in range(n_iterations):
            self.step()
            best_fitness_history.append(self.state.global_best_fitness)

            if len(best_fitness_history) > 1:
                if abs(best_fitness_history[-1] - best_fitness_history[-2]) < 1e-8:
                    no_improve += 1
                else:
                    no_improve = 0

            if no_improve >= early_stop_patience:
                logger.info(f"Early stopping at iteration {i} (no improvement for {early_stop_patience})")
                break

        return self.state
