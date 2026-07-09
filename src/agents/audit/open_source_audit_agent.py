"""OpenSourceAuditAgent — Open source license and security."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

OSS_CHECKS = {
    "license_compliance": {"severity": "high", "description": "License compliance"},
    "vulnerability_scanning": {"severity": "critical", "description": "Vulnerability scanning"},
    "outdated_dependencies": {"severity": "medium", "description": "Outdated dependencies"},
    "maintained_packages": {"severity": "medium", "description": "Well-maintained packages"},
    "security_advisories": {"severity": "high", "description": "Security advisory monitoring"},
    "sbom_generation": {"severity": "high", "description": "SBOM generation"},
    "dependency_review": {"severity": "high", "description": "Dependency change review"},
    "license_attribution": {"severity": "medium", "description": "License attribution"},
}


class OpenSourceAuditAgent(BaseAgent):
    """Open source license and security agent.

    Features
    --------
    * Open source license compliance validation
    * Vulnerability scanning for OSS dependencies
    * Dependency health assessment
    * Security advisory monitoring
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
        if msg_type == "oss_query":
            return {"compliance_score": self._compliance_score}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "open_source_audit", "license_compliance", "vulnerability_scanning",
            "dependency_health", "security_advisory_monitoring",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        config = task.payload.get("config", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []
        checks_passed = 0

        for check, config_item in OSS_CHECKS.items():
            if config.get(check, False):
                checks_passed += 1
            else:
                findings.append({
                    "type": "missing_check",
                    "severity": config_item["severity"],
                    "check": check,
                    "target": target,
                    "description": config_item["description"],
                })

        self._compliance_score = checks_passed / len(OSS_CHECKS)
        self._findings.extend(findings)

        return {
            "success": True,
            "target": target,
            "compliance_score": self._compliance_score,
            "checks_passed": checks_passed,
            "checks_total": len(OSS_CHECKS),
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
