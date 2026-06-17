from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MemoryAdapter:
    """Bridge between new MemorySystem and BH's MemoryBridge/MnemosyneBridge.

    Provides a unified memory interface that routes through:
    1. New MemorySystem (short/long/semantic/episodic)
    2. BH MemoryBridge (Git-based swarm sync)
    3. MnemosyneBridge (knowledge graph)
    """

    def __init__(self, memory_system=None, memory_bridge=None,
                 mnemosyne_bridge=None):
        self._memory = memory_system
        self._bridge = memory_bridge
        self._mnemosyne = mnemosyne_bridge

    def set_services(self, memory_system=None, memory_bridge=None,
                     mnemosyne_bridge=None):
        if memory_system:
            self._memory = memory_system
        if memory_bridge:
            self._bridge = memory_bridge
        if mnemosyne_bridge:
            self._mnemosyne = mnemosyne_bridge

    def store(self, key: str, content: str,
              tags: Optional[List[str]] = None,
              source: str = "bh") -> bool:
        ok = True
        if self._memory:
            self._memory.add(key, content, tags=tags or [])
        if self._bridge:
            try:
                self._bridge.log_memory(f"[{source}] {key}: {content[:200]}")
            except Exception as exc:
                logger.warning("MemoryBridge.log_memory failed: %s", exc)
                ok = False
        if self._mnemosyne:
            try:
                self._mnemosyne.store_knowledge(
                    key, content, tags=tags or [], source=source,
                )
            except Exception as exc:
                logger.warning("MnemosyneBridge.store_knowledge failed: %s", exc)
                ok = False
        return ok

    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        if self._memory:
            try:
                items = self._memory.search(query, limit=limit)
                for item in items:
                    results.append({
                        "source": "memory_system",
                        "key": item.get("key", ""),
                        "content": item.get("content", ""),
                        "score": item.get("score", 0),
                    })
            except Exception as exc:
                logger.warning("MemorySystem.search failed: %s", exc)
        if self._mnemosyne:
            try:
                items = self._mnemosyne.query_knowledge(query, limit=limit)
                for item in items:
                    results.append({
                        "source": "mnemosyne",
                        "key": item.get("title", ""),
                        "content": item.get("content", ""),
                        "score": item.get("score", 0),
                    })
            except Exception as exc:
                logger.warning("MnemosyneBridge.query_knowledge failed: %s", exc)
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results[:limit]

    def status(self) -> Dict[str, str]:
        status: Dict[str, str] = {}
        status["memory_system"] = "ok" if self._memory else "unavailable"
        status["memory_bridge"] = "ok" if self._bridge else "unavailable"
        status["mnemosyne"] = "ok" if self._mnemosyne else "unavailable"
        return status
