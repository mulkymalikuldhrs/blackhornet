"""MemorySystem – unified service wrapping all 7 memory sub-modules.

Provides a single entry point for:
  - Short-term memory (STM) — fast ring buffer with TTL expiry
  - Long-term memory (LTM) — persistent SQLite + FTS5
  - Semantic memory (SEM) — n-gram similarity + FTS5 hybrid
  - Episodic memory (EPI) — timeline with parent chains
  - Consolidation — STM→LTM→Semantic pipeline
  - Forgetting — decay-based archive/delete
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MemorySystemConfig:
    data_dir: str = "~/.bh/memory"
    stm_max_entries: int = 100
    stm_default_ttl: int = 3600
    consolidation_interval_hours: int = 1
    forgetting_threshold: float = 0.01
    archive_days: int = 90


class MemorySystem:
    """Unified memory service wrapping all 7 sub-modules."""

    def __init__(self, config: Optional[MemorySystemConfig] = None):
        self._config = config or MemorySystemConfig()
        data_dir = os.path.expanduser(self._config.data_dir)
        os.makedirs(data_dir, exist_ok=True)

        from src.memory.short_term import ShortTermMemory
        from src.memory.long_term import LongTermMemory
        from src.memory.semantic import SemanticMemory
        from src.memory.episodic import EpisodicMemory
        from src.memory.consolidation import MemoryConsolidator
        from src.memory.forgetting import ForgettingMechanism

        self.stm = ShortTermMemory(
            max_entries=self._config.stm_max_entries,
            default_ttl=self._config.stm_default_ttl,
        )
        self.ltm = LongTermMemory(db_path=os.path.join(data_dir, "long_term.db"))
        self.sem = SemanticMemory(db_path=os.path.join(data_dir, "semantic.db"))
        self.epi = EpisodicMemory(db_path=os.path.join(data_dir, "episodic.db"))
        self.cons = MemoryConsolidator(self.stm, self.ltm, self.sem, self.epi)
        self._forget = ForgettingMechanism(
            self.ltm, self.sem, self.epi,
            archive_dir=os.path.join(data_dir, "archive"),
        )
        self._last_consolidation: float = 0.0
        self._last_forgetting: float = 0.0
        self._initialized = False

    def initialize(self) -> None:
        """Verify all stores are accessible."""
        self.stm.stats()
        self.ltm.stats()
        self.sem.stats()
        self.epi.stats()
        self._initialized = True
        logger.info("MemorySystem initialized at %s", self._config.data_dir)

    # ── STM ────────────────────────────────────────────────────────

    def remember(self, key: str, content: str) -> bool:
        """Store in STM (fast, short-lived)."""
        self.stm.add(key, content)
        return True

    def recall_stm(self, key: str) -> Optional[str]:
        entry = self.stm.get(key)
        return entry.content if entry else None

    def recent_stm(self, limit: int = 10) -> List[str]:
        return [e.content for e in self.stm.recent(limit)]

    # ── LTM ────────────────────────────────────────────────────────

    def store(self, key: str, content: str, tags: Optional[List[str]] = None,
              importance: float = 0.5) -> int:
        return self.ltm.add(key, content, tags=tags or [], importance=importance)

    def retrieve(self, key: str) -> Optional[str]:
        entry = self.ltm.get(key)
        return entry.content if entry else None

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        results = self.ltm.search(query, limit=limit)
        return [
            {"key": r.key, "content": r.content[:200], "tags": r.tags,
             "importance": r.importance, "access_count": r.access_count}
            for r in results
        ]

    # ── Semantic ───────────────────────────────────────────────────

    def store_semantic(self, text: str, source: str = "conversation") -> int:
        return self.sem.add(text, source=source)

    def search_semantic(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        results = self.sem.search(query, limit=limit)
        return [{"id": r.id, "text": r.text[:200], "source": r.source,
                 "score": r.relevance_score} for r in results]

    def similar_to(self, text: str, threshold: float = 0.3, limit: int = 5) -> List[Dict[str, Any]]:
        results = self.sem.search_similar(text, threshold=threshold, limit=limit)
        return [{"id": r.id, "text": r.text[:200], "score": r.relevance_score} for r in results]

    # ── Episodic ───────────────────────────────────────────────────

    def record_episode(self, agent_id: str, event_type: str, summary: str,
                       outcome: str = "") -> int:
        return self.epi.add(agent_id, event_type, summary, outcome=outcome)

    def get_episodes(self, agent_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        episodes = self.epi.get_by_agent(agent_id, limit=limit)
        return [{"id": e.id, "type": e.event_type, "summary": e.summary,
                 "outcome": e.outcome, "timestamp": e.timestamp} for e in episodes]

    def get_timeline(self, start: float, end: float, limit: int = 100) -> List[Dict[str, Any]]:
        episodes = self.epi.get_timeline(start, end, limit=limit)
        return [{"id": e.id, "agent": e.agent_id, "type": e.event_type,
                 "summary": e.summary, "ts": e.timestamp} for e in episodes]

    # ── Consolidation ──────────────────────────────────────────────

    def consolidate(self, force: bool = False) -> Dict[str, Any]:
        now = time.time()
        if not force and (now - self._last_consolidation) < self._config.consolidation_interval_hours * 3600:
            return {"skipped": True, "message": "Consolidation not due yet"}
        report = self.cons.run_consolidation()
        self._last_consolidation = now
        return {
            "stm_to_ltm": report.stm_to_ltm,
            "ltm_to_semantic": report.ltm_to_semantic,
            "deduplicated": report.deduplicated,
            "archived": report.archived,
            "duration_ms": report.duration_ms,
        }

    def forget(self) -> Dict[str, Any]:
        report = self._forget.run_forgetting()
        self._last_forgetting = time.time()
        return {
            "archived": report.archived,
            "deleted": report.deleted,
            "duration_ms": report.duration_ms,
        }

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        return {
            "stm": self.stm.stats(),
            "ltm": self.ltm.stats(),
            "semantic": self.sem.stats(),
            "episodic": self.epi.stats(),
            "initialized": self._initialized,
            "last_consolidation": self._last_consolidation,
            "last_forgetting": self._last_forgetting,
        }

    # ── Lifecycle ──────────────────────────────────────────────────

    def close(self) -> None:
        self.sem.close()
        self.epi.close()
        logger.info("MemorySystem closed")
