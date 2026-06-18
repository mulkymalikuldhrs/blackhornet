"""Serverless specialist — Serverless computing and function management."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class ServerlessSpecialist(BaseAgent):
    """Specialist agent for serverless computing and function management.

    Handles function deployment, event triggers, API gateway configuration,
    cold start optimization, and serverless architecture patterns.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.EXECUTOR, autonomy_level=3)
        super().__init__(spec=spec, **kwargs)
        self._functions: Dict[str, Dict[str, Any]] = {}
        self._triggers: Dict[str, Dict[str, Any]] = {}
        self._invocation_logs: List[Dict[str, Any]] = []

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "deploy_function":
            return await self._deploy_function(task)
        elif action == "configure_trigger":
            return await self._configure_trigger(task)
        elif action == "invoke_function":
            return await self._invoke_function(task)
        elif action == "optimize_cold_start":
            return await self._optimize_cold_start(task)
        elif action == "configure_api_gateway":
            return await self._configure_api_gateway(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "function_status":
            func_name = message.get("payload", {}).get("function_name", "")
            return self._functions.get(func_name, {"found": False})
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "function_deployment", "event_trigger_management", "api_gateway_config",
            "cold_start_optimization", "serverless_architecture", "cost_management",
            "monitoring_integration", "auto_scaling",
        ]

    async def _deploy_function(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default-function")
        runtime = task.payload.get("runtime", "python3.11")
        handler = task.payload.get("handler", "index.handler")
        memory_mb = task.payload.get("memory_mb", 256)
        timeout_seconds = task.payload.get("timeout_seconds", 30)

        function = {
            "name": name,
            "runtime": runtime,
            "handler": handler,
            "memory_mb": memory_mb,
            "timeout_seconds": timeout_seconds,
            "status": "active",
            "invocation_count": 0,
            "avg_duration_ms": 0.0,
            "error_rate": 0.0,
            "deployed_at": time.time(),
        }
        self._functions[name] = function
        return {"success": True, "function": name, "status": "deployed"}

    async def _configure_trigger(self, task: Task) -> Dict[str, Any]:
        function_name = task.payload.get("function", "")
        trigger_type = task.payload.get("type", "http")
        config = task.payload.get("config", {})

        trigger = {
            "function": function_name,
            "type": trigger_type,
            "config": config,
            "enabled": True,
            "created_at": time.time(),
        }
        trigger_id = f"trigger-{function_name}-{trigger_type}"
        self._triggers[trigger_id] = trigger
        return {"success": True, "trigger_id": trigger_id, "config": trigger}

    async def _invoke_function(self, task: Task) -> Dict[str, Any]:
        function_name = task.payload.get("function", "")
        payload = task.payload.get("payload", {})

        if function_name not in self._functions:
            return {"success": False, "error": f"Function {function_name} not found"}

        func = self._functions[function_name]
        func["invocation_count"] += 1

        duration_ms = 45.5
        func["avg_duration_ms"] = (func["avg_duration_ms"] * (func["invocation_count"] - 1) + duration_ms) / func["invocation_count"]

        log = {
            "function": function_name,
            "duration_ms": duration_ms,
            "status": "success",
            "timestamp": time.time(),
        }
        self._invocation_logs.append(log)

        return {
            "success": True,
            "function": function_name,
            "duration_ms": duration_ms,
            "status": "success",
        }

    async def _optimize_cold_start(self, task: Task) -> Dict[str, Any]:
        function_name = task.payload.get("function", "")
        strategies = ["provisioned_concurrency", "smaller_package", "lazy_initialization", "keep_warm"]

        return {
            "success": True,
            "function": function_name,
            "strategies": strategies,
            "estimated_cold_start_reduction": "60%",
        }

    async def _configure_api_gateway(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default-gateway")
        routes = task.payload.get("routes", [])
        cors = task.payload.get("cors", {"enabled": True, "origins": ["*"]})

        gateway = {
            "name": name,
            "routes": routes,
            "cors": cors,
            "throttling": task.payload.get("throttling", {"rate": 1000, "burst": 500}),
            "created_at": time.time(),
        }
        return {"success": True, "gateway": name, "config": gateway}

    def _monitor(self) -> Dict[str, Any]:
        total_invocations = sum(f.get("invocation_count", 0) for f in self._functions.values())
        return {
            "success": True,
            "metrics": {
                "functions_count": len(self._functions),
                "triggers_count": len(self._triggers),
                "total_invocations": total_invocations,
                "avg_duration_ms": sum(f.get("avg_duration_ms", 0) for f in self._functions.values()) / max(1, len(self._functions)),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "serverless",
            "metrics": self._monitor()["metrics"],
        }
