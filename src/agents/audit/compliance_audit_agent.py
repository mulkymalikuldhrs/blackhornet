"""ComplianceAuditAgent — Regulatory compliance checking."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

COMPLIANCE_FRAMEWORKS = {
    "gdpr": {
        "patterns": {
            "data_retention": r"(?i)(retain.*data.*\d+.*year|no.*retention.*policy)",
            "consent_management": r"(?i)(no.*consent|no.*opt.?in|no.*privacy.*notice)",
            "right_to_erasure": r"(?i)(no.*delete.*request|no.*right.*forget|no.*erasure)",
            "data_portability": r"(?i)(no.*export.*data|no.*portability)",
        },
        "severity": "high",
    },
    "hipaa": {
        "patterns": {
            "phi_exposure": r"(?i)(phi.*exposed|health.*data.*unencrypted)",
            "access_controls": r"(?i)(no.*access.*log|no.*audit.*trail)",
            "encryption_required": r"(?i)(phi.*no.*encrypt|unencrypted.*health)",
        },
        "severity": "critical",
    },
    "pci_dss": {
        "patterns": {
            "card_data_storage": r"(?i)(store.*card.*number|save.*credit.*card)",
            "weak_encryption": r"(?i)(card.*data.*md5|card.*data.*sha1)",
            "no_network_segmentation": r"(?i)(no.*segment|flat.*network.*card)",
        },
        "severity": "critical",
    },
    "soc2": {
        "patterns": {
            "missing_audit_log": r"(?i)(no.*audit.*log|no.*change.*log)",
            "no_access_review": r"(?i)(no.*access.*review|no.*periodic.*access)",
            "no_incident_response": r"(?i)(no.*incident.*plan|no.*response.*procedure)",
        },
        "severity": "high",
    },
}


class ComplianceAuditAgent(BaseAgent):
    """Regulatory compliance checking agent.

    Features
    --------
    * GDPR compliance validation
    * HIPAA requirement checking
    * PCI DSS compliance auditing
    * SOC 2 control verification
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._compliance_status: Dict[str, str] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "audit")
        if action == "audit":
            return await self._audit(task)
        elif action == "check":
            return await self._check_framework(task)
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "compliance_query":
            return {"status": self._compliance_status}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "compliance_audit", "gdpr_checking", "hipaa_validation",
            "pci_dss_audit", "soc2_verification",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        config = task.payload.get("config", {})
        target = task.payload.get("target", "")
        frameworks = task.payload.get("frameworks", list(COMPLIANCE_FRAMEWORKS.keys()))
        findings: List[Dict[str, Any]] = []
        config_str = str(config)

        for framework in frameworks:
            if framework not in COMPLIANCE_FRAMEWORKS:
                continue
            fw = COMPLIANCE_FRAMEWORKS[framework]
            violations = 0
            for pattern_name, pattern in fw["patterns"].items():
                if re.search(pattern, config_str):
                    findings.append({
                        "type": pattern_name,
                        "framework": framework,
                        "severity": fw["severity"],
                        "target": target,
                        "description": f"{framework.upper()} violation: {pattern_name.replace('_', ' ')}",
                    })
                    violations += 1
            self._compliance_status[framework] = "fail" if violations > 0 else "pass"

        self._findings.extend(findings)
        return {
            "success": True,
            "target": target,
            "frameworks_checked": frameworks,
            "findings": findings,
            "compliance_status": dict(self._compliance_status),
        }

    async def _check_framework(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "total_findings": len(self._findings),
            "compliance_status": dict(self._compliance_status),
            "findings": self._findings[-20:],
        }
