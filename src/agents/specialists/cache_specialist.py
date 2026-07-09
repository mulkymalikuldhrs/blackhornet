"""Cache specialist — Caching strategies and cache management."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class CacheSpecialist(BaseAgent):
    """Specialist agent for caching strategies and cache management.

    Handles cache configuration, invalidation strategies, distributed caching,
    cache warming, and performance optimization through caching.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.EXECUTOR, autonomy_level=2)
        super().__init__(spec=spec, **kwargs)
        self._caches: Dict[str, Dict[str, Any]] = {}
        self._cache_entries: Dict[str, Dict[str, Any]] = {}
        self._hit_miss_stats: Dict[str, Dict[str, int]] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "configure_cache":
            return await self._configure_cache(task)
        elif action == "set":
            return await self._set_cache(task)
        elif action == "get":
            return await self._get_cache(task)
        elif action == "invalidate":
            return await self._invalidate_cache(task)
        elif action == "warm_cache":
            return await self._warm_cache(task)
        elif action == "get_stats":
            return await self._get_stats(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "cache_invalidate":
            key = message.get("payload", {}).get("key", "")
            self._cache_entries.pop(key, None)
            return {"invalidated": True, "key": key}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "cache_configuration", "cache_operations", "cache_invalidation",
            "distributed_caching", "cache_warming", "cache_analytics",
            "ttl_management", "cache_compression",
        ]

    async def _configure_cache(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_cache")
        backend = task.payload.get("backend", "memory")
        max_size = task.payload.get("max_size", 10000)
        default_ttl_seconds = task.payload.get("default_ttl_seconds", 3600)

        cache = {
            "name": name,
            "backend": backend,
            "max_size": max_size,
            "default_ttl_seconds": default_ttl_seconds,
            "eviction_policy": task.payload.get("eviction_policy", "lru"),
            "created_at": time.time(),
        }
        self._caches[name] = cache
        self._hit_miss_stats[name] = {"hits": 0, "misses": 0}
        return {"success": True, "cache": name, "config": cache}

    async def _set_cache(self, task: Task) -> Dict[str, Any]:
        cache_name = task.payload.get("cache", "default_cache")
        key = task.payload.get("key", "")
        value = task.payload.get("value", None)
        ttl_seconds = task.payload.get("ttl_seconds")

        entry = {
            "key": key,
            "value": value,
            "cache": cache_name,
            "set_at": time.time(),
            "ttl_seconds": ttl_seconds or self._caches.get(cache_name, {}).get("default_ttl_seconds", 3600),
            "access_count": 0,
        }
        self._cache_entries[key] = entry
        return {"success": True, "key": key, "cache": cache_name}

    async def _get_cache(self, task: Task) -> Dict[str, Any]:
        key = task.payload.get("key", "")
        cache_name = task.payload.get("cache", "default_cache")

        entry = self._cache_entries.get(key)
        stats = self._hit_miss_stats.setdefault(cache_name, {"hits": 0, "misses": 0})

        if entry and entry["cache"] == cache_name:
            elapsed = time.time() - entry["set_at"]
            if elapsed < entry["ttl_seconds"]:
                entry["access_count"] += 1
                stats["hits"] += 1
                return {"success": True, "hit": True, "key": key, "value": entry["value"]}
            else:
                del self._cache_entries[key]

        stats["misses"] += 1
        return {"success": True, "hit": False, "key": key, "value": None}

    async def _invalidate_cache(self, task: Task) -> Dict[str, Any]:
        key = task.payload.get("key", "")
        pattern = task.payload.get("pattern", "")

        invalidated = 0
        if key and key in self._cache_entries:
            del self._cache_entries[key]
            invalidated = 1
        elif pattern:
            keys_to_remove = [k for k in self._cache_entries if pattern in k]
            for k in keys_to_remove:
                del self._cache_entries[k]
                invalidated += 1

        return {"success": True, "invalidated_count": invalidated, "key": key, "pattern": pattern}

    async def _warm_cache(self, task: Task) -> Dict[str, Any]:
        cache_name = task.payload.get("cache", "default_cache")
        entries = task.payload.get("entries", [])

        warmed = 0
        for entry in entries:
            key = entry.get("key", "")
            value = entry.get("value")
            if key:
                self._cache_entries[key] = {
                    "key": key,
                    "value": value,
                    "cache": cache_name,
                    "set_at": time.time(),
                    "ttl_seconds": entry.get("ttl_seconds", 3600),
                    "access_count": 0,
                }
                warmed += 1

        return {"success": True, "cache": cache_name, "entries_warmed": warmed}

    async def _get_stats(self, task: Task) -> Dict[str, Any]:
        cache_name = task.payload.get("cache", "default_cache")
        stats = self._hit_miss_stats.get(cache_name, {"hits": 0, "misses": 0})
        total = stats["hits"] + stats["misses"]
        hit_rate = (stats["hits"] / total * 100) if total > 0 else 0

        return {
            "success": True,
            "cache": cache_name,
            "stats": {**stats, "total": total, "hit_rate_percent": round(hit_rate, 1)},
        }

    def _monitor(self) -> Dict[str, Any]:
        total_entries = len(self._cache_entries)
        total_hits = sum(s["hits"] for s in self._hit_miss_stats.values())
        total_misses = sum(s["misses"] for s in self._hit_miss_stats.values())
        total = total_hits + total_misses
        return {
            "success": True,
            "metrics": {
                "caches_count": len(self._caches),
                "total_entries": total_entries,
                "total_hits": total_hits,
                "total_misses": total_misses,
                "overall_hit_rate": round((total_hits / total * 100) if total > 0 else 0, 1),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "cache",
            "metrics": self._monitor()["metrics"],
        }
