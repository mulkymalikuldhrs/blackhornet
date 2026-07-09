"""
Stigmergic Communication Layer
Implements indirect coordination through a shared digital pheromone field.
Agents communicate by depositing and sensing pheromones, not by direct messaging.
This decouples agents in time and space: O(n) scaling instead of O(n²).

Pheromone types:
- EXPLORE: Encourages exploration of a region
- EXPLOIT: Signals a promising region to focus on
- DANGER: Marks a region to avoid
- TRAIL: Creates a path between promising regions

Pattern: deposit -> evaporate -> diffuse -> sense -> act
"""
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
try:
    import numpy as np
except ImportError:
    from ._numpy_shim import np
import time
import logging
import heapq
from collections import defaultdict

logger = logging.getLogger(__name__)

class PheromoneType(Enum):
    EXPLORE = "explore"
    EXPLOIT = "exploit"
    DANGER = "danger"
    TRAIL = "trail"
    ALERT = "alert"
    INFO = "info"

@dataclass
class Pheromone:
    position: Tuple[float, ...]
    type: PheromoneType
    intensity: float
    radius: float
    timestamp: float
    depositor_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class PheromoneField:
    """
    Shared digital pheromone field for stigmergic communication.

    Operations:
    1. deposit(): Agent leaves a pheromone at a position
    2. evaporate(): All pheromones decay over time
    3. diffuse(): Pheromones spread to neighboring regions
    4. sense(): Agent detects pheromones at a position
    5. cleanup(): Remove fully evaporated pheromones
    """

    def __init__(self,
                 evaporation_rate: float = 0.05,
                 diffusion_rate: float = 0.1,
                 max_pheromones: int = 10000,
                 grid_resolution: float = 0.1,
                 dimensions: int = 3):
        self.evaporation_rate = evaporation_rate
        self.diffusion_rate = diffusion_rate
        self.max_pheromones = max_pheromones
        self.grid_resolution = grid_resolution
        self.dimensions = dimensions

        self.pheromones: List[Pheromone] = []
        self.grid: Dict[Tuple, List[int]] = defaultdict(list)
        self._total_intensity: Dict[PheromoneType, float] = defaultdict(float)

    def deposit(self, position: Tuple[float, ...], type: PheromoneType,
                intensity: float = 1.0, radius: float = 0.5,
                depositor_id: str = "unknown", metadata: dict = None) -> Pheromone:
        """Agent deposits a pheromone at a position"""
        if len(self.pheromones) >= self.max_pheromones:
            oldest = min(self.pheromones, key=lambda p: p.timestamp)
            self.pheromones.remove(oldest)
            self._remove_from_grid(oldest)

        ph = Pheromone(
            position=tuple(position),
            type=type,
            intensity=max(0.0, min(1.0, intensity)),
            radius=radius,
            timestamp=time.time(),
            depositor_id=depositor_id,
            metadata=metadata or {},
        )
        self.pheromones.append(ph)
        self._add_to_grid(ph)
        self._total_intensity[type] += ph.intensity
        return ph

    def _add_to_grid(self, ph: Pheromone):
        """Add pheromone to spatial grid"""
        cell = self._position_to_cell(ph.position)
        self.grid[cell].append(len(self.pheromones) - 1)

    def _remove_from_grid(self, ph: Pheromone):
        """Remove pheromone from spatial grid"""
        cell = self._position_to_cell(ph.position)
        indices = self.grid.get(cell, [])
        for idx in range(len(self.pheromones)):
            if self.pheromones[idx] is ph:
                if idx in indices:
                    indices.remove(idx)
                break

    def _position_to_cell(self, position: Tuple[float, ...]) -> Tuple:
        """Convert continuous position to grid cell coordinates"""
        return tuple(int(round(p / self.grid_resolution)) for p in position)

    def evaporate(self, dt: Optional[float] = None):
        """Evaporate all pheromones (decay over time)"""
        now = time.time()
        to_remove = []

        for i, ph in enumerate(self.pheromones):
            age = now - ph.timestamp if dt is None else dt
            decay = self.evaporation_rate * age
            ph.intensity = max(0.0, ph.intensity - decay)
            self._total_intensity[ph.type] -= decay

            if ph.intensity <= 0.01:
                to_remove.append(i)

        for i in reversed(to_remove):
            self._remove_from_grid(self.pheromones[i])
            del self.pheromones[i]

    def diffuse(self):
        """Diffuse pheromones to neighboring grid cells"""
        new_deposits = []

        for ph in self.pheromones:
            if ph.radius > self.grid_resolution * 2:
                cell = self._position_to_cell(ph.position)
                for dc in self._neighbor_cells(cell):
                    diffusion_intensity = ph.intensity * self.diffusion_rate * 0.1
                    if diffusion_intensity > 0.01:
                        neighbor_pos = tuple(
                            (c + 0.5) * self.grid_resolution
                            for c in dc
                        )
                        new_deposits.append(Pheromone(
                            position=neighbor_pos,
                            type=ph.type,
                            intensity=diffusion_intensity,
                            radius=ph.radius * 0.5,
                            timestamp=ph.timestamp,
                            depositor_id=ph.depositor_id,
                            metadata={"diffused": True, "parent": id(ph)},
                        ))

        for nd in new_deposits:
            if len(self.pheromones) < self.max_pheromones:
                self.pheromones.append(nd)
                self._add_to_grid(nd)

    def _neighbor_cells(self, cell: Tuple) -> List[Tuple]:
        """Get neighboring grid cells (Moore neighborhood)"""
        neighbors = []
        for offsets in np.ndindex((3,) * self.dimensions):
            if all(o == 1 for o in offsets):
                continue
            neighbors.append(tuple(c + o - 1 for c, o in zip(cell, offsets)))
        return neighbors

    def sense(self, position: Tuple[float, ...],
              types: Optional[List[PheromoneType]] = None,
              radius: float = 1.0) -> Dict[PheromoneType, List[Pheromone]]:
        """
        Agent senses pheromones at/near a position.
        Returns pheromones grouped by type.
        """
        pos = np.array(position)
        results = defaultdict(list)

        cell = self._position_to_cell(position)
        search_cells = [cell]
        search_cells.extend(self._neighbor_cells(cell))

        seen = set()
        for sc in search_cells:
            for idx in self.grid.get(sc, []):
                if idx in seen:
                    continue
                seen.add(idx)
                ph = self.pheromones[idx]

                if types and ph.type not in types:
                    continue

                ph_pos = np.array(ph.position)
                distance = float(np.linalg.norm(pos - ph_pos))

                if distance <= radius:
                    results[ph.type].append(ph)

        return dict(results)

    def sense_strength(self, position: Tuple[float, ...],
                       type: Optional[PheromoneType] = None) -> float:
        """Get total pheromone intensity at position (for decision-making)"""
        sensed = self.sense(position, types=[type] if type else None)
        total = 0.0
        for ptype, pheromones in sensed.items():
            for ph in pheromones:
                distance = np.linalg.norm(np.array(position) - np.array(ph.position))
                total += ph.intensity / max(distance, 0.1)
        return total

    def cleanup(self):
        """Maintenance: remove old pheromones, compact storage"""
        now = time.time()
        self.pheromones = [
            ph for ph in self.pheromones
            if ph.intensity > 0.01 and (now - ph.timestamp) < 300
        ]
        self.grid.clear()
        for i, ph in enumerate(self.pheromones):
            self._add_to_grid(ph)

    def get_stats(self) -> Dict[str, Any]:
        """Get pheromone field statistics"""
        type_counts = defaultdict(int)
        type_intensities = defaultdict(float)
        for ph in self.pheromones:
            type_counts[ph.type.value] += 1
            type_intensities[ph.type.value] += ph.intensity

        return {
            "total_pheromones": len(self.pheromones),
            "type_counts": dict(type_counts),
            "type_intensities": dict(type_intensities),
            "grid_cells": len(self.grid),
        }
