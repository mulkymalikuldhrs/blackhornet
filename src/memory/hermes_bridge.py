"""HermesMemoryBridge — unified memory for Hermes agent.

Connects BHMemoryProvider -> MemorySystem -> GraphStore -> Mnemosyne
into a single, session-aware API.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.graph.graph_store import GraphStore
from src.graph.graphify_pipeline import GraphifyPipeline
from src.memory.session import SessionMemory

logger = logging.getLogger(__name__)


@dataclass
class HermesMemoryRecord:
    memory_id: str = ""
    agent_id: str = ""
    session_id: str = ""
    memory_type: str = "episodic"  # episodic | semantic | procedural | spatial
    content: str = ""
    tags: List[str] = field(default_factory=list)
    importance: float = 0.5
    timestamp: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class HermesMemoryBridge:
    """Unified memory API for Hermes agent.

    Provides a single interface across all memory tiers:
    - Short-term (session context)
    - Long-term (GraphStore nodes)
    - Semantic (knowledge graph)
    - Episodic (session history)
    """

    def __init__(
        self,
        session_memory: Optional[SessionMemory] = None,
        pipeline: Optional[GraphifyPipeline] = None,
        hermes_home: Optional[str] = None,
    ):
        self.sessions = session_memory or SessionMemory()
        self.pipeline = pipeline or GraphifyPipeline()

        self._records: Dict[str, HermesMemoryRecord] = {}
        self._hermes_home = Path(
            hermes_home or os.getenv("HERMES_HOME", str(Path.home() / ".hermes"))
        )
        self._hermes_home.mkdir(parents=True, exist_ok=True)

        self._bridge_path = self._hermes_home / "bridge_store.json"
        self._load_bridge_store()

    # ── Core API ──────────────────────────────────────────────────

    def store(
        self,
        agent_id: str,
        session_id: str = "",
        memory_type: str = "episodic",
        content: str = "",
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a memory across all tiers."""
        import uuid
        memory_id = uuid.uuid4().hex[:12]

        record = HermesMemoryRecord(
            memory_id=memory_id,
            agent_id=agent_id,
            session_id=session_id,
            memory_type=memory_type,
            content=content,
            tags=tags or [],
            importance=importance,
            timestamp=time.time(),
            metadata=metadata or {},
        )
        self._records[memory_id] = record

        self.pipeline.emit("memory_add", source=agent_id, data={
            "key": f"{memory_type}:{memory_id}",
            "value": content[:500],
            "agent": agent_id,
            "session_id": session_id,
            "tags": tags or [],
            "importance": importance,
        })

        self._save_bridge_store()
        return memory_id

    def query(
        self,
        agent_id: str = "",
        memory_type: str = "",
        tags: Optional[List[str]] = None,
        query: str = "",
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Query memories across all tiers."""
        results = []

        for rec in self._records.values():
            if agent_id and rec.agent_id != agent_id:
                continue
            if memory_type and rec.memory_type != memory_type:
                continue
            if tags and not any(t in rec.tags for t in tags):
                continue
            if query and query.lower() not in rec.content.lower():
                continue
            results.append({
                "memory_id": rec.memory_id,
                "agent_id": rec.agent_id,
                "session_id": rec.session_id,
                "memory_type": rec.memory_type,
                "content": rec.content[:500],
                "tags": rec.tags,
                "importance": rec.importance,
                "timestamp": rec.timestamp,
            })

        results.sort(key=lambda r: r["importance"], reverse=True)
        return results[:limit]

    def recall(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Recall a specific memory by ID."""
        rec = self._records.get(memory_id)
        if not rec:
            return None
        return {
            "memory_id": rec.memory_id,
            "agent_id": rec.agent_id,
            "session_id": rec.session_id,
            "memory_type": rec.memory_type,
            "content": rec.content,
            "tags": rec.tags,
            "importance": rec.importance,
            "timestamp": rec.timestamp,
            "metadata": rec.metadata,
        }

    def forget(self, memory_id: str) -> bool:
        """Forget/delete a memory."""
        if memory_id in self._records:
            del self._records[memory_id]
            self._save_bridge_store()
            return True
        return False

    # ── Session integration ───────────────────────────────────────

    async def session_context(self, session_id: str) -> Dict[str, Any]:
        """Get full session context with memory enrichment."""
        context = await self.sessions.get_context_window(session_id)
        session_memories = self.query(
            session_id=session_id,
            limit=10,
        )
        context["hermes_memories"] = session_memories
        return context

    async def record_turn(
        self,
        session_id: str,
        user_message: str = "",
        agent_message: str = "",
        agent_id: str = "hermes",
    ):
        """Record a conversation turn in all memory tiers."""
        if user_message:
            await self.sessions.add_message(session_id, "user", user_message)
            self.pipeline.emit("conversation", source=agent_id, data={
                "session_id": session_id, "user": user_message[:200],
            })

        if agent_message:
            await self.sessions.add_message(session_id, "assistant", agent_message)
            self.pipeline.emit("conversation", source=agent_id, data={
                "session_id": session_id, "agent": agent_message[:200],
            })

    # ── Mnemosyne sync ────────────────────────────────────────────

    def sync_to_mnemosyne(self, mnemosyne_url: str = "http://localhost:3001") -> Dict[str, Any]:
        """Push bridge state to external Mnemosyne service."""
        import urllib.request
        try:
            payload = {
                "source": "hermes_memory_bridge",
                "records": len(self._records),
                "systems": self.stats(),
            }
            req = urllib.request.Request(
                f"{mnemosyne_url}/api/sync",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return {"status": "synced", "code": resp.status}
        except Exception as e:
            logger.warning("Mnemosyne sync failed: %s", e)
            return {"status": "failed", "error": str(e)}

    # ── Stats / Export ────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        return {
            "total_records": len(self._records),
            "by_type": {
                t: sum(1 for r in self._records.values() if r.memory_type == t)
                for t in set(r.memory_type for r in self._records.values())
            },
            "top_tags": self._top_tags(10),
            "graph": self.pipeline.stats(),
        }

    def export(self) -> Dict[str, Any]:
        return {
            "records": {
                mid: {
                    "agent_id": r.agent_id,
                    "session_id": r.session_id,
                    "memory_type": r.memory_type,
                    "content": r.content[:200],
                    "tags": r.tags,
                    "importance": r.importance,
                }
                for mid, r in self._records.items()
            },
            "stats": self.stats(),
        }

    def _top_tags(self, n: int = 10) -> Dict[str, int]:
        tag_counts: Dict[str, int] = {}
        for rec in self._records.values():
            for tag in rec.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        return dict(sorted(tag_counts.items(), key=lambda x: -x[1])[:n])

    def _save_bridge_store(self):
        try:
            data = {
                mid: {
                    "memory_id": r.memory_id,
                    "agent_id": r.agent_id,
                    "session_id": r.session_id,
                    "memory_type": r.memory_type,
                    "content": r.content,
                    "tags": r.tags,
                    "importance": r.importance,
                    "timestamp": r.timestamp,
                    "metadata": r.metadata,
                }
                for mid, r in self._records.items()
            }
            self._bridge_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning("Failed to save bridge store: %s", e)

    def _load_bridge_store(self):
        try:
            if self._bridge_path.exists():
                data = json.loads(self._bridge_path.read_text())
                for mid, d in data.items():
                    self._records[mid] = HermesMemoryRecord(**d)
                logger.info("Loaded %d records from bridge store", len(self._records))
        except Exception as e:
            logger.warning("Failed to load bridge store: %s", e)

    def close(self):
        self._save_bridge_store()
        self.pipeline.close()
