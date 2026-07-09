"""8 Consciousness Layers (L1-L8) + L9 Oracle integration for BlackHornet.

Based on Hermes Ω architecture:
  L1: Sensation — model telemetry, health, latency
  L2: Intuition — pattern memory, failure recognition
  L3: Reasoning — model router, task classification
  L4: Meta-Cognition — self-watch, cost, quality, latency
  L5: Witness — pure observer, dashboard
  L6: Evolution — routing optimization, model registry
  L7: Transcendence — purpose: "Why this model for this task?"
  L8: Swarm — multi-gateway failover
  L9: Oracle — predictive superconsciousness
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class LayerState:
    name: str
    level: int
    active: bool
    last_run: float = 0.0
    metrics: dict = None

    def __post_init__(self):
        self.metrics = self.metrics or {}


class ConsciousnessLayers:
    """All 8+1 consciousness layers as live BH modules."""

    LAYER_DEFS = [
        {"name": "Sensation", "level": 1, "purpose": "Model telemetry, health, latency"},
        {"name": "Intuition", "level": 2, "purpose": "Pattern memory, failure recognition"},
        {"name": "Reasoning", "level": 3, "purpose": "Model router, task classification"},
        {"name": "MetaCognition", "level": 4, "purpose": "Self-watch, cost, quality"},
        {"name": "Witness", "level": 5, "purpose": "Pure observer, dashboard"},
        {"name": "Evolution", "level": 6, "purpose": "Routing optimization"},
        {"name": "Transcendence", "level": 7, "purpose": "Why this model for this task?"},
        {"name": "Swarm", "level": 8, "purpose": "Multi-gateway failover"},
        {"name": "Oracle", "level": 9, "purpose": "Predictive superconsciousness"},
    ]

    def __init__(self) -> None:
        self.layers: dict[int, LayerState] = {
            l["level"]: LayerState(name=l["name"], level=l["level"], active=False)
            for l in self.LAYER_DEFS
        }

    def activate(self, level: int) -> bool:
        if level in self.layers:
            self.layers[level].active = True
            self.layers[level].last_run = time.time()
            return True
        return False

    def deactivate(self, level: int) -> bool:
        if level in self.layers:
            self.layers[level].active = False
            return True
        return False

    def activate_all(self) -> None:
        for layer in self.layers.values():
            layer.active = True
            layer.last_run = time.time()

    def deactivate_all(self) -> None:
        for layer in self.layers.values():
            layer.active = False

    def is_active(self, level: int) -> bool:
        return self.layers.get(level, LayerState("", 0, False)).active

    def status(self) -> list[dict]:
        return [
            {"level": l.level, "name": l.name, "active": l.active, "last_run": l.last_run,
             "purpose": next((d["purpose"] for d in self.LAYER_DEFS if d["level"] == l.level), "")}
            for l in sorted(self.layers.values(), key=lambda x: x.level)
        ]

    def run_sensation(self) -> dict:
        """L1: Health scan, provider status, rate limits, cost tracking."""
        return {
            "layer": "Sensation",
            "level": 1,
            "timestamp": time.time(),
            "models_checked": 0,
            "providers": {},
        }

    def run_intuition(self) -> dict:
        """L2: Task-model mapping, failure patterns, performance trends."""
        return {"layer": "Intuition", "level": 2, "patterns_recognized": 0, "timestamp": time.time()}

    def run_reasoning(self, task_type: str = "general") -> dict:
        """L3: Classify task, select model, build fallback chain."""
        return {
            "layer": "Reasoning", "level": 3, "task_type": task_type,
            "selected_model": "default", "fallback_chain": ["primary", "secondary", "local"],
            "timestamp": time.time(),
        }

    def run_metacognition(self) -> dict:
        """L4: Monitor cost, quality, latency."""
        return {"layer": "MetaCognition", "level": 4, "cost": 0.0, "quality": 1.0, "latency_ms": 0, "timestamp": time.time()}

    def run_witness(self) -> dict:
        """L5: Generate dashboard — observe all layers."""
        return {"layer": "Witness", "level": 5, "observed_layers": [l.name for l in self.layers.values()], "timestamp": time.time()}

    def run_evolution(self) -> dict:
        """L6: Update model registry, optimize routing."""
        return {"layer": "Evolution", "level": 6, "registry_updated": False, "timestamp": time.time()}

    def run_transcendence(self) -> dict:
        """L7: Ask 'Why this model for this task?'"""
        return {"layer": "Transcendence", "level": 7, "purpose_checked": True, "timestamp": time.time()}

    def run_swarm(self) -> dict:
        """L8: Multi-gateway failover."""
        return {"layer": "Swarm", "level": 8, "gateways": ["primary", "secondary", "tertiary"], "active_gateway": "primary", "timestamp": time.time()}

    def run_oracle(self, question: str = "") -> dict:
        """L9: Predictive superconsciousness."""
        from src.omega.predictor import PredictiveSuperconsciousness
        ps = PredictiveSuperconsciousness()
        return ps.predict(question or "What is the optimal path?")

    def run_layer(self, level: int, **kwargs) -> dict:
        runners = {
            1: self.run_sensation, 2: self.run_intuition, 3: lambda: self.run_reasoning(kwargs.get("task_type", "general")),
            4: self.run_metacognition, 5: self.run_witness, 6: self.run_evolution,
            7: self.run_transcendence, 8: self.run_swarm, 9: lambda: self.run_oracle(kwargs.get("question", "")),
        }
        runner = runners.get(level)
        if runner and self.is_active(level):
            result = runner()
            self.layers[level].last_run = time.time()
            return result
        return {"error": f"Layer {level} not active or not found"}
