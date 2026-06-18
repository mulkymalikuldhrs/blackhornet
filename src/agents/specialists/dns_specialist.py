"""DNS specialist — DNS management and optimization."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class DnsSpecialist(BaseAgent):
    """Specialist agent for DNS management and optimization.

    Handles record management, zone configuration, DNS health checking,
    traffic routing, and DNS analytics.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.EXECUTOR, autonomy_level=2)
        super().__init__(spec=spec, **kwargs)
        self._zones: Dict[str, Dict[str, Any]] = {}
        self._records: Dict[str, List[Dict[str, Any]]] = {}
        self._query_log: List[Dict[str, Any]] = []

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "create_zone":
            return await self._create_zone(task)
        elif action == "add_record":
            return await self._add_record(task)
        elif action == "delete_record":
            return await self._delete_record(task)
        elif action == "health_check":
            return await self._health_check(task)
        elif action == "configure_failover":
            return await self._configure_failover(task)
        elif action == "get_analytics":
            return await self._get_analytics(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "dns_query":
            domain = message.get("payload", {}).get("domain", "")
            self._query_log.append({"domain": domain, "timestamp": time.time()})
            return {"resolved": True, "domain": domain}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "zone_management", "record_management", "health_checking",
            "failover_configuration", "traffic_routing", "dns_analytics",
            "dnssec_management", "propagation_monitoring",
        ]

    async def _create_zone(self, task: Task) -> Dict[str, Any]:
        domain = task.payload.get("domain", "example.com")
        nameservers = task.payload.get("nameservers", ["ns1.provider.com", "ns2.provider.com"])

        zone = {
            "domain": domain,
            "nameservers": nameservers,
            "created_at": time.time(),
            "record_count": 0,
            "status": "active",
        }
        self._zones[domain] = zone
        self._records[domain] = []
        return {"success": True, "domain": domain, "nameservers": nameservers}

    async def _add_record(self, task: Task) -> Dict[str, Any]:
        domain = task.payload.get("domain", "example.com")
        record_type = task.payload.get("type", "A")
        name = task.payload.get("name", "@")
        value = task.payload.get("value", "")
        ttl = task.payload.get("ttl", 300)

        if domain not in self._records:
            self._records[domain] = []

        record = {
            "type": record_type,
            "name": name,
            "value": value,
            "ttl": ttl,
            "created_at": time.time(),
        }
        self._records[domain].append(record)
        if domain in self._zones:
            self._zones[domain]["record_count"] = len(self._records[domain])
        return {"success": True, "record": record, "domain": domain}

    async def _delete_record(self, task: Task) -> Dict[str, Any]:
        domain = task.payload.get("domain", "example.com")
        record_type = task.payload.get("type", "A")
        name = task.payload.get("name", "@")

        if domain in self._records:
            self._records[domain] = [
                r for r in self._records[domain]
                if not (r.get("type") == record_type and r.get("name") == name)
            ]
        return {"success": True, "domain": domain, "deleted": f"{record_type} {name}"}

    async def _health_check(self, task: Task) -> Dict[str, Any]:
        domain = task.payload.get("domain", "example.com")
        records = self._records.get(domain, [])

        health = {
            "domain": domain,
            "total_records": len(records),
            "propagation_status": "complete",
            "resolution_time_ms": 25.0,
            "status": "healthy",
        }
        return {"success": True, "health": health}

    async def _configure_failover(self, task: Task) -> Dict[str, Any]:
        domain = task.payload.get("domain", "example.com")
        primary = task.payload.get("primary", "")
        secondary = task.payload.get("secondary", "")
        health_check_url = task.payload.get("health_check_url", "/health")

        failover = {
            "domain": domain,
            "primary": primary,
            "secondary": secondary,
            "health_check_url": health_check_url,
            "status": "configured",
        }
        return {"success": True, "failover": failover}

    async def _get_analytics(self, task: Task) -> Dict[str, Any]:
        time_range = task.payload.get("time_range", 86400)
        start_time = time.time() - time_range
        recent = [q for q in self._query_log if q.get("timestamp", 0) >= start_time]

        return {"success": True, "total_queries": len(recent), "unique_domains": len(set(q.get("domain", "") for q in recent))}

    def _monitor(self) -> Dict[str, Any]:
        total_records = sum(len(r) for r in self._records.values())
        return {
            "success": True,
            "metrics": {
                "zones_count": len(self._zones),
                "total_records": total_records,
                "total_queries": len(self._query_log),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "dns",
            "metrics": self._monitor()["metrics"],
        }
