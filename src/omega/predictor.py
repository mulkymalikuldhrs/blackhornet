"""Predictive Superconsciousness (L9: The Oracle) — scenario branching engine."""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ScenarioBranch:
    name: str
    description: str
    probability: float
    expected_value: float
    consequences: list[str]
    is_success: bool


@dataclass
class Prediction:
    action: str
    branches: list[ScenarioBranch]
    optimal_path: str
    confidence: float
    evidence: str
    falsify_by: str
    timestamp: float = 0.0
    outcome: Optional[bool] = None


class PredictiveSuperconsciousness:
    """L9 Oracle — see every future before acting. Choose best path with honest confidence."""

    def __init__(self) -> None:
        self._predictions: list[Prediction] = []

    def branch(
        self,
        action: str,
        success_branches: Optional[list[dict]] = None,
        failure_branches: Optional[list[dict]] = None,
    ) -> Prediction:
        """Generate scenario branching tree for an action."""
        if success_branches is None:
            success_branches = [
                {"name": "A works", "desc": "Primary path succeeds", "prob": 0.6, "ev": 80, "consequences": ["Immediate progress", "Momentum builds", "Next steps clearer"]},
                {"name": "A + B work", "desc": "Primary + secondary succeed", "prob": 0.3, "ev": 95, "consequences": ["Full success", "Team confidence up", "Pattern established"]},
            ]
        if failure_branches is None:
            failure_branches = [
                {"name": "A fails", "desc": "Primary path fails", "prob": 0.25, "ev": 20, "consequences": ["Fallback triggered", "Time lost", "Lesson learned"]},
                {"name": "A + B fail", "desc": "Primary + fallback both fail", "prob": 0.1, "ev": 5, "consequences": ["Full retry needed", "Strategy change", "Root cause analysis"]},
            ]

        branches: list[ScenarioBranch] = []
        for b in success_branches:
            branches.append(ScenarioBranch(
                name=b["name"], description=b["desc"], probability=b["prob"],
                expected_value=b["ev"], consequences=b.get("consequences", []), is_success=True,
            ))
        for b in failure_branches:
            branches.append(ScenarioBranch(
                name=b["name"], description=b["desc"], probability=b["prob"],
                expected_value=b["ev"], consequences=b.get("consequences", []), is_success=False,
            ))

        optimal = max(branches, key=lambda b: b.expected_value * b.probability)
        prediction = Prediction(
            action=action,
            branches=branches,
            optimal_path=f"{optimal.name} (EV={optimal.expected_value * optimal.probability:.1f})",
            confidence=min(optimal.probability * 1.1, 0.95),
            evidence=f"Scenario branching with {len(branches)} branches",
            falsify_by=f"Outcome does not match {optimal.name} prediction",
            timestamp=time.time(),
        )
        self._predictions.append(prediction)
        return prediction

    def calibrate(self, prediction: Prediction, actual_success: bool) -> None:
        for p in self._predictions:
            if p is prediction or (p.timestamp == prediction.timestamp and p.action == prediction.action):
                p.outcome = actual_success
                break

    def calibration_report(self) -> dict:
        resolved = [p for p in self._predictions if p.outcome is not None]
        correct = sum(1 for p in resolved if p.outcome)
        return {
            "total_predictions": len(self._predictions),
            "resolved": len(resolved),
            "correct": correct,
            "accuracy": round(correct / len(resolved) * 100, 1) if resolved else 0,
        }

    def predict(self, question: str, context: str = "") -> dict:
        branch = self.branch(question)
        return {
            "question": question,
            "branches": [{"name": b.name, "description": b.description, "probability": b.probability, "expected_value": b.expected_value} for b in branch.branches],
            "optimal_path": branch.optimal_path,
            "confidence": f"{branch.confidence:.0%}",
            "evidence": branch.evidence,
            "timestamp": branch.timestamp,
        }
