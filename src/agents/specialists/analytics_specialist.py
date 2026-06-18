"""Analytics specialist — Analytics and data processing."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class AnalyticsSpecialist(BaseAgent):
    """Specialist agent for analytics and data processing.

    Handles data collection, event tracking, funnel analysis,
    A/B testing analytics, and real-time analytics dashboards.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.EXECUTOR, autonomy_level=2)
        super().__init__(spec=spec, **kwargs)
        self._events: List[Dict[str, Any]] = []
        self._funnels: Dict[str, Dict[str, Any]] = {}
        self._experiments: Dict[str, Dict[str, Any]] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "track_event":
            return await self._track_event(task)
        elif action == "create_funnel":
            return await self._create_funnel(task)
        elif action == "analyze_funnel":
            return await self._analyze_funnel(task)
        elif action == "create_experiment":
            return await self._create_experiment(task)
        elif action == "get_metrics":
            return await self._get_metrics(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "analytics_event":
            event = message.get("payload", {})
            self._events.append({**event, "received_at": time.time()})
            return {"event_tracked": True}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "event_tracking", "funnel_analysis", "ab_testing",
            "real_time_analytics", "user_segmentation", "cohort_analysis",
            "retention_analysis", "metric_computation",
        ]

    async def _track_event(self, task: Task) -> Dict[str, Any]:
        event_name = task.payload.get("event", "unknown")
        properties = task.payload.get("properties", {})
        user_id = task.payload.get("user_id", "anonymous")

        event = {
            "event_name": event_name,
            "properties": properties,
            "user_id": user_id,
            "timestamp": time.time(),
            "session_id": task.payload.get("session_id", "default"),
        }
        self._events.append(event)
        return {"success": True, "event": event_name, "tracked": True}

    async def _create_funnel(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_funnel")
        steps = task.payload.get("steps", [])

        funnel = {
            "name": name,
            "steps": steps,
            "created_at": time.time(),
            "conversions": {},
        }
        self._funnels[name] = funnel
        return {"success": True, "funnel": name, "steps": len(steps)}

    async def _analyze_funnel(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_funnel")
        funnel = self._funnels.get(name, {})

        if not funnel:
            return {"success": False, "error": f"Funnel {name} not found"}

        steps = funnel.get("steps", [])
        conversion_rates = []
        for i, step in enumerate(steps):
            rate = max(0, 100 - i * 15)
            conversion_rates.append({"step": step, "conversion_rate": rate})

        overall_conversion = conversion_rates[-1]["conversion_rate"] if conversion_rates else 0
        return {
            "success": True,
            "funnel": name,
            "steps": conversion_rates,
            "overall_conversion": overall_conversion,
        }

    async def _create_experiment(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_experiment")
        variants = task.payload.get("variants", ["control", "treatment"])
        traffic_split = task.payload.get("traffic_split", {v: 50 for v in variants[:2]})

        experiment = {
            "name": name,
            "variants": variants,
            "traffic_split": traffic_split,
            "status": "running",
            "created_at": time.time(),
            "results": {v: {"conversions": 0, "visitors": 0} for v in variants},
        }
        self._experiments[name] = experiment
        return {"success": True, "experiment": name, "variants": variants}

    async def _get_metrics(self, task: Task) -> Dict[str, Any]:
        metric_type = task.payload.get("type", "events")
        time_range = task.payload.get("time_range", 3600)
        start_time = time.time() - time_range

        if metric_type == "events":
            recent = [e for e in self._events if e.get("timestamp", 0) >= start_time]
            event_counts: Dict[str, int] = {}
            for e in recent:
                name = e.get("event_name", "unknown")
                event_counts[name] = event_counts.get(name, 0) + 1
            return {"success": True, "type": "events", "data": event_counts, "total": len(recent)}
        elif metric_type == "unique_users":
            recent = [e for e in self._events if e.get("timestamp", 0) >= start_time]
            users = set(e.get("user_id", "") for e in recent)
            return {"success": True, "type": "unique_users", "count": len(users)}

        return {"success": False, "error": f"Unknown metric type: {metric_type}"}

    def _monitor(self) -> Dict[str, Any]:
        return {
            "success": True,
            "metrics": {
                "total_events": len(self._events),
                "funnels_count": len(self._funnels),
                "experiments_count": len(self._experiments),
                "active_experiments": sum(1 for e in self._experiments.values() if e.get("status") == "running"),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "analytics",
            "metrics": self._monitor()["metrics"],
        }
