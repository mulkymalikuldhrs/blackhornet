"""Ecosystem v2 API routes — Radar, Mesh, and Nest endpoints.

Endpoints:
  GET  /api/v1/radar/identity       — this colony's identity
  GET  /api/v1/radar/peers          — discovered colony peers
  GET  /api/v1/radar/peers/capability/{cap} — peers with capability
  GET  /api/v1/radar/stats          — radar statistics

  POST /api/v1/mesh/message         — receive a mesh message
  GET  /api/v1/mesh/stats           — mesh bus statistics

  GET  /api/v1/nest/health          — nest health report
  POST /api/v1/nest/restart/{component} — restart a component
  GET  /api/v1/nest/stats           — nest statistics
"""

from __future__ import annotations

from typing import Any, Optional

from src.config.logging_config import get_logger
from src.colony_types._pydantic_compat import model_dump

logger = get_logger(__name__)


class EcosystemV2Routes:
    """Route handlers for colony ecosystem v2."""

    def __init__(
        self,
        radar: Any = None,
        mesh_bus: Any = None,
        nest: Any = None,
    ) -> None:
        self._radar = radar
        self._mesh_bus = mesh_bus
        self._nest = nest

    async def get_radar_identity(self) -> dict[str, Any]:
        if self._radar:
            identity = self._radar._config.identity
            return model_dump(identity)
        return {"error": "radar not available", "code": "RADAR_UNAVAILABLE"}

    async def get_radar_peers(self) -> dict[str, Any]:
        if self._radar:
            peers = self._radar.get_peers()
            return {
                "peers": [model_dump(p) for p in peers],
                "total": len(peers),
            }
        return {"peers": [], "total": 0}

    async def get_radar_peers_by_capability(self, capability: str) -> dict[str, Any]:
        if self._radar:
            peers = await self._radar.get_peers_by_capability(capability)
            return {
                "capability": capability,
                "peers": [model_dump(p) for p in peers],
                "total": len(peers),
            }
        return {"capability": capability, "peers": [], "total": 0}

    async def get_radar_stats(self) -> dict[str, Any]:
        if self._radar:
            return self._radar.get_stats()
        return {"error": "radar not available"}

    async def receive_mesh_message(self, body: Optional[dict] = None) -> dict[str, Any]:
        if self._mesh_bus and body:
            return await self._mesh_bus.receive_message(body)
        return {"status": "error", "error": "mesh bus not available"}

    async def get_mesh_stats(self) -> dict[str, Any]:
        if self._mesh_bus:
            return self._mesh_bus.get_stats()
        return {"error": "mesh bus not available"}

    async def get_nest_health(self) -> dict[str, Any]:
        if self._nest:
            report = await self._nest.health_report()
            return model_dump(report)
        return {"error": "nest not available"}

    async def restart_nest_component(self, component: str) -> dict[str, Any]:
        if self._nest:
            success = await self._nest.restart_component(component)
            return {"component": component, "restart_initiated": success}
        return {"error": "nest not available"}

    async def get_nest_stats(self) -> dict[str, Any]:
        if self._nest:
            return self._nest.get_stats()
        return {"error": "nest not available"}
