"""
EvolutionaryOptimizer — Evolutionary algorithms for agent optimization.
Inspired by:
  - "LLMs as Evolutionary Optimizers" (arXiv:2310.19046)
  - "CodeEvolve: Open Source Evolutionary Coding Agent" (arXiv:2510.14150)
  - "Evolutionary and Coevolutionary MAS Design" (arXiv:2507.05534)

Mechanisms:
  1. Population management: maintain diverse strategy populations
  2. Selection: tournament-based fitness selection
  3. Mutation: random perturbations with adaptive rate
  4. Crossover: combine successful strategies
  5. Coevolution: multiple populations evolve in response to each other
"""
from __future__ import annotations

import logging
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class Genotype:
    """An evolvable strategy representation."""
    genes: dict[str, float]
    id: str = ""
    fitness: float = 0.0
    age: int = 0
    generation: int = 0
    parent_ids: list[str] = field(default_factory=list)
    mutation_rate: float = 0.1
    created_at: float = field(default_factory=time.time)

    @classmethod
    def random(cls, gene_names: list[str], mutation_rate: float = 0.1) -> Genotype:
        return cls(
            id=f"gen-{random.randint(0, 1000000):06d}",
            genes={name: random.gauss(0.5, 0.25) for name in gene_names},
            mutation_rate=mutation_rate,
        )

    def mutate(self) -> None:
        """Apply Gaussian mutation to all genes."""
        for key in self.genes:
            if random.random() < self.mutation_rate:
                self.genes[key] += random.gauss(0, 0.1)
                self.genes[key] = max(0.0, min(1.0, self.genes[key]))
        self.age += 1

    def crossover(self, other: Genotype) -> Genotype:
        """One-point crossover with another genotype."""
        child_genes = {}
        keys = list(self.genes.keys())
        split = random.randint(0, len(keys))
        for i, key in enumerate(keys):
            child_genes[key] = self.genes[key] if i < split else other.genes.get(key, self.genes[key])
        return Genotype(
            id=f"gen-{random.randint(0, 1000000):06d}",
            genes=child_genes,
            mutation_rate=(self.mutation_rate + other.mutation_rate) / 2,
            parent_ids=[self.id, other.id],
            generation=max(self.generation, other.generation) + 1,
        )


@dataclass
class EvolutionConfig:
    population_size: int = 50
    tournament_size: int = 3
    elite_count: int = 5
    mutation_rate: float = 0.1
    crossover_rate: float = 0.7
    generations_per_epoch: int = 10
    fitness_threshold: float = 0.9


@dataclass
class FitnessRecord:
    genotype_id: str
    fitness: float
    generation: int
    timestamp: float = field(default_factory=time.time)


class EvolutionaryOptimizer:
    """
    Evolutionary algorithm system for optimizing agent strategies.

    Maintains a population of Genotypes (strategy configurations),
    applies selection/mutation/crossover, and tracks fitness over
    generations. Supports coevolution with multiple populations.
    """

    def __init__(
        self,
        config: Optional[EvolutionConfig] = None,
        gene_names: Optional[list[str]] = None,
    ):
        self.config = config or EvolutionConfig()
        self.gene_names = gene_names or [
            "exploration_rate", "risk_tolerance", "cooperation_bias",
            "memory_decay", "delegation_threshold", "confidence_boost",
        ]
        self._populations: dict[str, list[Genotype]] = {"default": []}
        self._fitness_history: list[FitnessRecord] = []
        self._best_fitness: float = 0.0
        self._generation = 0
        self._best_genotype: Optional[Genotype] = None

    # ── Population Management ───────────────────────────────────

    def initialize_population(self, population_id: str = "default") -> None:
        """Create initial random population."""
        self._populations[population_id] = [
            Genotype.random(self.gene_names, self.config.mutation_rate)
            for _ in range(self.config.population_size)
        ]
        logger.info(
            "Initialized population '%s' with %d genotypes (%d genes)",
            population_id, self.config.population_size, len(self.gene_names),
        )

    def get_population(self, population_id: str = "default") -> list[Genotype]:
        if population_id not in self._populations:
            self.initialize_population(population_id)
        return self._populations[population_id]

    # ── Evolution Cycle ─────────────────────────────────────────

    def evolve(
        self,
        fitness_fn: Callable[[Genotype], float],
        generations: int = 1,
        population_id: str = "default",
    ) -> list[dict[str, Any]]:
        """
        Run one evolution cycle for the given number of generations.
        Returns a list of evolution events.
        """
        events: list[dict[str, Any]] = []
        population = self.get_population(population_id)

        for _ in range(generations):
            self._generation += 1

            # Evaluate fitness
            for genotype in population:
                if genotype.fitness == 0.0 or genotype.age > 0:
                    genotype.fitness = fitness_fn(genotype)

            # Sort by fitness
            population.sort(key=lambda g: g.fitness, reverse=True)

            # Track best
            if population[0].fitness > self._best_fitness:
                self._best_fitness = population[0].fitness
                self._best_genotype = population[0]
                self._fitness_history.append(FitnessRecord(
                    genotype_id=population[0].id,
                    fitness=population[0].fitness,
                    generation=self._generation,
                ))
                events.append({
                    "type": "new_best",
                    "generation": self._generation,
                    "fitness": population[0].fitness,
                })

            # Create next generation
            next_gen: list[Genotype] = []

            # Elitism: keep top performers
            next_gen.extend(population[:self.config.elite_count])

            # Fill rest with tournament selection + crossover/mutation
            while len(next_gen) < self.config.population_size:
                parent_a = self._tournament_select(population)
                parent_b = self._tournament_select(population)

                if random.random() < self.config.crossover_rate:
                    child = parent_a.crossover(parent_b)
                else:
                    child = Genotype(
                        id=f"gen-{random.randint(0, 1000000):06d}",
                        genes=dict(parent_a.genes),
                        mutation_rate=parent_a.mutation_rate,
                        parent_ids=[parent_a.id],
                        generation=parent_a.generation + 1,
                    )

                child.mutate()
                next_gen.append(child)

            self._populations[population_id] = next_gen[:self.config.population_size]

        avg_fitness = sum(g.fitness for g in population) / len(population)
        events.append({
            "type": "generation_complete",
            "generation": self._generation,
            "best_fitness": population[0].fitness if population else 0,
            "avg_fitness": avg_fitness,
            "population_size": len(population),
        })

        return events

    def _tournament_select(self, population: list[Genotype]) -> Genotype:
        """Tournament selection: pick k random, return best."""
        tournament = random.sample(population, min(self.config.tournament_size, len(population)))
        return max(tournament, key=lambda g: g.fitness)

    # ── Coevolution ─────────────────────────────────────────────

    def coevolve(
        self,
        fitness_fn: Callable[[str, Genotype], float],
        generations: int = 1,
    ) -> list[dict[str, Any]]:
        """
        Coevolve multiple populations that interact.
        Each population's fitness is evaluated in context of others.
        """
        events: list[dict[str, Any]] = []

        for pop_id in self._populations:
            pop = self._populations[pop_id]
            if len(pop) < self.config.population_size:
                while len(pop) < self.config.population_size:
                    pop.append(Genotype.random(self.gene_names, self.config.mutation_rate))

        for _ in range(generations):
            self._generation += 1

            for pop_id, population in self._populations.items():
                for genotype in population:
                    genotype.fitness = fitness_fn(pop_id, genotype)

                population.sort(key=lambda g: g.fitness, reverse=True)
                next_pop = population[:self.config.elite_count]

                while len(next_pop) < self.config.population_size:
                    a = self._tournament_select(population)
                    b = self._tournament_select(population)

                    if random.random() < self.config.crossover_rate:
                        child = a.crossover(b)
                    else:
                        child = Genotype(
                            id=f"gen-{random.randint(0, 1000000):06d}",
                            genes=dict(a.genes),
                            mutation_rate=a.mutation_rate,
                            parent_ids=[a.id],
                            generation=a.generation + 1,
                        )
                    child.mutate()
                    next_pop.append(child)

                self._populations[pop_id] = next_pop

            events.append({
                "type": "coevolution_cycle",
                "generation": self._generation,
                "populations": {
                    pid: max((g.fitness for g in pop), default=0)
                    for pid, pop in self._populations.items()
                },
            })

        return events

    # ── Query ───────────────────────────────────────────────────

    def get_best_genes(self, population_id: str = "default") -> dict[str, float]:
        """Get the genes of the best-performing genotype."""
        pop = self.get_population(population_id)
        if not pop:
            return {name: 0.5 for name in self.gene_names}
        best = max(pop, key=lambda g: g.fitness)
        return dict(best.genes)

    def get_diversity(self, population_id: str = "default") -> float:
        """Calculate genetic diversity (avg pairwise distance)."""
        pop = self.get_population(population_id)
        if len(pop) < 2:
            return 0.0
        total_dist = 0.0
        count = 0
        for i in range(min(len(pop), 20)):
            for j in range(i + 1, min(len(pop), 20)):
                dist = sum(abs(pop[i].genes[k] - pop[j].genes[k]) for k in self.gene_names)
                total_dist += dist / len(self.gene_names)
                count += 1
        return total_dist / max(count, 1)

    def get_stats(self) -> dict[str, Any]:
        return {
            "generation": self._generation,
            "populations": len(self._populations),
            "total_genotypes": sum(len(p) for p in self._populations.values()),
            "best_fitness": self._best_fitness,
            "fitness_history": len(self._fitness_history),
            "gene_count": len(self.gene_names),
            "diversity": self.get_diversity(),
            "config": {
                "population_size": self.config.population_size,
                "tournament_size": self.config.tournament_size,
                "elite_count": self.config.elite_count,
                "mutation_rate": self.config.mutation_rate,
                "crossover_rate": self.config.crossover_rate,
            },
        }
