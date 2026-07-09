from __future__ import annotations

import asyncio
import cmd
import logging
import shutil
import sys
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

TERM_WIDTH = shutil.get_terminal_size().columns
BOX_WIDTH = min(TERM_WIDTH - 2, 78)


class TUIRenderer:
    def __init__(self, api_bridge=None, event_bus=None):
        self._api = api_bridge
        self._event_bus = event_bus
        self._running = False
        self._auto_refresh_task: Optional[threading.Thread] = None
        self._auto_refresh_interval = 15
        self._auto_refresh_stop = threading.Event()

    def set_api(self, api_bridge):
        self._api = api_bridge

    def set_event_bus(self, event_bus):
        self._event_bus = event_bus

    def box(self, title: str, lines: List[str]) -> str:
        w = BOX_WIDTH
        out: List[str] = []
        out.append("┌" + "─" * (w - 2) + "┐")
        mid = w - 4
        out.append(f"│ {title:<{mid}} │")
        out.append("├" + "─" * (w - 2) + "┤")
        for line in lines:
            visible = line[:w - 4]
            out.append(f"│ {visible:<{mid}} │")
        out.append("└" + "─" * (w - 2) + "┘")
        return "\n".join(out)

    def render_graph(self, graph_data: Optional[Dict] = None) -> str:
        if graph_data:
            nodes = graph_data.get("nodes", [])
            edges = graph_data.get("edges", [])
        else:
            nodes = []
            edges = []
        lines: List[str] = []
        lines.append(f"Nodes: {len(nodes)}  |  Edges: {len(edges)}")
        lines.append("")
        for n in nodes[:15]:
            label = str(n.get("label", "?"))[:40]
            ntype = n.get("type", "")
            nid = n.get("id", "")
            lines.append(f"  [{nid}] {label} ({ntype})")
        if len(nodes) > 15:
            lines.append(f"  ... and {len(nodes) - 15} more")
        lines.append("")
        for e in edges[:8]:
            src = e.get("source", "")
            tgt = e.get("target", "")
            rel = e.get("relation", "")
            lines.append(f"  {src} ──[{rel}]──> {tgt}")
        if len(edges) > 8:
            lines.append(f"  ... and {len(edges) - 8} more")
        return self.box("Knowledge Graph", lines)

    def render_status(self, status_data: Optional[Dict] = None) -> str:
        lines: List[str] = []
        if status_data:
            services = status_data.get("services", {})
            for name, info in services.items():
                status = info.get("status", "?")
                icon = "✅" if status == "ok" else "❌"
                lines.append(f"  {icon} {name}: {status}")
                if "stats" in info:
                    stats = info["stats"]
                    if isinstance(stats, dict):
                        for k, v in stats.items():
                            lines.append(f"      {k}: {v}")
        else:
            lines.append("  Status unavailable")
        return self.box("System Status", lines)

    def render_events(self, events: Optional[List[Dict]] = None) -> str:
        lines: List[str] = []
        if events:
            for e in events[-10:]:
                ts = time.strftime("%H:%M:%S", time.localtime(e.get("timestamp", 0)))
                lines.append(f"  [{ts}] {e.get('type', '?')} from {e.get('source', '?')}")
        else:
            lines.append("  No events")
        return self.box("Recent Events", lines)

    def render_help(self) -> str:
        help_lines = [
            "  commands:",
            "    graph    — show knowledge graph",
            "    status   — show system status",
            "    agents   — show agent status list",
            "    ecosystem— show ecosystem status",
            "    events   — show recent events",
            "    search Q — search graph nodes",
            "    refresh  — refresh all data",
            "    watch [N]— auto-refresh every N seconds (default 15)",
            "    unwatch  — stop auto-refresh",
            "    help     — this help",
            "    quit     — exit TUI",
        ]
        return self.box("BlackHornet TUI", help_lines)

    def render_agents(self, agents_data: Optional[Dict] = None) -> str:
        lines: List[str] = []
        if agents_data:
            agents = agents_data.get("agents", [])
            total = agents_data.get("total", 0)
            lines.append(f"Total: {total}  |  Showing: {len(agents)}")
            lines.append("")
            for a in agents[:20]:
                label = str(a.get("label", a.get("name", "?")))[:40]
                ntype = a.get("type", "")
                props = a.get("properties", {})
                status = props.get("status", "?") if isinstance(props, dict) else "?"
                health = props.get("health", "-") if isinstance(props, dict) else "-"
                hand = props.get("hand", "") if isinstance(props, dict) else ""
                lines.append(f"  [{ntype}] {label}")
                lines.append(f"      status={status}  health={health}  hand={hand}")
            if len(agents) > 20:
                lines.append(f"  ... and {total - 20} more")
        else:
            lines.append("  API not available")
        return self.box("Agent Status", lines)

    def render_ecosystem(self, eco_data: Optional[Dict] = None) -> str:
        lines: List[str] = []
        if eco_data:
            stats = eco_data.get("stats", {})
            cache = eco_data.get("cache", {})
            running = stats.get("running", False)
            lines.append(f"Running: {'YES' if running else 'NO'}")
            lines.append(f"Colony: {stats.get('colony', '?')}")
            lines.append(f"Uptime: {stats.get('uptime', 0):.0f}s")
            lines.append(f"Syncs:  {stats.get('sync_count', 0)}")
            lines.append("")
            comps = stats.get("components", {})
            for name, enabled in comps.items():
                icon = "✅" if enabled else "⬜"
                lines.append(f"  {icon} {name}")
            lines.append("")
            gsync = stats.get("graph_sync", {})
            if gsync:
                lines.append("Graph sync:")
                for k, v in gsync.items():
                    lines.append(f"  {k}: {v}")
        else:
            lines.append("  Ecosystem status unavailable")
        return self.box("Ecosystem Status", lines)

    def start_auto_refresh(self, interval: int = 15) -> None:
        """Start auto-refresh background thread."""
        self.stop_auto_refresh()
        self._auto_refresh_interval = interval
        self._auto_refresh_stop.clear()

        def _refresh_loop():
            while not self._auto_refresh_stop.is_set():
                self._auto_refresh_stop.wait(self._auto_refresh_interval)
                if not self._auto_refresh_stop.is_set():
                    try:
                        self._auto_refresh_data()
                    except Exception as e:
                        logger.debug("Auto-refresh error: %s", e)

        self._auto_refresh_task = threading.Thread(target=_refresh_loop, daemon=True)
        self._auto_refresh_task.start()
        logger.info("TUI auto-refresh started: %ds", interval)

    def stop_auto_refresh(self) -> None:
        """Stop auto-refresh background thread."""
        self._auto_refresh_stop.set()
        if self._auto_refresh_task:
            self._auto_refresh_task.join(timeout=2)
            self._auto_refresh_task = None
        logger.info("TUI auto-refresh stopped")

    def _auto_refresh_data(self) -> None:
        """Fetch latest data for auto-refresh."""
        if self._api:
            try:
                resp = self._api.get_status()
                if resp.success:
                    self._status_cache = resp.data
            except Exception:
                pass
            try:
                resp = self._api.get_graph()
                if resp.success:
                    self._graph_cache = resp.data
            except Exception:
                pass
            try:
                resp = self._api.get_agents()
                if resp.success:
                    self._agents_cache = resp.data
            except Exception:
                pass


class TUIShell(cmd.Cmd):
    intro = """
╔══════════════════════════════════════════════════════╗
║          BlackHornet Living AGI — TUI               ║
║          Type "help" for commands                    ║
╚══════════════════════════════════════════════════════╝
"""
    prompt = "bh> "

    def __init__(self, renderer: TUIRenderer, api_bridge=None):
        super().__init__()
        self._renderer = renderer
        self._api = api_bridge
        self._graph_cache: Optional[Dict] = None
        self._agents_cache: Optional[Dict] = None
        self._eco_cache: Optional[Dict] = None
        self._status_cache: Optional[Dict] = None
        self._events_cache: Optional[List[Dict]] = None

    def precmd(self, line: str) -> str:
        return line.strip().lower()

    def do_graph(self, arg: str) -> None:
        if self._api:
            resp = self._api.get_graph()
            if resp.success:
                self._graph_cache = resp.data
        print(self._renderer.render_graph(self._graph_cache))

    def do_agents(self, arg: str) -> None:
        if self._api:
            resp = self._api.get_agents()
            if resp.success:
                self._agents_cache = resp.data
        print(self._renderer.render_agents(self._agents_cache))

    def do_ecosystem(self, arg: str) -> None:
        if self._api:
            resp = self._api.get_ecosystem_status()
            if resp.success:
                self._eco_cache = resp.data
        print(self._renderer.render_ecosystem(self._eco_cache))

    def do_status(self, arg: str) -> None:
        if self._api:
            resp = self._api.get_status()
            if resp.success:
                self._status_cache = resp.data
        print(self._renderer.render_status(self._status_cache))

    def do_events(self, arg: str) -> None:
        if self._api:
            resp = self._api.get_events()
            if resp.success:
                self._events_cache = resp.data.get("events", [])
        print(self._renderer.render_events(self._events_cache))

    def do_search(self, arg: str) -> None:
        if not arg:
            print("Usage: search <query>")
            return
        if self._api:
            resp = self._api.search_graph(arg)
            if resp.success:
                results = resp.data.get("results", [])
                if results:
                    lines = [f"  {r.get('label', '?')} ({r.get('type', '?')})"
                             for r in results[:20]]
                else:
                    lines = ["  No results found"]
            else:
                lines = [f"  Error: {resp.error}"]
        else:
            lines = ["  API not available"]
        print(self._renderer.box("Search Results", lines))

    def do_refresh(self, arg: str) -> None:
        self.do_graph("")
        self.do_agents("")
        self.do_ecosystem("")
        self.do_status("")
        self.do_events("")
        print(self._renderer.box("Refresh", ["  All data refreshed"]))

    def do_watch(self, arg: str) -> None:
        interval = int(arg) if arg.isdigit() else 15
        self._renderer.start_auto_refresh(interval)
        print(self._renderer.box("Auto-Refresh", [f"  Started: refreshing every {interval}s"]))

    def do_unwatch(self, arg: str) -> None:
        self._renderer.stop_auto_refresh()
        print(self._renderer.box("Auto-Refresh", ["  Stopped"]))

    def do_quit(self, arg: str) -> bool:
        print("Goodbye.")
        return True

    def do_exit(self, arg: str) -> bool:
        return self.do_quit(arg)

    def do_help(self, arg: str) -> None:
        print(self._renderer.render_help())

    def default(self, line: str) -> None:
        print(f"Unknown command: {line}. Type 'help'.")
