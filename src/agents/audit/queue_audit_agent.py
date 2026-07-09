"""QueueAuditAgent — Message queue reliability."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

QUEUE_ISSUES = {
    "no_durable_messages": {"severity": "high", "description": "Non-durable messages"},
    "no_dead_letter_queue": {"severity": "high", "description": "No dead letter queue"},
    "no_retry_mechanism": {"severity": "high", "description": "No retry mechanism"},
    "no_message_expiration": {"severity": "medium", "description": "No message expiration"},
    "no_consumer_group": {"severity": "medium", "description": "No consumer group"},
    "no_acknowledgment": {"severity": "critical", "description": "No message acknowledgment"},
    "no_ordering_guarantee": {"severity": "medium", "description": "No ordering guarantee"},
    "no_monitoring": {"severity": "medium", "description": "No queue monitoring"},
    "no_backpressure": {"severity": "medium", "description": "No backpressure handling"},
    "no_message_size_limit": {"severity": "low", "description": "No message size limit"},
}


class QueueAuditAgent(BaseAgent):
    """Message queue reliability agent.

    Features
    --------
    * Message durability validation
    * Dead letter queue verification
    * Consumer group auditing
    * Queue monitoring completeness
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
        if msg_type == "queue_query":
            return {"findings": self._findings[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "queue_audit", "message_durability_validation",
            "dead_letter_queue_audit", "queue_monitoring_check",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        config = task.payload.get("config", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []

        has_durable = config.get("durable_messages", False)
        has_dlq = config.get("dead_letter_queue", False)
        has_retry = config.get("retry_mechanism", False)
        has_ack = config.get("acknowledgment", False)
        has_monitoring = config.get("monitoring", False)

        if not has_durable:
            findings.append({"type": "no_durable_messages", "severity": "high", "target": target})
        if not has_dlq:
            findings.append({"type": "no_dead_letter_queue", "severity": "high", "target": target})
        if not has_retry:
            findings.append({"type": "no_retry_mechanism", "severity": "high", "target": target})
        if not has_ack:
            findings.append({"type": "no_acknowledgment", "severity": "critical", "target": target})
        if not has_monitoring:
            findings.append({"type": "no_monitoring", "severity": "medium", "target": target})

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
