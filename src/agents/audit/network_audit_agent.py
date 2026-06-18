"""NetworkAuditAgent — Network connectivity and security analysis."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

NETWORK_ISSUE_PATTERNS = {
    "insecure_protocol": {"pattern": r"(?i)(http://|ftp://)", "severity": "high"},
    "hardcoded_ip": {"pattern": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "severity": "medium"},
    "open_port": {"pattern": r"(?i)(port\s*:\s*\d+|listen\s+\d+)", "severity": "medium"},
    "weak_cipher": {"pattern": r"(?i)(RC4|DES|MD5|SHA1)", "severity": "high"},
    "exposed_endpoint": {"pattern": r"(?i)(/admin|/debug|/metrics|/health)", "severity": "medium"},
    "cors_wildcard": {"pattern": r"(?i)(Access-Control-Allow-Origin:\s*\*)", "severity": "high"},
}


class NetworkAuditAgent(BaseAgent):
    """Network connectivity and security analysis agent.

    Features
    --------
    * Protocol security validation
    * Port exposure analysis
    * CORS policy auditing
    * TLS/SSL configuration review
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
        if msg_type == "network_query":
            return {"findings": self._findings[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "network_analysis", "protocol_audit", "port_exposure_check",
            "cors_policy_audit", "tls_ssl_review",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        target = task.payload.get("target", "")
        content = task.payload.get("content", "")
        config = task.payload.get("config", {})
        findings: List[Dict[str, Any]] = []

        combined_text = content + " " + str(config)
        for issue_name, issue_config in NETWORK_ISSUE_PATTERNS.items():
            if re.search(issue_config["pattern"], combined_text):
                findings.append({
                    "type": issue_name,
                    "severity": issue_config["severity"],
                    "target": target,
                    "description": f"Network issue: {issue_name.replace('_', ' ')}",
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
