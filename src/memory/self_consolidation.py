"""
Self-Consolidation — Complementary evolution for self-improving agents.
Inspired by "Self-Consolidation for Self-Evolving Agents" (arXiv:2602.01966).

Two key mechanisms:
  1. Contrastive Reflection: summarize error-prone patterns + capture
     reusable insights from both successes and failures
  2. Self-Consolidation: distill textual experience into compact
     latent representations (parameterized memories)

This enables agents to internalize experience rather than just
accumulating raw trajectories that bloat the context window.
"""
from __future__ import annotations

import json
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ReflectedInsight:
    pattern: str
    category: str
    confidence: float
    source_count: int = 1
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    success_rate: float = 1.0
    is_error_pattern: bool = False
    actionable: str = ""

    def merge(self, other: ReflectedInsight) -> None:
        self.confidence = max(self.confidence, other.confidence)
        self.source_count += other.source_count
        self.last_seen = time.time()
        if other.success_rate is not None:
            total = self.source_count
            self.success_rate = (
                (self.success_rate * (total - other.source_count) + other.success_rate * other.source_count)
                / total
            )


@dataclass
class ConsolidatedMemory:
    latent_key: str
    compressed_content: str
    importance: float
    token_count: int
    source_trajectories: list[str] = field(default_factory=list)
    abstraction_level: int = 1
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    decay_rate: float = 0.01


@dataclass
class Experience:
    task: str
    action: str
    outcome: str
    feedback: str
    success: bool
    duration: float = 0.0
    timestamp: float = field(default_factory=time.time)


class SelfConsolidation:
    """
    Complementary evolution for self-improving agents.

    Two-phase approach:
      Phase 1 — Contrastive Reflection: Compare successes vs failures
                to extract actionable patterns. Error patterns are
                explicitly tagged so agents avoid repeating them.
      Phase 2 — Self-Consolidation: Compress multiple trajectories
                into compact latent memories that preserve essential
                information while minimizing token overhead.
    """

    def __init__(
        self,
        agent_id: str = "bh-agent",
        max_insights: int = 200,
        max_consolidated: int = 100,
        consolidation_threshold: float = 0.7,
        reflection_window: int = 100,
    ):
        self.agent_id = agent_id
        self.max_insights = max_insights
        self.max_consolidated = max_consolidated
        self.consolidation_threshold = consolidation_threshold
        self.reflection_window = reflection_window

        self._insights: dict[str, ReflectedInsight] = {}
        self._consolidated: dict[str, ConsolidatedMemory] = {}
        self._experiences: list[Experience] = []
        self._consolidation_count = 0
        self._reflection_count = 0

    # ── Phase 1: Contrastive Reflection ──────────────────────────

    def record_experience(self, exp: Experience) -> None:
        """Record an experience for reflection."""
        self._experiences.append(exp)
        if len(self._experiences) > 10000:
            self._experiences = self._experiences[-5000:]

    def reflect(self, force: bool = False) -> list[ReflectedInsight]:
        """
        Contrastive Reflection: analyze recent experiences to extract
        error-prone patterns and reusable insights.

        Compares successful vs failed trajectories to identify:
        - What patterns lead to success? (positive insights)
        - What patterns lead to failure? (error patterns)
        """
        window = self._experiences[-self.reflection_window:] if not force else self._experiences
        if len(window) < 3:
            return []

        successes = [e for e in window if e.success]
        failures = [e for e in window if not e.success]

        new_insights: list[ReflectedInsight] = []

        # Extract error patterns from failures
        if failures:
            error_patterns = self._extract_patterns(failures)
            for pattern, count in error_patterns.items():
                insight = ReflectedInsight(
                    pattern=pattern,
                    category="error_pattern",
                    confidence=count / max(len(failures), 1),
                    source_count=count,
                    success_rate=0.0,
                    is_error_pattern=True,
                    actionable=f"Avoid: {pattern}",
                )
                self._upsert_insight(insight)
                new_insights.append(insight)

        # Extract success patterns from successes
        if successes:
            success_patterns = self._extract_patterns(successes)
            for pattern, count in success_patterns.items():
                if pattern not in self._insights or not self._insights[pattern].is_error_pattern:
                    insight = ReflectedInsight(
                        pattern=pattern,
                        category="success_pattern",
                        confidence=count / max(len(successes), 1),
                        source_count=count,
                        success_rate=1.0,
                        is_error_pattern=False,
                        actionable=f"Repeat: {pattern}",
                    )
                    self._upsert_insight(insight)
                    new_insights.append(insight)

        self._reflection_count += 1
        self._prune_insights()

        if new_insights:
            logger.info(
                "Reflection #%d: %d new insights (%d successes, %d failures)",
                self._reflection_count, len(new_insights), len(successes), len(failures),
            )

        return new_insights

    def get_actionable_advice(self, task: str) -> list[str]:
        """Get actionable advice for a task based on reflected insights."""
        task_lower = task.lower()
        advice = []

        for insight in self._insights.values():
            if insight.confidence < 0.3:
                continue
            if any(word in task_lower for word in insight.pattern.lower().split()):
                advice.append(insight.actionable)

        return advice[:5]

    # ── Phase 2: Self-Consolidation ──────────────────────────────

    def consolidate(self, force: bool = False) -> list[ConsolidatedMemory]:
        """
        Self-Consolidation: compress multiple trajectories into compact
        latent memories.

        When experience volume exceeds the consolidation threshold,
        similar trajectories are merged into abstracted representations
        that preserve essential knowledge while minimizing token usage.
        """
        if len(self._experiences) < 10 and not force:
            return []

        usage_ratio = len(self._experiences) / max(self.reflection_window, 1)
        if usage_ratio < self.consolidation_threshold and not force:
            return []

        clusters = self._cluster_experiences(self._experiences)
        new_consolidated: list[ConsolidatedMemory] = []

        for cluster_key, cluster in clusters.items():
            if len(cluster) < 2:
                continue

            compressed = self._compress_cluster(cluster)
            key = f"latent:{hash(cluster_key) % (10 ** 8):08x}"

            if key in self._consolidated:
                existing = self._consolidated[key]
                existing.compressed_content = self._merge_compressed(existing.compressed_content, compressed)
                existing.source_trajectories.extend(e.task for e in cluster)
                existing.access_count += 1
                existing.last_accessed = time.time()
            else:
                cm = ConsolidatedMemory(
                    latent_key=key,
                    compressed_content=compressed,
                    importance=min(1.0, len(cluster) / 20),
                    token_count=self._estimate_tokens(compressed),
                    source_trajectories=[e.task for e in cluster],
                    abstraction_level=min(5, len(cluster) // 5 + 1),
                )
                self._consolidated[key] = cm
                new_consolidated.append(cm)

        self._consolidation_count += 1
        self._prune_consolidated()

        if new_consolidated:
            logger.info(
                "Consolidation #%d: %d clusters -> %d latent memories",
                self._consolidation_count, len(clusters), len(new_consolidated),
            )

        return new_consolidated

    def recall_consolidated(self, query: str, limit: int = 5) -> list[ConsolidatedMemory]:
        """Recall consolidated memories relevant to a query."""
        query_lower = query.lower()
        scored = []

        for cm in self._consolidated.values():
            cm.last_accessed = time.time()
            cm.access_count += 1

            score = 0.0
            if query_lower in cm.compressed_content.lower():
                score += cm.importance * 2
            for src in cm.source_trajectories:
                if query_lower in src.lower():
                    score += cm.importance
                    break

            decay = math.exp(-cm.decay_rate * (time.time() - cm.last_accessed) / 3600)
            score *= decay

            if score > 0:
                scored.append((score, cm))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [cm for _, cm in scored[:limit]]

    # ── Internal ─────────────────────────────────────────────────

    def _extract_patterns(self, experiences: list[Experience]) -> dict[str, int]:
        """Extract recurring patterns from a set of experiences."""
        patterns: dict[str, int] = {}
        for exp in experiences:
            words = (exp.action + " " + exp.outcome).lower().split()
            for i in range(len(words) - 1):
                bigram = f"{words[i]} {words[i+1]}"
                if len(bigram) > 5:
                    patterns[bigram] = patterns.get(bigram, 0) + 1
        return {k: v for k, v in patterns.items() if v >= 2}

    def _upsert_insight(self, insight: ReflectedInsight) -> None:
        """Add or merge an insight."""
        if insight.pattern in self._insights:
            self._insights[insight.pattern].merge(insight)
        else:
            self._insights[insight.pattern] = insight

    def _prune_insights(self) -> None:
        """Remove low-confidence or stale insights."""
        if len(self._insights) <= self.max_insights:
            return
        sorted_insights = sorted(
            self._insights.values(),
            key=lambda i: (i.confidence, i.source_count),
            reverse=True,
        )
        self._insights = {i.pattern: i for i in sorted_insights[:self.max_insights]}

    def _cluster_experiences(self, experiences: list[Experience]) -> dict[str, list[Experience]]:
        """Cluster experiences by task similarity."""
        clusters: dict[str, list[Experience]] = {}
        for exp in experiences:
            task_key = exp.task.split(":")[0] if ":" in exp.task else exp.task[:30]
            if task_key not in clusters:
                clusters[task_key] = []
            clusters[task_key].append(exp)
        return clusters

    def _compress_cluster(self, cluster: list[Experience]) -> str:
        """Compress a cluster of experiences into a compact summary."""
        total = len(cluster)
        successes = sum(1 for e in cluster if e.success)
        failures = total - successes

        tasks = set(e.task for e in cluster)
        actions = set(e.action for e in cluster)
        outcomes = set(e.outcome for e in cluster)

        parts = [
            f"[{total} episodes | {successes}OK/{failures}FAIL]",
            f"tasks: {', '.join(list(tasks)[:5])}",
            f"actions: {', '.join(list(actions)[:5])}",
            f"outcomes: {', '.join(list(outcomes)[:3])}",
        ]
        return " | ".join(parts)

    def _merge_compressed(self, existing: str, new: str) -> str:
        """Merge compressed summaries."""
        if new not in existing:
            return f"{existing}; {new}"
        return existing

    def _estimate_tokens(self, text: str) -> int:
        """Rough token count estimate."""
        return len(text) // 4

    def _prune_consolidated(self) -> None:
        """Remove least important consolidated memories."""
        if len(self._consolidated) <= self.max_consolidated:
            return
        sorted_cm = sorted(
            self._consolidated.values(),
            key=lambda c: (c.importance * c.access_count / max(1, time.time() - c.created_at)),
            reverse=True,
        )
        self._consolidated = {c.latent_key: c for c in sorted_cm[:self.max_consolidated]}

    def get_stats(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "total_experiences": len(self._experiences),
            "total_insights": len(self._insights),
            "total_consolidated": len(self._consolidated),
            "reflection_count": self._reflection_count,
            "consolidation_count": self._consolidation_count,
            "error_patterns": sum(1 for i in self._insights.values() if i.is_error_pattern),
            "success_patterns": sum(1 for i in self._insights.values() if not i.is_error_pattern),
            "avg_insight_confidence": (
                sum(i.confidence for i in self._insights.values()) / max(len(self._insights), 1)
            ),
        }
