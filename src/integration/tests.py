"""Tests for FASE 10: Inject BH Modules.

Run: python3 src/integration/tests.py -v
"""

from __future__ import annotations

import os
import sys
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestGraphTracker(unittest.TestCase):
    """10.1 GraphTracker — track BH entities in graph."""

    def setUp(self):
        from src.integration.graph_tracker import GraphTracker
        self.gt = GraphTracker()

    def test_track_without_store(self):
        nid = self.gt.track_agent("agent_1")
        self.assertEqual(nid, "agent_1")

    def test_track_with_store(self):
        import tempfile, os
        tmp = tempfile.mkdtemp()
        db = os.path.join(tmp, "test.db")
        from src.graph.graph_store import GraphStore
        gs = GraphStore(db)
        from src.integration.graph_tracker import GraphTracker
        gt = GraphTracker(graph_store=gs)
        nid = gt.track_agent("test_agent", "agent", {"key": "val"})
        self.assertIsNotNone(nid)
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    def test_track_task(self):
        nid = self.gt.track_task("task_1", "do something")
        self.assertIsNotNone(nid)

    def test_snapshot(self):
        self.gt.track_agent("a1")
        self.gt.track_agent("a2")
        snap = self.gt.snapshot()
        self.assertEqual(snap["tracked_count"], 2)


class TestMemoryAdapter(unittest.TestCase):
    """10.2 MemoryAdapter — bridge memory systems."""

    def setUp(self):
        from src.integration.memory_adapter import MemoryAdapter
        self.ma = MemoryAdapter()

    def test_store_without_services(self):
        ok = self.ma.store("key", "content")
        self.assertTrue(ok)

    def test_search_empty(self):
        results = self.ma.search("test")
        self.assertEqual(len(results), 0)

    def test_status(self):
        status = self.ma.status()
        self.assertIn("memory_system", status)
        self.assertIn("memory_bridge", status)


class TestProviderHub(unittest.TestCase):
    """10.3 ProviderHub — combine LLM providers."""

    def setUp(self):
        from src.integration.provider_hub import ProviderHub
        self.ph = ProviderHub()

    def test_scan_without_discovery(self):
        result = self.ph.scan_and_register()
        self.assertEqual(result, {})

    def test_list_providers(self):
        listing = self.ph.list_providers()
        self.assertIn("discovered", listing)

    def test_get_best_provider(self):
        prov = self.ph.get_best_provider()
        self.assertEqual(prov, "")


class TestEventHub(unittest.TestCase):
    """10.4 EventHub — bridge event buses."""

    def setUp(self):
        from src.integration.event_hub import EventHub
        from src.ui.event_bus import EventBus
        self.new_bus = EventBus()
        self.eh = EventHub(new_event_bus=self.new_bus)

    def test_start_stop(self):
        self.eh.start()
        self.assertTrue(self.eh._running)
        self.eh.stop()
        self.assertFalse(self.eh._running)

    def test_publish_with_new_bus(self):
        self.eh.start()
        self.eh.publish("test.event", {"msg": "hello"})
        history = self.new_bus.get_history("test.event")
        self.assertEqual(len(history), 1)
        self.eh.stop()

    def test_status(self):
        status = self.eh.status()
        self.assertIn("new_event_bus", status)
        self.assertIn("running", status)


class TestUnifiedLauncher(unittest.TestCase):
    """10.5 UnifiedLauncher — unified entry point."""

    def setUp(self):
        from src.integration.unified_launcher import UnifiedLauncher
        self.launcher = UnifiedLauncher()

    def test_start_all(self):
        results = self.launcher.start_all()
        self.assertIn("_started", results)
        self.assertGreater(len(results["_started"]), 0)
        self.launcher.stop()

    def test_status(self):
        self.launcher.start_all()
        status = self.launcher.status()
        self.assertTrue(status["running"])
        self.launcher.stop()
        status2 = self.launcher.status()
        self.assertFalse(status2["running"])

    def test_stop(self):
        self.launcher.start_all()
        self.launcher.stop()
        self.assertFalse(self.launcher._running)


class TestKeeperExtension(unittest.TestCase):
    """10.6 KeeperExtension — health checks."""

    def setUp(self):
        from src.integration.keeper_extension import KeeperExtension
        self.K = KeeperExtension

    def test_check_module_auto_discovery(self):
        result = self.K.check_module("auto_discovery")
        self.assertEqual(result["status"], "ok")

    def test_check_module_memory(self):
        result = self.K.check_module("memory")
        self.assertEqual(result["status"], "ok")

    def test_check_module_graph(self):
        result = self.K.check_module("graph")
        self.assertEqual(result["status"], "ok")

    def test_check_module_sandbox(self):
        result = self.K.check_module("sandbox")
        self.assertEqual(result["status"], "ok")

    def test_check_module_ui(self):
        result = self.K.check_module("ui")
        self.assertEqual(result["status"], "ok")

    def test_check_module_unknown(self):
        result = self.K.check_module("nonexistent")
        self.assertEqual(result["status"], "unknown_module")

    def test_check_all(self):
        results = self.K.check_all()
        self.assertTrue(results["all_ok"])

    def test_summary(self):
        s = self.K.summary()
        self.assertIn("auto_discovery", s)
        self.assertIn("memory", s)


class TestSrcInit(unittest.TestCase):
    """src/__init__.py exports."""

    def test_get_unified_launcher(self):
        from src import get_unified_launcher
        launcher = get_unified_launcher()
        self.assertIsNotNone(launcher)

    def test_check_all_modules(self):
        from src import check_all_modules
        results = check_all_modules()
        self.assertTrue(results["all_ok"])

    def test_get_keeper_extension(self):
        from src import get_keeper_extension
        K = get_keeper_extension()
        self.assertIsNotNone(K)


class TestAMCBridge(unittest.TestCase):
    """11.1 AMCBridge — wire new modules into AMC core."""

    def setUp(self):
        from src.integration.amc_bridge import AMCBridge
        self.bridge = AMCBridge()

    def test_create(self):
        self.assertIsNotNone(self.bridge)

    def test_start_stop(self):
        self.bridge.start()
        self.assertTrue(self.bridge._running)
        self.bridge.stop()
        self.assertFalse(self.bridge._running)

    def test_status(self):
        status = self.bridge.get_status()
        self.assertIn("running", status)
        self.assertIn("new_event_bus", status)

    def test_sync_without_services(self):
        c = self.bridge.sync_memory_to_amc("k", "v")
        self.assertFalse(c)
        c = self.bridge.sync_amc_agents_to_graph()
        self.assertEqual(c, 0)
        c = self.bridge.sync_colonies_to_graph()
        self.assertEqual(c, 0)

    def test_set_services(self):
        from src.ui.event_bus import EventBus
        eb = EventBus()
        self.bridge.set_new_services(event_bus=eb)
        self.bridge.start()
        self.assertTrue(self.bridge._running)
        self.bridge.stop()


class TestAMCToolRegistrar(unittest.TestCase):
    """11.2 AMCToolRegistrar — register new modules as AMC tools."""

    def setUp(self):
        from src.integration.amc_tools import AMCToolRegistrar
        self.reg = AMCToolRegistrar()

    def test_create(self):
        self.assertIsNotNone(self.reg)

    def test_register_without_registry(self):
        count = self.reg.register_all()
        self.assertEqual(count, 0)

    def test_registered_tools_empty(self):
        tools = self.reg.registered_tools()
        self.assertEqual(tools, [])

    def test_register_with_adapter_no_registry(self):
        from src.integration.memory_adapter import MemoryAdapter
        count = self.reg.register_all(memory_adapter=MemoryAdapter())
        self.assertEqual(count, 0)

    def test_register_with_graph_tracker_no_registry(self):
        from src.integration.graph_tracker import GraphTracker
        count = self.reg.register_all(graph_tracker=GraphTracker())
        self.assertEqual(count, 0)

    def test_register_all_no_registry(self):
        from src.integration.memory_adapter import MemoryAdapter
        from src.integration.graph_tracker import GraphTracker
        from src.integration.provider_hub import ProviderHub
        count = self.reg.register_all(
            memory_adapter=MemoryAdapter(),
            graph_tracker=GraphTracker(),
            provider_hub=ProviderHub(),
        )
        self.assertEqual(count, 0)


class TestInitExports(unittest.TestCase):
    """Updated __init__.py exports."""

    def test_all_exports(self):
        from src.integration import (
            GraphTracker, MemoryAdapter, ProviderHub,
            EventHub, UnifiedLauncher, KeeperExtension,
            AMCBridge, AMCToolRegistrar,
        )
        for cls in [GraphTracker, MemoryAdapter, ProviderHub,
                    EventHub, UnifiedLauncher, KeeperExtension,
                    AMCBridge, AMCToolRegistrar]:
            self.assertIsNotNone(cls)


if __name__ == "__main__":
    unittest.main()
