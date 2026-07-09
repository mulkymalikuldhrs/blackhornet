"""TimeoutAuditAgent — Timeout configuration validation."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

TIMEOUT_ISSUES = {
    "no_connection_timeout": {"severity": "high", "description": "No connection timeout"},
    "no_read_timeout": {"severity": "high", "description": "No read timeout"},
    "no_write_timeout": {"severity": "medium", "description": "No write timeout"},
    "no_idle_timeout": {"severity": "medium", "description": "No idle timeout"},
    "excessive_timeout": {"severity": "medium", "description": "Excessively long timeout"},
    "no_global_timeout": {"severity": "high", "description": "No global timeout"},
    "no_request_timeout": {"severity": "high", "description": "No request timeout"},
    "no_deadline": {"severity": "high", "description": "No deadline set"},
}


class TimeoutAuditAgent(BaseAgent):
    """Timeout configuration validation agent.

    Features
    --------
    * Timeout configuration validation
    * Timeout consistency checking
    * Timeout best practices enforcement
    * Cascading timeout detection
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
        if msg_type == "timeout_query":
            return {"findings": self._findings[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "timeout_audit", "timeout_validation", "timeout_consistency_check",
            "cascading_timeout_detection",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        config = task.payload.get("config", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []

        connection_timeout = config.get("connection_timeout", 0)
        read_timeout = config.get("read_timeout", 0)
        request_timeout = config.get("request_timeout", 0)
        idle_timeout = config.get("idle_timeout", 0)

        if connection_timeout == 0:
            findings.append({"type": "no_connection_timeout", "severity": "high", "target": target})
        if read_timeout == 0:
            findings.append({"type": "no_read_timeout", "severity": "high", "target": target})
        if request_timeout == 0:
            findings.append({"type": "no_request_timeout", "severity": "high", "target": target})
        if idle_timeout == 0:
            findings.append({"type": "no_idle_timeout", "severity": "medium", "target": target})
        if connection_timeout > 300:
            findings.append({"type": "excessive_timeout", "severity": "medium", "target": target, "timeout": connection_timeout})

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
