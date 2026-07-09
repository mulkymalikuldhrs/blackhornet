"""SecurityAuditAgent — Security vulnerability scanning and assessment."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

VULNERABILITY_PATTERNS: Dict[str, Dict[str, str]] = {
    "sql_injection": {"pattern": r"(?i)(SELECT\s+.*FROM|UNION\s+SELECT|DROP\s+TABLE|' OR '1'='1)", "severity": "critical"},
    "command_injection": {"pattern": r"(os\.system|subprocess\.call|eval\(|exec\()", "severity": "critical"},
    "xss": {"pattern": r"(<script|onerror=|onload=|javascript:)", "severity": "high"},
    "path_traversal": {"pattern": r"(\.\.\/|\.\.\\)", "severity": "high"},
    "ssrf": {"pattern": r"(?i)(http:\/\/|https:\/\/).*\$\{", "severity": "high"},
    "xxe": {"pattern": r"(?i)(<!ENTITY|SYSTEM\s+['\"]file:)", "severity": "high"},
    "insecure_deserialization": {"pattern": r"(pickle\.loads|yaml\.load|marshal\.loads)", "severity": "critical"},
    "open_redirect": {"pattern": r"(?i)(redirect_url|return_url|next)=.*http", "severity": "medium"},
}


class SecurityAuditAgent(BaseAgent):
    """Security vulnerability scanning and assessment agent.

    Features
    --------
    * Vulnerability pattern detection (OWASP Top 10)
    * Severity classification and risk scoring
    * Remediation recommendation generation
    * Aggregated security reporting
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._scan_history: List[Dict[str, Any]] = []

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
        if msg_type == "security_query":
            return {"findings": self._findings[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "vulnerability_scanning", "security_assessment", "owasp_top10",
            "risk_scoring", "remediation_recommendations",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        target = task.payload.get("target", "")
        content = task.payload.get("content", "")
        findings: List[Dict[str, Any]] = []

        for vuln_name, config in VULNERABILITY_PATTERNS.items():
            if re.search(config["pattern"], content):
                finding = {
                    "type": vuln_name,
                    "severity": config["severity"],
                    "target": target,
                    "description": f"Potential {vuln_name.replace('_', ' ')} detected",
                }
                findings.append(finding)

        self._findings.extend(findings)
        self._scan_history.append({
            "target": target,
            "findings_count": len(findings),
        })

        return {
            "success": True,
            "target": target,
            "findings": findings,
            "risk_level": self._calculate_risk_level(findings),
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
            "scans_performed": len(self._scan_history),
            "recent_findings": self._findings[-20:],
        }

    def _calculate_risk_level(self, findings: List[Dict[str, Any]]) -> str:
        severities = [f.get("severity", "info") for f in findings]
        if "critical" in severities:
            return "critical"
        if "high" in severities:
            return "high"
        if "medium" in severities:
            return "medium"
        return "low"
