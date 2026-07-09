"""EncryptionAuditAgent — Encryption standards compliance."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

ENCRYPTION_ISSUES = {
    "weak_algorithm": {"pattern": r"(?i)(MD5|SHA1|DES|RC4|Blowfish)", "severity": "high"},
    "hardcoded_key": {"pattern": r"(?i)(secret_key|encryption_key)\s*[:=]\s*['\"][^'\"]+['\"]", "severity": "critical"},
    "no_encryption": {"pattern": r"(?i)(no.*encrypt|plaintext|unencrypted)", "severity": "high"},
    "weak_tls": {"pattern": r"(?i)(TLSv1\.0|TLSv1\.1|SSLv3)", "severity": "critical"},
    "short_key_length": {"pattern": r"(?i)(key.*length.*128|rsa.*1024|des.*key)", "severity": "high"},
    "iv_reuse": {"pattern": r"(?i)(iv.*reuse|same.*iv|static.*iv)", "severity": "critical"},
    "ecb_mode": {"pattern": r"(?i)(ECB.*mode|mode.*ECB)", "severity": "high"},
}


class EncryptionAuditAgent(BaseAgent):
    """Encryption standards compliance agent.

    Features
    --------
    * Algorithm strength validation
    * Key management auditing
    * TLS/SSL configuration review
    * Cryptographic compliance checking
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
        if msg_type == "encryption_query":
            return {"findings": self._findings[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "encryption_audit", "algorithm_validation", "key_management_audit",
            "tls_ssl_review", "cryptographic_compliance",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        target = task.payload.get("target", "")
        content = task.payload.get("content", "")
        config = task.payload.get("config", {})
        findings: List[Dict[str, Any]] = []
        combined = content + " " + str(config)

        for issue_name, issue_config in ENCRYPTION_ISSUES.items():
            if re.search(issue_config["pattern"], combined):
                findings.append({
                    "type": issue_name,
                    "severity": issue_config["severity"],
                    "target": target,
                    "description": f"Encryption issue: {issue_name.replace('_', ' ')}",
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
