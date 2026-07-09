"""ThirdPartyAuditAgent — Third-party service security."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

THIRD_PARTY_CHECKS = {
    "data_processing_agreement": {"severity": "critical", "description": "Data Processing Agreement"},
    "security_certifications": {"severity": "high", "description": "Security certifications (SOC2, ISO)"},
    "encryption_standards": {"severity": "critical", "description": "Encryption standards"},
    "access_controls": {"severity": "high", "description": "Access controls"},
    "incident_response": {"severity": "high", "description": "Incident response plan"},
    "data_residency": {"severity": "medium", "description": "Data residency compliance"},
    "vendor_assessment": {"severity": "high", "description": "Vendor security assessment"},
    "sla_defined": {"severity": "medium", "description": "Service Level Agreement"},
    "exit_strategy": {"severity": "medium", "description": "Vendor exit strategy"},
    "penetration_testing": {"severity": "high", "description": "Regular penetration testing"},
}


class ThirdPartyAuditAgent(BaseAgent):
    """Third-party service security agent.

    Features
    --------
    * Third-party vendor security assessment
    * Data processing agreement validation
    * Security certification verification
    * Vendor risk management
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._vendor_scores: Dict[str, float] = {}

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
        if msg_type == "third_party_query":
            return {"vendor_scores": self._vendor_scores}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "third_party_audit", "vendor_security_assessment",
            "data_processing_agreement", "vendor_risk_management",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        vendors = task.payload.get("vendors", [])
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []

        for vendor in vendors:
            name = vendor.get("name", "")
            checks = vendor.get("checks", {})
            checks_passed = 0

            for check, config in THIRD_PARTY_CHECKS.items():
                if checks.get(check, False):
                    checks_passed += 1
                else:
                    findings.append({
                        "type": "missing_check",
                        "severity": config["severity"],
                        "vendor": name,
                        "check": check,
                        "target": target,
                        "description": config["description"],
                    })

            self._vendor_scores[name] = checks_passed / len(THIRD_PARTY_CHECKS)

        self._findings.extend(findings)
        return {
            "success": True,
            "target": target,
            "vendors_assessed": len(vendors),
            "vendor_scores": self._vendor_scores,
            "findings": findings,
        }

    async def _validate(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "total_findings": len(self._findings),
            "vendor_scores": self._vendor_scores,
            "findings": self._findings[-20:],
        }
