"""Backend API specialist — REST/GraphQL API development and optimization."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class BackendApiSpecialist(BaseAgent):
    """Specialist agent for REST and GraphQL API development and optimization.

    Handles API endpoint design, request validation, rate limiting,
    response optimization, and API versioning strategies.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.CODER, autonomy_level=2)
        super().__init__(spec=spec, **kwargs)
        self._endpoints: Dict[str, Dict[str, Any]] = {}
        self._request_metrics: Dict[str, List[float]] = {}
        self._rate_limits: Dict[str, Dict[str, Any]] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "create_endpoint":
            return await self._create_endpoint(task)
        elif action == "optimize_endpoint":
            return await self._optimize_endpoint(task)
        elif action == "validate_request":
            return await self._validate_request(task)
        elif action == "analyze_performance":
            return await self._analyze_performance(task)
        elif action == "configure_rate_limit":
            return await self._configure_rate_limit(task)
        elif action == "generate_api_spec":
            return await self._generate_api_spec(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "api_health_check":
            return {"status": "healthy", "endpoints": len(self._endpoints)}
        elif msg_type == "endpoint_query":
            endpoint = message.get("payload", {}).get("endpoint", "")
            return self._endpoints.get(endpoint, {"found": False})
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "rest_api_development", "graphql_api", "api_design",
            "request_validation", "rate_limiting", "response_optimization",
            "api_versioning", "openapi_spec", "endpoint_monitoring",
        ]

    async def _create_endpoint(self, task: Task) -> Dict[str, Any]:
        path = task.payload.get("path", "/")
        method = task.payload.get("method", "GET").upper()
        handler = task.payload.get("handler", "default_handler")
        middleware = task.payload.get("middleware", [])
        validation_rules = task.payload.get("validation", {})
        rate_limit = task.payload.get("rate_limit", {"requests": 100, "window_seconds": 60})

        endpoint_key = f"{method} {path}"
        endpoint = {
            "path": path,
            "method": method,
            "handler": handler,
            "middleware": middleware,
            "validation": validation_rules,
            "rate_limit": rate_limit,
            "created_at": time.time(),
            "request_count": 0,
            "error_count": 0,
            "avg_response_ms": 0.0,
        }
        self._endpoints[endpoint_key] = endpoint
        self._request_metrics[endpoint_key] = []

        logger.info(f"Created endpoint: {method} {path}")
        return {"success": True, "endpoint": endpoint_key, "config": endpoint}

    async def _optimize_endpoint(self, task: Task) -> Dict[str, Any]:
        endpoint_key = task.payload.get("endpoint", "")
        if endpoint_key not in self._endpoints:
            return {"success": False, "error": f"Endpoint {endpoint_key} not found"}

        endpoint = self._endpoints[endpoint_key]
        optimizations: List[str] = []

        if endpoint["avg_response_ms"] > 200:
            optimizations.append("add_response_caching")
        if endpoint["request_count"] > 1000:
            optimizations.append("add_pagination")
        if not endpoint["middleware"]:
            optimizations.append("add_input_validation_middleware")

        endpoint["optimizations"] = optimizations
        return {"success": True, "endpoint": endpoint_key, "optimizations": optimizations}

    async def _validate_request(self, task: Task) -> Dict[str, Any]:
        endpoint_key = task.payload.get("endpoint", "")
        request_data = task.payload.get("data", {})
        endpoint = self._endpoints.get(endpoint_key, {})
        validation_rules = endpoint.get("validation", {})

        errors: List[Dict[str, str]] = []
        for field, rules in validation_rules.items():
            value = request_data.get(field)
            if rules.get("required") and value is None:
                errors.append({"field": field, "error": "required"})
            elif value is not None:
                if "max_length" in rules and len(str(value)) > rules["max_length"]:
                    errors.append({"field": field, "error": "exceeds max_length"})
                if "type" in rules and not isinstance(value, rules["type"]):
                    errors.append({"field": field, "error": "invalid_type"})

        return {"valid": len(errors) == 0, "errors": errors}

    async def _analyze_performance(self, task: Task) -> Dict[str, Any]:
        endpoint_key = task.payload.get("endpoint", "")
        metrics = self._request_metrics.get(endpoint_key, [])

        if not metrics:
            return {"success": True, "endpoint": endpoint_key, "data": {"no_data": True}}

        avg_ms = sum(metrics) / len(metrics)
        p95_ms = sorted(metrics)[int(len(metrics) * 0.95)] if len(metrics) > 1 else avg_ms
        p99_ms = sorted(metrics)[int(len(metrics) * 0.99)] if len(metrics) > 1 else avg_ms

        return {
            "success": True,
            "endpoint": endpoint_key,
            "data": {
                "total_requests": len(metrics),
                "avg_response_ms": round(avg_ms, 2),
                "p95_response_ms": round(p95_ms, 2),
                "p99_response_ms": round(p99_ms, 2),
                "min_response_ms": round(min(metrics), 2),
                "max_response_ms": round(max(metrics), 2),
            },
        }

    async def _configure_rate_limit(self, task: Task) -> Dict[str, Any]:
        endpoint_key = task.payload.get("endpoint", "")
        requests = task.payload.get("requests", 100)
        window = task.payload.get("window_seconds", 60)

        self._rate_limits[endpoint_key] = {
            "requests": requests,
            "window_seconds": window,
            "current_count": 0,
            "window_start": time.time(),
        }
        return {"success": True, "endpoint": endpoint_key, "rate_limit": self._rate_limits[endpoint_key]}

    async def _generate_api_spec(self, task: Task) -> Dict[str, Any]:
        spec = {
            "openapi": "3.0.3",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {},
        }
        for key, endpoint in self._endpoints.items():
            path = endpoint["path"]
            method = endpoint["method"].lower()
            if path not in spec["paths"]:
                spec["paths"][path] = {}
            spec["paths"][path][method] = {
                "summary": f"Handler: {endpoint['handler']}",
                "responses": {"200": {"description": "Success"}},
            }
        return {"success": True, "spec": spec}

    def _monitor(self) -> Dict[str, Any]:
        total_requests = sum(len(m) for m in self._request_metrics.values())
        return {
            "success": True,
            "metrics": {
                "endpoints_count": len(self._endpoints),
                "total_requests": total_requests,
                "rate_limits_configured": len(self._rate_limits),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "backend_api",
            "metrics": self._monitor()["metrics"],
        }
