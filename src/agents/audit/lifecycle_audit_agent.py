"""LifecycleAuditAgent — Component lifecycle management."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

LIFECYCLE_ISSUES = {
    "no_initialization": {"severity": "high", "description": "No initialization phase"},
    "no_cleanup": {"severity": "high", "description": "No cleanup on shutdown"},
    "no_health_check": {"severity": "medium", "description": "No health check"},
    "no_readiness_probe": {"severity": "medium", "description": "No readiness probe"},
    "no_liveness_probe": {"severity": "medium", "description": "No liveness probe"},
    "no_graceful_shutdown": {"severity": "high", "description": "No graceful shutdown"},
    "no_dependency_injection": {"severity": "medium", "description": "No dependency injection"},
    "no_configuration_validation": {"severity": "medium", "description": "No config validation"},
    "no_resource_pooling": {"severity": "medium", "description": "No resource pooling"},
    "no_connection_pooling": {"severity": "medium", "description": "No connection pooling"},
}


class LifecycleAuditAgent(BaseAgent):
    """Component lifecycle management agent.

    Features
    --------
    * Component initialization validation
    * Cleanup and shutdown verification
    * Health check configuration audit
    * Resource management validation
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
        if msg_type == "lifecycle_query":
            return {"findings": self._findings[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "lifecycle_audit", "initialization_validation",
            "cleanup_verification", "health_check_audit",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        config = task.payload.get("config", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []

        checks = {
            "initialization": "no_initialization",
            "cleanup": "no_cleanup",
            "health_check": "no_health_check",
            "readiness_probe": "no_readiness_probe",
            "liveness_probe": "no_liveness_probe",
            "graceful_shutdown": "no_graceful_shutdown",
            "dependency_injection": "no_dependency_injection",
            "config_validation": "no_configuration_validation",
        }

        for config_key, issue_key in checks.items():
            if not config.get(config_key, False):
                issue = LIFECYCLE_ISSUES[issue_key]
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
