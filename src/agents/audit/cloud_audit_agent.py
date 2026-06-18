"""CloudAuditAgent — Cloud service configuration audit."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

CLOUD_CHECKS = {
    "iam_policies": {"severity": "critical", "description": "IAM policy review"},
    "security_groups": {"severity": "high", "description": "Security group rules"},
    "encryption_at_rest": {"severity": "critical", "description": "Encryption at rest"},
    "encryption_in_transit": {"severity": "critical", "description": "Encryption in transit"},
    "logging_enabled": {"severity": "high", "description": "Cloud logging enabled"},
    "access_logging": {"severity": "high", "description": "Access logging enabled"},
    "mfa_enabled": {"severity": "critical", "description": "MFA for root account"},
    "unused_resources": {"severity": "low", "description": "Unused resource cleanup"},
    "cost_optimization": {"severity": "low", "description": "Cost optimization"},
    "compliance_tags": {"severity": "medium", "description": "Resource tagging"},
}


class CloudAuditAgent(BaseAgent):
    """Cloud service configuration audit agent.

    Features
    --------
    * IAM policy validation
    * Security group auditing
    * Encryption configuration review
    * Cloud compliance checking
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._compliance_score: float = 0.0

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
        if msg_type == "cloud_query":
            return {"compliance_score": self._compliance_score}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "cloud_audit", "iam_policy_validation", "security_group_audit",
            "encryption_config_review", "cloud_compliance",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        cloud_config = task.payload.get("cloud_config", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []
        checks_passed = 0

        for check, config in CLOUD_CHECKS.items():
            if cloud_config.get(check, False):
                checks_passed += 1
            else:
                findings.append({
                    "type": "missing_check",
                    "severity": config["severity"],
                    "check": check,
                    "target": target,
                    "description": config["description"],
                })

        self._compliance_score = checks_passed / len(CLOUD_CHECKS)
        self._findings.extend(findings)

        return {
            "success": True,
            "target": target,
            "compliance_score": self._compliance_score,
            "checks_passed": checks_passed,
            "checks_total": len(CLOUD_CHECKS),
            "findings": findings,
        }

    async def _validate(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "total_findings": len(self._findings),
            "compliance_score": self._compliance_score,
            "findings": self._findings[-20:],
        }
