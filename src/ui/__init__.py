"""UI module — interactive web + TUI dual interface.

8.1 WebServer — lightweight HTTP server (stdlib http.server)
8.2 CytoscapeRenderer — Cytoscape.js HTML/JS generation
8.3 TUIRenderer — terminal UI via cmd module
8.4 EventBus — observer pattern event distribution
8.5 APIBridge — REST API for graph/memory/status
8.6 Dashboard — system monitoring dashboard
8.7 Integration — wire everything together
8.8 WebSocketHandler — real-time push via WebSocket bridge
"""

from .event_bus import EventBus, Event
from .api_bridge import APIBridge, APIResponse
from .cytoscape_renderer import CytoscapeRenderer
from .tui_renderer import TUIRenderer
from .web_server import WebServer
from .dashboard import Dashboard
from .integration import UIIntegration
from .websocket_handler import WebSocketHandler

__all__ = [
    "EventBus", "Event",
    "APIBridge", "APIResponse",
    "CytoscapeRenderer",
    "TUIRenderer",
    "WebServer",
    "Dashboard",
    "UIIntegration",
    "WebSocketHandler",
]
