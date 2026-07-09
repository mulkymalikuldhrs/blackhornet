"""
MemoryFederation — Cross-agent memory sharing and synchronization.
Inspired by:
  - "Memory for Autonomous LLM Agents: Survey" (arXiv:2603.07670)
  - "MemInsight: Autonomous Memory Augmentation" (arXiv:2503.21760)
  - "AutoMem: Learning Memory as Cognitive Skill" (arXiv:2607.01224)

Provides:
  1. Cross-agent memory sharing (shared insights between agents)
  2. Memory synchronization (resolve conflicts, merge)
  3. Importance-weighted retrieval
  4. Automatic memory consolidation from agent experiences
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class FederatedMemory:
    memory_id: str
    content: str
    source_agent: str
    memory_type: str  # "insight", "pattern", "fact", "skill_ref", "warning"
    importance: float = 0.5
    confidence: float = 0.5
    tags: list[str] = field(default_factory=list)
    source_tasks: list[str] = field(default_factory=list)
    agreement_count: int = 1
    conflict_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    ttl: float = 0.0  # 0 = permanent

    @property
    def is_expired(self) -> bool:
        return self.ttl > 0 and time.time() - self.created_at > self.ttl

    @property
    def relevance_score(self) -> float:
        """Combined importance + confidence + recency."""
        age_hours = (time.time() - self.last_accessed) / 3600
        recency = math.exp(-age_hours / 24)  # half-life 24h
        return self.importance * 0.4 + self.confidence * 0.3 + recency * 0.3


@dataclass
class MemorySyncEvent:
    source_agent: str
    target_agent: str
    memory_id: str
    action: str  # "share", "merge", "conflict", "resolve"
    timestamp: float = field(default_factory=time.time)
    detail: str = ""


class MemoryFederation:
    """
    Cross-agent memory federation system.

    Agents can share insights, patterns, and knowledge across
    the colony. The federation handles:
    - Memory distribution (push/pull)
    - Conflict resolution
    - Importance-weighted consolidation
    - Automatic pruning of low-value memories
    """

    def __init__(
        self,
        colony_id: str = "bh-colony",
        max_shared_memories: int = 500,
        sync_threshold: float = 0.3,
    ):
        self.colony_id = colony_id
        self.max_shared_memories = max_shared_memories
        self.sync_threshold = sync_threshold
        self._memories: dict[str, FederatedMemory] = {}
        self._sync_log: list[MemorySyncEvent] = []
        self._agent_registry: dict[str, float] = {}  # agent_id -> last seen

    # ── Memory Creation & Sharing ───────────────────────────────

    def share_memory(
        self,
        content: str,
        source_agent: str,
        memory_type: str = "insight",
        importance: float = 0.5,
        confidence: float = 0.5,
        tags: Optional[list[str]] = None,
        source_tasks: Optional[list[str]] = None,
    ) -> FederatedMemory:
        """
        Share a memory across the federation.
        If similar memory exists, merge instead of creating duplicate.
        """
        memory_id = hashlib.md5(content.encode()).hexdigest()[:16]

        if memory_id in self._memories:
            existing = self._memories[memory_id]
            existing.agreement_count += 1
            existing.access_count += 1
            existing.last_accessed = time.time()
            existing.confidence = min(1.0, existing.confidence + 0.05)
            if source_tasks:
                existing.source_tasks.extend(source_tasks)
            return existing

        memory = FederatedMemory(
            memory_id=memory_id,
            content=content,
            source_agent=source_agent,
            memory_type=memory_type,
            importance=importance,
            confidence=confidence,
            tags=tags or [],
            source_tasks=source_tasks or [],
        )

        self._memories[memory_id] = memory
        self._agent_registry[source_agent] = time.time()

        logger.info(
            "Memory shared: %s (%s) by %s (importance=%.2f)",
            memory_id[:8], memory_type, source_agent, importance,
        )

        self._prune()
        return memory

    def report_conflict(
        self,
        memory_id: str,
        conflicting_agent: str,
        reason: str,
    ) -> None:
        """Report a conflict with an existing memory."""
        memory = self._memories.get(memory_id)
        if not memory:
            return
        memory.conflict_count += 1
        memory.confidence = max(0.0, memory.confidence - 0.1)

        self._sync_log.append(MemorySyncEvent(
            source_agent=conflicting_agent,
            target_agent=memory.source_agent,
            memory_id=memory_id,
            action="conflict",
            detail=reason,
        ))

    # ── Retrieval ───────────────────────────────────────────────

    def recall(
        self,
        query: str,
        agent_id: Optional[str] = None,
        min_importance: float = 0.0,
        memory_type: Optional[str] = None,
        limit: int = 10,
    ) -> list[FederatedMemory]:
        """Retrieve memories matching query, sorted by relevance."""
        query_lower = query.lower()
        scored: list[tuple[float, FederatedMemory]] = []

        for memory in self._memories.values():
            if memory.is_expired:
                continue
            if min_importance > 0 and memory.importance < min_importance:
                continue
            if memory_type and memory.memory_type != memory_type:
                continue

            # Text match score
            score = 0.0
            if query_lower in memory.content.lower():
                score += memory.relevance_score * 2

            # Tag match
            for tag in memory.tags:
                if query_lower in tag.lower():
                    score += memory.relevance_score * 1.5

            # Task match
            for task in memory.source_tasks:
                if query_lower in task.lower():
                    score += memory.relevance_score * 1.0

            if score > 0:
                scored.append((score, memory))

        scored.sort(key=lambda x: x[0], reverse=True)

        retrieved = [m for _, m in scored[:limit]]
        for m in retrieved:
            m.access_count += 1
            m.last_accessed = time.time()

        return retrieved

    def get_memories_by_agent(self, agent_id: str) -> list[FederatedMemory]:
        """Get all memories shared by a specific agent."""
        return [m for m in self._memories.values() if m.source_agent == agent_id]

    def get_memories_by_type(self, memory_type: str) -> list[FederatedMemory]:
        return [m for m in self._memories.values() if m.memory_type == memory_type]

    # ── Synchronization ─────────────────────────────────────────

    def sync_from(self, other_federation: MemoryFederation) -> list[MemorySyncEvent]:
        """
        Import memories from another federation node.
        Resolves conflicts via confidence + agreement_count.
        """
        events: list[MemorySyncEvent] = []
        for mem_id, mem in other_federation._memories.items():
            if mem.is_expired:
                continue

            existing = self._memories.get(mem_id)
            if not existing:
                self._memories[mem_id] = FederatedMemory(
                    memory_id=mem_id,
                    content=mem.content,
                    source_agent=mem.source_agent,
                    memory_type=mem.memory_type,
                    importance=mem.importance,
                    confidence=mem.confidence,
                    tags=list(mem.tags),
                    source_tasks=list(mem.source_tasks),
                    agreement_count=mem.agreement_count,
                )
                events.append(MemorySyncEvent(
                    source_agent=mem.source_agent,
                    target_agent=self.colony_id,
                    memory_id=mem_id,
                    action="share",
                    detail=f"synced from federation",
                ))
            elif existing.agreement_count < mem.agreement_count:
                # Remote has more agreement — resolve in its favor
                existing.agreement_count = mem.agreement_count
                existing.confidence = max(existing.confidence, mem.confidence)
                events.append(MemorySyncEvent(
                    source_agent=mem.source_agent,
                    target_agent=existing.source_agent,
                    memory_id=mem_id,
                    action="resolve",
                    detail="remote version has higher agreement",
                ))

        self._prune()
        return events

    def _prune(self) -> None:
        """Remove expired and low-value memories."""
        if len(self._memories) <= self.max_shared_memories:
            # Just remove expired
            expired = [k for k, v in self._memories.items() if v.is_expired]
            for k in expired:
                del self._memories[k]
            return

        # Sort by relevance, keep top N
        sorted_mems = sorted(
            self._memories.values(),
            key=lambda m: m.relevance_score,
            reverse=True,
        )
        self._memories = {m.memory_id: m for m in sorted_mems[:self.max_shared_memories]}

    # ── Agent Registry ──────────────────────────────────────────

    def register_agent(self, agent_id: str) -> None:
        self._agent_registry[agent_id] = time.time()

    def get_active_agents(self, max_age: float = 3600) -> list[str]:
        """Get agents that shared memories within max_age seconds."""
        now = time.time()
        return [aid for aid, last in self._agent_registry.items() if now - last < max_age]

    # ── Stats ───────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        return {
            "colony_id": self.colony_id,
            "total_memories": len(self._memories),
            "sync_events": len(self._sync_log),
            "active_agents": len(self._agent_registry),
            "memory_types": {
                t: sum(1 for m in self._memories.values() if m.memory_type == t)
                for t in set(m.memory_type for m in self._memories.values())
            },
            "avg_importance": (
                sum(m.importance for m in self._memories.values()) / max(len(self._memories), 1)
            ),
            "avg_confidence": (
                sum(m.confidence for m in self._memories.values()) / max(len(self._memories), 1)
            ),
            "total_conflicts": sum(m.conflict_count for m in self._memories.values()),
        }
