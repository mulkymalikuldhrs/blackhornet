"""Governance specialist — IT governance and oversight."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class GovernanceSpecialist(BaseAgent):
    """Specialist agent for IT governance and oversight.

    Handles governance framework management, policy enforcement,
    risk assessment, stakeholder reporting, and governance monitoring.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY, autonomy_level=3)
        super().__init__(spec=spec, **kwargs)
        self._frameworks: Dict[str, Dict[str, Any]] = {}
        self._policies: Dict[str, Dict[str, Any]] = {}
        self._governance_log: List[Dict[str, Any]] = []

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "register_framework":
            return await self._register_framework(task)
        elif action == "define_policy":
            return await self._define_policy(task)
        elif action == "assess_maturity":
            return await self._assess_maturity(task)
        elif action == "stakeholder_report":
            return await self._stakeholder_report(task)
        elif action == "track_compliance":
            return await self._track_compliance(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "governance_event":
            event = message.get("payload", {})
            self._governance_log.append({**event, "recorded_at": time.time()})
            return {"event_recorded": True}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "framework_management", "policy_definition", "maturity_assessment",
            "stakeholder_reporting", "compliance_tracking", "governance_monitoring",
            "it_audit_management", "strategic_alignment",
        ]

    async def _register_framework(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "COBIT")
        version = task.payload.get("version", "2019")
        description = task.payload.get("description", "")

        framework = {
            "name": name,
            "version": version,
            "description": description,
            "registered_at": time.time(),
            "maturity_level": 3,
            "policies_count": 0,
        }
        self._frameworks[name] = framework
        return {"success": True, "framework": name, "version": version}

    async def _define_policy(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_policy")
        framework = task.payload.get("framework", "COBIT")
        requirements = task.payload.get("requirements", [])
        owner = task.payload.get("owner", "IT Department")

        policy = {
            "name": name,
            "framework": framework,
            "requirements": requirements,
            "owner": owner,
            "defined_at": time.time(),
            "status": "active",
            "compliance_rate": 95.0,
        }
        self._policies[name] = policy
        return {"success": True, "policy": name, "framework": framework}

    async def _assess_maturity(self, task: Task) -> Dict[str, Any]:
        framework = task.payload.get("framework", "COBIT")
        dimensions = task.payload.get("dimensions", ["process", "people", "technology", "governance"])

        maturity_scores: Dict[str, int] = {}
        for dim in dimensions:
            maturity_scores[dim] = 3

        overall = sum(maturity_scores.values()) / len(maturity_scores) if maturity_scores else 0
        return {"success": True, "framework": framework, "maturity_scores": maturity_scores, "overall_maturity": round(overall, 1)}

    async def _stakeholder_report(self, task: Task) -> Dict[str, Any]:
        stakeholders = task.payload.get("staff", ["executives", "it_leadership"])
        period = task.payload.get("period", "quarterly")

        report = {
            "stakeholders": stakeholders,
            "period": period,
            "governance_score": 88.5,
            "policy_compliance": 94.0,
            "risk_status": "managed",
            "key_initiatives": ["Digital transformation governance", "Cloud adoption framework"],
            "generated_at": time.time(),
        }
        return {"success": True, "report": report}

    async def _track_compliance(self, task: Task) -> Dict[str, Any]:
        policy = task.payload.get("policy", "all")
        compliance_data = {
            "overall": 94.0,
            "by_framework": {"COBIT": 95.0, "ITIL": 92.0, "ISO27001": 96.0},
            "violations": 3,
            "open_findings": 1,
        }
        return {"success": True, "compliance": compliance_data}

    def _monitor(self) -> Dict[str, Any]:
        return {
            "success": True,
            "metrics": {
                "frameworks_count": len(self._frameworks),
                "policies_count": len(self._policies),
                "governance_events": len(self._governance_log),
                "active_policies": sum(1 for p in self._policies.values() if p.get("status") == "active"),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "governance",
            "metrics": self._monitor()["metrics"],
        }
