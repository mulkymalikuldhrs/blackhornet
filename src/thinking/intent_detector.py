"""IntentDetector — detect user intent from natural language messages.

Classifies user messages into intent categories using keyword matching,
pattern recognition, and n-gram similarity. Supports custom intents
and confidence scoring.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Pattern

from src.memory.semantic import ngram_similarity

logger = logging.getLogger(__name__)


@dataclass
class Intent:
    name: str = ""
    confidence: float = 0.0
    category: str = ""
    entities: Dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""


@dataclass
class IntentPattern:
    name: str = ""
    patterns: List[str] = field(default_factory=list)
    category: str = ""
    priority: int = 5
    examples: List[str] = field(default_factory=list)
    compiled: List[Pattern] = field(default_factory=list, init=False)

    def __post_init__(self):
        self.compiled = [re.compile(p, re.IGNORECASE) for p in self.patterns]


_DEFAULT_INTENTS: List[IntentPattern] = [
    IntentPattern("greeting", [r"\bhello\b", r"\bhi\b", r"\bhey\b", r"\bgood morning\b", r"\bgood evening\b"], "social", 1),
    IntentPattern("farewell", [r"\bbye\b", r"\bgoodbye\b", r"\bsee you\b", r"\bexit\b", r"\bquit\b"], "social", 1),
    IntentPattern("question", [r"\?$", r"\bwhat\b", r"\bhow\b", r"\bwhy\b", r"\bwhen\b", r"\bwhere\b", r"\bwho\b", r"\bwhich\b"], "inquiry", 3),
    IntentPattern("help", [r"\bhelp\b", r"\bguide\b", r"\btutorial\b", r"\bhow do I\b", r"\bhow to\b"], "support", 4),
    IntentPattern("feedback", [r"\bfeedback\b", r"\brating\b", r"\breview\b", r"\bthis is (good|bad|great|terrible)\b"], "feedback", 3),
    IntentPattern("command", [r"\bexecute\b", r"\brun\b", r"\bdo\b", r"\bperform\b", r"\bstart\b", r"\bstop\b"], "action", 5),
    IntentPattern("create", [r"\bcreate\b", r"\bmake\b", r"\bbuild\b", r"\bgenerate\b", r"\bwrite\b", r"\bdevelop\b"], "creation", 5),
    IntentPattern("search_query", [r"\bfind\b", r"\bsearch\b", r"\blook for\b", r"\blocate\b"], "information", 4),
    IntentPattern("status", [r"\bstatus\b", r"\bprogress\b", r"\bhow is\b.*going\b", r"\bwhat.*happening\b"], "information", 3),
    IntentPattern("setting", [r"\bchange\b", r"\bset\b", r"\bconfigure\b", r"\bpreference\b", r"\bsetting\b"], "configuration", 4),
    IntentPattern("error_report", [r"\berror\b", r"\bbug\b", r"\bissue\b", r"\bproblem\b", r"\bnot working\b", r"\bfail\b"], "support", 5),
    IntentPattern("reminder", [r"\bremind\b", r"\bremember\b", r"\bdon.?t forget\b"], "planning", 4),
    IntentPattern("goal", [r"\bgoal\b", r"\bobjective\b", r"\baim\b", r"\btarget\b", r"\bwant to\b"], "planning", 4),
]


class IntentDetector:
    """Detect user intent from messages using patterns and similarity."""

    def __init__(self, custom_intents: Optional[List[IntentPattern]] = None):
        self._intents = list(_DEFAULT_INTENTS)
        if custom_intents:
            self._intents.extend(custom_intents)
        self._examples_cache: Dict[str, str] = {}

    def detect(self, text: str) -> Intent:
        if not text:
            return Intent(name="unknown", confidence=0.0, category="unknown", raw_text=text)

        text_lower = text.strip().lower()
        scored: List[tuple[float, IntentPattern]] = []

        for intent in self._intents:
            score = 0.0
            for pattern in intent.compiled:
                match = pattern.search(text_lower)
                if match:
                    score = max(score, 0.5 + (intent.priority / 20.0))

            if intent.examples:
                best_example_sim = max(
                    (ngram_similarity(text_lower, ex.lower(), n=3) for ex in intent.examples),
                    default=0.0,
                )
                if best_example_sim > 0.3:
                    score = max(score, best_example_sim)

            if score > 0:
                scored.append((score, intent))

        if not scored:
            return Intent(name="unknown", confidence=0.0, category="general", raw_text=text)

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_intent = scored[0]

        return Intent(
            name=best_intent.name,
            confidence=min(1.0, best_score),
            category=best_intent.category,
            raw_text=text,
        )

    def detect_all(self, text: str, threshold: float = 0.3) -> List[Intent]:
        results: List[Intent] = []
        if not text:
            return results

        text_lower = text.strip().lower()
        for intent in self._intents:
            score = 0.0
            for pattern in intent.compiled:
                if pattern.search(text_lower):
                    score = max(score, 0.5 + (intent.priority / 20.0))

            if score >= threshold:
                results.append(Intent(
                    name=intent.name, confidence=min(1.0, score),
                    category=intent.category, raw_text=text,
                ))

        results.sort(key=lambda x: x.confidence, reverse=True)
        return results

    def add_custom_intent(self, name: str, patterns: List[str],
                          category: str = "custom", priority: int = 5,
                          examples: Optional[List[str]] = None) -> None:
        self._intents.append(IntentPattern(
            name=name, patterns=patterns, category=category,
            priority=priority, examples=examples or [],
        ))

    def get_categories(self) -> List[str]:
        return list(set(i.category for i in self._intents))
