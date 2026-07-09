"""Load balancer specialist — Load balancing and traffic distribution."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class LoadBalancerSpecialist(BaseAgent):
    """Specialist agent for load balancing and traffic distribution.

    Handles backend pool management, health checking, algorithm configuration,
    session persistence, and traffic analytics.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.EXECUTOR, autonomy_level=3)
        super().__init__(spec=spec, **kwargs)
        self._pools: Dict[str, Dict[str, Any]] = {}
        self._backends: Dict[str, Dict[str, Any]] = {}
        self._traffic_log: List[Dict[str, Any]] = []

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "create_pool":
            return await self._create_pool(task)
        elif action == "add_backend":
            return await self._add_backend(task)
        elif action == "configure_algorithm":
            return await self._configure_algorithm(task)
        elif action == "health_check":
            return await self._health_check(task)
        elif action == "configure_sticky_session":
            return await self._configure_sticky_session(task)
        elif action == "get_traffic_stats":
            return await self._get_traffic_stats(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "traffic_request":
            pool = message.get("payload", {}).get("pool", "default")
            self._traffic_log.append({"pool": pool, "timestamp": time.time()})
            return {"routed": True}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "pool_management", "backend_management", "algorithm_configuration",
            "health_checking", "sticky_sessions", "traffic_analytics",
            "failover_management", "ssl_termination",
        ]

    async def _create_pool(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_pool")
        algorithm = task.payload.get("algorithm", "round_robin")
        health_check_path = task.payload.get("health_check_path", "/health")

        pool = {
            "name": name,
            "algorithm": algorithm,
            "health_check_path": health_check_path,
            "backends": [],
            "created_at": time.time(),
            "total_requests": 0,
        }
        self._pools[name] = pool
        return {"success": True, "pool": name, "algorithm": algorithm}

    async def _add_backend(self, task: Task) -> Dict[str, Any]:
        pool_name = task.payload.get("pool", "default_pool")
        address = task.payload.get("address", "localhost:8080")
        weight = task.payload.get("weight", 1)

        if pool_name not in self._pools:
            return {"success": False, "error": f"Pool {pool_name} not found"}

        backend_id = f"backend-{address.replace(':', '-')}"
        backend = {
            "id": backend_id,
            "pool": pool_name,
            "address": address,
            "weight": weight,
            "status": "healthy",
            "connections": 0,
            "total_requests": 0,
        }
        self._backends[backend_id] = backend
        self._pools[pool_name]["backends"].append(backend_id)
        return {"success": True, "backend_id": backend_id, "address": address}

    async def _configure_algorithm(self, task: Task) -> Dict[str, Any]:
        pool_name = task.payload.get("pool", "default_pool")
        algorithm = task.payload.get("algorithm", "round_robin")

        if pool_name in self._pools:
            self._pools[pool_name]["algorithm"] = algorithm

        return {"success": True, "pool": pool_name, "algorithm": algorithm}

    async def _health_check(self, task: Task) -> Dict[str, Any]:
        pool_name = task.payload.get("pool", "all")
        results: Dict[str, Any] = {}

        pools_to_check = [pool_name] if pool_name != "all" else list(self._pools.keys())
        for pname in pools_to_check:
            pool = self._pools.get(pname, {})
            backends = pool.get("backends", [])
            healthy = sum(1 for bid in backends if self._backends.get(bid, {}).get("status") == "healthy")
            results[pname] = {"total": len(backends), "healthy": healthy, "unhealthy": len(backends) - healthy}

        return {"success": True, "health_results": results}

    async def _configure_sticky_session(self, task: Task) -> Dict[str, Any]:
        pool_name = task.payload.get("pool", "default_pool")
        method = task.payload.get("method", "cookie")
        cookie_name = task.payload.get("cookie_name", "LBID")
        ttl_seconds = task.payload.get("ttl_seconds", 3600)

        config = {"method": method, "cookie_name": cookie_name, "ttl_seconds": ttl_seconds}
        if pool_name in self._pools:
            self._pools[pool_name]["sticky_session"] = config
        return {"success": True, "pool": pool_name, "sticky_session": config}

    async def _get_traffic_stats(self, task: Task) -> Dict[str, Any]:
        time_range = task.payload.get("time_range", 3600)
        start_time = time.time() - time_range
        recent = [t for t in self._traffic_log if t.get("timestamp", 0) >= start_time]

        by_pool: Dict[str, int] = {}
        for t in recent:
            pool = t.get("pool", "unknown")
            by_pool[pool] = by_pool.get(pool, 0) + 1

        return {"success": True, "total_requests": len(recent), "by_pool": by_pool}

    def _monitor(self) -> Dict[str, Any]:
        total_backends = len(self._backends)
        healthy_backends = sum(1 for b in self._backends.values() if b.get("status") == "healthy")
        return {
            "success": True,
            "metrics": {
                "pools_count": len(self._pools),
                "total_backends": total_backends,
                "healthy_backends": healthy_backends,
                "total_requests": len(self._traffic_log),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "load_balancer",
            "metrics": self._monitor()["metrics"],
        }
