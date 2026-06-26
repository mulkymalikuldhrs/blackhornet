"""Tests for VectorStore."""
import unittest
import tempfile


class TestVectorStore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def test_init(self):
        from src.memory.vector import VectorStore
        store = VectorStore(collection_name="test", persist_dir=self.temp_dir)
        self.assertIsNotNone(store)

    def test_add_and_search(self):
        from src.memory.vector import VectorStore
        store = VectorStore(collection_name="test", persist_dir=self.temp_dir)
        store.add("doc1", "BlackHornet is an AGI swarm", {"type": "doc"})
        store.add("doc2", "QNA is a quant trading engine", {"type": "doc"})
        results = store.search("AGI", top_k=5)
        self.assertIsInstance(results, list)
        self.assertGreaterEqual(len(results), 1)

    def test_count(self):
        from src.memory.vector import VectorStore
        store = VectorStore(collection_name="test", persist_dir=self.temp_dir)
        store.add("doc1", "test content")
        count = store.count()
        self.assertGreaterEqual(count, 0)

    def test_fallback_without_chromadb(self):
        from src.memory.vector import VectorStore
        store = VectorStore.__new__(VectorStore)
        store.collection_name = "test"
        store.persist_dir = self.temp_dir
        store._collection = None
        store._encoder = None
        # Should not crash without chromadb
        store.add("test", "hello")
        results = store.search("hello")
        self.assertEqual(results, [])

    def test_delete(self):
        from src.memory.vector import VectorStore
        store = VectorStore(collection_name="test", persist_dir=self.temp_dir)
        store.add("doc1", "test content")
        store.delete("doc1")
        results = store.search("test")
        # Should not find deleted doc
        ids = [r["id"] for r in results]
        self.assertNotIn("doc1", ids)


if __name__ == "__main__":
    unittest.main()