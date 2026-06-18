"""CachingAuditAgent — Caching strategy validation."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

CACHING_ISSUES = {
    "no_cache_strategy": {"severity": "medium", "description": "No caching strategy"},
    "no_ttl_configured": {"severity": "high", "description": "No TTL configured"},
    "no_invalidation": {"severity": "high", "description": "No cache invalidation"},
    "cache_stampede": {"severity": "medium", "description": "Cache stampede potential"},
    "no_cache_headers": {"severity": "medium", "description": "No HTTP cache headers"},
    "infinite_ttl": {"severity": "high", "description": "Infinite TTL configured"},
    "no_cache_size_limit": {"severity": "medium", "description": "No cache size limit"},
    "no_warm_up": {"severity": "low", "description": "No cache warm-up strategy"},
    "stale_serving": {"severity": "medium", "description": "Stale content serving"},
    "no_distributed_cache": {"severity": "medium", "description": "No distributed caching"},
}


class CachingAuditAgent(BaseAgent):
    """Caching strategy validation agent.

    Features
    --------
    * Cache configuration auditing
    * TTL validation
    * Cache invalidation checking
    * Cache performance analysis
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "audit")
        if action == "audit":
            return await self._audit(task)
        elif action == "validate":
            return await self._validate(task)
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "cache_query":
            return {"findings": self._findings[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "caching_audit", "ttl_validation", "cache_invalidation_check",
            "cache_performance_analysis",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        config = task.payload.get("config", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []

        has_caching = config.get("caching_enabled", False)
        has_ttl = config.get("ttl", 0) > 0
        has_invalidation = config.get("invalidation_strategy", False)
        has_size_limit = config.get("max_size", 0) > 0

        if not has_caching:
            findings.append({"type": "no_cache_strategy", "severity": "medium", "target": target})
        if has_caching and not has_ttl:
            findings.append({"type": "no_ttl_configured", "severity": "high", "target": target})
        if has_caching and not has_invalidation:
            findings.append({"type": "no_invalidation", "severity": "high", "target": target})
        if has_caching and not has_size_limit:
            findings.append({"type": "no_cache_size_limit", "severity": "medium", "target": target})

        self._findings.extend(findings)
        return {
            "success": True,
            "target": target,
            "findings": findings,
        }

    async def _validate(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "total_findings": len(self._findings),
            "findings": self._findings[-20:],
        }
