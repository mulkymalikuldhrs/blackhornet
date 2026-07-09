"""DeploymentAuditAgent — Deployment safety and correctness."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

DEPLOYMENT_CHECKS = {
    "environment_parity": {"severity": "high", "description": "Dev/staging/prod parity"},
    "infrastructure_as_code": {"severity": "high", "description": "IaC configuration"},
    "secrets_management": {"severity": "critical", "description": "Secrets handling"},
    "health_checks": {"severity": "high", "description": "Health check endpoints"},
    "graceful_shutdown": {"severity": "medium", "description": "Graceful shutdown handling"},
    "resource_limits": {"severity": "high", "description": "Resource limits configured"},
    "monitoring_alerts": {"severity": "medium", "description": "Monitoring and alerts"},
    "rollback_mechanism": {"severity": "critical", "description": "Rollback capability"},
}


class DeploymentAuditAgent(BaseAgent):
    """Deployment safety and correctness agent.

    Features
    --------
    * Deployment configuration validation
    * Environment parity checking
    * Secrets management auditing
    * Rollback mechanism verification
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._deployment_score: float = 0.0

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
        if msg_type == "deployment_query":
            return {"deployment_score": self._deployment_score}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "deployment_audit", "environment_parity_check", "secrets_management_audit",
            "rollback_verification", "deployment_safety",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        deployment_config = task.payload.get("deployment_config", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []
        checks_passed = 0

        for check, config in DEPLOYMENT_CHECKS.items():
            if deployment_config.get(check, False):
                checks_passed += 1
            else:
                findings.append({
                    "type": "missing_check",
                    "severity": config["severity"],
                    "check": check,
                    "target": target,
                    "description": config["description"],
                })

        self._deployment_score = checks_passed / len(DEPLOYMENT_CHECKS)
        self._findings.extend(findings)

        return {
            "success": True,
            "target": target,
            "deployment_score": self._deployment_score,
            "checks_passed": checks_passed,
            "checks_total": len(DEPLOYMENT_CHECKS),
            "findings": findings,
        }

    async def _validate(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "total_findings": len(self._findings),
            "deployment_score": self._deployment_score,
            "findings": self._findings[-20:],
        }
