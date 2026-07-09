"""PenetrationTestAgent — Security penetration testing."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

TEST_VECTORS = {
    "injection": {
        "payloads": ["' OR '1'='1", "'; DROP TABLE users;--", "<script>alert(1)</script>"],
        "severity": "critical",
    },
    "authentication_bypass": {
        "payloads": ["admin:admin", "root:root", "'' OR ''='"],
        "severity": "critical",
    },
    "path_traversal": {
        "payloads": ["../../../etc/passwd", "..\\..\\windows\\system32"],
        "severity": "high",
    },
    "ssrf": {
        "payloads": ["http://169.254.169.254", "http://localhost:8080"],
        "severity": "high",
    },
    "header_injection": {
        "payloads": ["X-Forwarded-For: 127.0.0.1", "Host: evil.com"],
        "severity": "medium",
    },
}


class PenetrationTestAgent(BaseAgent):
    """Security penetration testing agent.

    Features
    --------
    * Automated payload generation
    * Injection testing (SQL, XSS, command)
    * Authentication bypass attempts
    * Security control bypass testing
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._test_results: List[Dict[str, Any]] = []

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "audit")
        if action == "audit":
            return await self._audit(task)
        elif action == "test":
            return await self._test(task)
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "pentest_query":
            return {"results": self._test_results[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "penetration_testing", "injection_testing", "auth_bypass_testing",
            "payload_generation", "security_control_bypass",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        target = task.payload.get("target", "")
        endpoints = task.payload.get("endpoints", [])
        findings: List[Dict[str, Any]] = []

        for endpoint in endpoints:
            for test_name, config in TEST_VECTORS.items():
                for payload in config["payloads"]:
                    if self._check_vulnerability(endpoint, payload):
                        findings.append({
                            "type": test_name,
                            "severity": config["severity"],
                            "endpoint": endpoint.get("path", ""),
                            "payload": payload[:50],
                            "target": target,
                        })

        self._findings.extend(findings)
        self._test_results.append({
            "target": target,
            "endpoints_tested": len(endpoints),
            "vulnerabilities_found": len(findings),
        })

        return {
            "success": True,
            "target": target,
            "vulnerabilities": findings,
            "total": len(findings),
        }

    async def _test(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _check_vulnerability(self, endpoint: Dict[str, Any], payload: str) -> bool:
        body = str(endpoint.get("body", ""))
        params = str(endpoint.get("params", ""))
        return payload in body or payload in params

    def _report(self) -> Dict[str, Any]:
        severity_counts: Dict[str, int] = {}
        for f in self._findings:
            sev = f.get("severity", "info")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        return {
            "success": True,
            "total_findings": len(self._findings),
            "tests_performed": len(self._test_results),
            "severity_breakdown": severity_counts,
            "findings": self._findings[-20:],
        }
