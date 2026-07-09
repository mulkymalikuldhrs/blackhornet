"""ContextAdapter — adapt responses based on user context and history.

Adjusts response style, complexity, and content based on the user
model, conversation history, and situational context.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AdaptationResult:
    complexity: str = "medium"
    style: str = "neutral"
    temperature: float = 0.7
    max_tokens: int = 2048
    include_examples: bool = True
    include_code: bool = True
    explanation_depth: str = "moderate"
    formality: str = "neutral"


class ContextAdapter:
    """Adapt interaction parameters based on user context.

    Analyzes user profile, preferences, expertise, and feedback
    to produce adaptation parameters for response generation.
    """

    def __init__(self, user_store: Any = None, preference_learner: Any = None):
        self._user_store = user_store
        self._pref_learner = preference_learner

    def set_stores(self, user_store: Any, preference_learner: Any) -> None:
        self._user_store = user_store
        self._pref_learner = preference_learner

    def adapt(self, user_id: str, task_type: str = "", query: str = "") -> AdaptationResult:
        result = AdaptationResult()
        if not user_id:
            return result

        expertise = self._get_expertise(user_id)
        prefs = self._get_preferences(user_id)
        feedback = self._get_feedback_pattern(user_id)

        result.complexity = self._compute_complexity(expertise, task_type, prefs)
        result.style = prefs.get("communication_style", "neutral")
        result.formality = self._compute_formality(result.style)
        result.temperature = self._compute_temperature(feedback)
        result.explanation_depth = self._compute_explanation_depth(expertise, result.complexity)
        result.include_code = self._should_include_code(task_type, prefs)
        result.include_examples = result.explanation_depth != "minimal"

        return result

    def format_adaptation_block(self, user_id: str, task_type: str = "", query: str = "") -> str:
        ad = self.adapt(user_id, task_type, query)
        return json.dumps({
            "complexity": ad.complexity,
            "style": ad.style,
            "formality": ad.formality,
            "temperature": ad.temperature,
            "explanation_depth": ad.explanation_depth,
            "include_code": ad.include_code,
            "include_examples": ad.include_examples,
        })

    def _get_expertise(self, user_id: str) -> Dict[str, float]:
        if self._pref_learner:
            return self._pref_learner.get_expertise(user_id)
        return {}

    def _get_preferences(self, user_id: str) -> Dict[str, Any]:
        prefs: Dict[str, Any] = {}
        if self._user_store:
            profile = self._user_store.get_by_user_id(user_id)
            if profile:
                prefs.update(profile.preferences)
        if self._pref_learner:
            model = self._pref_learner.get_model(user_id)
            for k, p in model.preferences.items():
                prefs[k] = p.value
        return prefs

    def _get_feedback_pattern(self, user_id: str) -> Optional[Dict[str, Any]]:
        return None

    def _compute_complexity(self, expertise: Dict[str, float], task_type: str,
                            prefs: Dict[str, Any]) -> str:
        override = prefs.get("complexity", "")
        if override in ("simple", "medium", "complex"):
            return override
        if not expertise:
            return "medium"
        avg = sum(expertise.values()) / max(len(expertise), 1)
        if avg < 0.3:
            return "simple"
        if avg < 0.7:
            return "medium"
        return "complex"

    def _compute_formality(self, style: str) -> str:
        mapping = {"casual": "informal", "professional": "formal", "technical": "formal",
                   "friendly": "informal", "neutral": "neutral"}
        return mapping.get(style, "neutral")

    def _compute_temperature(self, feedback: Optional[Dict[str, Any]]) -> float:
        return 0.7

    def _compute_explanation_depth(self, expertise: Dict[str, float],
                                    complexity: str) -> str:
        if complexity == "simple":
            return "thorough"
        if not expertise:
            return "moderate"
        avg = sum(expertise.values()) / max(len(expertise), 1)
        if avg < 0.3:
            return "thorough"
        if avg < 0.7:
            return "moderate"
        return "minimal"

    def _should_include_code(self, task_type: str, prefs: Dict[str, Any]) -> bool:
        if task_type in ("creative", "general"):
            return prefs.get("include_code", True)
        return True
