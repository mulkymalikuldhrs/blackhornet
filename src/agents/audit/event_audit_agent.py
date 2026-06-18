"""EventAuditAgent — Event system integrity."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

EVENT_ISSUES = {
    "no_event_schema": {"severity": "high", "description": "No event schema defined"},
    "no_event_versioning": {"severity": "high", "description": "No event versioning"},
    "no_idempotency": {"severity": "high", "description": "No event idempotency"},
    "no_ordering_guarantee": {"severity": "medium", "description": "No ordering guarantee"},
    "no_event_store": {"severity": "medium", "description": "No event store"},
    "no_replay_capability": {"severity": "medium", "description": "No event replay"},
    "no_event_monitoring": {"severity": "medium", "description": "No event monitoring"},
    "no_error_handling": {"severity": "high", "description": "No event error handling"},
    "no_event_audit_log": {"severity": "high", "description": "No event audit log"},
    "no_circuit_breaker": {"severity": "medium", "description": "No circuit breaker for events"},
}


class EventAuditAgent(BaseAgent):
    """Event system integrity agent.

    Features
    --------
    * Event schema validation
    * Event versioning verification
    * Event store completeness audit
    * Event processing reliability check
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
        if msg_type == "event_query":
            return {"findings": self._findings[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "event_audit", "event_schema_validation",
            "event_versioning_check", "event_store_audit",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        config = task.payload.get("config", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []

        checks = {
            "event_schema": "no_event_schema",
            "event_versioning": "no_event_versioning",
            "idempotency": "no_idempotency",
            "event_store": "no_event_store",
            "replay_capability": "no_replay_capability",
            "event_monitoring": "no_event_monitoring",
            "error_handling": "no_error_handling",
            "audit_log": "no_event_audit_log",
        }

        for config_key, issue_key in checks.items():
            if not config.get(config_key, False):
                issue = EVENT_ISSUES[issue_key]
                findings.append({
                    "type": issue_key,
                    "severity": issue["severity"],
                    "target": target,
                    "description": issue["description"],
                })

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
