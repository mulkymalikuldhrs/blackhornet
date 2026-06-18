"""FilesystemAuditAgent — File system permissions and integrity."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

PERMISSION_ISSUES = {
    "world_writable": {"octal_check": 0o002, "severity": "high", "description": "File is world-writable"},
    "world_readable_secret": {"octal_check": 0o004, "severity": "critical", "description": "Secret file is world-readable"},
    "suid_bit": {"octal_check": 0o4000, "severity": "high", "description": "SUID bit set"},
    "sgid_bit": {"octal_check": 0o2000, "severity": "high", "description": "SGID bit set"},
    "no_owner": {"check": "no_owner", "severity": "medium", "description": "File has no valid owner"},
    "sensitive_path": {"check": "sensitive", "severity": "medium", "description": "Sensitive file in accessible location"},
}

SENSITIVE_PATHS = [".env", ".ssh", "id_rsa", "credentials", "secrets", ".git/config"]


class FilesystemAuditAgent(BaseAgent):
    """File system permissions and integrity agent.

    Features
    --------
    * File permission validation
    * Sensitive file exposure detection
    * SUID/SGID bit auditing
    * Integrity hash verification
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._file_hashes: Dict[str, str] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "audit")
        if action == "audit":
            return await self._audit(task)
        elif action == "verify_integrity":
            return await self._verify_integrity(task)
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "fs_query":
            return {"findings": self._findings[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "permission_audit", "sensitive_file_detection", "suid_audit",
            "integrity_verification", "file_ownership_check",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        files = task.payload.get("files", [])
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []

        for file_info in files:
            path = file_info.get("path", "")
            permissions = file_info.get("permissions", 0)
            owner = file_info.get("owner", "")

            for issue_name, config in PERMISSION_ISSUES.items():
                if "octal_check" in config:
                    if permissions & config["octal_check"]:
                        findings.append({
                            "type": issue_name,
                            "severity": config["severity"],
                            "path": path,
                            "description": config["description"],
                        })
                elif config.get("check") == "sensitive":
                    for sensitive in SENSITIVE_PATHS:
                        if sensitive in path:
                            findings.append({
                                "type": issue_name,
                                "severity": config["severity"],
                                "path": path,
                                "description": config["description"],
                            })

        self._findings.extend(findings)
        return {
            "success": True,
            "target": target,
            "files_checked": len(files),
            "findings": findings,
        }

    async def _verify_integrity(self, task: Task) -> Dict[str, Any]:
        import hashlib
        files = task.payload.get("files", [])
        results: List[Dict[str, Any]] = []

        for file_info in files:
            path = file_info.get("path", "")
            content = file_info.get("content", "")
            current_hash = hashlib.sha256(content.encode()).hexdigest()
            previous_hash = self._file_hashes.get(path)
            changed = previous_hash is not None and previous_hash != current_hash
            self._file_hashes[path] = current_hash
            results.append({
                "path": path,
                "hash": current_hash,
                "changed": changed,
            })

        return {"success": True, "results": results}

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "total_findings": len(self._findings),
            "files_tracked": len(self._file_hashes),
            "findings": self._findings[-20:],
        }
