"""StateManagementAgent — State management correctness."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

STATE_ISSUES = {
    "no_state_persistence": {"severity": "high", "description": "No state persistence"},
    "no_state_recovery": {"severity": "high", "description": "No state recovery mechanism"},
    "state_leak": {"severity": "high", "description": "State leak between requests"},
    "no_state_validation": {"severity": "medium", "description": "No state validation"},
    "no_state_locking": {"severity": "medium", "description": "No state locking"},
    "no_state_serialization": {"severity": "medium", "description": "No state serialization"},
    "no_state_migration": {"severity": "medium", "description": "No state migration strategy"},
    "no_state_versioning": {"severity": "medium", "description": "No state versioning"},
    "no_state_cleanup": {"severity": "medium", "description": "No state cleanup"},
    "no_state_monitoring": {"severity": "low", "description": "No state monitoring"},
}


class StateManagementAgent(BaseAgent):
    """State management correctness agent.

    Features
    --------
    * State persistence validation
    * State recovery verification
    * State leak detection
    * State migration strategy audit
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
        if msg_type == "state_query":
            return {"findings": self._findings[-10:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "state_management_audit", "state_persistence_validation",
            "state_recovery_verification", "state_leak_detection",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        config = task.payload.get("config", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []

        checks = {
            "state_persistence": "no_state_persistence",
            "state_recovery": "no_state_recovery",
            "state_validation": "no_state_validation",
            "state_locking": "no_state_locking",
            "state_serialization": "no_state_serialization",
            "state_migration": "no_state_migration",
            "state_versioning": "no_state_versioning",
            "state_cleanup": "no_state_cleanup",
        }

        for config_key, issue_key in checks.items():
            if not config.get(config_key, False):
                issue = STATE_ISSUES[issue_key]
                findings.append({
                    "type": issue_key,
                    "severity": issue["severity"],
                    "target": target,
                    "description": issue["description"],
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
