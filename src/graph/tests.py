"""Tests for FASE 6: Graphify.

Run: python3 src/graph/tests.py -v
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestGraphStore(unittest.TestCase):
    """6.1 GraphStore — graph database."""

    def setUp(self):
        from src.graph.graph_store import GraphStore
        self.temp = tempfile.mkdtemp()
        self.gs = GraphStore(db_path=os.path.join(self.temp, "graph.db"))

    def tearDown(self):
        import shutil
        self.gs.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_add_and_get_node(self):
        nid = self.gs.add_node("python", "language", {"paradigm": "OOP"})
        self.assertGreater(nid, 0)
        node = self.gs.get_node(nid)
        self.assertEqual(node.label, "python")

    def test_find_or_create(self):
        nid1 = self.gs.find_or_create("unique", "test")
        nid2 = self.gs.find_or_create("unique", "test")
        self.assertEqual(nid1, nid2)

    def test_search_nodes(self):
        self.gs.add_node("apple", "fruit")
        self.gs.add_node("banana", "fruit")
        results = self.gs.search_nodes("apple")
        self.assertGreaterEqual(len(results), 1)

    def test_add_edge(self):
        a = self.gs.add_node("A", "test")
        b = self.gs.add_node("B", "test")
        eid = self.gs.add_edge(a, b, "relates", 0.8)
        self.assertGreater(eid, 0)

    def test_add_edge_by_label(self):
        self.gs.add_node("source", "test")
        self.gs.add_node("target", "test")
        eid = self.gs.add_edge_by_label("source", "target", "connects")
        self.assertGreater(eid, 0)

    def test_get_edges(self):
        a = self.gs.add_node("A")
        b = self.gs.add_node("B")
        self.gs.add_edge(a, b, "knows")
        edges = self.gs.get_edges(a)
        self.assertGreaterEqual(len(edges), 1)

    def test_remove_node(self):
        nid = self.gs.add_node("temp", "test")
        self.assertTrue(self.gs.remove_node(nid))
        self.assertIsNone(self.gs.get_node(nid))

    def test_export_json(self):
        self.gs.add_node("test", "t")
        data = self.gs.export_json()
        self.assertIn("nodes", data)
        self.assertGreaterEqual(len(data["nodes"]), 1)

    def test_stats(self):
        self.gs.add_node("a", "type1")
        self.gs.add_node("b", "type2")
        stats = self.gs.stats()
        self.assertEqual(stats["nodes"], 2)


class TestEntityTracker(unittest.TestCase):
    """6.2 EntityTracker — track entities."""

    def setUp(self):
        from src.graph.entity_tracker import EntityTracker
        self.et = EntityTracker()

    def test_track_new(self):
        ent = self.et.track("Python", "language", "conversation")
        self.assertEqual(ent.name, "Python")
        self.assertEqual(ent.mention_count, 1)

    def test_track_existing(self):
        self.et.track("Python", "language")
        ent = self.et.track("Python", "language")
        self.assertEqual(ent.mention_count, 2)

    def test_search(self):
        self.et.track("Machine Learning", "concept")
        results = self.et.search("Learning")
        self.assertGreaterEqual(len(results), 1)

    def test_get_by_type(self):
        self.et.track("A", "type1")
        self.et.track("B", "type1")
        self.et.track("C", "type2")
        results = self.et.get_by_type("type1")
        self.assertEqual(len(results), 2)

    def test_get_entity(self):
        self.et.track("test_ent", "test")
        ent = self.et.get_entity("test_ent", "test")
        self.assertIsNotNone(ent)

    def test_stats(self):
        self.et.track("A", "t1")
        self.et.track("B", "t2")
        stats = self.et.stats()
        self.assertEqual(stats["total_entities"], 2)


class TestRelationshipMapper(unittest.TestCase):
    """6.3 RelationshipMapper — map relationships."""

    def setUp(self):
        from src.graph.relationship_mapper import RelationshipMapper
        self.rm = RelationshipMapper()

    def test_record(self):
        rel = self.rm.record("Alice", "Bob", "knows", 0.9)
        self.assertEqual(rel.source, "Alice")
        self.assertEqual(rel.target, "Bob")

    def test_record_cooccurrence(self):
        count = self.rm.record_cooccurrence(["A", "B", "C"])
        self.assertGreater(count, 0)

    def test_get_related(self):
        self.rm.record("X", "Y", "related")
        related = self.rm.get_related("X")
        self.assertGreaterEqual(len(related), 1)

    def test_get_graph(self):
        self.rm.record("root", "child1", "has")
        self.rm.record("child1", "child2", "has")
        graph = self.rm.get_graph("root", max_depth=2)
        self.assertIn("root", graph["nodes"])
        self.assertGreaterEqual(len(graph["edges"]), 1)

    def test_stats(self):
        self.rm.record("A", "B", "knows")
        stats = self.rm.stats()
        self.assertGreaterEqual(stats["total_relationships"], 1)


class TestGraphVisualizer(unittest.TestCase):
    """6.4 GraphVisualizer — generate visualizations."""

    def setUp(self):
        from src.graph.graph_visualizer import GraphVisualizer
        from src.graph.graph_store import GraphStore
        self.temp = tempfile.mkdtemp()
        self.gs = GraphStore(db_path=os.path.join(self.temp, "viz.db"))
        self.gv = GraphVisualizer(graph_store=self.gs)

    def tearDown(self):
        import shutil
        self.gs.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_build_graph(self):
        vg = self.gv.build_graph()
        self.assertIsNotNone(vg)

    def test_to_json(self):
        result = self.gv.to_json()
        self.assertIn("nodes", result)

    def test_to_ascii(self):
        result = self.gv.to_ascii()
        self.assertIsInstance(result, str)

    def test_to_dot(self):
        result = self.gv.to_dot()
        self.assertIn("digraph", result)

    def test_to_cytoscape(self):
        elements = self.gv.to_cytoscape_elements()
        self.assertIsInstance(elements, list)


class TestAutoGraphUpdater(unittest.TestCase):
    """6.5 AutoGraphUpdater — auto-update graph."""

    def setUp(self):
        from src.graph.auto_updater import AutoGraphUpdater
        from src.graph.graph_store import GraphStore
        self.temp = tempfile.mkdtemp()
        self.gs = GraphStore(db_path=os.path.join(self.temp, "auto.db"))
        self.agu = AutoGraphUpdater(graph_store=self.gs)

    def tearDown(self):
        import shutil
        self.gs.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_on_memory_add(self):
        count = self.agu.on_memory_add("key1", "content", ["tag1"])
        self.assertGreater(count, 0)

    def test_on_concept_add(self):
        count = self.agu.on_concept_add("test_concept", "category1")
        self.assertGreater(count, 0)

    def test_on_episode(self):
        count = self.agu.on_episode("agent1", "decision", "test episode")
        self.assertGreater(count, 0)

    def test_stats(self):
        self.agu.on_memory_add("k", "c")
        stats = self.agu.stats()
        self.assertGreaterEqual(stats["total_updates"], 0)


if __name__ == "__main__":
    unittest.main()
