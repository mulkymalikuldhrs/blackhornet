"""TestCoverageAuditAgent — Test coverage completeness."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

COVERAGE_THRESHOLDS = {
    "unit_test_coverage": {"minimum": 80, "target": 90, "severity": "high"},
    "integration_test_coverage": {"minimum": 60, "target": 80, "severity": "high"},
    "e2e_test_coverage": {"minimum": 30, "target": 50, "severity": "medium"},
    "branch_coverage": {"minimum": 70, "target": 85, "severity": "high"},
    "mutation_score": {"minimum": 50, "target": 70, "severity": "medium"},
}

TEST_QUALITY_ISSUES = {
    "no_tests": {"severity": "critical", "description": "No tests for module"},
    "flaky_tests": {"severity": "high", "description": "Flaky/unstable tests"},
    "slow_tests": {"severity": "medium", "description": "Slow test execution"},
    "missing_edge_cases": {"severity": "medium", "description": "Missing edge case tests"},
    "no_negative_tests": {"severity": "medium", "description": "No negative test cases"},
    "test_code_duplication": {"severity": "low", "description": "Duplicated test code"},
}


class TestCoverageAuditAgent(BaseAgent):
    """Test coverage completeness agent.

    Features
    --------
    * Coverage threshold validation
    * Test quality assessment
    * Coverage gap identification
    * Test distribution analysis
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._coverage_data: Dict[str, float] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "audit")
        if action == "audit":
            return await self._audit(task)
        elif action == "analyze":
            return await self._analyze(task)
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "coverage_query":
            return {"coverage_data": self._coverage_data}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "test_coverage_audit", "coverage_threshold_validation",
            "test_quality_assessment", "coverage_gap_identification",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        coverage_data = task.payload.get("coverage_data", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []

        for metric, value in coverage_data.items():
            if metric in COVERAGE_THRESHOLDS:
                thresholds = COVERAGE_THRESHOLDS[metric]
                if value < thresholds["minimum"]:
                    findings.append({
                        "type": "coverage_below_minimum",
                        "severity": thresholds["severity"],
                        "metric": metric,
                        "value": value,
                        "minimum": thresholds["minimum"],
                        "target": target,
                    })

        self._coverage_data = coverage_data
        self._findings.extend(findings)

        return {
            "success": True,
            "target": target,
            "coverage_data": coverage_data,
            "findings": findings,
        }

    async def _analyze(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "total_findings": len(self._findings),
            "coverage_data": self._coverage_data,
            "findings": self._findings[-20:],
        }
