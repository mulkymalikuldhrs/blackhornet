"""BlackHornet Memory Provider — BH MemoryProvider plugin.

Uses MemorySystem (STM + LTM + Semantic + Episodic + Consolidation + Forgetting)
as a drop-in memory backend for Nous Hermes Agent.

Registration:
  Place this in plugins/memory/bh_memory/ and add to BH config:
    memory:
      provider: bh_memory

Or register explicitly:
    from plugins.memory.bh_memory import BHMemoryProvider
    context.register_memory_provider(BHMemoryProvider())
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from agent.memory_provider import MemoryProvider
except ImportError:
    from ._stubs import MemoryProvider

logger = logging.getLogger(__name__)

_MIN_CAPTURE_LENGTH = 10
_DEFAULT_MAX_RECALL = 10


STORE_SCHEMA: Dict[str, Any] = {
    "name": "bh_store",
    "description": "Store a memory in long-term memory. Use for facts, preferences, and information worth remembering.",
    "parameters": {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Unique key for this memory"},
            "content": {"type": "string", "description": "Memory content to store"},
            "importance": {"type": "number", "description": "Importance 0.0-1.0 (default 0.5)"},
        },
        "required": ["key", "content"],
    },
}

SEARCH_SCHEMA: Dict[str, Any] = {
    "name": "bh_search",
    "description": "Search long-term and semantic memory for relevant information.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "limit": {"type": "integer", "description": "Max results (default 5)"},
        },
        "required": ["query"],
    },
}

FORGET_SCHEMA: Dict[str, Any] = {
    "name": "bh_forget",
    "description": "Remove a memory entry by key or search query.",
    "parameters": {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Memory key to forget"},
        },
        "required": ["key"],
    },
}


class BHMemoryProvider(MemoryProvider):
    """BH MemoryProvider backed by BlackHornet MemorySystem."""

    def __init__(self):
        self._session_id = ""
        self._turn_count = 0
        self._active = False
        self._bh_home = ""
        self._data_dir = ""
        self._write_enabled = True
        self._session_turns: List[Dict[str, str]] = []
        self._sync_lock = threading.Lock()
        self._prefetch_cache = ""
        self._last_maintenance: float = 0.0
        self._system: Any = None

    @property
    def name(self) -> str:
        return "bh_memory"

    def is_available(self) -> bool:
        try:
            from src.memory.system import MemorySystem
            MemorySystem
            return True
        except Exception:
            return False

    def get_config_schema(self) -> List[Dict[str, Any]]:
        return [
            {"key": "data_dir", "description": "Memory data directory", "required": False, "default": "~/.bh/memory"},
        ]

    def initialize(self, session_id: str, **kwargs) -> None:
        from hermes_constants import get_hermes_home
        self._bh_home = kwargs.get("hermes_home") or str(get_hermes_home())
        self._session_id = session_id
        self._turn_count = 0

        self._data_dir = os.path.join(self._bh_home, "bh_memory")
        os.makedirs(self._data_dir, exist_ok=True)

        from src.memory.system import MemorySystem, MemorySystemConfig
        config = MemorySystemConfig(data_dir=self._data_dir)
        self._system = MemorySystem(config=config)
        self._system.initialize()

        agent_context = kwargs.get("agent_context", "")
        self._write_enabled = agent_context not in {"cron", "flush", "subagent"}
        self._active = True
        logger.info("BHMemoryProvider initialized: session=%s dir=%s", session_id, self._data_dir)

    def system_prompt_block(self) -> str:
        if not self._active:
            return ""
        return (
            "# BlackHornet Memory\n"
            "Active. Persistent long-term memory with semantic search.\n"
            "Use bh_store to remember facts, bh_search to recall.\n"
        )

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        if not self._active or not self._system:
            return ""
        if self._prefetch_cache:
            result = self._prefetch_cache
            self._prefetch_cache = ""
            return result
        try:
            results = self._system.search(query, limit=_DEFAULT_MAX_RECALL)
            sem_results = self._system.search_semantic(query, limit=_DEFAULT_MAX_RECALL)
            all_results = results + sem_results
            if not all_results:
                return ""
            lines = ["<bh-memory-context>", "Relevant memories:"]
            for r in all_results[:5]:
                content = r.get("content") or r.get("text", "")
                lines.append(f"  - {content[:200]}")
            lines.append("</bh-memory-context>")
            return "\n".join(lines)
        except Exception:
            logger.warning("Prefetch failed", exc_info=True)
            return ""

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        def _do_prefetch():
            try:
                self._prefetch_cache = self.prefetch(query, session_id=session_id)
            except Exception:
                pass
        thread = threading.Thread(target=_do_prefetch, daemon=True)
        thread.start()

    def sync_turn(self, user_content: str, assistant_content: str, *,
                  session_id: str = "", messages: Optional[List[Dict[str, Any]]] = None) -> None:
        if not self._active or not self._system:
            return
        with self._sync_lock:
            self._session_turns.append({"user": user_content, "assistant": assistant_content})

        self._record_episode("user", user_content[:200])
        self._record_episode("assistant", assistant_content[:200])

        if len(user_content.strip()) >= _MIN_CAPTURE_LENGTH:
            self._system.remember(f"turn_{self._turn_count}_{int(time.time())}", user_content[:500])

        self._maintenance_check()

    def _record_episode(self, agent_id: str, summary: str) -> None:
        try:
            self._system.record_episode(agent_id, "message", summary)
        except Exception:
            pass

    def _maintenance_check(self) -> None:
        now = time.time()
        if now - self._last_maintenance < 300:
            return
        self._last_maintenance = now
        try:
            self._system.consolidate()
            self._system.forget()
        except Exception:
            logger.warning("Maintenance cycle failed", exc_info=True)

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [STORE_SCHEMA, SEARCH_SCHEMA, FORGET_SCHEMA]

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        if not self._active or not self._system:
            return json.dumps({"error": "BH Memory is not initialized"})

        tool_map = {
            "bh_store": self._tool_store,
            "bh_search": self._tool_search,
            "bh_forget": self._tool_forget,
        }
        handler = tool_map.get(tool_name)
        if handler:
            return handler(args)
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    def _tool_store(self, args: Dict[str, Any]) -> str:
        key = str(args.get("key", "")).strip()
        content = str(args.get("content", "")).strip()
        importance = float(args.get("importance", 0.5))
        if not key or not content:
            return json.dumps({"error": "key and content are required"})
        eid = self._system.store(key, content, importance=importance)
        self._record_episode("system", f"Stored memory: {key}")
        return json.dumps({"stored": True, "key": key, "id": eid, "preview": content[:80]})

    def _tool_search(self, args: Dict[str, Any]) -> str:
        query = str(args.get("query", "")).strip()
        limit = max(1, min(20, int(args.get("limit", 5))))
        if not query:
            return json.dumps({"error": "query is required"})
        results = self._system.search(query, limit=limit)
        sem_results = self._system.search_semantic(query, limit=limit)
        all_results = results + sem_results
        formatted = []
        seen = set()
        for r in all_results:
            rid = r.get("key") or str(r.get("id", ""))
            if rid in seen:
                continue
            seen.add(rid)
            formatted.append({
                "key": r.get("key", ""),
                "content": r.get("content") or r.get("text", ""),
                "importance": r.get("importance", 0),
                "access_count": r.get("access_count", 0),
            })
        return json.dumps({"results": formatted[:limit], "count": min(len(formatted), limit)})

    def _tool_forget(self, args: Dict[str, Any]) -> str:
        key = str(args.get("key", "")).strip()
        if not key:
            return json.dumps({"error": "key is required"})
        removed = self._system.ltm.remove(key)
        return json.dumps({"forgotten": removed, "key": key})

    def shutdown(self) -> None:
        if self._system:
            try:
                self._system.consolidate(force=True)
            except Exception:
                pass
            self._system.close()
        self._active = False
        logger.info("BHMemoryProvider shut down")


def register(ctx):
    ctx.register_memory_provider(BHMemoryProvider())
