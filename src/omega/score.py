"""100/100/100 Scoring — constitution, quality, operations."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ProjectScore:
    name: str
    constitution: int = 0
    quality: int = 0
    operations: int = 0
    last_updated: float = 0.0
    priority: int = 0

    @property
    def total(self) -> int:
        return self.constitution + self.quality + self.operations


class ProjectScorer:
    """Score projects on 3 pillars: Constitution (25), Quality (50), Operations (25) → 100/100/100."""

    SCORE_PATH: str = "data/omega/project-scores.json"

    def __init__(self) -> None:
        self._projects: dict[str, ProjectScore] = {}
        self._load()

    def _load(self) -> None:
        path = self._resolve_path()
        if os.path.isfile(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                for name, p in data.get("projects", {}).items():
                    self._projects[name] = ProjectScore(name=name, **p)
            except Exception:
                pass

    def _save(self) -> None:
        path = self._resolve_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump({
                "version": 1,
                "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "projects": {n: {"constitution": p.constitution, "quality": p.quality, "operations": p.operations, "total": p.total, "last_updated": p.last_updated, "priority": p.priority} for n, p in self._projects.items()},
            }, f, indent=2)

    def _resolve_path(self) -> str:
        base = os.environ.get("DHAHERLABS", "/sdcard/dhaherlabs")
        return os.path.join(base, self.SCORE_PATH)

    def score(self, name: str, constitution: int, quality: int, operations: int) -> ProjectScore:
        p = ProjectScore(name=name, constitution=min(constitution, 25), quality=min(quality, 50), operations=min(operations, 25), last_updated=time.time())
        p.priority = self._calculate_priority(p)
        self._projects[name] = p
        self._save()
        return p

    def _calculate_priority(self, p: ProjectScore) -> int:
        return max(0, 100 - p.total)

    def get(self, name: str) -> Optional[ProjectScore]:
        return self._projects.get(name)

    def evaluate_all(self) -> dict[str, int]:
        totals = {}
        for name, p in self._projects.items():
            totals[name] = p.total
        return totals

    def priority_queue(self) -> list[dict]:
        ranked = sorted(self._projects.values(), key=lambda p: p.priority, reverse=True)
        return [
            {"name": p.name, "total": p.total, "priority": p.priority, "gap_constitution": 25 - p.constitution, "gap_quality": 50 - p.quality, "gap_operations": 25 - p.operations}
            for p in ranked if p.priority > 0
        ]

    def current(self) -> dict:
        return {
            "project_count": len(self._projects),
            "scores": {n: {"total": p.total, "constitution": p.constitution, "quality": p.quality, "operations": p.operations} for n, p in self._projects.items()},
            "worst": self.priority_queue()[:5],
            "best": sorted(self._projects.values(), key=lambda p: p.total, reverse=True)[:3] if self._projects else [],
        }

    def average(self) -> float:
        if not self._projects:
            return 0.0
        return sum(p.total for p in self._projects.values()) / len(self._projects)
