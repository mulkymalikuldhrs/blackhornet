"""CDN specialist — Content delivery network optimization."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class CdnSpecialist(BaseAgent):
    """Specialist agent for content delivery network optimization.

    Handles cache rule management, origin configuration, purge operations,
    performance monitoring, and CDN analytics.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.EXECUTOR, autonomy_level=2)
        super().__init__(spec=spec, **kwargs)
        self._cache_rules: Dict[str, Dict[str, Any]] = {}
        self._origins: Dict[str, Dict[str, Any]] = {}
        self._purge_log: List[Dict[str, Any]] = []
        self._hit_stats: Dict[str, int] = {"hits": 0, "misses": 0}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "create_cache_rule":
            return await self._create_cache_rule(task)
        elif action == "configure_origin":
            return await self._configure_origin(task)
        elif action == "purge_cache":
            return await self._purge_cache(task)
        elif action == "get_hit_ratio":
            return await self._get_hit_ratio(task)
        elif action == "configure_compression":
            return await self._configure_compression(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "cdn_request":
            path = message.get("payload", {}).get("path", "")
            hit = any(path.startswith(rule.get("pattern", "")) for rule in self._cache_rules.values())
            if hit:
                self._hit_stats["hits"] += 1
            else:
                self._hit_stats["misses"] += 1
            return {"hit": hit}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "cache_rule_management", "origin_configuration", "cache_purge",
            "compression_optimization", "performance_monitoring",
            "ssl_configuration", "waf_rules", "analytics",
        ]

    async def _create_cache_rule(self, task: Task) -> Dict[str, Any]:
        pattern = task.payload.get("pattern", "/*")
        ttl_seconds = task.payload.get("ttl_seconds", 3600)
        bypass_on_cookie = task.payload.get("bypass_on_cookie", False)

        rule_id = f"rule-{int(time.time())}"
        rule = {
            "id": rule_id,
            "pattern": pattern,
            "ttl_seconds": ttl_seconds,
            "bypass_on_cookie": bypass_on_cookie,
            "created_at": time.time(),
        }
        self._cache_rules[rule_id] = rule
        return {"success": True, "rule_id": rule_id, "pattern": pattern}

    async def _configure_origin(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_origin")
        address = task.payload.get("address", "origin.example.com")
        port = task.payload.get("port", 443)
        protocol = task.payload.get("protocol", "https")

        origin = {
            "name": name,
            "address": address,
            "port": port,
            "protocol": protocol,
            "created_at": time.time(),
            "health": "healthy",
        }
        self._origins[name] = origin
        return {"success": True, "origin": name, "address": address}

    async def _purge_cache(self, task: Task) -> Dict[str, Any]:
        pattern = task.payload.get("pattern", "/*")
        purge_type = task.payload.get("type", "selective")

        purge = {
            "pattern": pattern,
            "type": purge_type,
            "purged_at": time.time(),
            "estimated_purge_count": 500 if purge_type == "full" else 50,
        }
        self._purge_log.append(purge)
        return {"success": True, "purge": purge}

    async def _get_hit_ratio(self, task: Task) -> Dict[str, Any]:
        total = self._hit_stats["hits"] + self._hit_stats["misses"]
        hit_ratio = (self._hit_stats["hits"] / total * 100) if total > 0 else 0
        return {
            "success": True,
            "hit_ratio": round(hit_ratio, 1),
            "total_requests": total,
            **self._hit_stats,
        }

    async def _configure_compression(self, task: Task) -> Dict[str, Any]:
        algorithms = task.payload.get("algorithms", ["gzip", "brotli"])
        min_size_bytes = task.payload.get("min_size_bytes", 1024)
        content_types = task.payload.get("content_types", ["text/*", "application/json", "application/javascript"])

        config = {
            "algorithms": algorithms,
            "min_size_bytes": min_size_bytes,
            "content_types": content_types,
            "enabled": True,
        }
        return {"success": True, "compression_config": config}

    def _monitor(self) -> Dict[str, Any]:
        total = self._hit_stats["hits"] + self._hit_stats["misses"]
        return {
            "success": True,
            "metrics": {
                "cache_rules": len(self._cache_rules),
                "origins": len(self._origins),
                "purge_count": len(self._purge_log),
                "hit_ratio": round((self._hit_stats["hits"] / total * 100) if total > 0 else 0, 1),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "cdn",
            "metrics": self._monitor()["metrics"],
        }
