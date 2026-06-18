"""Risk management specialist — Risk assessment and management."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class RiskManagementSpecialist(BaseAgent):
    """Specialist agent for risk assessment and management.

    Handles risk identification, assessment, mitigation planning,
    risk monitoring, and risk reporting.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY, autonomy_level=3)
        super().__init__(spec=spec, **kwargs)
        self._risks: Dict[str, Dict[str, Any]] = {}
        self._mitigations: Dict[str, Dict[str, Any]] = {}
        self._risk_register: List[Dict[str, Any]] = []

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "identify_risk":
            return await self._identify_risk(task)
        elif action == "assess_risk":
            return await self._assess_risk(task)
        elif action == "create_mitigation":
            return await self._create_mitigation(task)
        elif action == "get_risk_register":
            return await self._get_risk_register(task)
        elif action == "calculate_risk_score":
            return await self._calculate_risk_score(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "risk_event":
            event = message.get("payload", {})
            risk_id = event.get("risk_id", "")
            if risk_id in self._risks:
                self._risks[risk_id]["status"] = "triggered"
            return {"risk_event_processed": True}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "risk_identification", "risk_assessment", "mitigation_planning",
            "risk_monitoring", "risk_reporting", "risk_register_management",
            "quantitative_analysis", "qualitative_analysis",
        ]

    async def _identify_risk(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_risk")
        category = task.payload.get("category", "operational")
        description = task.payload.get("description", "")
        owner = task.payload.get("owner", "risk_team")

        risk_id = f"risk-{int(time.time())}"
        risk = {
            "risk_id": risk_id,
            "name": name,
            "category": category,
            "description": description,
            "owner": owner,
            "status": "identified",
            "identified_at": time.time(),
            "probability": 0.5,
            "impact": 0.5,
            "risk_score": 0.25,
        }
        self._risks[risk_id] = risk
        self._risk_register.append(risk)
        return {"success": True, "risk_id": risk_id, "name": name}

    async def _assess_risk(self, task: Task) -> Dict[str, Any]:
        risk_id = task.payload.get("risk_id", "")
        probability = task.payload.get("probability", 0.5)
        impact = task.payload.get("impact", 0.5)

        if risk_id not in self._risks:
            return {"success": False, "error": f"Risk {risk_id} not found"}

        risk = self._risks[risk_id]
        risk["probability"] = probability
        risk["impact"] = impact
        risk["risk_score"] = probability * impact
        risk["status"] = "assessed"

        if risk["risk_score"] > 0.7:
            risk["level"] = "critical"
        elif risk["risk_score"] > 0.4:
            risk["level"] = "high"
        elif risk["risk_score"] > 0.2:
            risk["level"] = "medium"
        else:
            risk["level"] = "low"

        return {"success": True, "risk_id": risk_id, "risk_score": risk["risk_score"], "level": risk["level"]}

    async def _create_mitigation(self, task: Task) -> Dict[str, Any]:
        risk_id = task.payload.get("risk_id", "")
        strategy = task.payload.get("strategy", "mitigate")
        actions = task.payload.get("actions", [])
        owner = task.payload.get("owner", "")

        mitigation_id = f"mit-{int(time.time())}"
        mitigation = {
            "mitigation_id": mitigation_id,
            "risk_id": risk_id,
            "strategy": strategy,
            "actions": actions,
            "owner": owner,
            "status": "planned",
            "created_at": time.time(),
        }
        self._mitigations[mitigation_id] = mitigation
        if risk_id in self._risks:
            self._risks[risk_id]["mitigation"] = mitigation_id
        return {"success": True, "mitigation_id": mitigation_id, "strategy": strategy}

    async def _get_risk_register(self, task: Task) -> Dict[str, Any]:
        category = task.payload.get("category")
        level = task.payload.get("level")

        register = list(self._risk_register)
        if category:
            register = [r for r in register if r.get("category") == category]
        if level:
            register = [r for r in register if r.get("level") == level]

        return {"success": True, "risks": register, "total": len(register)}

    async def _calculate_risk_score(self, task: Task) -> Dict[str, Any]:
        probability = task.payload.get("probability", 0.5)
        impact = task.payload.get("impact", 0.5)
        risk_score = probability * impact

        return {"success": True, "probability": probability, "impact": impact, "risk_score": risk_score}

    def _monitor(self) -> Dict[str, Any]:
        critical = sum(1 for r in self._risks.values() if r.get("level") == "critical")
        return {
            "success": True,
            "metrics": {
                "total_risks": len(self._risks),
                "critical_risks": critical,
                "mitigations_count": len(self._mitigations),
                "average_risk_score": round(sum(r.get("risk_score", 0) for r in self._risks.values()) / max(1, len(self._risks)), 2),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "risk_management",
            "metrics": self._monitor()["metrics"],
        }
