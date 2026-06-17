from __future__ import annotations

import argparse
import logging
import sys
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class UnifiedLauncher:
    """Unified entry point for the entire BlackHornet system.

    Starts and coordinates all modules:
    - Web UI (src/ui/)
    - Graph system (src/graph/)
    - Memory system (src/memory/)
    - Event bus bridging (src/integration/event_hub.py)
    - Provider hub (src/integration/provider_hub.py)
    - Graph tracker (src/integration/graph_tracker.py)
    - Memory adapter (src/integration/memory_adapter.py)
    """

    def __init__(self):
        self._components: Dict[str, Any] = {}
        self._running = False

    def start_all(self, web_port: int = 8080) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        started: List[str] = []

        # 1. Event bus
        try:
            from src.ui.event_bus import EventBus
            eb = EventBus()
            self._components["event_bus"] = eb
            started.append("event_bus")
            results["event_bus"] = "ok"
        except Exception as exc:
            results["event_bus"] = str(exc)

        # 2. Graph store
        try:
            from src.graph.graph_store import GraphStore
            gs = GraphStore()
            self._components["graph_store"] = gs
            started.append("graph_store")
            results["graph_store"] = "ok"
        except Exception as exc:
            results["graph_store"] = str(exc)

        # 3. Graph tracker
        try:
            from src.integration.graph_tracker import GraphTracker
            gt = GraphTracker(graph_store=self._components.get("graph_store"))
            self._components["graph_tracker"] = gt
            started.append("graph_tracker")
            results["graph_tracker"] = "ok"
        except Exception as exc:
            results["graph_tracker"] = str(exc)

        # 4. Memory system
        try:
            from src.memory.system import MemorySystem
            ms = MemorySystem()
            self._components["memory_system"] = ms
            started.append("memory_system")
            results["memory_system"] = "ok"
        except Exception as exc:
            results["memory_system"] = str(exc)

        # 5. Memory adapter
        try:
            from src.integration.memory_adapter import MemoryAdapter
            ma = MemoryAdapter(memory_system=self._components.get("memory_system"))
            self._components["memory_adapter"] = ma
            started.append("memory_adapter")
            results["memory_adapter"] = "ok"
        except Exception as exc:
            results["memory_adapter"] = str(exc)

        # 6. API bridge
        try:
            from src.ui.api_bridge import APIBridge
            ab = APIBridge(
                graph_store=self._components.get("graph_store"),
                memory_system=self._components.get("memory_system"),
                event_bus=self._components.get("event_bus"),
            )
            self._components["api_bridge"] = ab
            started.append("api_bridge")
            results["api_bridge"] = "ok"
        except Exception as exc:
            results["api_bridge"] = str(exc)

        # 7. Web server
        try:
            from src.ui.web_server import WebServer
            ws = WebServer(port=web_port, api_bridge=self._components.get("api_bridge"))
            if ws.start():
                self._components["web_server"] = ws
                started.append("web_server")
                results["web_server"] = f"ok (port {web_port})"
            else:
                results["web_server"] = "failed to start"
        except Exception as exc:
            results["web_server"] = str(exc)

        # 8. Dashboard
        try:
            from src.ui.dashboard import Dashboard
            db = Dashboard(
                api_bridge=self._components.get("api_bridge"),
                event_bus=self._components.get("event_bus"),
            )
            self._components["dashboard"] = db
            started.append("dashboard")
            results["dashboard"] = "ok"
        except Exception as exc:
            results["dashboard"] = str(exc)

        # 9. Provider hub
        try:
            from src.integration.provider_hub import ProviderHub
            ph = ProviderHub()
            self._components["provider_hub"] = ph
            started.append("provider_hub")
            results["provider_hub"] = "ok"
        except Exception as exc:
            results["provider_hub"] = str(exc)

        # 10. Keeper extension
        try:
            from src.integration.keeper_extension import KeeperExtension
            self._components["keeper_extension"] = KeeperExtension
            started.append("keeper_extension")
            results["keeper_extension"] = "ok"
        except Exception as exc:
            results["keeper_extension"] = str(exc)

        # 11. AMC bridge
        try:
            from src.integration.amc_bridge import AMCBridge
            amc = AMCBridge()
            amc.set_new_services(
                event_bus=self._components.get("event_bus"),
                memory_system=self._components.get("memory_system"),
                graph_store=self._components.get("graph_store"),
                graph_tracker=self._components.get("graph_tracker"),
            )
            self._components["amc_bridge"] = amc
            started.append("amc_bridge")
            results["amc_bridge"] = "ok"
        except Exception as exc:
            results["amc_bridge"] = str(exc)

        # 12. AMC tools (register if AMC tool registry is available)
        try:
            from src.integration.amc_tools import AMCToolRegistrar
            registrar = AMCToolRegistrar()
            registered = registrar.register_all(
                memory_adapter=self._components.get("memory_adapter"),
                graph_tracker=self._components.get("graph_tracker"),
                provider_hub=self._components.get("provider_hub"),
                memory_system=self._components.get("memory_system"),
                graph_store=self._components.get("graph_store"),
            )
            self._components["amc_tools"] = registrar
            started.append(f"amc_tools ({registered} tools)")
            results["amc_tools"] = f"ok ({registered} tools)"
        except Exception as exc:
            results["amc_tools"] = str(exc)

        self._running = True
        results["_started"] = started
        logger.info("UnifiedLauncher: started %d components", len(started))
        return results

    def stop(self) -> None:
        self.stop_all()

    def stop_all(self) -> None:
        if "web_server" in self._components:
            self._components["web_server"].stop()
        if "event_bus" in self._components:
            self._components["event_bus"].clear_history()
        self._running = False
        logger.info("UnifiedLauncher: stopped")

    def status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "components": list(self._components.keys()),
        }


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="BlackHornet Unified Launcher")
    p.add_argument("--port", type=int, default=8080, help="Web UI port")
    p.add_argument("--tui", action="store_true", help="Start TUI instead of web")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    launcher = UnifiedLauncher()
    results = launcher.start_all(web_port=args.port)
    started = results.get("_started", [])
    print(f"Started {len(started)} components: {', '.join(started)}")
    if args.tui:
        print("Starting TUI...")
        try:
            from src.ui.tui_renderer import TUIShell, TUIRenderer
            api = launcher._components.get("api_bridge")
            tui_renderer = TUIRenderer(api_bridge=api,
                                        event_bus=launcher._components.get("event_bus"))
            shell = TUIShell(tui_renderer, api)
            shell.cmdloop()
        except ImportError as e:
            logger.warning(f"TUI not available: {e}")
    else:
        web = launcher._components.get("web_server")
        if web:
            print(f"Web UI: http://localhost:{args.port}")
            print("Press Ctrl+C to stop")
        try:
            while launcher._running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    launcher.stop()


if __name__ == "__main__":
    main()
