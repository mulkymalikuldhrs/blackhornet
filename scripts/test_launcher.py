"""Tests for BH Doctor CLI launcher (bh-doctor).

Run: python3 -m pytest scripts/test_launcher.py -v
"""

from __future__ import annotations

import importlib.machinery
import json
import os
import sys
import tempfile
import types as pytypes
import unittest
from unittest.mock import MagicMock, patch


PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)


def _load_bh_doctor():
    path = os.path.join(PROJECT_ROOT, "bh-doctor")
    if not os.path.exists(path):
        path = os.path.join(PROJECT_ROOT, "bh_doctor")
    with open(path) as f:
        source = f.read()
    code = compile(source, path, "exec")
    mod = pytypes.ModuleType("bh_doctor_module")
    mod.__file__ = path
    mod.__name__ = "bh_doctor_module"
    mod.__package__ = ""
    mod.__path__ = [PROJECT_ROOT]
    sys.modules["bh_doctor_module"] = mod
    exec(code, mod.__dict__)
    return mod


bh_doctor = _load_bh_doctor()


class TestBHDoctorConstructor(unittest.TestCase):
    """BHDoctor.__init__"""

    def setUp(self):
        self.doctor = bh_doctor.BHDoctor()

    def test_initial_components_empty(self):
        self.assertEqual(len(self.doctor._components), 0)

    def test_initial_not_running(self):
        self.assertFalse(self.doctor._running)

    def test_pid_dir_set(self):
        self.assertEqual(self.doctor._pid_dir, bh_doctor.BASE_DIR / "data")


class TestBHDoctorStart(unittest.TestCase):
    """BHDoctor.start — component wiring"""

    def setUp(self):
        self.doctor = bh_doctor.BHDoctor()

    def tearDown(self):
        self.doctor.stop()

    @patch("bh_doctor_module.BHDoctor._save_pid")
    def test_start_returns_results_dict(self, mock_save):
        result = self.doctor.start()
        self.assertIn("_started", result)
        self.assertIn("_version", result)
        self.assertIn("_sovereign", result)
        self.assertIsInstance(result["_started"], list)

    @patch("bh_doctor_module.BHDoctor._save_pid")
    def test_start_sets_running(self, mock_save):
        self.doctor.start()
        self.assertTrue(self.doctor._running)

    @patch("bh_doctor_module.BHDoctor._save_pid")
    def test_start_graceful_on_import_error(self, mock_save):
        with patch("builtins.__import__", side_effect=ImportError("no module")):
            result = self.doctor.start()
            self.assertIn("_started", result)
            self.assertEqual(len(result["_started"]), 0)


class TestBHDoctorStop(unittest.TestCase):
    """BHDoctor.stop"""

    def setUp(self):
        self.doctor = bh_doctor.BHDoctor()

    def test_stop_clears_running(self):
        self.doctor._running = True
        self.doctor.stop()
        self.assertFalse(self.doctor._running)

    def test_stop_handles_missing_pid(self):
        self.doctor._running = True
        self.doctor.stop()


class TestBHDoctorStatus(unittest.TestCase):
    """BHDoctor.status"""

    def setUp(self):
        self.doctor = bh_doctor.BHDoctor()

    def test_status_returns_metadata(self):
        s = self.doctor.status()
        self.assertEqual(s["system"], "BH Doctor")
        self.assertIn("version", s)
        self.assertIn("sovereign", s)
        self.assertIn("running", s)
        self.assertIn("uptime", s)
        self.assertIn("components", s)


class TestBHDoctorDoctor(unittest.TestCase):
    """BHDoctor.doctor — diagnostics"""

    def setUp(self):
        self.doctor = bh_doctor.BHDoctor()

    def test_doctor_returns_dict_with_keys(self):
        d = self.doctor.doctor()
        self.assertIn("issues", d)
        self.assertIn("fixes", d)
        self.assertIn("healthy", d)

    def test_doctor_reports_when_graph_store_missing(self):
        d = self.doctor.doctor()
        self.assertIn("Graph store not started", d["issues"])

    def test_doctor_detects_all_missing_components(self):
        d = self.doctor.doctor()
        expected = [
            "Graph store not started",
            "Entity tracker not started",
            "Relationship mapper not started",
            "Auto graph updater not started",
            "Memory system not started",
            "Event bus not started",
            "Session recorder not started",
        ]
        for e in expected:
            with self.subTest(issue=e):
                self.assertIn(e, d["issues"])

    def test_doctor_not_healthy_without_components(self):
        d = self.doctor.doctor()
        self.assertFalse(d["healthy"])

    def test_doctor_creates_log_dir(self):
        log_dir = bh_doctor.BASE_DIR / "logs"
        if log_dir.exists():
            log_dir.rmdir()
        d = self.doctor.doctor()
        self.assertTrue(log_dir.exists())
        self.assertIn("Created log directory", d["fixes"])


class TestBHDoctorGraphExport(unittest.TestCase):
    """BHDoctor.graph_export — all formats"""

    def setUp(self):
        self.doctor = bh_doctor.BHDoctor()

    def test_graph_export_json_without_store(self):
        result = self.doctor.graph_export("json")
        parsed = json.loads(result)
        self.assertEqual(parsed.get("error"), "Graph store not available")

    def test_graph_export_dot_without_store(self):
        result = self.doctor.graph_export("dot")
        self.assertIn("Graph store not available", result)

    def test_graph_export_ascii_without_store(self):
        result = self.doctor.graph_export("ascii")
        self.assertIn("Graph store not available", result)

    def test_graph_export_with_store(self):
        sys.path.insert(0, str(bh_doctor.BASE_DIR / "src"))
        try:
            from graph.graph_store import GraphStore
            gs = GraphStore(db_path="/tmp/test_graph_export.db")
            gs.add_node("test", "test_type")
            self.doctor._components["graph_store"] = gs
            result = self.doctor.graph_export("json")
            parsed = json.loads(result)
            self.assertIn("nodes", parsed)
            self.assertIn("edges", parsed)
            self.assertGreaterEqual(len(parsed["nodes"]), 1)
        except ImportError:
            self.skipTest("graph_store import error (types circular)")
        finally:
            if os.path.exists("/tmp/test_graph_export.db"):
                os.unlink("/tmp/test_graph_export.db")

    def test_graph_export_dot_with_store(self):
        sys.path.insert(0, str(bh_doctor.BASE_DIR / "src"))
        try:
            from graph.graph_store import GraphStore
            gs = GraphStore(db_path="/tmp/test_graph_dot.db")
            gs.add_node("test", "test_type")
            self.doctor._components["graph_store"] = gs
            result = self.doctor.graph_export("dot")
            self.assertIn("digraph", result)
            self.assertIn("KnowledgeGraph", result)
        except ImportError:
            self.skipTest("graph_store import error")
        finally:
            if os.path.exists("/tmp/test_graph_dot.db"):
                os.unlink("/tmp/test_graph_dot.db")

    def test_graph_export_ascii_with_store(self):
        sys.path.insert(0, str(bh_doctor.BASE_DIR / "src"))
        try:
            from graph.graph_store import GraphStore
            gs = GraphStore(db_path="/tmp/test_graph_ascii.db")
            gs.add_node("test", "test_type")
            self.doctor._components["graph_store"] = gs
            result = self.doctor.graph_export("ascii")
            self.assertIn("Knowledge Graph", result)
        except ImportError:
            self.skipTest("graph_store import error")
        finally:
            if os.path.exists("/tmp/test_graph_ascii.db"):
                os.unlink("/tmp/test_graph_ascii.db")


class TestBHDoctorExportSession(unittest.TestCase):
    """BHDoctor.export_session"""

    def setUp(self):
        self.doctor = bh_doctor.BHDoctor()

    def test_export_returns_path(self):
        result = self.doctor.export_session()
        self.assertTrue(result.startswith("Exported to"))

    def test_export_creates_export_dir(self):
        export_dir = bh_doctor.BASE_DIR / "data" / "session-export"
        self.doctor.export_session()
        self.assertTrue(export_dir.exists())


class TestBHDoctorE2B(unittest.TestCase):
    """BHDoctor.e2b_validate"""

    def setUp(self):
        self.doctor = bh_doctor.BHDoctor()

    def test_e2b_returns_dict(self):
        result = self.doctor.e2b_validate()
        self.assertIsInstance(result, dict)

    def test_e2b_returns_error_without_sandbox(self):
        result = self.doctor.e2b_validate()
        self.assertIn("error", result)
        self.assertEqual(result["error"], "E2B sandbox not available")


class TestMainCommands(unittest.TestCase):
    """main() — command dispatch"""

    @patch("bh_doctor_module.BHDoctor.run_forever")
    def test_start_command(self, mock_run):
        with patch("sys.argv", ["bh-doctor", "start"]):
            bh_doctor.main()
        mock_run.assert_called_once()

    @patch("bh_doctor_module.BHDoctor.stop")
    def test_stop_command(self, mock_stop):
        with patch("sys.argv", ["bh-doctor", "stop"]):
            bh_doctor.main()
        mock_stop.assert_called_once()

    @patch("bh_doctor_module.BHDoctor.status")
    def test_status_command(self, mock_status):
        mock_status.return_value = {
            "system": "BH Doctor", "version": "5.0.0",
            "sovereign": "Test", "running": False, "uptime": 0,
            "components": {},
        }
        with patch("sys.argv", ["bh-doctor", "status"]):
            bh_doctor.main()
        mock_status.assert_called_once()

    @patch("bh_doctor_module.BHDoctor.doctor")
    def test_doctor_command(self, mock_doctor):
        mock_doctor.return_value = {"issues": [], "fixes": [], "healthy": True}
        with patch("sys.argv", ["bh-doctor", "doctor"]):
            bh_doctor.main()
        mock_doctor.assert_called_once()

    @patch("bh_doctor_module.BHDoctor.graph_export")
    def test_graph_command_default_format(self, mock_graph):
        mock_graph.return_value = "{}"
        with patch("sys.argv", ["bh-doctor", "graph"]):
            bh_doctor.main()
        mock_graph.assert_called_once_with(format="json")

    def test_export_command(self):
        with patch("sys.argv", ["bh-doctor", "export"]):
            try:
                bh_doctor.main()
            except SystemExit:
                self.fail("export command caused SystemExit")


class TestSessionRecorderEventBusWiring(unittest.TestCase):
    """Verify SessionRecorder is wired to EventBus in start()"""

    def test_session_recorder_created_with_event_bus(self):
        doc = bh_doctor.BHDoctor()
        with patch("bh_doctor_module.BHDoctor._save_pid"):
            doc.start()
        sr = doc._components.get("session_recorder")
        self.assertIsNotNone(sr, "SessionRecorder should be in components")
        if sr:
            self.assertIsNotNone(sr._event_bus, "SessionRecorder should have event_bus")
            self.assertIsNotNone(sr._updater, "SessionRecorder should have auto_updater")

    def test_session_recorder_subscribes_to_event_bus_by_starting(self):
        sys.path.insert(0, str(bh_doctor.BASE_DIR / "src"))
        try:
            from graph.session_recorder import SessionRecorder
        except ImportError:
            self.skipTest("SessionRecorder import failed")
        doc = bh_doctor.BHDoctor()
        eb = MagicMock()
        doc._components["event_bus"] = eb
        doc._components["auto_graph_updater"] = MagicMock()
        doc._components["graph_store"] = MagicMock()
        doc._components["entity_tracker"] = MagicMock()
        doc._components["relationship_mapper"] = MagicMock()
        sr = SessionRecorder(
            auto_updater=doc._components["auto_graph_updater"],
            graph_store=doc._components["graph_store"],
            entity_tracker=doc._components["entity_tracker"],
            relationship_mapper=doc._components["relationship_mapper"],
            event_bus=eb,
        )
        sr.start()
        eb.subscribe.assert_any_call("action", sr._on_event)
        eb.subscribe.assert_any_call("observation", sr._on_event)


class TestRunForever(unittest.TestCase):
    """BHDoctor.run_forever"""

    def test_run_forever_starts_and_stops(self):
        doc = bh_doctor.BHDoctor()
        doc._running = False
        with patch.object(doc, "start", return_value={"_started": []}) as mock_start:
            with patch.object(doc, "stop") as mock_stop:
                doc.run_forever()
                mock_start.assert_called_once()
                mock_stop.assert_called_once()

    def test_run_forever_calls_doctor_periodically(self):
        doc = bh_doctor.BHDoctor()
        doc._running = True
        cycle_count = [0]
        original_sleep = bh_doctor.time.sleep

        def fake_sleep(n):
            cycle_count[0] += 1
            if cycle_count[0] >= 3:
                doc._running = False

        with patch.object(doc, "start", return_value={"_started": []}):
            with patch.object(doc, "doctor", return_value={"healthy": True, "issues": [], "fixes": []}):
                with patch.object(doc, "stop"):
                    with patch("bh_doctor_module.time.sleep", fake_sleep):
                        doc.run_forever()
                        self.assertGreaterEqual(cycle_count[0], 1)


class TestErrorHandling(unittest.TestCase):
    """Graceful error handling"""

    def test_import_error_in_start_is_graceful(self):
        doc = bh_doctor.BHDoctor()
        with patch("bh_doctor_module.sys.path", side_effect=Exception("path fail")):
            result = doc.start()
            self.assertIn("_started", result)

    def test_component_error_does_not_crash_stop(self):
        doc = bh_doctor.BHDoctor()
        doc._components["bad_comp"] = object()
        doc._running = True
        try:
            doc.stop()
        except Exception:
            self.fail("stop() crashed on unknown component")

    def test_stop_with_no_components(self):
        doc = bh_doctor.BHDoctor()
        try:
            doc.stop()
        except Exception:
            self.fail("stop() crashed with no components")

    def test_doctor_handles_broken_graph_store(self):
        doc = bh_doctor.BHDoctor()
        broken = MagicMock()
        broken.stats.side_effect = RuntimeError("db corrupted")
        doc._components["graph_store"] = broken
        d = doc.doctor()
        self.assertTrue(any("db corrupted" in i for i in d["issues"]))


if __name__ == "__main__":
    unittest.main()
