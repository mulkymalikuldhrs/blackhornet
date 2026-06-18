"""PerformanceAuditAgent — Performance bottleneck detection and analysis."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

PERFORMANCE_THRESHOLDS = {
    "response_time_ms": {"warning": 200, "critical": 1000},
    "cpu_usage_percent": {"warning": 70, "critical": 90},
    "memory_usage_mb": {"warning": 512, "critical": 1024},
    "disk_io_ms": {"warning": 50, "critical": 200},
    "query_time_ms": {"warning": 100, "critical": 500},
    "throughput_rps": {"warning": 100, "critical": 50},
}


class PerformanceAuditAgent(BaseAgent):
    """Performance bottleneck detection and analysis agent.

    Features
    --------
    * Response time analysis
    * Resource utilization monitoring
    * Query performance profiling
    * Bottleneck identification and recommendations
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._metrics: Dict[str, List[float]] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "audit")
        if action == "audit":
            return await self._audit(task)
        elif action == "benchmark":
            return await self._benchmark(task)
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "performance_query":
            return {"metrics": self._metrics}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "performance_analysis", "bottleneck_detection", "resource_monitoring",
            "query_profiling", "throughput_analysis",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        metrics = task.payload.get("metrics", {})
        target = task.payload.get("target", "")
        findings: List[Dict[str, Any]] = []

        for metric_name, value in metrics.items():
            if metric_name in PERFORMANCE_THRESHOLDS:
                thresholds = PERFORMANCE_THRESHOLDS[metric_name]
                if value >= thresholds["critical"]:
                    findings.append({
                        "metric": metric_name,
                        "severity": "critical",
                        "value": value,
                        "threshold": thresholds["critical"],
                        "target": target,
                    })
                elif value >= thresholds["warning"]:
                    findings.append({
                        "metric": metric_name,
                        "severity": "medium",
                        "value": value,
                        "threshold": thresholds["warning"],
                        "target": target,
                    })

            if metric_name not in self._metrics:
                self._metrics[metric_name] = []
            self._metrics[metric_name].append(value)

        self._findings.extend(findings)
        return {
            "success": True,
            "target": target,
            "findings": findings,
            "metrics_summary": {k: sum(v)/len(v) for k, v in self._metrics.items() if v},
        }

    async def _benchmark(self, task: Task) -> Dict[str, Any]:
        start = time.monotonic()
        result = await self._audit(task)
        elapsed = (time.monotonic() - start) * 1000
        result["benchmark_ms"] = elapsed
        return result

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "total_findings": len(self._findings),
            "metrics_tracked": len(self._metrics),
            "findings": self._findings[-20:],
        }
