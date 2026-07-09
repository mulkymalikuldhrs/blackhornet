"""
NeuralMemoryBridge — graph-based spreading activation memory for BlackHornet.

Wraps NeuralGraphMemory (self-contained, networkx + sqlite3) as MemoryTier.T6_NEURAL
for BlackHornet's MemoryManager. Uses neural-memory-inspired architecture but has
zero dependency on neural-memory's internal APIs.

Usage:
    bridge = NeuralMemoryBridge(data_dir="data/neural")
    nid = await bridge.remember("user set max drawdown to 5%", tags=["risk"])
    results = await bridge.recall("what is max drawdown?")
    report = await bridge.consolidate()
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.memory.neural_graph import NeuralGraphMemory, NEURON_TYPES, SYNAPSE_TYPES

logger = logging.getLogger(__name__)


class NeuralMemoryBridge:
    """Adapter between BlackHornet MemoryManager and NeuralGraphMemory.

    Provides remember/recall/forget/consolidate with spreading activation,
    synapse linking, and statistical tracking.
    """

    def __init__(
        self,
        brain_name: str = "blackhornet-main",
        data_dir: str | Path | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        if data_dir is None:
            data_dir = Path(os.environ.get("BH_DATA_DIR", "data")) / "neural"
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._brain_name = brain_name
        self._mutated = False
        self._config = config or {}
        self._ngm: NeuralGraphMemory | None = None

    # ── Async context manager ─────────────────────────────────────────

    async def __aenter__(self) -> NeuralMemoryBridge:
        await self.initialize()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.shutdown()

    async def initialize(self) -> None:
        """Initialize the underlying NeuralGraphMemory (lazy)."""
        if self._ngm is not None:
            return

        db_path = self._data_dir / f"{self._brain_name}.db"
        self._ngm = NeuralGraphMemory(db_path)
        await self._ngm.initialize()
        logger.info("NeuralMemoryBridge initialized: %s @ %s", self._brain_name, db_path)

    async def shutdown(self) -> None:
        if self._ngm:
            await self._ngm.shutdown()
            self._ngm = None

    # ── Core API ─────────────────────────────────────────────────────

    async def remember(
        self,
        content: str,
        *,
        neuron_type: str = "concept",
        tags: list[str] | None = None,
        source: str | None = None,
        importance: float = 0.5,
    ) -> str:
        """Store a memory neuron. Returns neuron ID."""
        await self._lazy_init()
        assert self._ngm is not None
        return await self._ngm.remember(
            content=content,
            neuron_type=neuron_type,
            tags=tags,
            source=source,
            importance=importance,
        )

    async def recall(
        self,
        query: str,
        *,
        limit: int = 10,
        min_score: float = 0.2,
        max_hops: int = 3,
    ) -> list[dict[str, Any]]:
        """Search memory via spreading activation.

        Returns results sorted by activation score descending.
        """
        await self._lazy_init()
        assert self._ngm is not None
        return await self._ngm.recall(
            query=query,
            limit=limit,
            min_score=min_score,
            max_hops=max_hops,
        )

    async def forget(self, neuron_id: str) -> bool:
        """Soft-delete a neuron."""
        await self._lazy_init()
        assert self._ngm is not None
        return await self._ngm.forget(neuron_id)

    async def consolidate(self) -> dict[str, Any]:
        """Run consolidation cycle: prune, Hebbian update."""
        await self._lazy_init()
        assert self._ngm is not None
        return await self._ngm.consolidate()

    async def link(
        self,
        from_id: str,
        to_id: str,
        *,
        relation: str = "related_to",
        weight: float = 0.5,
    ) -> str:
        """Create a typed synapse between two neurons."""
        await self._lazy_init()
        assert self._ngm is not None
        return await self._ngm.link(
            from_id=from_id, to_id=to_id, relation=relation, weight=weight,
        )

    async def stats(self) -> dict[str, Any]:
        """Return current brain statistics."""
        await self._lazy_init()
        assert self._ngm is not None
        s = await self._ngm.stats()
        s["brain_name"] = self._brain_name
        return s

    # ── Internals ────────────────────────────────────────────────────

    async def _lazy_init(self) -> None:
        if self._ngm is None:
            await self.initialize()
