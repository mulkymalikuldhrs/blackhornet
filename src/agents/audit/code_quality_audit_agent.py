"""CodeQualityAuditAgent — Code quality, complexity, and maintainability analysis."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

COMPLEXITY_PATTERNS = {
    "deep_nesting": {"pattern": r"(\t|\s{4}).*(\t|\s{4}).*(\t|\s{4}).*(\t|\s{4})", "severity": "medium"},
    "long_line": {"pattern": r".{200,}", "severity": "low"},
    "todo_fixme": {"pattern": r"(?i)(TODO|FIXME|HACK|XXX)", "severity": "info"},
    "magic_number": {"pattern": r"[^a-zA-Z_]\b\d{3,}\b", "severity": "low"},
    "god_function": {"pattern": r"def \w+\([^)]*\):[^}]{500,}", "severity": "high"},
    "duplicate_code": {"pattern": r"(.{50,})\1", "severity": "medium"},
}

MAINTAINABILITY_INDICATORS = {
    "comment_ratio": {"min": 0.1, "max": 0.4},
    "function_length": {"max": 50},
    "file_length": {"max": 500},
    "parameter_count": {"max": 5},
}


class CodeQualityAuditAgent(BaseAgent):
    """Code quality, complexity, and maintainability analysis agent.

    Features
    --------
    * Complexity metric computation
    * Maintainability index scoring
    * Code smell detection
    * Quality gate enforcement
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._metrics: Dict[str, Any] = {}

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
        if msg_type == "quality_query":
            return {"metrics": self._metrics}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "code_quality_analysis", "complexity_scoring", "maintainability_index",
            "code_smell_detection", "quality_gates",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        content = task.payload.get("content", "")
        target = task.payload.get("target", "")
        lines = content.split("\n")
        findings: List[Dict[str, Any]] = []

        metrics = {
            "total_lines": len(lines),
            "blank_lines": sum(1 for l in lines if not l.strip()),
            "comment_lines": sum(1 for l in lines if l.strip().startswith("#")),
            "code_lines": 0,
        }

        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                metrics["code_lines"] += 1

        metrics["comment_ratio"] = metrics["comment_lines"] / max(1, metrics["code_lines"])
        metrics["blank_ratio"] = metrics["blank_lines"] / max(1, metrics["total_lines"])

        for indicator, config in COMPLEXITY_PATTERNS.items():
            matches = re.findall(config["pattern"], content)
            if matches:
                findings.append({
                    "type": indicator,
                    "severity": config["severity"],
                    "count": len(matches),
                    "target": target,
                })

        self._findings.extend(findings)
        self._metrics = metrics

        return {
            "success": True,
            "target": target,
            "metrics": metrics,
            "findings": findings,
            "maintainability_score": self._maintainability_score(metrics),
        }

    async def _analyze(self, task: Task) -> Dict[str, Any]:
        return await self._audit(task)

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "total_findings": len(self._findings),
            "metrics": self._metrics,
            "findings": self._findings[-20:],
        }

    def _maintainability_score(self, metrics: Dict[str, Any]) -> float:
        score = 1.0
        if metrics.get("comment_ratio", 0) < 0.1:
            score -= 0.2
        if metrics.get("total_lines", 0) > 500:
            score -= 0.1
        severity_penalty = {"high": 0.2, "medium": 0.1, "low": 0.05, "info": 0.0}
        for f in self._findings:
            score -= severity_penalty.get(f.get("severity", "info"), 0)
        return max(0.0, min(1.0, score))
