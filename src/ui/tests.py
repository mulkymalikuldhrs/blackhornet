"""Tests for FASE 8: Interactive UI + Dual Interface.

Run: python3 src/ui/tests.py -v
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestEventBus(unittest.TestCase):
    """8.4 EventBus — observer pattern event distribution."""

    def setUp(self):
        from src.ui.event_bus import EventBus
        self.eb = EventBus()

    def test_publish_and_subscribe(self):
        received = []
        def handler(event):
            received.append(event)
        self.eb.subscribe("test.event", handler)
        from src.ui.event_bus import Event
        self.eb.publish(Event("test.event", {"msg": "hello"}, source="test"))
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].type, "test.event")
        self.assertEqual(received[0].data["msg"], "hello")

    def test_unsubscribe(self):
        received = []
        def handler(event):
            received.append(event)
        self.eb.subscribe("test.event", handler)
        self.eb.unsubscribe("test.event", handler)
        from src.ui.event_bus import Event
        self.eb.publish(Event("test.event", {}))
        self.assertEqual(len(received), 0)

    def test_history(self):
        from src.ui.event_bus import Event
        for i in range(5):
            self.eb.publish(Event("evt", {"i": i}))
        history = self.eb.get_history("evt")
        self.assertEqual(len(history), 5)

    def test_count(self):
        from src.ui.event_bus import Event
        self.eb.publish(Event("a", {}))
        self.eb.publish(Event("a", {}))
        self.eb.publish(Event("b", {}))
        counts = self.eb.count()
        self.assertEqual(counts.get("a"), 2)
        self.assertEqual(counts.get("b"), 1)

    def test_clear_history(self):
        from src.ui.event_bus import Event
        self.eb.publish(Event("x", {}))
        self.eb.clear_history()
        self.assertEqual(len(self.eb.get_history()), 0)


class TestAPIBridge(unittest.TestCase):
    """8.5 APIBridge — REST API for graph/memory/status."""

    def setUp(self):
        from src.ui.api_bridge import APIBridge
        self.api = APIBridge()

    def test_graph_unavailable(self):
        resp = self.api.get_graph()
        self.assertFalse(resp.success)
        self.assertEqual(resp.status_code, 503)

    def test_memory_unavailable(self):
        resp = self.api.get_memory("test")
        self.assertFalse(resp.success)
        self.assertEqual(resp.status_code, 503)

    def test_status_without_services(self):
        resp = self.api.get_status()
        self.assertTrue(resp.success)
        self.assertIn("services", resp.data)

    def test_events_unavailable(self):
        resp = self.api.get_events()
        self.assertFalse(resp.success)
        self.assertEqual(resp.status_code, 503)

    def test_handle_request_404(self):
        resp = self.api.handle_request("GET", "/api/v1/nonexistent")
        self.assertFalse(resp.success)
        self.assertEqual(resp.status_code, 404)


class TestAPIBridgeWithGraphStore(unittest.TestCase):
    """8.5 APIBridge — integration with GraphStore."""

    def setUp(self):
        from src.ui.api_bridge import APIBridge
        import tempfile, os
        self.tmp = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp, "test_graph.db")
        from src.graph.graph_store import GraphStore
        self.store = GraphStore(self.db_path)
        self.api = APIBridge(graph_store=self.store)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_get_graph_empty(self):
        resp = self.api.get_graph()
        self.assertTrue(resp.success)
        self.assertEqual(len(resp.data.get("nodes", [])), 0)

    def test_search_graph_empty(self):
        resp = self.api.search_graph("test")
        self.assertTrue(resp.success)

    def test_get_graph_with_node(self):
        self.store.find_or_create("test_node", "concept", {"key": "val"})
        resp = self.api.get_graph()
        self.assertTrue(resp.success)


class TestCytoscapeRenderer(unittest.TestCase):
    """8.2 CytoscapeRenderer — HTML/JS generation."""

    def setUp(self):
        from src.ui.cytoscape_renderer import CytoscapeRenderer
        self.cr = CytoscapeRenderer()

    def test_render_html(self):
        html = self.cr.render_html()
        self.assertIn("cytoscape", html)
        self.assertIn("BlackHornet", html)

    def test_render_elements(self):
        data = {
            "nodes": [{"id": "1", "label": "test", "type": "concept"}],
            "edges": [{"source": "1", "target": "2", "relation": "knows"}],
        }
        elements = self.cr.render_elements(data)
        self.assertEqual(len(elements), 2)
        self.assertEqual(elements[0]["data"]["label"], "test")

    def test_cytoscape_js_url(self):
        from src.ui.cytoscape_renderer import CytoscapeRenderer as CR
        url = CR.cytoscape_js_url()
        self.assertIn("cdnjs.cloudflare.com", url)
        self.assertIn("cytoscape", url)


class TestTUIRenderer(unittest.TestCase):
    """8.3 TUIRenderer — terminal UI rendering."""

    def setUp(self):
        from src.ui.tui_renderer import TUIRenderer
        self.tui = TUIRenderer()

    def test_box(self):
        box = self.tui.box("Title", ["Line 1", "Line 2"])
        self.assertIn("Title", box)
        self.assertIn("Line 1", box)
        self.assertIn("┌", box)
        self.assertIn("└", box)

    def test_render_graph_empty(self):
        result = self.tui.render_graph({"nodes": [], "edges": []})
        self.assertIn("Graph", result)

    def test_render_status_empty(self):
        result = self.tui.render_status({"services": {}})
        self.assertIn("Status", result)

    def test_render_events_empty(self):
        result = self.tui.render_events([])
        self.assertIn("Events", result)

    def test_render_help(self):
        result = self.tui.render_help()
        self.assertIn("help", result)
        self.assertIn("quit", result)


class TestTUIShell(unittest.TestCase):
    """8.3 TUIShell — cmd-based interactive shell."""

    def setUp(self):
        from src.ui.tui_renderer import TUIRenderer, TUIShell
        self.tui = TUIRenderer()
        self.shell = TUIShell(self.tui)

    def test_help_command(self):
        self.shell.onecmd("help")

    def test_graph_command(self):
        self.shell.onecmd("graph")

    def test_status_command(self):
        self.shell.onecmd("status")

    def test_events_command(self):
        self.shell.onecmd("events")

    def test_quit_command(self):
        result = self.shell.onecmd("quit")
        self.assertTrue(result)

    def test_search_no_query(self):
        self.shell.onecmd("search")

    def test_search_with_query(self):
        self.shell.onecmd("search test")

    def test_unknown_command(self):
        self.shell.onecmd("nonexistent")

    def test_precmd_lower(self):
        result = self.shell.precmd("GRAPH")
        self.assertEqual(result, "graph")


class TestWebServer(unittest.TestCase):
    """8.1 WebServer — HTTP server."""

    def setUp(self):
        from src.ui.web_server import WebServer
        self.ws = WebServer(host="127.0.0.1", port=0)

    def test_create(self):
        self.assertIsNotNone(self.ws)

    def test_find_free_port(self):
        from src.ui.web_server import WebServer as WS
        port = WS.find_free_port(9190, 9200)
        self.assertGreater(port, 0)

    def test_url(self):
        from src.ui.web_server import WebServer as WS
        ws2 = WS(host="0.0.0.0", port=8080)
        self.assertEqual(ws2.url, "http://0.0.0.0:8080")


class TestDashboard(unittest.TestCase):
    """8.6 Dashboard — system monitoring."""

    def setUp(self):
        from src.ui.dashboard import Dashboard
        self.dash = Dashboard()

    def test_snapshot_without_services(self):
        snap = self.dash.snapshot()
        self.assertIn("timestamp", snap)
        self.assertIn("graph", snap)
        self.assertIn("events", snap)

    def test_summary(self):
        summary = self.dash.summary()
        self.assertIsInstance(summary, str)

    def test_history(self):
        self.dash.snapshot()
        self.dash.snapshot()
        history = self.dash.history(limit=10)
        self.assertEqual(len(history), 2)

    def test_to_json(self):
        self.dash.snapshot()
        j = self.dash.to_json()
        self.assertIsInstance(j, str)

    def test_clear(self):
        self.dash.snapshot()
        self.dash.clear()
        self.assertEqual(len(self.dash.history()), 0)


class TestUIIntegration(unittest.TestCase):
    """8.7 UIIntegration — wire everything together."""

    def setUp(self):
        from src.ui.integration import UIIntegration
        self.ui = UIIntegration()

    def test_create(self):
        self.assertIsNotNone(self.ui.event_bus)
        self.assertIsNotNone(self.ui.api_bridge)
        self.assertIsNotNone(self.ui.cytoscape)
        self.assertIsNotNone(self.ui.tui)
        self.assertIsNotNone(self.ui.dashboard)

    def test_start_stop_web(self):
        ok = self.ui.start_web("127.0.0.1", 0)
        self.assertTrue(ok)
        self.assertTrue(self.ui.web.is_running)
        self.ui.stop()
        self.assertFalse(self.ui.web.is_running)

    def test_publish_event(self):
        from src.ui.event_bus import Event
        received = []
        def handler(e):
            received.append(e)
        self.ui.event_bus.subscribe("test", handler)
        self.ui.event_bus.publish(Event("test", {"a": 1}))
        self.assertEqual(len(received), 1)


class TestStaticFiles(unittest.TestCase):
    """Static frontend files exist and are valid."""

    def test_index_html_exists(self):
        path = os.path.join(os.path.dirname(__file__), "static", "index.html")
        self.assertTrue(os.path.isfile(path))
        with open(path) as f:
            content = f.read()
        self.assertIn("cytoscape", content.lower())


class TestEventDataclass(unittest.TestCase):
    """Event dataclass correctness."""

    def test_event_defaults(self):
        from src.ui.event_bus import Event
        e = Event("test.type", {"key": "val"}, source="test")
        self.assertEqual(e.type, "test.type")
        self.assertEqual(e.data["key"], "val")
        self.assertEqual(e.source, "test")
        self.assertGreater(e.timestamp, 0)

    def test_event_timestamp_override(self):
        from src.ui.event_bus import Event
        e = Event("t", {}, timestamp=123.0)
        self.assertEqual(e.timestamp, 123.0)


class TestAPIResponse(unittest.TestCase):
    """APIResponse dataclass correctness."""

    def test_success_default(self):
        from src.ui.api_bridge import APIResponse
        r = APIResponse(data={"ok": True})
        self.assertTrue(r.success)
        self.assertEqual(r.status_code, 200)

    def test_error_response(self):
        from src.ui.api_bridge import APIResponse
        r = APIResponse(success=False, error="fail", status_code=500)
        self.assertFalse(r.success)
        self.assertEqual(r.error, "fail")

    def test_to_dict(self):
        from src.ui.api_bridge import APIResponse
        r = APIResponse(data=[1, 2, 3])
        d = r.to_dict()
        self.assertTrue(d["success"])
        self.assertEqual(d["data"], [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
