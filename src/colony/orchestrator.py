"""EcosystemOrchestrator — autonomous control center for Blackhornet colonies.

Central hub that wires together:
  - ColonyRadar (peer discovery)
  - MeshBus (cross-colony messaging)
  - SelfNest (self-hosting)
  - AgentRegistry (agent management)
  - Graphify (knowledge graph)
  - Docs auto-sync (AGENTS.md, SOUL.md, ARCHITECTURE.md)
  - Unified status dashboard

Runs a periodic synchronization loop that updates all subsystems,
generates status reports, and auto-maintains documentation.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from src.config.logging_config import get_logger
from src.colony_types._pydantic_compat import model_dump
from src.colony.graph_sync import GraphifySyncBridge
from src.colony.session_export import SessionExporter

logger = get_logger(__name__)

SYNC_INTERVAL = 60
DOC_SYNC_INTERVAL = 300


@dataclass
class OrchestratorConfig:
    colony_id: str
    colony_name: str = "blackhornet"
    version: str = "5.0.0"
    sync_interval: int = SYNC_INTERVAL
    doc_sync_interval: int = DOC_SYNC_INTERVAL
    data_dir: str = "data"
    docs_dir: str = "."
    agent_log_dir: str = "data/agent-logs"
    export_dir: str = "data/session-export"
    auto_sync_docs: bool = True
    auto_export_sessions: bool = True
    verbose: bool = False


class EcosystemOrchestrator:
    """Autonomous control center — wires all subsystems together.

    Usage:
        orch = EcosystemOrchestrator(config)
        orch.wire(radar=radar, mesh=mesh_bus, nest=nest)
        await orch.start()
        status = await orch.full_status()
    """

    def __init__(self, config: OrchestratorConfig, health_monitor: Optional[ColonyHealthMonitor] = None) -> None:
        self._config = config
        self._running = False
        self._start_time: Optional[float] = None

        self._radar = None
        self._mesh_bus = None
        self._nest = None
        self._agent_registry = None
        self._colony_manager = None
        self._health_monitor = health_monitor
        self._graph_store = None
        self._session_recorder = None
        self._memory_system = None
        self._lifecycle_recorder = None
        self._session_exporter: Optional[SessionExporter] = None
        self._mcp_server: Any = None

        self._graph_sync: Optional[GraphifySyncBridge] = None

        self._tasks: list[asyncio.Task] = []
        self._sync_count = 0
        self._last_doc_sync: Optional[float] = None
        self._status_cache: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    def wire(
        self,
        radar: Any = None,
        mesh: Any = None,
        nest: Any = None,
        agent_registry: Any = None,
        colony_manager: Any = None,
        graph_store: Any = None,
        session_recorder: Any = None,
        memory_system: Any = None,
        lifecycle_recorder: Any = None,
        session_exporter: Any = None,
        mcp_server: Any = None,
    ) -> None:
        """Wire all ecosystem components together."""
        self._radar = radar
        self._mesh_bus = mesh
        self._nest = nest
        self._agent_registry = agent_registry
        self._colony_manager = colony_manager
        self._graph_store = graph_store
        self._session_recorder = session_recorder
        self._memory_system = memory_system
        self._lifecycle_recorder = lifecycle_recorder
        self._session_exporter = session_exporter
        self._mcp_server = mcp_server

        if graph_store:
            self._graph_sync = GraphifySyncBridge(graph_store)

        # Register colony tools on MCP server
        if self._mcp_server:
            self._register_mcp_tools()

        # Wire health monitor to subsystems during initialization
        if self._health_monitor:
            if self._radar:
                # Create a new Radar with health monitor
                radar_config = self._radar._config
                self._radar = ColonyRadar(radar_config, self._health_monitor)
            if self._mesh_bus:
                # Create a new MeshBus with health monitor
                mesh_config = self._mesh_bus._config
                self._mesh_bus = MeshBus(self._mesh_bus._local_bus, self._mesh_bus._identity, self._mesh_bus._http_port, self._health_monitor)
            if self._nest:
                # Create a new SelfNest with health monitor
                nest_config = self._nest._config
                self._nest = SelfNest(nest_config, self._health_monitor)

        logger.info(
            "orchestrator_wired radar=%s mesh=%s nest=%s registry=%s colony=%s graph=%s session=%s memory=%s lifecycle=%s mcp=%s",
            radar is not None,
            mesh is not None,
            nest is not None,
            agent_registry is not None,
            colony_manager is not None,
            graph_store is not None,
            session_recorder is not None,
            memory_system is not None,
            lifecycle_recorder is not None,
        )

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._start_time = time.time()

        self._tasks.append(asyncio.create_task(self._sync_loop()))
        if self._config.auto_sync_docs:
            self._tasks.append(asyncio.create_task(self._doc_sync_loop()))
        if self._config.auto_export_sessions:
            self._tasks.append(asyncio.create_task(self._export_loop()))

        logger.info("orchestrator_started colony=%s", self._config.colony_name)

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        if self._session_exporter and self._lifecycle_recorder:
            try:
                status = await self.full_status()
                events = await self._lifecycle_recorder.get_history(limit=500)
                await self._session_exporter.export_final(
                    status=status,
                    lifecycle_events=events,
                    colony_id=self._config.colony_id,
                )
            except Exception as e:
                logger.debug("final_export_error err=%s", e)

        logger.info("orchestrator_stopped colony=%s", self._config.colony_name)

    async def full_status(self) -> dict[str, Any]:
        """Return a comprehensive status of the entire ecosystem.

        Aggregates radar peers, mesh stats, nest health, agent registry,
        colony manager, graph store, and session recorder into one report.
        """
        status: dict[str, Any] = {
            "orchestrator": {
                "colony_id": self._config.colony_id,
                "colony_name": self._config.colony_name,
                "version": self._config.version,
                "running": self._running,
                "uptime": time.time() - self._start_time if self._start_time else 0,
                "sync_count": self._sync_count,
            },
            "radar": {},
            "mesh": {},
            "nest": {},
            "agents": {},
            "colonies": {},
            "graph": {},
            "session": {},
            "memory": {},
            "lifecycle": {},
        }

        if self._radar:
            status["radar"] = {
                "peers": [model_dump(p) for p in self._radar.get_peers()],
                "peer_count": self._radar.peer_count,
                "stats": self._radar.get_stats(),
            }

        if self._mesh_bus:
            status["mesh"] = self._mesh_bus.get_stats()

        if self._nest:
            report = await self._nest.health_report()
            status["nest"] = model_dump(report)
            if self._health_monitor:
                health_stats = self._health_monitor.get_stats()
                status["nest"]["health"] = {
                    "detector": health_stats["detector"],
                    "orchestrator": health_stats["orchestrator"],
                }

        if self._agent_registry:
            try:
                agents = self._agent_registry.list_agents() if hasattr(self._agent_registry, "list_agents") else []
                status["agents"] = {"total": len(agents), "agents": agents[:50]}
            except Exception as e:
                status["agents"] = {"error": str(e)}

        if self._colony_manager:
            try:
                colonies = self._colony_manager.list_colonies() if hasattr(self._colony_manager, "list_colonies") else []
                status["colonies"] = {"total": len(colonies), "colonies": colonies[:20]}
            except Exception as e:
                status["colonies"] = {"error": str(e)}

        if self._graph_store:
            try:
                stats = self._graph_store.get_stats() if hasattr(self._graph_store, "get_stats") else {}
                status["graph"] = stats
            except Exception as e:
                status["graph"] = {"error": str(e)}

        if self._session_recorder:
            try:
                sr_stats = self._session_recorder.get_stats() if hasattr(self._session_recorder, "get_stats") else {}
                status["session"] = sr_stats
            except Exception as e:
                status["session"] = {"error": str(e)}

        if self._memory_system:
            try:
                mem_stats = self._memory_system.get_stats() if hasattr(self._memory_system, "get_stats") else {}
                status["memory"] = mem_stats
            except Exception as e:
                status["memory"] = {"error": str(e)}

        if self._lifecycle_recorder:
            try:
                lc_summary = self._lifecycle_recorder.get_summary() if hasattr(self._lifecycle_recorder, "get_summary") else {}
                status["lifecycle"] = lc_summary
            except Exception as e:
                status["lifecycle"] = {"error": str(e)}

        async with self._lock:
            self._status_cache = status

        return status

    async def _sync_loop(self) -> None:
        while self._running:
            try:
                status = await self.full_status()
                self._sync_count += 1

                if self._mesh_bus and self._radar:
                    self._mesh_bus.update_peers(self._radar.get_peers())

                await self._sync_agent_graph()

                logger.debug(
                    "orchestrator_sync #%d peers=%d agents=%d",
                    self._sync_count,
                    status.get("radar", {}).get("peer_count", 0),
                    status.get("agents", {}).get("total", 0),
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("orchestrator_sync_error err=%s", e)

            await asyncio.sleep(self._config.sync_interval)

    async def _sync_agent_graph(self) -> None:
        """Sync agent states to Graphify knowledge graph via GraphifySyncBridge."""
        if not self._graph_sync:
            return
        try:
            agents: list[dict[str, Any]] = []

            if self._agent_registry:
                if hasattr(self._agent_registry, "list_agent_info"):
                    raw = self._agent_registry.list_agent_info()
                    for info in raw:
                        d = model_dump(info) if hasattr(info, "model_dump") else (
                            info if isinstance(info, dict) else {"agent_id": str(info)}
                        )
                        agents.append(d)
                elif hasattr(self._agent_registry, "list_agents"):
                    raw = self._agent_registry.list_agents()
                    for agent in raw[:50]:
                        if isinstance(agent, dict):
                            agents.append(agent)
                        else:
                            agents.append({
                                "agent_id": getattr(agent, "agent_id", str(agent)),
                                "name": getattr(agent, "name", None),
                                "type": str(getattr(agent, "agent_type", "agent")),
                                "status": str(getattr(agent, "state", getattr(agent, "status", "unknown"))),
                                "health": getattr(agent, "health_score", 0),
                            })

            self._graph_sync.sync_agents_batch(agents)

            if self._colony_manager and hasattr(self._colony_manager, "list_colonies"):
                try:
                    colonies_raw = self._colony_manager.list_colonies()
                    colony_dicts = []
                    for c in colonies_raw[:20]:
                        if isinstance(c, dict):
                            colony_dicts.append(c)
                        else:
                            colony_dicts.append({
                                "colony_id": getattr(c, "colony_id", str(c)),
                                "name": getattr(c, "name", None),
                                "health": getattr(c, "health", 0),
                                "agent_count": getattr(c, "agent_count", 0),
                                "status": getattr(c, "status", "active"),
                            })
                    self._graph_sync.sync_colonies_batch(colony_dicts)
                except Exception as e:
                    logger.debug("colony_sync_error err=%s", e)

            if self._lifecycle_recorder:
                try:
                    recent = await self._lifecycle_recorder.get_recent_activity(seconds=3600)
                    self._graph_sync.sync_lifecycle_batch(recent)
                except Exception as e:
                    logger.debug("lifecycle_sync_error err=%s", e)

        except Exception as e:
            logger.debug("agent_graph_sync_error err=%s", e)

    async def _doc_sync_loop(self) -> None:
        while self._running:
            try:
                await self._sync_documentation()
                self._last_doc_sync = time.time()
            except Exception as e:
                logger.warning("doc_sync_error err=%s", e)
            await asyncio.sleep(self._config.doc_sync_interval)

    async def _sync_documentation(self) -> None:
        """Update AGENTS.md, SOUL.md, and status docs with current state.

        Generates status sections that reflect live colony state rather than
        stale hardcoded values.
        """
        status = await self.full_status()

        agent_count = status.get("agents", {}).get("total", 0)
        peer_count = status.get("radar", {}).get("peer_count", 0)
        colony_count = status.get("colonies", {}).get("total", 0)
        uptime = status.get("orchestrator", {}).get("uptime", 0)

        docs = {
            "AGENTS.md": self._generate_agents_section(agent_count, peer_count, colony_count, uptime),
            "SOUL.md": self._generate_soul_section(status),
        }

        base_dir = self._config.docs_dir
        for filename, content in docs.items():
            filepath = os.path.join(base_dir, filename)
            try:
                if os.path.exists(filepath):
                    await asyncio.to_thread(self._append_to_file, filepath, content)
            except Exception as e:
                logger.warning("doc_write_error file=%s err=%s", filename, e)

        logger.info(
            "doc_sync_complete agents=%d peers=%d colonies=%d",
            agent_count,
            peer_count,
            colony_count,
        )

    def _generate_agents_section(
        self, agent_count: int, peer_count: int, colony_count: int, uptime: float
    ) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        return (
            f"\n## Auto-Generated Status ({now})\n"
            f"- **Agents**: {agent_count}\n"
            f"- **Peers (Radar)**: {peer_count}\n"
            f"- **Colonies**: {colony_count}\n"
            f"- **Uptime**: {uptime:.1f}s\n"
            f"- **Last Sync**: {now}\n"
        )

    def _generate_soul_section(self, status: dict[str, Any]) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        lines = ["", f"## Auto-Status ({now})", ""]
        orch = status.get("orchestrator", {})
        lines.append(f"Colony: {orch.get('colony_name', '?')} v{orch.get('version', '?')}")
        lines.append(f"Status: {'RUNNING' if orch.get('running') else 'STOPPED'}")
        if orch.get("uptime"):
            lines.append(f"Uptime: {orch['uptime']:.0f}s")
        lines.append("")

        radar = status.get("radar", {})
        if radar.get("peer_count", 0) > 0:
            lines.append(f"Peers discovered: {radar['peer_count']}")

        nest = status.get("nest", {})
        if nest:
            comps = nest.get("components", {})
            healthy = sum(1 for s in comps.values() if s == "running")
            total = len(comps)
            lines.append(f"Nest components: {healthy}/{total} healthy")

        lines.append("")
        return "\n".join(lines)

    def _append_to_file(self, filepath: str, content: str) -> None:
        with open(filepath, "a") as f:
            f.write(content)

    async def _export_loop(self) -> None:
        """Always-on session and memory export via SessionExporter."""
        if not self._session_exporter:
            logger.debug("export_loop_skipped no_exporter")
            return

        if self._start_time:
            self._session_exporter.set_session_start(self._start_time)

        while self._running:
            try:
                status = await self.full_status()
                lc = self._lifecycle_recorder
                events = await lc.get_history(limit=500) if lc else []

                await self._session_exporter.export_full(
                    status=status,
                    lifecycle_events=events,
                    graph_store=self._graph_store,
                    memory_system=self._memory_system,
                    colony_id=self._config.colony_id,
                )
            except Exception as e:
                logger.warning("export_error err=%s", e)
            await asyncio.sleep(self._config.sync_interval * 2)

    def get_status_cache(self) -> dict[str, Any]:
        return dict(self._status_cache)

    @property
    def uptime(self) -> float:
        return time.time() - self._start_time if self._start_time else 0.0

    def get_stats(self) -> dict[str, Any]:
        stats = {
            "running": self._running,
            "colony": self._config.colony_name,
            "uptime": self.uptime,
            "sync_count": self._sync_count,
            "last_doc_sync": self._last_doc_sync,
            "components": {
                "radar": self._radar is not None,
                "mesh": self._mesh_bus is not None,
                "nest": self._nest is not None,
                "registry": self._agent_registry is not None,
                "colony_mgr": self._colony_manager is not None,
                "graph": self._graph_store is not None,
                "session": self._session_recorder is not None,
                "memory": self._memory_system is not None,
                "lifecycle": self._lifecycle_recorder is not None,
            },
            "graph_sync": self._graph_sync.sync_report if self._graph_sync else {},
        }
        if self._health_monitor:
            health_stats = self._health_monitor.get_stats()
            stats["health"] = {
                "detector": health_stats["detector"],
                "circuit_breaker": health_stats["circuit_breaker"],
                "orchestrator": health_stats["orchestrator"],
            }
        return stats

    def _register_mcp_tools(self) -> None:
        """Register colony tools on the MCP server."""
        if not self._mcp_server:
            return

        # Register colony.status tool
        async def colony_status(**kwargs: Any) -> Any:
            return await self.full_status()

        self._mcp_server.register_tool(
            name="colony.status",
            handler=colony_status,
            description="Get full colony ecosystem status",
            required_level=0,
        )

        # Register colony.sync tool
        async def colony_sync(**kwargs: Any) -> Any:
            await self._sync_agent_graph()
            return {"status": "synced"}

        self._mcp_server.register_tool(
            name="colony.sync",
            handler=colony_sync,
            description="Trigger manual sync of colony state",
            required_level=1,
        )

        # Register colony.agents tool
        async def colony_agents(**kwargs: Any) -> Any:
            if self._agent_registry and hasattr(self._agent_registry, "list_agents"):
                agents = self._agent_registry.list_agents()
                return {"agents": agents[:50], "total": len(agents)}
            return {"agents": [], "total": 0}

        self._mcp_server.register_tool(
            name="colony.agents",
            handler=colony_agents,
            description="List colony agents",
            required_level=0,
        )

        # Register colony.radar tool
        async def colony_radar(**kwargs: Any) -> Any:
            if self._radar:
                peers = self._radar.get_peers()
                from src.colony_types._pydantic_compat import model_dump
                return {"peers": [model_dump(p) for p in peers], "count": len(peers)}
            return {"peers": [], "count": 0}

        self._mcp_server.register_tool(
            name="colony.radar",
            handler=colony_radar,
            description="Get radar peer list",
            required_level=0,
        )

        # Register colony.mesh tool
        async def colony_mesh(**kwargs: Any) -> Any:
            if self._mesh_bus:
                return self._mesh_bus.get_stats()
            return {}

        self._mcp_server.register_tool(
            name="colony.mesh",
            handler=colony_mesh,
            description="Get mesh bus statistics",
            required_level=0,
        )

        # Register colony.nest tool
        async def colony_nest(**kwargs: Any) -> Any:
            if self._nest:
                report = await self._nest.health_report()
                from src.colony_types._pydantic_compat import model_dump
                return model_dump(report)
            return {}

        self._mcp_server.register_tool(
            name="colony.nest",
            handler=colony_nest,
            description="Get nest health report",
            required_level=0,
        )

        logger.info("mcp_tools_registered count=6")
