"""RiskAssessmentAgent — Risk identification and scoring."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

RISK_CATEGORIES = {
    "technical": {"weight": 0.3, "factors": ["complexity", "dependencies", "technology_age"]},
    "security": {"weight": 0.35, "factors": ["vulnerabilities", "exposure", "sensitivity"]},
    "operational": {"weight": 0.2, "factors": ["availability", "scalability", "maintainability"]},
    "compliance": {"weight": 0.15, "factors": ["regulatory", "policy", "audit_readiness"]},
}

SEVERITY_LEVELS = {
    "critical": {"score_range": (9, 10), "action": "immediate"},
    "high": {"score_range": (7, 8.99), "action": "urgent"},
    "medium": {"score_range": (4, 6.99), "action": "planned"},
    "low": {"score_range": (0, 3.99), "action": "monitor"},
}


class RiskAssessmentAgent(BaseAgent):
    """Risk identification and scoring agent.

    Features
    --------
    * Multi-factor risk scoring
    * Risk categorization and prioritization
    * Mitigation recommendation generation
    * Risk trend tracking over time
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._risk_history: List[Dict[str, Any]] = []

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "audit")
        if action == "audit":
            return await self._audit(task)
        elif action == "assess":
            return await self._assess(task)
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "risk_query":
            return {"risk_history": self._risk_history[-5:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "risk_assessment", "risk_scoring", "risk_categorization",
            "mitigation_recommendations", "risk_trend_tracking",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        risk_factors = task.payload.get("risk_factors", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []
        category_scores: Dict[str, float] = {}

        for category, config in RISK_CATEGORIES.items():
            category_factors = risk_factors.get(category, {})
            factor_scores = []
            for factor in config["factors"]:
                score = category_factors.get(factor, 5.0)
                factor_scores.append(float(score))
                if score >= 7:
                    findings.append({
                        "factor": factor,
                        "category": category,
                        "score": score,
                        "severity": "high" if score >= 8 else "medium",
                        "target": target,
                    })
            if factor_scores:
                category_scores[category] = sum(factor_scores) / len(factor_scores)

        overall_score = sum(
            category_scores.get(cat, 5.0) * config["weight"]
            for cat, config in RISK_CATEGORIES.items()
        )

        risk_level = "low"
        for level, level_config in SEVERITY_LEVELS.items():
            min_score, max_score = level_config["score_range"]
            if min_score <= overall_score <= max_score:
                risk_level = level
                break

        self._findings.extend(findings)
        assessment = {
            "target": target,
            "overall_score": round(overall_score, 2),
            "risk_level": risk_level,
            "category_scores": category_scores,
            "findings_count": len(findings),
        }
        self._risk_history.append(assessment)

        return {
            "success": True,
            "assessment": assessment,
            "findings": findings,
        }

    async def _assess(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "total_findings": len(self._findings),
            "assessments_performed": len(self._risk_history),
            "recent_assessments": self._risk_history[-5:],
            "findings": self._findings[-20:],
        }
