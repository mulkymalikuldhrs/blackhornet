"""Tests for Knowledge Graph."""
import unittest
import tempfile
import os
import shutil


class TestKnowledgeGraph(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.kg_path = os.path.join(self.temp_dir, "knowledge_graph.json")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_add_and_get_entity(self):
        from src.core.knowledge_graph import KnowledgeGraph, Entity
        kg = KnowledgeGraph(persist_path=self.kg_path)
        entity = Entity(id="e1", type="concept", properties={"name": "test"})
        kg.add_entity(entity)
        retrieved = kg.get_entity("e1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, "e1")
        self.assertEqual(retrieved.type, "concept")

    def test_add_relation(self):
        from src.core.knowledge_graph import KnowledgeGraph, Entity, Relation
        kg = KnowledgeGraph(persist_path=self.kg_path)
        kg.add_entity(Entity(id="e1", type="a"))
        kg.add_entity(Entity(id="e2", type="b"))
        kg.add_relation(Relation(source="e1", target="e2", relation="connects", weight=0.9))
        self.assertEqual(len(kg.relations), 1)
        self.assertEqual(kg.relations[0].source, "e1")

    def test_query_returns_entity_and_relations(self):
        from src.core.knowledge_graph import KnowledgeGraph, Entity, Relation
        kg = KnowledgeGraph(persist_path=self.kg_path)
        kg.add_entity(Entity(id="e1", type="agent", properties={"role": "coder"}))
        kg.add_entity(Entity(id="e2", type="tool", properties={"name": "search"}))
        kg.add_relation(Relation(source="e1", target="e2", relation="uses"))
        result = kg.query("e1")
        self.assertIsNotNone(result["entity"])
        self.assertEqual(len(result["relations"]), 1)
        self.assertEqual(result["related_entities"][0]["id"], "e2")

    def test_query_with_depth(self):
        from src.core.knowledge_graph import KnowledgeGraph, Entity, Relation
        kg = KnowledgeGraph(persist_path=self.kg_path)
        kg.add_entity(Entity(id="e1", type="a"))
        kg.add_entity(Entity(id="e2", type="b"))
        kg.add_entity(Entity(id="e3", type="c"))
        kg.add_relation(Relation(source="e1", target="e2", relation="r1"))
        kg.add_relation(Relation(source="e2", target="e3", relation="r2"))
        result = kg.query("e1", max_depth=2)
        self.assertGreaterEqual(len(result["paths"]), 1)

    def test_get_stats(self):
        from src.core.knowledge_graph import KnowledgeGraph, Entity, Relation
        kg = KnowledgeGraph(persist_path=self.kg_path)
        kg.add_entity(Entity(id="e1", type="type1"))
        kg.add_entity(Entity(id="e2", type="type2"))
        kg.add_relation(Relation(source="e1", target="e2", relation="rel"))
        stats = kg.get_stats()
        self.assertEqual(stats["entities"], 2)
        self.assertEqual(stats["relations"], 1)
        self.assertIn("type1", stats["entity_types"])

    def test_persistence_round_trip(self):
        from src.core.knowledge_graph import KnowledgeGraph, Entity, Relation
        kg1 = KnowledgeGraph(persist_path=self.kg_path)
        kg1.add_entity(Entity(id="e1", type="persist_test", properties={"value": 42}))
        kg1.add_relation(Relation(source="e1", target="e1", relation="self"))
        kg2 = KnowledgeGraph(persist_path=self.kg_path)
        self.assertEqual(len(kg2.entities), 1)
        self.assertEqual(len(kg2.relations), 1)
        self.assertEqual(kg2.get_entity("e1").properties["value"], 42)

    def test_empty_kg(self):
        from src.core.knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph(persist_path=self.kg_path)
        stats = kg.get_stats()
        self.assertEqual(stats["entities"], 0)
        self.assertEqual(stats["relations"], 0)
        result = kg.query("nonexistent")
        self.assertIsNone(result["entity"])


if __name__ == "__main__":
    unittest.main()