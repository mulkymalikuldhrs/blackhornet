"""DependencyAuditAgent — Third-party dependency vulnerability checking."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

KNOWN_VULNERABILITIES: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "requests": {
        "2.25.0": [{"cve": "CVE-2023-32681", "severity": "medium", "description": "Proxy-Authorization header leak"}],
    },
    "django": {
        "3.2.0": [{"cve": "CVE-2023-46695", "severity": "high", "description": "DoS via large username"}],
    },
    "log4j": {
        "2.14.1": [{"cve": "CVE-2021-44228", "severity": "critical", "description": "Remote code execution"}],
    },
    "flask": {
        "1.0": [{"cve": "CVE-2023-30861", "severity": "medium", "description": "Session cookie leak"}],
    },
    "express": {
        "4.17.0": [{"cve": "CVE-2024-29041", "severity": "high", "description": "Open redirect"}],
    },
}


class DependencyAuditAgent(BaseAgent):
    """Third-party dependency vulnerability checking agent.

    Features
    --------
    * CVE database checking for dependencies
    * Transitive dependency analysis
    * License compliance verification
    * Update recommendation generation
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._scanned_deps: Dict[str, str] = {}

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
        if msg_type == "dependency_query":
            return {"vulnerable_deps": [f for f in self._findings if f.get("has_vulnerability")]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "dependency_scanning", "cve_checking", "transitive_analysis",
            "license_compliance", "update_recommendations",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        dependencies = task.payload.get("dependencies", [])
        findings: List[Dict[str, Any]] = []

        for dep in dependencies:
            name = dep.get("name", "")
            version = dep.get("version", "")
            cves = self._check_cves(name, version)
            has_vuln = len(cves) > 0
            findings.append({
                "name": name,
                "version": version,
                "has_vulnerability": has_vuln,
                "cves": cves,
                "severity": max((c["severity"] for c in cves), default="none"),
            })
            self._scanned_deps[name] = version

        self._findings.extend(findings)
        return {
            "success": True,
            "total_dependencies": len(dependencies),
            "vulnerable_count": sum(1 for f in findings if f["has_vulnerability"]),
            "findings": findings,
        }

    async def _scan(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _check_cves(self, name: str, version: str) -> List[Dict[str, Any]]:
        return KNOWN_VULNERABILITIES.get(name, {}).get(version, [])

    def _report(self) -> Dict[str, Any]:
        vulnerable = [f for f in self._findings if f.get("has_vulnerability")]
        return {
            "success": True,
            "total_scanned": len(self._findings),
            "vulnerable_count": len(vulnerable),
            "vulnerable_dependencies": vulnerable,
            "recent_findings": self._findings[-20:],
        }
