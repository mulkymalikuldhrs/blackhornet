"""InfrastructureAuditAgent — Infrastructure security and reliability."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

INFRA_CHECKS = {
    "network_segmentation": {"severity": "high", "description": "Network segmentation"},
    "firewall_rules": {"severity": "high", "description": "Firewall configuration"},
    "intrusion_detection": {"severity": "high", "description": "IDS/IPS system"},
    "vulnerability_scanning": {"severity": "medium", "description": "Regular vulnerability scans"},
    "patch_management": {"severity": "high", "description": "Patch management process"},
    "access_controls": {"severity": "critical", "description": "Infrastructure access controls"},
    "monitoring_logging": {"severity": "high", "description": "Infrastructure monitoring"},
    "backup_recovery": {"severity": "critical", "description": "Backup and recovery"},
    "disaster_recovery": {"severity": "high", "description": "Disaster recovery plan"},
    "physical_security": {"severity": "high", "description": "Physical security controls"},
}


class InfrastructureAuditAgent(BaseAgent):
    """Infrastructure security and reliability agent.

    Features
    --------
    * Network security validation
    * Firewall configuration auditing
    * Patch management verification
    * Physical security assessment
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._security_score: float = 0.0

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
        if msg_type == "infra_query":
            return {"security_score": self._security_score}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "infrastructure_audit", "network_security_validation",
            "firewall_audit", "patch_management_verification",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        infra_config = task.payload.get("infra_config", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []
        checks_passed = 0

        for check, config in INFRA_CHECKS.items():
            if infra_config.get(check, False):
                checks_passed += 1
            else:
                findings.append({
                    "type": "missing_check",
                    "severity": config["severity"],
                    "check": check,
                    "target": target,
                    "description": config["description"],
                })

        self._security_score = checks_passed / len(INFRA_CHECKS)
        self._findings.extend(findings)

        return {
            "success": True,
            "target": target,
            "security_score": self._security_score,
            "checks_passed": checks_passed,
            "checks_total": len(INFRA_CHECKS),
            "findings": findings,
        }

    async def _validate(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "total_findings": len(self._findings),
            "security_score": self._security_score,
            "findings": self._findings[-20:],
        }
