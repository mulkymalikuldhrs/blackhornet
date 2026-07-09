"""Tests for SessionRecorder and AutoGraphUpdater additions.

Run: python3 -m pytest src/graph/test_session_recorder.py -v
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestAutoGraphUpdaterConversation(unittest.TestCase):
    """AutoGraphUpdater.on_conversation"""

    def setUp(self):
        from src.graph.auto_updater import AutoGraphUpdater
        from src.graph.graph_store import GraphStore
        self.temp = tempfile.mkdtemp()
        self.gs = GraphStore(db_path=os.path.join(self.temp, "test.db"))
        self.agu = AutoGraphUpdater(graph_store=self.gs)

    def tearDown(self):
        import shutil
        self.gs.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_on_conversation_creates_nodes(self):
        count = self.agu.on_conversation("AI Safety", "Discussion about alignment", ["agent1", "agent2"])
        self.assertGreater(count, 0)

    def test_on_conversation_without_participants(self):
        count = self.agu.on_conversation("test topic", "just a summary", [])
        self.assertGreaterEqual(count, 1)

    def test_on_conversation_returns_zero_without_graph(self):
        from src.graph.auto_updater import AutoGraphUpdater
        agu = AutoGraphUpdater()
        count = agu.on_conversation("no graph", "", ["a"])
        self.assertEqual(count, 0)


class TestAutoGraphUpdaterDecision(unittest.TestCase):
    """AutoGraphUpdater.on_decision"""

    def setUp(self):
        from src.graph.auto_updater import AutoGraphUpdater
        from src.graph.graph_store import GraphStore
        self.temp = tempfile.mkdtemp()
        self.gs = GraphStore(db_path=os.path.join(self.temp, "test.db"))
        self.agu = AutoGraphUpdater(graph_store=self.gs)

    def tearDown(self):
        import shutil
        self.gs.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_on_decision_creates_nodes(self):
        count = self.agu.on_decision("agent1", "approve_action", "high risk scenario", 0.9)
        self.assertGreater(count, 0)

    def test_on_decision_default_confidence(self):
        count = self.agu.on_decision("agent2", "reject", "low priority")
        self.assertGreater(count, 0)

    def test_on_decision_returns_zero_without_graph(self):
        from src.graph.auto_updater import AutoGraphUpdater
        agu = AutoGraphUpdater()
        count = agu.on_decision("a", "d", "c")
        self.assertEqual(count, 0)


class TestAutoGraphUpdaterExport(unittest.TestCase):
    """AutoGraphUpdater.auto_export"""

    def setUp(self):
        from src.graph.auto_updater import AutoGraphUpdater
        from src.graph.graph_store import GraphStore
        self.temp = tempfile.mkdtemp()
        self.gs = GraphStore(db_path=os.path.join(self.temp, "test.db"))
        self.agu = AutoGraphUpdater(graph_store=self.gs)

    def tearDown(self):
        import shutil
        self.gs.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_auto_export_writes_file(self):
        self.agu.on_memory_add("k1", "content", ["tag1"])
        self.agu.on_concept_add("test_concept", "category1")
        result = self.agu.auto_export(self.temp)
        self.assertIn("export_path", result)
        self.assertTrue(os.path.exists(result["export_path"]))
        self.assertIn("nodes", result)

    def test_auto_export_creates_directory(self):
        nested = os.path.join(self.temp, "a", "b", "c")
        result = self.agu.auto_export(nested)
        self.assertIn("export_path", result)
        self.assertTrue(os.path.exists(result["export_path"]))

    def test_auto_export_returns_error_without_graph(self):
        from src.graph.auto_updater import AutoGraphUpdater
        agu = AutoGraphUpdater()
        result = agu.auto_export(self.temp)
        self.assertIn("error", result)


class TestSessionRecorder(unittest.TestCase):
    """SessionRecorder recording methods"""

    def setUp(self):
        from src.graph.session_recorder import SessionRecorder
        from src.graph.auto_updater import AutoGraphUpdater
        from src.graph.graph_store import GraphStore
        self.temp = tempfile.mkdtemp()
        self.gs = GraphStore(db_path=os.path.join(self.temp, "session.db"))
        self.agu = AutoGraphUpdater(graph_store=self.gs)
        self.sr = SessionRecorder(auto_updater=self.agu)

    def tearDown(self):
        import shutil
        self.gs.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_record_conversation_returns_record(self):
        rec = self.sr.record_conversation("topic1", "summary1", ["ent1"])
        self.assertEqual(rec["topic"], "topic1")
        self.assertEqual(rec["summary"], "summary1")
        self.assertEqual(rec["entities"], ["ent1"])
        self.assertEqual(rec["type"], "conversation")

    def test_record_conversation_default_entities(self):
        rec = self.sr.record_conversation("t", "s")
        self.assertEqual(rec["entities"], [])

    def test_record_decision_returns_record(self):
        rec = self.sr.record_decision("agent1", "approve", "context x", 0.85)
        self.assertEqual(rec["agent_id"], "agent1")
        self.assertEqual(rec["decision"], "approve")
        self.assertEqual(rec["confidence"], 0.85)

    def test_record_decision_default_confidence(self):
        rec = self.sr.record_decision("a1", "d1", "c1")
        self.assertEqual(rec["confidence"], 0.5)

    def test_get_session_data_empty_initially(self):
        self.assertEqual(len(self.sr.get_session_data()), 0)

    def test_get_session_data_accumulates_records(self):
        self.sr.record_conversation("t1", "s1", ["e1"])
        self.sr.record_decision("a1", "d1", "c1")
        self.sr.record_conversation("t2", "s2", ["e2"])
        data = self.sr.get_session_data()
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]["type"], "conversation")
        self.assertEqual(data[1]["type"], "decision")


class TestSessionRecorderExport(unittest.TestCase):
    """SessionRecorder.auto_export"""

    def setUp(self):
        from src.graph.session_recorder import SessionRecorder
        from src.graph.auto_updater import AutoGraphUpdater
        from src.graph.graph_store import GraphStore
        self.temp = tempfile.mkdtemp()
        self.gs = GraphStore(db_path=os.path.join(self.temp, "session.db"))
        self.agu = AutoGraphUpdater(graph_store=self.gs)
        self.sr = SessionRecorder(auto_updater=self.agu)

    def tearDown(self):
        import shutil
        self.gs.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_auto_export_writes_session_file(self):
        self.sr.record_conversation("t", "s", ["e"])
        result = self.sr.auto_export(self.temp)
        self.assertIn("session_path", result)
        self.assertTrue(os.path.exists(result["session_path"]))
        with open(result["session_path"]) as f:
            data = json.load(f)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["topic"], "t")

    def test_auto_export_without_updater(self):
        from src.graph.session_recorder import SessionRecorder
        sr = SessionRecorder()
        sr.record_conversation("t", "s")
        result = sr.auto_export(self.temp)
        self.assertIn("session_path", result)

    def test_auto_export_creates_directory(self):
        nested = os.path.join(self.temp, "x", "y", "z")
        result = self.sr.auto_export(nested)
        self.assertTrue(os.path.exists(result["session_path"]))


if __name__ == "__main__":
    unittest.main()
