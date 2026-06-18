"""QueenAgent — unified command center for the colony ecosystem.

The Queen is the highest-level intelligence in the colony:
  - Wraps EcosystemOrchestrator for unified control
  - Accepts commands from CLI, TUI, API, or voice
  - Routes tasks to the best available agent (round-robin, capability-match)
  - Speaks through VoiceService (TTS) and broadcasts via MeshBus
  - Records every command in LifecycleRecorder
  - Provides proactive idle monitoring

Usage:
    queen = QueenAgent(orchestrator)
    queen.wire(voice=voice_service, mesh=mesh_bus, lifecycle=lifecycle_recorder)
    await queen.start()
    result = await queen.command("status")
    await queen.say("System is healthy")
    result = await queen.command("broadcast hello all colonies")
    await queen.stop()
"""

from __future__ import annotations

import asyncio
import shlex
import time
from datetime import datetime, timezone
from typing import Any, Optional

from src.config.logging_config import get_logger

logger = get_logger(__name__)


class QueenAgent:
    """Queen-class superintelligence — unified command interface.

    Accepts natural-language-like commands and routes them to the
    appropriate subsystem (orchestrator, radar, mesh, nest, graph).
    Can speak via VoiceService and broadcast via MeshBus.
    """

    def __init__(
        self,
        orchestrator: Any = None,
        colony_name: str = "queen",
        version: str = "5.0.0",
        idle_timeout: int = 300,
        proactive: bool = True,
        mcp_client: Any = None,
    ) -> None:
        self._orchestrator = orchestrator
        self._colony_name = colony_name
        self._version = version
        self._idle_timeout = idle_timeout
        self._proactive = proactive

        self._voice: Any = None
        self._mesh_bus: Any = None
        self._lifecycle_recorder: Any = None
        self._consciousness: Any = None
        self._intelligence: Any = None
        self._mcp_client = mcp_client
        self._trading: Any = None

        self._running = False
        self._start_time: Optional[float] = None
        self._last_activity: Optional[float] = None
        self._command_count = 0
        self._say_count = 0
        self._tasks: list[asyncio.Task] = []
        self._agent_queue: list[str] = []
        self._rr_index: dict[str, int] = {}

    def wire(
        self,
        voice: Any = None,
        mesh_bus: Any = None,
        lifecycle_recorder: Any = None,
        consciousness: Any = None,
        intelligence: Any = None,
        mcp_client: Any = None,
        trading: Any = None,
    ) -> None:
        """Wire voice, mesh, lifecycle, consciousness, intelligence, MCP, and trading subsystems."""
        self._voice = voice
        self._mesh_bus = mesh_bus
        self._lifecycle_recorder = lifecycle_recorder
        self._consciousness = consciousness
        self._intelligence = intelligence
        if mcp_client is not None:
            self._mcp_client = mcp_client
        if trading is not None:
            self._trading = trading
        logger.info(
            "queen_wired voice=%s mesh=%s lifecycle=%s consciousness=%s intelligence=%s mcp=%s trading=%s",
            voice is not None,
            mesh_bus is not None,
            lifecycle_recorder is not None,
            consciousness is not None,
            intelligence is not None,
            self._mcp_client is not None,
            self._trading is not None,
        )

    @property
    def uptime(self) -> float:
        return time.time() - self._start_time if self._start_time else 0.0

    @property
    def is_idle(self) -> bool:
        if not self._last_activity:
            return True
        return (time.time() - self._last_activity) > self._idle_timeout

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._start_time = time.time()
        self._last_activity = time.time()

        if self._proactive:
            self._tasks.append(asyncio.create_task(self._proactive_loop()))

        logger.info("queen_started colony=%s", self._colony_name)

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("queen_stopped colony=%s", self._colony_name)

    async def say(self, text: str, broadcast: bool = True) -> None:
        """Speak text through voice service, log, and optionally broadcast.

        If voice service is wired, speaks aloud via TTS.
        If lifecycle recorder is wired, records as a milestone event.
        If mesh bus is wired and broadcast=True, sends to all peers.
        """
        self._say_count += 1
        logger.info("queen_say: %s", text)

        if self._voice and hasattr(self._voice, "say"):
            try:
                if asyncio.iscoroutinefunction(self._voice.say):
                    await self._voice.say(text)
                else:
                    self._voice.say(text)
            except Exception as e:
                logger.debug("queen_voice_error err=%s", e)

        if self._lifecycle_recorder and hasattr(self._lifecycle_recorder, "record_milestone"):
            try:
                await self._lifecycle_recorder.record_milestone(
                    name="queen_say",
                    description=text[:200],
                )
            except Exception as e:
                logger.debug("queen_lifecycle_error err=%s", e)

        if broadcast and self._mesh_bus and hasattr(self._mesh_bus, "broadcast"):
            try:
                if asyncio.iscoroutinefunction(self._mesh_bus.broadcast):
                    await self._mesh_bus.broadcast(
                        sender=self._colony_name,
                        channel="queen",
                        content={"message": text, "timestamp": time.time()},
                    )
            except Exception as e:
                logger.debug("queen_mesh_broadcast_error err=%s", e)

    async def command(self, cmd: str, **kwargs) -> dict[str, Any]:
        """Execute a command against the colony.

        Command syntax:
          status                    -> get full ecosystem status
          status <subsystem>        -> get subsystem status (radar, mesh, nest, agents)
          agents                    -> list all agents
          agents <agent_id>         -> get specific agent info
          colonies                  -> list all colonies
          deploy agent=<type> ...   -> deploy new agents
          graph                     -> get knowledge graph state
          export                    -> trigger session export
          sync                      -> force sync cycle
          broadcast <message>       -> send message to all mesh peers
          voice on|off|lang=<code>  -> configure voice settings
          help                      -> list available commands
        """
        self._command_count += 1
        self._last_activity = time.time()

        cmd = cmd.strip().lower()
        parts = shlex.split(cmd)
        if not parts:
            return self._help()

        base = parts[0]

        if base in ("help", "?"):
            return self._help()
        elif base == "status":
            return await self._cmd_status(parts[1:] if len(parts) > 1 else None)
        elif base == "agents":
            return await self._cmd_agents(parts[1] if len(parts) > 1 else None)
        elif base == "colonies":
            return await self._cmd_colonies()
        elif base == "deploy":
            return await self._cmd_deploy(parts[1:])
        elif base == "graph":
            return await self._cmd_graph()
        elif base == "export":
            return await self._cmd_export()
        elif base == "sync":
            return await self._cmd_sync()
        elif base == "broadcast":
            return await self._cmd_broadcast(parts[1:])
        elif base == "voice":
            return await self._cmd_voice(parts[1:])
        elif base in ("consciousness", "conscious", "cs"):
            return await self._cmd_consciousness(parts[1:])
        elif base == "ask":
            return await self._cmd_ask(parts[1:])
        elif base == "think":
            return await self._cmd_think(parts[1:])
        elif base == "stats":
            return self._cmd_stats()
        elif base == "mcp":
            return await self._cmd_mcp(parts[1:])
        elif base in ("trade", "market"):
            return await self._cmd_trade(parts[1:])
        else:
            return {"success": False, "error": f"Unknown command: {base}", "command": cmd}

    async def _cmd_status(self, subsystem: Optional[list[str]] = None) -> dict[str, Any]:
        if not self._orchestrator:
            return {"success": False, "error": "No orchestrator wired"}

        full = await self._orchestrator.full_status()

        if subsystem:
            key = subsystem[0]
            if key in full:
                return {"success": True, "subsystem": key, "data": full[key]}
            return {"success": False, "error": f"Unknown subsystem: {key}", "available": list(full.keys())}

        return {"success": True, "data": full}

    async def _cmd_agents(self, agent_id: Optional[str] = None) -> dict[str, Any]:
        if not self._orchestrator:
            return {"success": False, "error": "No orchestrator wired"}

        if self._orchestrator._graph_sync:
            report = self._orchestrator._graph_sync.sync_report
        else:
            report = {}

        return {
            "success": True,
            "agent_id": agent_id,
            "sync_report": report,
        }

    async def _cmd_colonies(self) -> dict[str, Any]:
        if not self._orchestrator:
            return {"success": False, "error": "No orchestrator wired"}
        status = await self._orchestrator.full_status()
        return {"success": True, "data": status.get("colonies", {})}

    async def _cmd_deploy(self, args: list[str]) -> dict[str, Any]:
        params: dict[str, str] = {}
        for arg in args:
            if "=" in arg:
                k, v = arg.split("=", 1)
                params[k] = v

        agent_type = params.get("agent", params.get("type", "coder"))
        count = int(params.get("count", "1"))

        if not self._orchestrator or not self._orchestrator._agent_registry:
            return {"success": False, "error": "No agent registry available"}

        deployed: list[str] = []
        errors: list[str] = []

        for _ in range(count):
            try:
                registry = self._orchestrator._agent_registry
                if hasattr(registry, "create_agent"):
                    agent = registry.create_agent(agent_type)
                    deployed.append(getattr(agent, "agent_id", str(agent)))
                else:
                    errors.append(f"Cannot create agent of type {agent_type}")
            except Exception as e:
                errors.append(str(e))

        return {
            "success": len(errors) == 0,
            "deployed": deployed,
            "errors": errors if errors else None,
        }

    async def _cmd_graph(self) -> dict[str, Any]:
        if not self._orchestrator or not self._orchestrator._graph_store:
            return {"success": False, "error": "No graph store available"}

        try:
            gs = self._orchestrator._graph_store
            if hasattr(gs, "export_json"):
                data = gs.export_json()
            elif hasattr(gs, "get_graph"):
                data = gs.get_graph()
            else:
                data = {}
            return {"success": True, "data": data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _cmd_export(self) -> dict[str, Any]:
        if not self._orchestrator:
            return {"success": False, "error": "No orchestrator wired"}
        exporter = getattr(self._orchestrator, "_session_exporter", None)
        if not exporter:
            return {"success": False, "error": "No session exporter wired"}

        status = await self._orchestrator.full_status()
        lc = getattr(self._orchestrator, "_lifecycle_recorder", None)
        events = await lc.get_history(limit=200) if lc else []
        paths = await exporter.export_full(
            status=status,
            lifecycle_events=events,
            graph_store=self._orchestrator._graph_store,
            memory_system=self._orchestrator._memory_system,
            colony_id=self._orchestrator._config.colony_id,
        )
        return {"success": True, "files": paths}

    async def _cmd_sync(self) -> dict[str, Any]:
        if not self._orchestrator:
            return {"success": False, "error": "No orchestrator wired"}
        status = await self._orchestrator.full_status()
        return {"success": True, "sync_count": self._orchestrator._sync_count}

    async def _cmd_ask(self, args: list[str]) -> dict[str, Any]:
        """Ask the intelligence system a question.

        Usage: ask <question>
        """
        if not self._intelligence:
            return {"success": False, "error": "No intelligence bridge wired"}
        if not args:
            return {"success": False, "error": "No question provided"}

        query = " ".join(args)
        try:
            ask_fn = self._intelligence.ask
            if asyncio.iscoroutinefunction(ask_fn):
                result = await ask_fn(query)
            else:
                result = ask_fn(query)
            return {
                "success": result.success,
                "answer": result.answer,
                "provider": result.provider,
                "model": result.model,
                "latency_ms": result.latency_ms,
                "cached": result.cached,
                "error": result.error,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _cmd_think(self, args: list[str]) -> dict[str, Any]:
        """Ask the intelligence to think/analyze.

        Usage: think <prompt>
        """
        if not self._intelligence:
            return {"success": False, "error": "No intelligence bridge wired"}
        if not args:
            return {"success": False, "error": "No prompt provided"}

        prompt = " ".join(args)
        try:
            think_fn = self._intelligence.think
            if asyncio.iscoroutinefunction(think_fn):
                result = await think_fn(prompt, temperature=0.3)
            else:
                result = think_fn(prompt, temperature=0.3)
            return {
                "success": result.success,
                "answer": result.answer,
                "provider": result.provider,
                "model": result.model,
                "latency_ms": result.latency_ms,
                "error": result.error,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _cmd_mcp(self, args: list[str]) -> dict[str, Any]:
        """MCP client commands.

        Subcommands:
          list              -> list available MCP tools
          call <tool> [args] -> call an MCP tool
          status            -> MCP connection status
        """
        if not self._mcp_client:
            return {"success": False, "error": "No MCP client wired"}

        sub = args[0] if args else "status"

        try:
            if sub == "list":
                tools = await self._mcp_client.list_tools()
                return {"success": True, "tools": tools, "count": len(tools)}
            elif sub == "call" and len(args) > 1:
                tool_name = args[1]
                tool_args = {}
                for arg in args[2:]:
                    if "=" in arg:
                        k, v = arg.split("=", 1)
                        tool_args[k] = v
                result = await self._mcp_client.call_tool(tool_name, tool_args)
                return {"success": True, "tool": tool_name, "result": result}
            elif sub == "status":
                status = await self._mcp_client.get_status()
                return {"success": True, "mcp_status": status}
            else:
                return {"success": False, "error": f"Unknown MCP subcommand: {sub}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _cmd_trade(self, args: list[str]) -> dict[str, Any]:
        """Trading intelligence commands.

        Subcommands:
          analyze <symbol> [timeframe]  -> market analysis
          signal <symbol> [strategy]    -> generate trading signal
          explain <trade_id>            -> explain a trade decision
          stats                         -> trading analyst stats
        """
        if not self._trading:
            return {"success": False, "error": "No trading analyst wired"}

        sub = args[0] if args else "stats"

        try:
            if sub == "analyze" and len(args) > 1:
                symbol = args[1]
                timeframe = args[2] if len(args) > 2 else "1h"
                result = await self._trading.analyze_market(symbol, timeframe)
                return result
            elif sub == "signal" and len(args) > 1:
                symbol = args[1]
                strategy = args[2] if len(args) > 2 else "momentum"
                result = await self._trading.get_signal(symbol, strategy)
                return result
            elif sub == "explain" and len(args) > 1:
                explanation = await self._trading.explain_decision(args[1])
                return {"success": True, "explanation": explanation}
            elif sub == "stats":
                return {"success": True, "stats": self._trading.get_stats()}
            else:
                return {"success": False, "error": f"Unknown trade subcommand: {sub}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _cmd_consciousness(self, args: list[str]) -> dict[str, Any]:
        """Query colony consciousness.

        Subcommands:
          summary         -> self-summary of colony state
          timeline        -> recent timeline of events
          timeline <hrs>  -> timeline for last N hours
          search <query>  -> search memories
        """
        if not self._consciousness:
            return {"success": False, "error": "No consciousness wired"}

        sub = args[0] if args else "summary"

        if sub == "summary":
            summary = await self._consciousness.self_summary()
            return {"success": True, "data": summary}
        elif sub == "timeline":
            hours = int(args[1]) if len(args) > 1 else 24
            events = await self._consciousness.timeline(hours=hours)
            return {"success": True, "hours": hours, "events": events, "count": len(events)}
        elif sub == "search" and len(args) > 1:
            query = " ".join(args[1:])
            results = await self._consciousness.search_memories(query)
            return {"success": True, "query": query, "results": results, "count": len(results)}
        elif sub == "stats":
            return {"success": True, "data": self._consciousness.get_stats()}
        else:
            return {"success": False, "error": f"Unknown consciousness subcmd: {sub}"}

    def _cmd_stats(self) -> dict[str, Any]:
        return {
            "success": True,
            "colony": self._colony_name,
            "version": self._version,
            "running": self._running,
            "uptime": self.uptime,
            "commands_processed": self._command_count,
            "say_count": self._say_count,
            "idle": self.is_idle,
            "orchestrator_wired": self._orchestrator is not None,
            "voice_wired": self._voice is not None,
            "mesh_wired": self._mesh_bus is not None,
            "lifecycle_wired": self._lifecycle_recorder is not None,
        }

    async def _cmd_broadcast(self, args: list[str]) -> dict[str, Any]:
        """Broadcast a message to all mesh peers."""
        if not self._mesh_bus:
            return {"success": False, "error": "No mesh bus wired"}
        if not args:
            return {"success": False, "error": "No message to broadcast"}
        message = " ".join(args)
        try:
            if hasattr(self._mesh_bus, "broadcast"):
                if asyncio.iscoroutinefunction(self._mesh_bus.broadcast):
                    await self._mesh_bus.broadcast(
                        sender=self._colony_name,
                        channel="queen",
                        content={"message": message, "timestamp": time.time()},
                    )
                else:
                    self._mesh_bus.broadcast(
                        sender=self._colony_name,
                        channel="queen",
                        content={"message": message, "timestamp": time.time()},
                    )
            elif hasattr(self._mesh_bus, "publish"):
                if asyncio.iscoroutinefunction(self._mesh_bus.publish):
                    await self._mesh_bus.publish("queen", {"message": message})
                else:
                    self._mesh_bus.publish("queen", {"message": message})
            return {"success": True, "message": message, "channel": "queen"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _cmd_voice(self, args: list[str]) -> dict[str, Any]:
        """Configure voice settings."""
        if not self._voice:
            return {"success": False, "error": "No voice service wired"}

        if not args:
            stats = self._voice.get_stats() if hasattr(self._voice, "get_stats") else {}
            return {"success": True, "data": stats}

        arg = args[0]
        if arg == "on":
            if hasattr(self._voice, "enable"):
                self._voice.enable()
            return {"success": True, "voice": "enabled"}
        elif arg == "off":
            if hasattr(self._voice, "disable"):
                self._voice.disable()
            return {"success": True, "voice": "disabled"}
        elif arg.startswith("lang="):
            lang = arg.split("=", 1)[1]
            if hasattr(self._voice, "set_language"):
                self._voice.set_language(lang)
            return {"success": True, "language": lang}
        elif arg.startswith("wake="):
            word = arg.split("=", 1)[1]
            if hasattr(self._voice, "set_wake_word"):
                self._voice.set_wake_word(word)
            return {"success": True, "wake_word": word}
        else:
            return {"success": False, "error": f"Unknown voice option: {arg}"}

    async def route_task(self, task: str, capabilities: Optional[list[str]] = None) -> Optional[str]:
        """Route a task to the best available agent (round-robin).

        Uses orchestrator's agent registry if available.
        """
        if not self._orchestrator:
            return None

        registry = getattr(self._orchestrator, "_agent_registry", None)
        if not registry:
            return None

        try:
            if capabilities and hasattr(registry, "search_by_capability"):
                candidates = registry.search_by_capability(capabilities[0])
                if candidates:
                    candidate = candidates[0]
                    return getattr(candidate, "agent_id", str(candidate))

            if hasattr(registry, "list_agents"):
                all_agents = registry.list_agents()
                if all_agents:
                    key = str(id(self._orchestrator))
                    idx = self._rr_index.get(key, 0)
                    agent = all_agents[idx % len(all_agents)]
                    self._rr_index[key] = idx + 1
                    return getattr(agent, "agent_id", str(agent))
        except Exception as e:
            logger.debug("route_task_error err=%s", e)

        return None

    def _help(self) -> dict[str, Any]:
        return {
            "success": True,
            "commands": {
                "status": "Get full ecosystem status",
                "status <subsystem>": "Get subsystem status (radar, mesh, nest, agents, graph)",
                "agents": "List all agents and sync report",
                "agents <id>": "Get specific agent info",
                "colonies": "List all colonies",
                "deploy agent=<type> count=<n>": "Deploy new agents",
                "graph": "Export knowledge graph state",
                "export": "Trigger full session export",
                "sync": "Force sync cycle",
                "broadcast <message>": "Send message to all mesh peers",
                "voice on|off": "Enable/disable voice output",
                "voice lang=<code>": "Set voice language (en, id)",
                "voice wake=<word>": "Set wake word",
                "stats": "Queen stats and health",
                "consciousness": "Query colony consciousness (summary, timeline, search)",
                "ask <question>": "Ask a question through the intelligence system",
                "think <prompt>": "Structured thinking/analysis",
                "mcp list": "List available MCP tools",
                "mcp call <tool> [args]": "Call an MCP tool",
                "mcp status": "MCP connection status",
                "trade analyze <sym> [tf]": "Analyze market for symbol",
                "trade signal <sym> [strat]": "Generate trading signal",
                "trade explain <id>": "Explain a trade decision",
                "trade stats": "Trading analyst stats",
                "help": "This help",
            },
        }

    async def _proactive_loop(self) -> None:
        """Idle monitoring — checks system health and reports issues."""
        while self._running:
            try:
                if self.is_idle and self._orchestrator:
                    status = await self._orchestrator.full_status()
                    nest = status.get("nest", {})
                    comps = nest.get("components", {})
                    unhealthy = [k for k, v in comps.items() if v != "running"]
                    if unhealthy:
                        logger.info("queen_proactive unhealthy=%s", unhealthy)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug("queen_proactive_error err=%s", e)
            await asyncio.sleep(self._idle_timeout // 2)

    def get_stats(self) -> dict[str, Any]:
        return {
            "colony": self._colony_name,
            "version": self._version,
            "running": self._running,
            "uptime": self.uptime,
            "commands_processed": self._command_count,
            "say_count": self._say_count,
            "idle": self.is_idle,
            "idle_timeout": self._idle_timeout,
            "proactive": self._proactive,
            "voice_wired": self._voice is not None,
            "mesh_wired": self._mesh_bus is not None,
            "lifecycle_wired": self._lifecycle_recorder is not None,
        }
