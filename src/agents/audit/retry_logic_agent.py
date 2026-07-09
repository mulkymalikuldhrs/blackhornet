"""RetryLogicAgent — Retry logic correctness."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

RETRY_ISSUES = {
    "no_retry_mechanism": {"severity": "high", "description": "No retry mechanism"},
    "infinite_retry": {"severity": "critical", "description": "Infinite retry loop"},
    "no_exponential_backoff": {"severity": "medium", "description": "No exponential backoff"},
    "no_max_retries": {"severity": "high", "description": "No maximum retry limit"},
    "retry_on_success": {"severity": "medium", "description": "Retry on success responses"},
    "no_jitter": {"severity": "low", "description": "No jitter in retry timing"},
    "no_circuit_breaker": {"severity": "medium", "description": "No circuit breaker pattern"},
    "no_idempotency_key": {"severity": "medium", "description": "Missing idempotency key"},
    "retry_writes": {"severity": "high", "description": "Retrying non-idempotent operations"},
    "no_timeout_per_retry": {"severity": "medium", "description": "No timeout per retry attempt"},
}


class RetryLogicAgent(BaseAgent):
    """Retry logic correctness agent.

    Features
    --------
    * Retry pattern validation
    * Backoff strategy verification
    * Idempotency checking
    * Circuit breaker pattern validation
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
        if msg_type == "retry_query":
            return {"findings": self._findings[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "retry_logic_audit", "backoff_strategy_validation",
            "idempotency_check", "circuit_breaker_validation",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        config = task.payload.get("config", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []

        has_retry = config.get("max_retries", 0) > 0
        has_backoff = config.get("exponential_backoff", False)
        has_jitter = config.get("jitter", False)
        has_circuit_breaker = config.get("circuit_breaker", False)
        max_retries = config.get("max_retries", 0)

        if not has_retry:
            findings.append({
                "type": "no_retry_mechanism",
                "severity": "high",
                "target": target,
            })
        elif max_retries > 100:
            findings.append({
                "type": "infinite_retry",
                "severity": "critical",
                "max_retries": max_retries,
                "target": target,
            })

        if has_retry and not has_backoff:
            findings.append({
                "type": "no_exponential_backoff",
                "severity": "medium",
                "target": target,
            })

        if has_retry and not has_jitter:
            findings.append({
                "type": "no_jitter",
                "severity": "low",
                "target": target,
            })

        if not has_circuit_breaker:
            findings.append({
                "type": "no_circuit_breaker",
                "severity": "medium",
                "target": target,
            })

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
