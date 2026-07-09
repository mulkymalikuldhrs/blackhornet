"""CicdAuditAgent — CI/CD pipeline security and efficiency."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

CICD_ISSUES = {
    "hardcoded_secrets": {"pattern": r"(?i)(SECRET|PASSWORD|TOKEN|KEY)\s*[:=]", "severity": "critical"},
    "insecure_pipeline": {"pattern": r"(?i)(no.*ssl|insecure.*registry|skip.*verify)", "severity": "high"},
    "no_dependency_scanning": {"pattern": r"(?i)(no.*snyk|no.*dependabot|no.*dep.*scan)", "severity": "medium"},
    "no_secret_scanning": {"pattern": r"(?i)(no.*gitleaks|no.*trufflehog|no.*secret.*scan)", "severity": "high"},
    "no_code_signing": {"pattern": r"(?i)(no.*sign|no.*cosign|no.*gpg)", "severity": "medium"},
    "long_lived_tokens": {"pattern": r"(?i)(token.*expir.*never|token.*no.*expire)", "severity": "high"},
    "no_artifact_scanning": {"pattern": r"(?i)(no.*trivy|no.*grype|no.*artifact.*scan)", "severity": "medium"},
}


class CicdAuditAgent(BaseAgent):
    """CI/CD pipeline security and efficiency agent.

    Features
    --------
    * Pipeline configuration security audit
    * Secret management validation
    * Dependency scanning verification
    * Build artifact integrity checking
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
        if msg_type == "cicd_query":
            return {"findings": self._findings[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "cicd_audit", "pipeline_security", "secret_management_validation",
            "dependency_scanning_check", "artifact_integrity",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        target = task.payload.get("target", "")
        content = task.payload.get("content", "")
        findings: List[Dict[str, Any]] = []

        for issue_name, issue_config in CICD_ISSUES.items():
            if re.search(issue_config["pattern"], content):
                findings.append({
                    "type": issue_name,
                    "severity": issue_config["severity"],
                    "target": target,
                    "description": f"CI/CD issue: {issue_name.replace('_', ' ')}",
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
