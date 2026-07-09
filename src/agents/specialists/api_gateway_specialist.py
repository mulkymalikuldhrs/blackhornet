"""API gateway specialist — API gateway management and optimization."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class ApiGatewaySpecialist(BaseAgent):
    """Specialist agent for API gateway management and optimization.

    Handles route configuration, rate limiting, authentication,
    request transformation, and gateway monitoring.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.EXECUTOR, autonomy_level=3)
        super().__init__(spec=spec, **kwargs)
        self._routes: Dict[str, Dict[str, Any]] = {}
        self._rate_limits: Dict[str, Dict[str, Any]] = {}
        self._request_log: List[Dict[str, Any]] = []

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "configure_route":
            return await self._configure_route(task)
        elif action == "set_rate_limit":
            return await self._set_rate_limit(task)
        elif action == "configure_auth":
            return await self._configure_auth(task)
        elif action == "transform_request":
            return await self._transform_request(task)
        elif action == "get_usage":
            return await self._get_usage(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "gateway_request":
            route = message.get("payload", {}).get("route", "")
            self._request_log.append({"route": route, "timestamp": time.time(), "status": "processed"})
            return {"request_processed": True}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "route_management", "rate_limiting", "authentication",
            "request_transformation", "response_caching", "load_balancing",
            "circuit_breaker", "api_analytics",
        ]

    async def _configure_route(self, task: Task) -> Dict[str, Any]:
        path = task.payload.get("path", "/")
        method = task.payload.get("method", "GET").upper()
        upstream = task.payload.get("upstream", "http://localhost:8080")
        strip_prefix = task.payload.get("strip_prefix", False)

        route_key = f"{method} {path}"
        route = {
            "path": path,
            "method": method,
            "upstream": upstream,
            "strip_prefix": strip_prefix,
            "created_at": time.time(),
            "request_count": 0,
            "avg_latency_ms": 0.0,
        }
        self._routes[route_key] = route
        return {"success": True, "route": route_key, "upstream": upstream}

    async def _set_rate_limit(self, task: Task) -> Dict[str, Any]:
        route = task.payload.get("route", "*")
        requests_per_second = task.payload.get("requests_per_second", 100)
        burst = task.payload.get("burst", 200)

        rate_limit = {
            "route": route,
            "requests_per_second": requests_per_second,
            "burst": burst,
            "enabled": True,
            "configured_at": time.time(),
        }
        self._rate_limits[route] = rate_limit
        return {"success": True, "route": route, "rate_limit": rate_limit}

    async def _configure_auth(self, task: Task) -> Dict[str, Any]:
        route = task.payload.get("route", "*")
        auth_type = task.payload.get("type", "jwt")
        config = task.payload.get("config", {})

        auth_config = {
            "route": route,
            "type": auth_type,
            "config": config,
            "enabled": True,
        }
        if route in self._routes:
            self._routes[route]["auth"] = auth_config
        return {"success": True, "route": route, "auth": auth_config}

    async def _transform_request(self, task: Task) -> Dict[str, Any]:
        route = task.payload.get("route", "*")
        add_headers = task.payload.get("add_headers", {})
        remove_headers = task.payload.get("remove_headers", [])
        add_query = task.payload.get("add_query_params", {})

        transformation = {
            "add_headers": add_headers,
            "remove_headers": remove_headers,
            "add_query_params": add_query,
        }
        if route in self._routes:
            self._routes[route]["transformation"] = transformation
        return {"success": True, "route": route, "transformation": transformation}

    async def _get_usage(self, task: Task) -> Dict[str, Any]:
        time_range = task.payload.get("time_range", 3600)
        start_time = time.time() - time_range

        recent = [r for r in self._request_log if r.get("timestamp", 0) >= start_time]
        routes: Dict[str, int] = {}
        for r in recent:
            route = r.get("route", "unknown")
            routes[route] = routes.get(route, 0) + 1

        return {"success": True, "total_requests": len(recent), "by_route": routes}

    def _monitor(self) -> Dict[str, Any]:
        return {
            "success": True,
            "metrics": {
                "routes_count": len(self._routes),
                "rate_limits_count": len(self._rate_limits),
                "total_requests": len(self._request_log),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "api_gateway",
            "metrics": self._monitor()["metrics"],
        }
