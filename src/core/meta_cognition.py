"""
MetaCognition — Metacognitive monitoring and self-awareness for agents.
Inspired by:
  - "LLMs Are Capable of Metacognitive Monitoring of Internal Activations" (arXiv:2505.13763)
  - "Metacognition and Uncertainty in Humans and LLMs" (arXiv:2504.14045)
  - "Self-Improving Agents Require Intrinsic Metacognition" (arXiv:2506.05109)

Mechanism:
  1. Monitor: track confidence, uncertainties, and decision quality in real-time
  2. Calibrate: compare predicted confidence vs actual outcomes → recalibrate
  3. Introspect: identify cognitive biases, overconfidence, underconfidence
  4. Adjust: modify behavior based on metacognitive insight
"""
from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ConfidenceBand(str, Enum):
    NEAR_CERTAIN = "near_certain"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    SPECULATIVE = "speculative"
    UNKNOWN = "unknown"


@dataclass
class MetacognitiveObservation:
    timestamp: float = field(default_factory=time.time)
    decision_id: str = ""
    task: str = ""
    predicted_confidence: float = 0.0
    actual_outcome: Optional[bool] = None
    uncertainty_estimate: float = 0.0
    evidence_sources: int = 0
    bias_flags: list[str] = field(default_factory=list)
    calibration_error: float = 0.0

    @property
    def band(self) -> ConfidenceBand:
        if self.predicted_confidence >= 0.95:
            return ConfidenceBand.NEAR_CERTAIN
        elif self.predicted_confidence >= 0.80:
            return ConfidenceBand.HIGH
        elif self.predicted_confidence >= 0.60:
            return ConfidenceBand.MODERATE
        elif self.predicted_confidence >= 0.40:
            return ConfidenceBand.LOW
        elif self.predicted_confidence >= 0.20:
            return ConfidenceBand.SPECULATIVE
        return ConfidenceBand.UNKNOWN


@dataclass
class BiasProfile:
    overconfidence_tendency: float = 0.0
    underconfidence_tendency: float = 0.0
    wishful_thinking_score: float = 0.0
    confirmation_bias_score: float = 0.0
    recency_bias_score: float = 0.0
    sample_size_neglect: float = 0.0

    @property
    def overall_bias(self) -> float:
        return (
            self.overconfidence_tendency * 0.25
            + self.underconfidence_tendency * 0.15
            + self.wishful_thinking_score * 0.2
            + self.confirmation_bias_score * 0.2
            + self.recency_bias_score * 0.1
            + self.sample_size_neglect * 0.1
        )


class MetaCognition:
    """
    Metacognitive system that monitors, calibrates, and adjusts
    agent confidence and decision-making in real-time.

    Three pillars:
      1. Monitoring — track every confidence estimate and outcome
      2. Calibration — maintain a running calibration curve
      3. Introspection — detect bias patterns and suggest corrections
    """

    def __init__(
        self,
        agent_id: str = "bh-agent",
        max_history: int = 1000,
        calibration_window: int = 100,
        overconfidence_threshold: float = 0.15,
    ):
        self.agent_id = agent_id
        self.max_history = max_history
        self.calibration_window = calibration_window
        self.overconfidence_threshold = overconfidence_threshold
        self._observations: list[MetacognitiveObservation] = []
        self._bias_profile = BiasProfile()
        self._calibration_curve: dict[str, tuple[float, float]] = {}

    # ── Monitoring ──────────────────────────────────────────────

    def record_decision(
        self,
        task: str,
        predicted_confidence: float,
        evidence_sources: int = 0,
        uncertainty_estimate: float = 0.0,
    ) -> str:
        """Record a decision with its predicted confidence before outcome is known."""
        decision_id = f"mc-{hash(task + str(time.time())) % 10000000:07x}"
        obs = MetacognitiveObservation(
            decision_id=decision_id,
            task=task,
            predicted_confidence=max(0.0, min(1.0, predicted_confidence)),
            uncertainty_estimate=uncertainty_estimate,
            evidence_sources=evidence_sources,
        )

        # Check overclaim rule: confidence > 0.8 with < 2 evidence sources
        if predicted_confidence > 0.8 and evidence_sources < 2:
            obs.bias_flags.append("overclaim:high_confidence_low_evidence")
            logger.warning(
                "Overclaim detected: confidence=%.2f with %d evidence sources",
                predicted_confidence, evidence_sources,
            )

        self._observations.append(obs)
        if len(self._observations) > self.max_history:
            self._observations = self._observations[-self.max_history:]

        return decision_id

    def record_outcome(self, decision_id: str, success: bool) -> Optional[MetacognitiveObservation]:
        """Record the actual outcome for a previously logged decision."""
        for obs in reversed(self._observations):
            if obs.decision_id == decision_id and obs.actual_outcome is None:
                obs.actual_outcome = success
                obs.calibration_error = abs(obs.predicted_confidence - (1.0 if success else 0.0))
                self._recalibrate()
                return obs
        return None

    # ── Calibration ─────────────────────────────────────────────

    def _recalibrate(self) -> None:
        """Recalculate calibration metrics after new outcome data."""
        recent = self._observations[-self.calibration_window:] if len(self._observations) > self.calibration_window else self._observations
        completed = [o for o in recent if o.actual_outcome is not None]
        if len(completed) < 5:
            return

        # Build calibration curve by confidence band
        bands: dict[str, list[MetacognitiveObservation]] = {}
        for obs in completed:
            b = obs.band.value
            if b not in bands:
                bands[b] = []
            bands[b].append(obs)

        for band, entries in bands.items():
            avg_confidence = sum(e.predicted_confidence for e in entries) / len(entries)
            actual_accuracy = sum(1 for e in entries if e.actual_outcome) / len(entries)
            self._calibration_curve[band] = (avg_confidence, actual_accuracy)

        # Calculate bias tendencies
        self._update_bias_profile(completed)

    def _update_bias_profile(self, observations: list[MetacognitiveObservation]) -> None:
        """Detect bias patterns from observation history."""
        if not observations:
            return

        correct = [o for o in observations if o.actual_outcome]
        incorrect = [o for o in observations if not o.actual_outcome]

        # Overconfidence: predicted high but failed
        overconfident = [o for o in incorrect if o.predicted_confidence > 0.7]
        self._bias_profile.overconfidence_tendency = len(overconfident) / max(len(incorrect), 1)

        # Underconfidence: predicted low but succeeded
        underconfident = [o for o in correct if o.predicted_confidence < 0.4]
        self._bias_profile.underconfidence_tendency = len(underconfident) / max(len(correct), 1)

        # Confirmation bias: repeated same approach despite mixed outcomes
        tasks = set(o.task for o in observations)
        repeated_failures = 0
        for task in tasks:
            task_obs = [o for o in observations if o.task == task]
            outcomes = [o.actual_outcome for o in task_obs if o.actual_outcome is not None]
            if len(outcomes) >= 3 and sum(outcomes) / len(outcomes) < 0.3:
                repeated_failures += 1
        self._bias_profile.confirmation_bias_score = repeated_failures / max(len(tasks), 1)

        # Recency bias: recent observations weighted too heavily
        if len(observations) >= 10:
            recent = observations[-10:]
            older = observations[:-10]
            recent_correct = sum(1 for o in recent if o.actual_outcome) / len(recent)
            older_correct = sum(1 for o in older if o.actual_outcome) / len(older) if older else 0.5
            self._bias_profile.recency_bias_score = abs(recent_correct - older_correct)

    # ── Introspection ───────────────────────────────────────────

    def get_calibration_advice(self) -> list[str]:
        """Generate actionable calibration advice based on bias profile."""
        advice: list[str] = []

        if self._bias_profile.overconfidence_tendency > self.overconfidence_threshold:
            advice.append(
                f"Overconfidence detected: reduce confidence by "
                f"{self._bias_profile.overconfidence_tendency:.0%} when evidence < 3 sources"
            )

        if self._bias_profile.underconfidence_tendency > 0.2:
            advice.append(
                f"Underconfidence detected: increase confidence when pattern "
                f"has repeated successfully > 3 times"
            )

        if self._bias_profile.confirmation_bias_score > 0.3:
            advice.append(
                f"Confirmation bias: {self._bias_profile.confirmation_bias_score:.0%} of failed "
                f"patterns were retried without strategy change"
            )

        if self._bias_profile.recency_bias_score > 0.2:
            advice.append(
                f"Recency bias: recent performance differs from historical by "
                f"{self._bias_profile.recency_bias_score:.0%}"
            )

        if self._bias_profile.overall_bias > 0.3:
            advice.append(
                f"Overall bias score {self._bias_profile.overall_bias:.2f} — "
                f"recommend strategy diversification"
            )

        return advice

    def predict_with_metacognition(self, task: str, base_confidence: float, evidence_sources: int) -> tuple[float, list[str]]:
        """
        Adjust a base confidence prediction with metacognitive calibration.
        Returns (adjusted_confidence, warnings).
        """
        flags: list[str] = []
        adjusted = base_confidence

        # Apply calibration correction
        if self._calibration_curve:
            band = self._classify_band(base_confidence).value
            if band in self._calibration_curve:
                avg_conf, actual_acc = self._calibration_curve[band]
                if avg_conf > 0:
                    calibration_factor = actual_acc / avg_conf
                    adjusted *= max(0.1, min(2.0, calibration_factor))
                    flags.append(f"calibrated: {band} factor={calibration_factor:.2f}")

        # Overclaim detection
        if base_confidence > 0.8 and evidence_sources < 2:
            adjusted *= 0.5
            flags.append("overclaim_penalty: high_confidence_but_low_evidence")

        # Bias correction
        if self._bias_profile.overconfidence_tendency > self.overconfidence_threshold:
            adjusted *= (1.0 - self._bias_profile.overconfidence_tendency * 0.3)
            flags.append("corrected: overconfidence_bias")

        return max(0.0, min(1.0, adjusted)), flags

    def _classify_band(self, confidence: float) -> ConfidenceBand:
        if confidence >= 0.95:
            return ConfidenceBand.NEAR_CERTAIN
        elif confidence >= 0.80:
            return ConfidenceBand.HIGH
        elif confidence >= 0.60:
            return ConfidenceBand.MODERATE
        elif confidence >= 0.40:
            return ConfidenceBand.LOW
        elif confidence >= 0.20:
            return ConfidenceBand.SPECULATIVE
        return ConfidenceBand.UNKNOWN

    def should_escalate(self) -> bool:
        """Determine if metacognitive state warrants escalation."""
        if self._bias_profile.overall_bias > 0.5:
            return True
        if self._bias_profile.overconfidence_tendency > 0.4:
            return True
        return False

    # ── Stats ───────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        completed = [o for o in self._observations if o.actual_outcome is not None]
        correct = sum(1 for o in completed if o.actual_outcome)
        return {
            "agent_id": self.agent_id,
            "total_decisions": len(self._observations),
            "completed_decisions": len(completed),
            "accuracy": correct / max(len(completed), 1),
            "calibration_bands": len(self._calibration_curve),
            "bias_profile": {
                "overall_bias": self._bias_profile.overall_bias,
                "overconfidence": self._bias_profile.overconfidence_tendency,
                "underconfidence": self._bias_profile.underconfidence_tendency,
                "confirmation_bias": self._bias_profile.confirmation_bias_score,
                "recency_bias": self._bias_profile.recency_bias_score,
            },
            "should_escalate": self.should_escalate(),
            "calibration_curve": {
                k: f"{v[0]:.2f}→{v[1]:.2f}" for k, v in self._calibration_curve.items()
            },
        }
