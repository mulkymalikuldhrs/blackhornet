"""PrivacyAuditAgent — Privacy regulation compliance."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

PRIVACY_ISSUES = {
    "pii_collection": {"pattern": r"(?i)(collect.*email|collect.*phone|collect.*address|collect.*ssn)", "severity": "high"},
    "no_consent": {"pattern": r"(?i)(no.*consent|collect.*without.*consent)", "severity": "critical"},
    "no_data_retention": {"pattern": r"(?i)(no.*retention.*policy|indefinite.*retention)", "severity": "high"},
    "no_deletion_mechanism": {"pattern": r"(?i)(no.*delete.*request|no.*right.*forget)", "severity": "high"},
    "cross_border_transfer": {"pattern": r"(?i)(transfer.*overseas|cross.*border.*data)", "severity": "medium"},
    "third_party_sharing": {"pattern": r"(?i)(share.*third.*party|sell.*data)", "severity": "high"},
    "no_privacy_notice": {"pattern": r"(?i)(no.*privacy.*policy|no.*privacy.*notice)", "severity": "high"},
}


class PrivacyAuditAgent(BaseAgent):
    """Privacy regulation compliance agent.

    Features
    --------
    * GDPR compliance validation
    * CCPA requirement checking
    * PII collection auditing
    * Data retention policy verification
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "audit")
        if action == "audit":
            return await self._audit(task)
        elif action == "scan":
            return await self._scan(task)
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "privacy_query":
            return {"findings": self._findings[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "privacy_compliance", "gdpr_validation", "ccpa_checking",
            "pii_audit", "data_retention_verification",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        target = task.payload.get("target", "")
        content = task.payload.get("content", "")
        config = task.payload.get("config", {})
        findings: List[Dict[str, Any]] = []
        combined = content + " " + str(config)

        for issue_name, issue_config in PRIVACY_ISSUES.items():
            if re.search(issue_config["pattern"], combined):
                findings.append({
                    "type": issue_name,
                    "severity": issue_config["severity"],
                    "target": target,
                    "description": f"Privacy issue: {issue_name.replace('_', ' ')}",
                })

        self._findings.extend(findings)
        return {
            "success": True,
            "target": target,
            "findings": findings,
        }

    async def _scan(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _report(self) -> Dict[str, Any]:
        severity_counts: Dict[str, int] = {}
        for f in self._findings:
            sev = f.get("severity", "info")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        return {
            "success": True,
            "total_findings": len(self._findings),
            "severity_breakdown": severity_counts,
            "findings": self._findings[-20:],
        }
