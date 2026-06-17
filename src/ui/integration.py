from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from src.ui.event_bus import EventBus, Event
from src.ui.api_bridge import APIBridge
from src.ui.cytoscape_renderer import CytoscapeRenderer
from src.ui.tui_renderer import TUIRenderer, TUIShell
from src.ui.web_server import WebServer
from src.ui.dashboard import Dashboard

logger = logging.getLogger(__name__)


class UIIntegration:
    def __init__(self, graph_store=None, memory_system=None,
                 thinking=None):
        self._graph = graph_store
        self._memory = memory_system
        self._thinking = thinking

        self.event_bus = EventBus()
        self.api_bridge = APIBridge(
            graph_store=graph_store,
            memory_system=memory_system,
            event_bus=self.event_bus,
            thinking=thinking,
        )
        self.cytoscape = CytoscapeRenderer(api_bridge=self.api_bridge)
        self.tui = TUIRenderer(api_bridge=self.api_bridge,
                               event_bus=self.event_bus)
        self.web = WebServer(api_bridge=self.api_bridge)
        self.dashboard = Dashboard(api_bridge=self.api_bridge,
                                    event_bus=self.event_bus)

    def start_web(self, host: str = "0.0.0.0", port: int = 8080) -> bool:
        self.web = WebServer(host=host, port=port, api_bridge=self.api_bridge)
        return self.web.start()

    def start_tui(self) -> None:
        shell = TUIShell(self.tui, self.api_bridge)
        shell.cmdloop()

    def start_all(self, web_host: str = "0.0.0.0",
                  web_port: int = 8080) -> None:
        logger.info("UIIntegration: starting all services")
        self.event_bus.publish(Event("system.startup", {"mode": "all"}))
        ok = self.start_web(web_host, web_port)
        if ok:
            logger.info("Web UI: %s", self.web.url)
        else:
            logger.warning("Web UI failed to start")

    def stop(self) -> None:
        self.event_bus.publish(Event("system.shutdown", {}))
        self.web.stop()
        logger.info("UIIntegration: all services stopped")
