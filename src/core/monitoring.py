from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable

@dataclass
class Metric:
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    def __init__(self) -> None:
        self._metrics: dict[str, list[Metric]] = defaultdict(list)

    def record(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        self._metrics[name].append(Metric(name=name, value=value, tags=tags or {}))

    def get_metric(self, name: str) -> list[Metric]:
        return self._metrics.get(name, [])

    def summary(self) -> dict[str, dict[str, float]]:
        result: dict[str, dict[str, float]] = {}
        for name, values in self._metrics.items():
            vals = [m.value for m in values]
            result[name] = {
                "count": len(vals),
                "min": min(vals),
                "max": max(vals),
                "mean": sum(vals) / len(vals) if vals else 0.0,
                "latest": vals[-1] if vals else 0.0,
            }
        return result


class HealthEndpoint:
    def __init__(self) -> None:
        self._checks: dict[str, Callable[[], bool]] = {}

    def register(self, name: str, check_fn: Callable[[], bool]) -> None:
        self._checks[name] = check_fn

    def check_all(self) -> dict[str, dict[str, bool | str]]:
        results: dict[str, dict[str, bool | str]] = {}
        for name, fn in self._checks.items():
            try:
                ok = fn()
                results[name] = {"healthy": ok, "error": ""}
            except Exception as e:
                results[name] = {"healthy": False, "error": str(e)}
        return results


_metrics_instance: MetricsCollector | None = None
_health_instance: HealthEndpoint | None = None


def get_metrics() -> MetricsCollector:
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = MetricsCollector()
    return _metrics_instance


def get_health() -> HealthEndpoint:
    global _health_instance
    if _health_instance is None:
        _health_instance = HealthEndpoint()
    return _health_instance
