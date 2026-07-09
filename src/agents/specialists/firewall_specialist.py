"""Firewall specialist — Firewall configuration and management."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class FirewallSpecialist(BaseAgent):
    """Specialist agent for firewall configuration and management.

    Handles rule management, policy configuration, traffic filtering,
    intrusion prevention, and firewall monitoring.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY, autonomy_level=3)
        super().__init__(spec=spec, **kwargs)
        self._rules: Dict[str, Dict[str, Any]] = {}
        self._policies: Dict[str, Dict[str, Any]] = {}
        self._traffic_log: List[Dict[str, Any]] = []

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "add_rule":
            return await self._add_rule(task)
        elif action == "delete_rule":
            return await self._delete_rule(task)
        elif action == "configure_policy":
            return await self._configure_policy(task)
        elif action == "analyze_traffic":
            return await self._analyze_traffic(task)
        elif action == "block_ip":
            return await self._block_ip(task)
        elif action == "get_rule_stats":
            return await self._get_rule_stats(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "firewall_event":
            event = message.get("payload", {})
            self._traffic_log.append({**event, "timestamp": time.time()})
            return {"event_logged": True}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "rule_management", "policy_configuration", "traffic_filtering",
            "ip_blocking", "traffic_analysis", "intrusion_prevention",
            "log_analysis", "rule_statistics",
        ]

    async def _add_rule(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_rule")
        action_type = task.payload.get("action", "allow")
        protocol = task.payload.get("protocol", "tcp")
        port = task.payload.get("port", 443)
        source = task.payload.get("source", "0.0.0.0/0")
        destination = task.payload.get("destination", "0.0.0.0/0")
        direction = task.payload.get("direction", "inbound")

        rule = {
            "name": name,
            "action": action_type,
            "protocol": protocol,
            "port": port,
            "source": source,
            "destination": destination,
            "direction": direction,
            "enabled": True,
            "created_at": time.time(),
            "hit_count": 0,
        }
        self._rules[name] = rule
        return {"success": True, "rule": name, "config": rule}

    async def _delete_rule(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "")
        if name in self._rules:
            del self._rules[name]
            return {"success": True, "deleted": name}
        return {"success": False, "error": f"Rule {name} not found"}

    async def _configure_policy(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_policy")
        default_action = task.payload.get("default_action", "deny")
        rules = task.payload.get("rules", [])

        policy = {
            "name": name,
            "default_action": default_action,
            "rules": rules,
            "enabled": True,
            "created_at": time.time(),
        }
        self._policies[name] = policy
        return {"success": True, "policy": name, "default_action": default_action}

    async def _analyze_traffic(self, task: Task) -> Dict[str, Any]:
        time_range = task.payload.get("time_range", 3600)
        start_time = time.time() - time_range

        recent = [t for t in self._traffic_log if t.get("timestamp", 0) >= start_time]
        blocked = sum(1 for t in recent if t.get("action") == "block")
        allowed = sum(1 for t in recent if t.get("action") == "allow")

        return {"success": True, "total": len(recent), "blocked": blocked, "allowed": allowed, "block_rate": round(blocked / max(1, len(recent)) * 100, 1)}

    async def _block_ip(self, task: Task) -> Dict[str, Any]:
        ip = task.payload.get("ip", "")
        reason = task.payload.get("reason", "manual_block")
        duration_seconds = task.payload.get("duration_seconds", 3600)

        rule_name = f"block-{ip.replace('.', '-')}"
        rule = {
            "name": rule_name,
            "action": "deny",
            "protocol": "any",
            "port": "any",
            "source": ip,
            "destination": "0.0.0.0/0",
            "direction": "inbound",
            "reason": reason,
            "expires_at": time.time() + duration_seconds,
            "enabled": True,
        }
        self._rules[rule_name] = rule
        return {"success": True, "blocked_ip": ip, "rule": rule_name, "expires_in_seconds": duration_seconds}

    async def _get_rule_stats(self, task: Task) -> Dict[str, Any]:
        stats = {name: {"hit_count": rule.get("hit_count", 0), "enabled": rule.get("enabled", True)} for name, rule in self._rules.items()}
        return {"success": True, "rules": stats, "total_rules": len(stats)}

    def _monitor(self) -> Dict[str, Any]:
        return {
            "success": True,
            "metrics": {
                "rules_count": len(self._rules),
                "policies_count": len(self._policies),
                "total_traffic_events": len(self._traffic_log),
                "blocked_rules": sum(1 for r in self._rules.values() if r.get("action") == "deny"),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "firewall",
            "metrics": self._monitor()["metrics"],
        }
