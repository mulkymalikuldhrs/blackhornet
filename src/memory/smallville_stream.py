"""Smallville Memory Stream — 3-factor retrieval + reflection synthesis.

Port of Autonomous Organism's memory-stream.ts (Generative Agents paper).
Implements the 3-factor scoring from 'Generative Agents: Interactive Simulacra
of Human Behavior' (Park et al. 2023):

  score = α × recency + β × relevance + γ × importance

Where:
  - recency: exponential decay over time (half-life = 24h)
  - relevance: cosine similarity between query and memory
  - importance: explicit importance score (0-10) assigned on creation

Plus reflection synthesis when accumulated importance crosses threshold.

Integrates with BH's existing memory systems as a complementary retrieval layer.
"""

from __future__ import annotations

import asyncio
import json
import math
import time
import hashlib
from dataclasses import dataclass, field
from typing import Any, Optional

from src.config.logging_config import get_logger

logger = get_logger(__name__)


# ── Constants ──────────────────────────────────────────────────────────

RECENCY_HALF_LIFE_SECONDS = 24 * 3600  # 24 hours half-life
REFLECTION_THRESHOLD = 150  # sum of importance scores before reflection triggers
DEFAULT_ALPHA = 0.3  # recency weight
DEFAULT_BETA = 0.4   # relevance weight
DEFAULT_GAMMA = 0.3  # importance weight
MAX_RETRIEVAL = 15   # max memories per query


# ── Types ──────────────────────────────────────────────────────────────

@dataclass
class SmallvilleMemory:
    """A single memory record ala Generative Agents."""
    id: str
    content: str
    importance: float  # 0-10 scale
    embedding: list[float]  # pseudo-embedding (128-dim TF-IDF-like)
    created_at: float  # epoch seconds
    agent_id: str = ""
    memory_type: str = "observation"  # observation | reflection | thought
    keywords: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)  # for reflections, links to source obs
    access_count: int = 0
    last_accessed: float = 0.0


@dataclass
class RetrievalScore:
    """Score for a retrieved memory with component breakdown."""
    total: float
    recency: float
    relevance: float
    importance: float


@dataclass
class RetrievedMemory:
    """A memory with its retrieval score."""
    memory: SmallvilleMemory
    score: RetrievalScore


# ── Pseudo-Embedding (TF-IDF style) ───────────────────────────────────

class PseudoEmbedding:
    """Generate pseudo-embeddings using TF-IDF-like bag-of-words hashing.

    Produces consistent 128-dim vectors from text for similarity comparison.
    No external dependencies or models needed.
    """

    DIM = 128

    @classmethod
    def generate(cls, text: str) -> list[float]:
        """Generate a 128-dim pseudo-embedding from text."""
        vec = [0.0] * cls.DIM
        words = text.lower().split()
        if not words:
            return vec

        for word in words:
            h = hashlib.md5(word.encode()).digest()
            # Use first 8 bytes to determine position and value
            for i in range(4):
                idx = (h[i * 2] + h[i * 2 + 1] * 256) % cls.DIM
                freq = words.count(word) / len(words)
                vec[idx] += freq * (0.5 + (h[i] / 255.0) * 0.5)

        # Normalize
        mag = math.sqrt(sum(v * v for v in vec))
        if mag > 0:
            vec = [v / mag for v in vec]
        return vec

    @classmethod
    def cosine_similarity(cls, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0
        dot = sum(ai * bi for ai, bi in zip(a, b))
        mag_a = math.sqrt(sum(ai * ai for ai in a))
        mag_b = math.sqrt(sum(bi * bi for bi in b))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)


# ── Scoring ────────────────────────────────────────────────────────────

def recency_score(created_at: float, now: float | None = None) -> float:
    """Exponential decay: newer memories score higher.

    Score = exp(-ln(2) * age_hours / half_life_hours)
    """
    if now is None:
        now = time.time()
    age_seconds = max(0, now - created_at)
    return math.exp(-math.log(2) * age_seconds / RECENCY_HALF_LIFE_SECONDS)


def importance_score(importance: float) -> float:
    """Normalize importance to 0-1 range (divide by 10)."""
    return min(1.0, importance / 10.0)


def retrieval_score(
    memory: SmallvilleMemory,
    query_embedding: list[float],
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
    gamma: float = DEFAULT_GAMMA,
    now: float | None = None,
) -> RetrievalScore:
    """Compute 3-factor retrieval score for a memory given a query.

    score = α × recency + β × relevance + γ × importance

    Args:
        memory: The memory to score.
        query_embedding: Pseudo-embedding of the query.
        alpha: Recency weight (default 0.3).
        beta: Relevance weight (default 0.4).
        gamma: Importance weight (default 0.3).
        now: Current time for recency calculation.

    Returns:
        RetrievalScore with total and component scores.
    """
    r_recency = recency_score(memory.created_at, now)
    r_relevance = PseudoEmbedding.cosine_similarity(query_embedding, memory.embedding)
    r_importance = importance_score(memory.importance)

    total = alpha * r_recency + beta * r_relevance + gamma * r_importance
    return RetrievalScore(
        total=total,
        recency=r_recency,
        relevance=r_relevance,
        importance=r_importance,
    )


# ── Memory Stream ──────────────────────────────────────────────────────

class SmallvilleStream:
    """Memory stream implementing Generative Agents 3-factor retrieval.

    Manages a collection of SmallvilleMemory records with:
    - Insert with automatic importance estimation
    - 3-factor retrieval (recency × relevance × importance)
    - Reflection synthesis when importance threshold crossed
    - Pseudo-embedding generation for relevance computation

    Integrates with BH's existing memory systems (STM, LTM, etc.)
    as a complementary retrieval layer optimized for simulation-style
    agent memory.
    """

    def __init__(
        self,
        memory_limit: int = 500,
        alpha: float = DEFAULT_ALPHA,
        beta: float = DEFAULT_BETA,
        gamma: float = DEFAULT_GAMMA,
    ) -> None:
        self._memories: list[SmallvilleMemory] = []
        self._memory_limit = memory_limit
        self._alpha = alpha
        self._beta = beta
        self._gamma = gamma
        self._total_inserted = 0
        self._total_reflections = 0
        self._unreflected_importance: float = 0.0

        # LLM client for reflection synthesis (optional — uses JeumpaBrain by default)
        self._llm = None

    def set_llm(self, llm_client: Any) -> None:
        """Set an LLM client for reflection synthesis.

        The client must have a `chat(message, ...)` or `ask(query, ...)` method.
        """
        self._llm = llm_client

    def insert(
        self,
        content: str,
        importance: float | None = None,
        agent_id: str = "",
        memory_type: str = "observation",
        keywords: list[str] | None = None,
    ) -> SmallvilleMemory:
        """Insert a new memory into the stream.

        Args:
            content: Memory content text.
            importance: Explicit importance (0-10). Auto-estimated if None.
            agent_id: Optional agent/citizen identifier.
            memory_type: 'observation', 'reflection', or 'thought'.
            keywords: Optional list of keywords for search.

        Returns:
            The created SmallvilleMemory.
        """
        if importance is None:
            importance = self._estimate_importance(content)

        embedding = PseudoEmbedding.generate(content)

        mem_id = hashlib.md5(
            f"{content}:{importance}:{time.time()}:{agent_id}".encode()
        ).hexdigest()[:16]

        memory = SmallvilleMemory(
            id=mem_id,
            content=content,
            importance=min(10.0, max(0.0, importance)),
            embedding=embedding,
            created_at=time.time(),
            agent_id=agent_id,
            memory_type=memory_type,
            keywords=keywords or [],
            access_count=0,
            last_accessed=time.time(),
        )

        self._memories.append(memory)
        self._total_inserted += 1
        self._unreflected_importance += memory.importance

        # Trim oldest if over limit
        if len(self._memories) > self._memory_limit:
            self._memories.sort(key=lambda m: m.created_at)
            self._memories = self._memories[-self._memory_limit:]

        logger.debug(
            "smallville_insert id=%s importance=%.1f total=%d",
            mem_id, memory.importance, len(self._memories),
        )

        return memory

    async def retrieve(
        self,
        query: str,
        limit: int = MAX_RETRIEVAL,
        agent_id: str | None = None,
        memory_type: str | None = None,
        recency_weight: float | None = None,
        relevance_weight: float | None = None,
        importance_weight: float | None = None,
    ) -> list[RetrievedMemory]:
        """Retrieve memories using 3-factor scoring.

        Args:
            query: Query text to match against.
            limit: Max results to return.
            agent_id: Filter by agent. None = all agents.
            memory_type: Filter by type. None = all types.
            recency_weight: Override alpha (default 0.3).
            relevance_weight: Override beta (default 0.4).
            importance_weight: Override gamma (default 0.3).

        Returns:
            List of RetrievedMemory sorted by score (descending).
        """
        alpha = recency_weight if recency_weight is not None else self._alpha
        beta = relevance_weight if relevance_weight is not None else self._beta
        gamma = importance_weight if importance_weight is not None else self._gamma
        now = time.time()

        # Filter
        candidates = self._memories
        if agent_id:
            candidates = [m for m in candidates if m.agent_id == agent_id]
        if memory_type:
            candidates = [m for m in candidates if m.memory_type == memory_type]

        if not candidates:
            return []

        query_embedding = PseudoEmbedding.generate(query)

        scored = []
        for memory in candidates:
            score = retrieval_score(memory, query_embedding, alpha, beta, gamma, now)
            scored.append(RetrievedMemory(memory=memory, score=score))

        # Sort by total score descending
        scored.sort(key=lambda x: x.score.total, reverse=True)

        # Update access counts for retrieved memories
        for rm in scored[:limit]:
            rm.memory.access_count += 1
            rm.memory.last_accessed = now

        return scored[:limit]

    def should_reflect(self) -> bool:
        """Check if accumulated importance crosses reflection threshold."""
        return self._unreflected_importance >= REFLECTION_THRESHOLD

    async def reflect(self, agent_context: str = "") -> list[SmallvilleMemory]:
        """Synthesize reflections from recent important memories.

        Returns:
            List of new reflection memories created.
        """
        if not self.should_reflect() and not agent_context:
            return []

        # Get most important recent memories
        sorted_memories = sorted(
            self._memories,
            key=lambda m: m.importance,
            reverse=True,
        )[:20]

        reflections: list[SmallvilleMemory] = []
        context = "\n".join(
            f"- {m.content} (importance: {m.importance:.1f})"
            for m in sorted_memories
        )

        # Try LLM-based reflection synthesis
        reflection_texts: list[str] = []
        if self._llm:
            try:
                prompt = (
                    f"Based on these memories, synthesize 3 high-level insights or reflections.\n"
                    f"Each reflection should be a general truth derived from multiple memories.\n\n"
                    f"Agent context: {agent_context}\n\n"
                    f"Memories:\n{context}\n\n"
                    f"Generate exactly 3 reflections, one per line, starting with '- '"
                )

                if hasattr(self._llm, "chat"):
                    if asyncio.iscoroutinefunction(self._llm.chat):
                        result = await self._llm.chat(prompt, task="reasoning")
                    else:
                        result = self._llm.chat(prompt, task="reasoning")
                elif hasattr(self._llm, "ask"):
                    if asyncio.iscoroutinefunction(self._llm.ask):
                        result = await self._llm.ask(prompt)
                    else:
                        result = self._llm.ask(prompt)
                else:
                    result = None

                if result and hasattr(result, "content") and result.content:
                    for line in result.content.split("\n"):
                        line = line.strip().lstrip("- ")
                        if line and len(line) > 20:
                            reflection_texts.append(line)
                elif result and hasattr(result, "answer") and result.answer:
                    for line in result.answer.split("\n"):
                        line = line.strip().lstrip("- ")
                        if line and len(line) > 20:
                            reflection_texts.append(line)
            except Exception as e:
                logger.debug("smallville_reflection_llm_error err=%s", e)

        # Fallback: keyword-based reflection if LLM fails
        if not reflection_texts:
          # Extract common keywords as pseudo-reflections
            all_keywords = []
            for m in sorted_memories[:10]:
                all_keywords.extend(m.keywords or m.content.lower().split()[:5])
            common_words = set(w for w in all_keywords if len(w) > 4)
            if common_words:
                reflection_texts.append(
                    f"Multiple memories reference: {', '.join(list(common_words)[:5])}"
                )
            # Add importance-based summary
            avg_importance = sum(m.importance for m in sorted_memories[:10]) / min(10, len(sorted_memories))
            reflection_texts.append(
                f"Recent memories have average importance of {avg_importance:.1f}/10"
            )

        # Create reflection memories
        source_ids = [m.id for m in sorted_memories[:10]]
        for text in reflection_texts[:3]:
            reflection = self.insert(
                content=text,
                importance=7.0,  # Reflections are inherently important
                memory_type="reflection",
                keywords=["reflection", "insight"],
            )
            reflection.source_ids = source_ids
            reflections.append(reflection)

        self._total_reflections += len(reflections)
        self._unreflected_importance = 0.0  # Reset counter

        logger.info(
            "smallville_reflection count=%d total=%d",
            len(reflections), self._total_reflections,
        )

        return reflections

    def get_recent(self, limit: int = 10, agent_id: str | None = None) -> list[SmallvilleMemory]:
        """Get most recent memories."""
        candidates = self._memories
        if agent_id:
            candidates = [m for m in candidates if m.agent_id == agent_id]
        candidates.sort(key=lambda m: m.created_at, reverse=True)
        return candidates[:limit]

    def get_important(self, limit: int = 10, agent_id: str | None = None) -> list[SmallvilleMemory]:
        """Get most important memories."""
        candidates = self._memories
        if agent_id:
            candidates = [m for m in candidates if m.agent_id == agent_id]
        candidates.sort(key=lambda m: m.importance, reverse=True)
        return candidates[:limit]

    def get_stats(self) -> dict[str, Any]:
        """Get stream statistics."""
        return {
            "total_memories": len(self._memories),
            "total_inserted": self._total_inserted,
            "total_reflections": self._total_reflections,
            "memory_limit": self._memory_limit,
            "unreflected_importance": self._unreflected_importance,
            "should_reflect": self.should_reflect(),
            "avg_importance": (
                sum(m.importance for m in self._memories) / len(self._memories)
                if self._memories else 0.0
            ),
            "avg_age_seconds": (
                (time.time() - sum(m.created_at for m in self._memories) / len(self._memories))
                if self._memories else 0.0
            ),
        }

    def clear(self, agent_id: str | None = None) -> int:
        """Clear memories. If agent_id provided, only that agent's memories."""
        if agent_id:
            before = len(self._memories)
            self._memories = [m for m in self._memories if m.agent_id != agent_id]
            return before - len(self._memories)
        else:
            count = len(self._memories)
            self._memories.clear()
            self._unreflected_importance = 0.0
            return count

    def to_dict(self, limit: int = 50) -> list[dict[str, Any]]:
        """Export memories as dicts for serialization."""
        sorted_mems = sorted(
            self._memories, key=lambda m: m.created_at, reverse=True
        )[:limit]
        return [
            {
                "id": m.id,
                "content": m.content[:200],
                "importance": m.importance,
                "type": m.memory_type,
                "created_at": m.created_at,
                "agent_id": m.agent_id,
                "access_count": m.access_count,
                "keywords": m.keywords,
            }
            for m in sorted_mems
        ]

    # ── Private ──

    @staticmethod
    def _estimate_importance(text: str) -> float:
        """Estimate importance of a memory based on content heuristics.

        Scores 0-10 based on:
        - Presence of emotional/high-impact words
        - Length (longer = more detailed = more important)
        - Question marks (curiosity)
        - Exclamation marks (emotional intensity)
        - First-person references (personal relevance)
        """
        score = 3.0  # Base importance

        # Emotional/high-impact keywords
        high_impact = {
            "discover": 3, "invent": 4, "create": 3, "found": 3,
            "revolution": 4, "important": 2, "critical": 3,
            "emergency": 4, "breakthrough": 4, "achievement": 3,
            "fail": 2, "success": 2, "win": 2, "loss": 2,
            "love": 3, "hate": 3, "danger": 3, "threat": 3,
            "promotion": 2, "demotion": 2, "birth": 4, "death": 5,
            "marriage": 3, "conflict": 3, "resolution": 2,
            "secret": 2, "betray": 3, "ally": 2, "enemy": 2,
        }

        lower = text.lower()
        for word, boost in high_impact.items():
            if word in lower:
                score += boost * 0.5

        # Length bonus (detailed memories are more important)
        word_count = len(text.split())
        if word_count > 50:
            score += 2
        elif word_count > 20:
            score += 1

        # Punctuation signals
        if "?" in text:
            score += 0.5  # Curiosity
        if "!" in text:
            score += 1.0  # Emotional intensity
        if "I" in text or "my" in lower:
            score += 0.5  # Personal relevance

        return min(10.0, max(0.0, score))
