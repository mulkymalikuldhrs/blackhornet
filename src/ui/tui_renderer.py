from __future__ import annotations

import cmd
import logging
import shutil
import sys
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
            "    events   — show recent events",
            "    search Q — search graph nodes",
            "    refresh  — refresh all data",
            "    help     — this help",
            "    quit     — exit TUI",
        ]
        return self.box("BlackHornet TUI", help_lines)


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
        self.do_status("")
        self.do_events("")
        print(self._renderer.box("Refresh", ["  All data refreshed"]))

    def do_quit(self, arg: str) -> bool:
        print("Goodbye.")
        return True

    def do_exit(self, arg: str) -> bool:
        return self.do_quit(arg)

    def do_help(self, arg: str) -> None:
        print(self._renderer.render_help())

    def default(self, line: str) -> None:
        print(f"Unknown command: {line}. Type 'help'.")
