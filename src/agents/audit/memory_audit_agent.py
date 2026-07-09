"""MemoryAuditAgent — Memory usage and leak detection."""

from __future__ import annotations

import logging
import tracemalloc
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)

MEMORY_THRESHOLDS = {
    "heap_usage_mb": {"warning": 256, "critical": 512},
    "heap_growth_rate": {"warning": 10, "critical": 50},
    "gc_pressure": {"warning": 0.5, "critical": 0.8},
    "object_count": {"warning": 100000, "critical": 500000},
    "fragmentation_ratio": {"warning": 0.3, "critical": 0.6},
}


class MemoryAuditAgent(BaseAgent):
    """Memory usage and leak detection agent.

    Features
    --------
    * Heap memory tracking
    * Memory leak detection via growth analysis
    * Object lifecycle monitoring
    * Garbage collection pressure analysis
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY)
        super().__init__(spec=spec, **kwargs)
        self._findings: List[Dict[str, Any]] = []
        self._snapshots: List[Dict[str, Any]] = []
        self._tracking = False

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "audit")
        if action == "audit":
            return await self._audit(task)
        elif action == "start_tracking":
            return self._start_tracking()
        elif action == "stop_tracking":
            return self._stop_tracking()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "memory_query":
            return {"snapshots": self._snapshots[-5:]}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "memory_tracking", "leak_detection", "heap_analysis",
            "object_lifecycle", "gc_pressure_analysis",
        ]

    async def _audit(self, task: Task) -> Dict[str, Any]:
        target = task.payload.get("target", "")
        memory_stats = task.payload.get("memory_stats", {})
        findings: List[Dict[str, Any]] = []

        for metric, value in memory_stats.items():
            if metric in MEMORY_THRESHOLDS:
                thresholds = MEMORY_THRESHOLDS[metric]
                if value >= thresholds["critical"]:
                    findings.append({
                        "metric": metric,
                        "severity": "critical",
                        "value": value,
                        "threshold": thresholds["critical"],
                        "target": target,
                    })
                elif value >= thresholds["warning"]:
                    findings.append({
                        "metric": metric,
                        "severity": "medium",
                        "value": value,
                        "threshold": thresholds["warning"],
                        "target": target,
                    })

        snapshot = {
            "target": target,
            "findings_count": len(findings),
            "stats": memory_stats,
        }
        self._snapshots.append(snapshot)
        self._findings.extend(findings)

        return {
            "success": True,
            "target": target,
            "findings": findings,
            "snapshot": snapshot,
        }

    def _start_tracking(self) -> Dict[str, Any]:
        if not self._tracking:
            tracemalloc.start()
            self._tracking = True
        return {"success": True, "tracking": True}

    def _stop_tracking(self) -> Dict[str, Any]:
        if self._tracking:
            tracemalloc.stop()
            self._tracking = False
        return {"success": True, "tracking": False}

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "total_findings": len(self._findings),
            "snapshots_taken": len(self._snapshots),
            "tracking_active": self._tracking,
            "findings": self._findings[-20:],
        }
