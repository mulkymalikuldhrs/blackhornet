"""Self-Confidence System — every action has measured confidence ≥70%."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ConfidenceEntry:
    timestamp: float
    action: str
    confidence: float
    evidence_sources: int
    outcome: Optional[bool] = None
    calibrated: bool = False


@dataclass
class PredictionRecord:
    prediction: str
    confidence: float
    outcome: Optional[bool] = None
    evidence: str = ""
    timestamp: float = 0.0


class SelfConfidenceSystem:
    """SCS — track, calibrate, and report confidence for every action."""

    CONFIDENCE_PATH: str = "data/omega/self-confidence.json"

    def __init__(self) -> None:
        self._entries: list[ConfidenceEntry] = []
        self._predictions: list[PredictionRecord] = []
        self._load()

    def _load(self) -> None:
        path = self._resolve_path()
        if os.path.isfile(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                self._entries = [ConfidenceEntry(**e) for e in data.get("entries", [])]
                self._predictions = [PredictionRecord(**p) for p in data.get("predictions", [])]
            except Exception:
                pass

    def _save(self) -> None:
        path = self._resolve_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump({
                "entries": [asdict(e) for e in self._entries[-100:]],
                "predictions": [asdict(p) for p in self._predictions[-200:]],
            }, f, indent=2)

    def _resolve_path(self) -> str:
        base = os.environ.get("DHAHERLABS", "/sdcard/dhaherlabs")
        return os.path.join(base, self.CONFIDENCE_PATH)

    def record_action(self, action: str, confidence: float, evidence_sources: int) -> ConfidenceEntry:
        entry = ConfidenceEntry(
            timestamp=time.time(),
            action=action,
            confidence=min(max(confidence, 0.0), 1.0),
            evidence_sources=evidence_sources,
        )
        self._entries.append(entry)
        self._save()
        return entry

    def record_outcome(self, entry: ConfidenceEntry, success: bool) -> None:
        for e in self._entries:
            if e is entry or (e.timestamp == entry.timestamp and e.action == entry.action):
                e.outcome = success
                e.calibrated = True
                break
        self._save()

    def record_prediction(self, prediction: str, confidence: float, evidence: str = "") -> PredictionRecord:
        rec = PredictionRecord(
            prediction=prediction,
            confidence=min(max(confidence, 0.0), 1.0),
            evidence=evidence,
            timestamp=time.time(),
        )
        self._predictions.append(rec)
        self._save()
        return rec

    def resolve_prediction(self, rec: PredictionRecord, correct: bool) -> None:
        for p in self._predictions:
            if p is rec or (p.timestamp == rec.timestamp and p.prediction == rec.prediction):
                p.outcome = correct
                break
        self._save()

    def calculate_score(self) -> dict:
        recent = [e for e in self._entries if e.calibrated][-20:]
        predictions = [p for p in self._predictions if p.outcome is not None][-20:]

        prediction_accuracy = sum(1 for p in predictions if p.outcome) / len(predictions) if predictions else 0.5
        success_rate = sum(1 for e in recent if e.outcome) / len(recent) if recent else 0.5

        calibration_score = 0.0
        if predictions:
            diffs = [abs(p.confidence - (1.0 if p.outcome else 0.0)) for p in predictions]
            calibration_score = 1.0 - (sum(diffs) / len(diffs))

        scs = prediction_accuracy * 0.4 + calibration_score * 0.3 + success_rate * 0.2 + 0.1
        return {
            "scs": round(scs * 100, 1),
            "prediction_accuracy": round(prediction_accuracy * 100, 1),
            "calibration_score": round(calibration_score * 100, 1),
            "success_rate": round(success_rate * 100, 1),
            "total_predictions": len(predictions),
            "total_actions": len(recent),
            "threshold_ok": scs >= 0.7,
        }

    def status(self) -> dict:
        score = self.calculate_score()
        return {
            **score,
            "timestamp": time.time(),
            "message": f"SCS: {score['scs']}% — {'PROCEED' if score.get('threshold_ok', False) else 'GATHER EVIDENCE'}",
        }

    def check_overclaim(self, confidence: float, evidence_sources: int) -> Optional[str]:
        if confidence > 0.8 and evidence_sources < 2:
            return f"OVERCLAIM: confidence {confidence:.0%} with only {evidence_sources} evidence source(s)"
        return None

    def action_confidence(self, action: str, complexity: str = "moderate") -> dict:
        score = self.calculate_score()
        base = score["scs"] / 100.0
        complexity_map = {"low": 0.05, "moderate": 0.0, "high": -0.1, "critical": -0.2}
        adjusted = min(max(base + complexity_map.get(complexity, 0.0), 0.0), 1.0)
        if adjusted >= 0.7:
            verdict = "PROCEED"
        elif adjusted >= 0.5:
            verdict = "PROCEED WITH CAUTION"
        elif adjusted >= 0.3:
            verdict = "GATHER EVIDENCE"
        else:
            verdict = "DO NOT PROCEED"
        return {
            "action": action,
            "scs_current": score["scs"],
            "action_confidence": round(adjusted * 100, 1),
            "complexity": complexity,
            "verdict": verdict,
            "threshold": adjusted >= 0.7,
        }
