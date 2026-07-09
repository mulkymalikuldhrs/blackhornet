"""RateLimitingAgent — Rate limiting effectiveness."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

RATE_LIMIT_ISSUES = {
    "no_rate_limiting": {"severity": "critical", "description": "No rate limiting"},
    "no_per_user_limit": {"severity": "high", "description": "No per-user rate limit"},
    "no_per_ip_limit": {"severity": "high", "description": "No per-IP rate limit"},
    "no_global_limit": {"severity": "high", "description": "No global rate limit"},
    "no_burst_protection": {"severity": "high", "description": "No burst protection"},
    "missing_headers": {"severity": "medium", "description": "Missing rate limit headers"},
    "no_429_response": {"severity": "high", "description": "No 429 status code"},
    "no_escalation": {"severity": "medium", "description": "No rate limit escalation"},
}


class RateLimitingAgent(BaseAgent):
    """Rate limiting effectiveness agent.

    Features
    --------
    * Rate limiting configuration validation
    * Burst protection verification
    * Rate limit header presence checking
    * Rate limiting strategy assessment
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []

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
        if msg_type == "rate_limit_query":
            return {"findings": self._findings[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "rate_limiting_audit", "burst_protection_validation",
            "rate_limit_header_check", "rate_limiting_strategy_assessment",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        config = task.payload.get("config", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []

        has_rate_limiting = config.get("rate_limiting", False)
        has_per_user = config.get("per_user_limit", False)
        has_per_ip = config.get("per_ip_limit", False)
        has_burst_protection = config.get("burst_protection", False)
        has_headers = config.get("rate_limit_headers", False)

        if not has_rate_limiting:
            findings.append({"type": "no_rate_limiting", "severity": "critical", "target": target})
        if not has_per_user:
            findings.append({"type": "no_per_user_limit", "severity": "high", "target": target})
        if not has_per_ip:
            findings.append({"type": "no_per_ip_limit", "severity": "high", "target": target})
        if not has_burst_protection:
            findings.append({"type": "no_burst_protection", "severity": "high", "target": target})
        if not has_headers:
            findings.append({"type": "missing_headers", "severity": "medium", "target": target})

        self._findings.extend(findings)
        return {
            "success": True,
            "target": target,
            "findings": findings,
        }

    async def _validate(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "total_findings": len(self._findings),
            "findings": self._findings[-20:],
        }
