"""Tests for BlackHornet Memory System (FASE 2).

Run: python3 src/memory/tests.py -v
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestShortTermMemory(unittest.TestCase):
    """Sub-agent 2.1: Short-Term Memory."""

    def setUp(self):
        from src.memory.short_term import ShortTermMemory
        self.stm = ShortTermMemory(max_entries=5, default_ttl=3600)

    def test_add_and_get(self):
        self.stm.add("test_key", "test content")
        entry = self.stm.get("test_key")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.content, "test content")

    def test_eviction(self):
        for i in range(10):
            self.stm.add(f"key_{i}", f"content_{i}")
        self.assertIsNone(self.stm.get("key_0"))
        self.assertIsNotNone(self.stm.get("key_9"))

    def test_ttl_expiry(self):
        self.stm.add("expire_key", "content", ttl=0)
        entry = self.stm.get("expire_key")
        self.assertIsNone(entry)

    def test_remove(self):
        self.stm.add("key", "content")
        self.assertTrue(self.stm.remove("key"))
        self.assertIsNone(self.stm.get("key"))

    def test_recent(self):
        for i in range(3):
            self.stm.add(f"k{i}", f"c{i}")
        recent = self.stm.recent(2)
        self.assertEqual(len(recent), 2)

    def test_search(self):
        self.stm.add("alpha", "hello world")
        self.stm.add("beta", "goodbye world")
        results = self.stm.search("world")
        self.assertEqual(len(results), 2)
        results = self.stm.search("hello")
        self.assertEqual(len(results), 1)

    def test_count(self):
        self.assertEqual(self.stm.count(), 0)
        self.stm.add("k1", "c1")
        self.assertEqual(self.stm.count(), 1)

    def test_stats(self):
        stats = self.stm.stats()
        self.assertIn("current_entries", stats)
        self.assertIn("max_entries", stats)
        self.assertIn("default_ttl_seconds", stats)

    def test_update_without_unnecessary_eviction(self):
        self.stm.add("key_a", "first")
        self.stm.add("key_b", "second")
        self.stm.add("key_c", "third")
        self.stm.add("key_d", "fourth")
        self.stm.add("key_e", "fifth")
        self.assertEqual(self.stm.count(), 5)
        self.assertEqual(self.stm.stats()["eviction_count"], 0)
        self.stm.add("key_a", "updated_first")
        self.assertEqual(self.stm.count(), 5)
        self.assertEqual(self.stm.stats()["eviction_count"], 0)
        self.assertIsNotNone(self.stm.get("key_a"))
        self.assertIsNotNone(self.stm.get("key_b"))

    def test_ttl_precision_does_not_expire_prematurely(self):
        self.stm.add("fresh", "content", ttl=3600)
        entry = self.stm.get("fresh")
        self.assertIsNotNone(entry)
        self.assertFalse(entry.is_expired)

    def test_thread_safety(self):
        import threading
        errors = []
        def writer():
            for i in range(50):
                try:
                    self.stm.add(f"t_key_{i}", f"value_{i}")
                except Exception as e:
                    errors.append(e)
        def reader():
            for i in range(50):
                try:
                    self.stm.get(f"t_key_{i}")
                    self.stm.count()
                    self.stm.stats()
                except Exception as e:
                    errors.append(e)
        threads = [threading.Thread(target=writer) for _ in range(4)]
        threads += [threading.Thread(target=reader) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])


class TestLongTermMemory(unittest.TestCase):
    """Sub-agent 2.2: Long-Term Memory."""

    def setUp(self):
        from src.memory.long_term import LongTermMemory
        self.temp = tempfile.mkdtemp()
        self.db = os.path.join(self.temp, "test_ltm.db")
        self.ltm = LongTermMemory(db_path=self.db)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_add_and_get(self):
        eid = self.ltm.add("key1", "hello world", tags=["test"])
        self.assertGreater(eid, 0)
        entry = self.ltm.get("key1")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.content, "hello world")
        self.assertIn("test", entry.tags)

    def test_get_by_id(self):
        eid = self.ltm.add("k", "content")
        entry = self.ltm.get_by_id(eid)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.id, eid)

    def test_fts5_search(self):
        self.ltm.add("a", "apple banana cherry")
        self.ltm.add("b", "banana date elderberry")
        results = self.ltm.search("banana")
        self.assertGreaterEqual(len(results), 2)

    def test_search_by_tag(self):
        self.ltm.add("a", "content", tags=["tag1", "tag2"])
        self.ltm.add("b", "other", tags=["tag2"])
        self.ltm.add("c", "else", tags=["tag3"])
        results = self.ltm.search_by_tag("tag2")
        self.assertEqual(len(results), 2)

    def test_update(self):
        eid = self.ltm.add("k", "original")
        self.ltm.update(eid, content="updated", importance=0.9)
        entry = self.ltm.get("k")
        self.assertEqual(entry.content, "updated")
        self.assertEqual(entry.importance, 0.9)

    def test_remove(self):
        self.ltm.add("k", "content")
        self.assertTrue(self.ltm.remove("k"))
        self.assertIsNone(self.ltm.get("k"))

    def test_list_recent(self):
        self.ltm.add("a", "first")
        time.sleep(0.01)
        self.ltm.add("b", "second")
        recent = self.ltm.list_recent(limit=5)
        self.assertGreaterEqual(len(recent), 2)

    def test_list_by_importance(self):
        self.ltm.add("a", "low", importance=0.2)
        self.ltm.add("b", "high", importance=0.9)
        important = self.ltm.list_by_importance(min_importance=0.7)
        self.assertEqual(len(important), 1)

    def test_count_and_stats(self):
        self.ltm.add("a", "x")
        self.ltm.add("b", "y")
        self.assertEqual(self.ltm.count(), 2)
        stats = self.ltm.stats()
        self.assertIn("total_entries", stats)


class TestSemanticMemory(unittest.TestCase):
    """Sub-agent 2.3: Semantic Memory."""

    def setUp(self):
        from src.memory.semantic import SemanticMemory
        self.temp = tempfile.mkdtemp()
        self.db = os.path.join(self.temp, "test_sem.db")
        self.sem = SemanticMemory(db_path=self.db)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_ngram_utilities(self):
        from src.memory.semantic import compute_ngrams, ngram_similarity, ngrams_to_hash, hash_to_ngrams
        ngrams = compute_ngrams("hello", n=2)
        self.assertGreater(len(ngrams), 0)
        sim = ngram_similarity("hello world", "hello", n=2)
        self.assertGreater(sim, 0.0)
        sim_diff = ngram_similarity("hello", "xyz")
        self.assertEqual(sim_diff, 0.0)
        h = ngrams_to_hash({"ab", "bc"})
        restored = hash_to_ngrams(h)
        self.assertEqual(restored, {"ab", "bc"})

    def test_add_and_get(self):
        eid = self.sem.add("hello world", source="test")
        self.assertGreater(eid, 0)
        entry = self.sem.get(eid)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.text, "hello world")

    def test_search_keyword(self):
        self.sem.add("apple banana")
        self.sem.add("banana cherry")
        results = self.sem.search_keyword("banana")
        self.assertGreaterEqual(len(results), 2)

    def test_search_similar(self):
        self.sem.add("hello world this is a test")
        self.sem.add("completely different topic here")
        results = self.sem.search_similar("hello test world", threshold=0.2)
        self.assertGreaterEqual(len(results), 1)

    def test_search_hybrid(self):
        self.sem.add("machine learning is interesting")
        self.sem.add("deep learning with neural networks")
        results = self.sem.search("learning", limit=5)
        self.assertGreaterEqual(len(results), 1)

    def test_remove(self):
        eid = self.sem.add("content")
        self.assertTrue(self.sem.remove(eid))
        self.assertIsNone(self.sem.get(eid))

    def test_count_and_stats(self):
        self.sem.add("a")
        self.sem.add("b")
        self.assertEqual(self.sem.count(), 2)
        stats = self.sem.stats()
        self.assertIn("total_entries", stats)


class TestEpisodicMemory(unittest.TestCase):
    """Sub-agent 2.4: Episodic Memory."""

    def setUp(self):
        from src.memory.episodic import EpisodicMemory
        self.temp = tempfile.mkdtemp()
        self.db = os.path.join(self.temp, "test_epi.db")
        self.epi = EpisodicMemory(db_path=self.db)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_add_and_get(self):
        eid = self.epi.add("agent1", "decision", "selected model A", outcome="success")
        self.assertGreater(eid, 0)
        ep = self.epi.get(eid)
        self.assertIsNotNone(ep)
        self.assertEqual(ep.summary, "selected model A")

    def test_get_by_agent(self):
        self.epi.add("agent1", "msg", "hello")
        self.epi.add("agent2", "msg", "world")
        self.epi.add("agent1", "msg", "again")
        results = self.epi.get_by_agent("agent1")
        self.assertEqual(len(results), 2)

    def test_get_by_type(self):
        self.epi.add("a1", "error", "fail")
        self.epi.add("a2", "decision", "choose")
        self.epi.add("a3", "error", "crash")
        results = self.epi.get_by_type("error")
        self.assertEqual(len(results), 2)

    def test_timeline(self):
        now = time.time()
        self.epi.add("a", "msg", "first")
        self.epi.add("b", "msg", "second")
        # timeline should include both (added just now)
        results = self.epi.get_timeline(start=now - 60, end=now + 60)
        self.assertGreaterEqual(len(results), 2)

    def test_children_and_chain(self):
        parent = self.epi.add("a", "decision", "root")
        child = self.epi.add("a", "action", "child", parent_id=parent)
        grandchild = self.epi.add("a", "result", "grandchild", parent_id=child)
        children = self.epi.get_children(parent)
        self.assertEqual(len(children), 1)
        chain = self.epi.get_chain(grandchild)
        self.assertEqual(len(chain), 3)

    def test_search(self):
        self.epi.add("a", "error", "connection timeout")
        self.epi.add("b", "decision", "normal operation")
        results = self.epi.search("timeout")
        self.assertGreaterEqual(len(results), 1)

    def test_count_and_stats(self):
        self.epi.add("a", "msg", "one")
        self.epi.add("b", "msg", "two")
        self.assertEqual(self.epi.count(), 2)
        stats = self.epi.stats()
        self.assertIn("total_episodes", stats)


class TestConsolidation(unittest.TestCase):
    """Sub-agent 2.5: Memory Consolidation."""

    def setUp(self):
        from src.memory.short_term import ShortTermMemory
        from src.memory.long_term import LongTermMemory
        from src.memory.semantic import SemanticMemory
        from src.memory.episodic import EpisodicMemory
        from src.memory.consolidation import MemoryConsolidator
        self.temp = tempfile.mkdtemp()
        self.stm = ShortTermMemory(max_entries=10)
        self.ltm = LongTermMemory(db_path=os.path.join(self.temp, "cons_ltm.db"))
        self.sem = SemanticMemory(db_path=os.path.join(self.temp, "cons_sem.db"))
        self.epi = EpisodicMemory(db_path=os.path.join(self.temp, "cons_epi.db"))
        self.cons = MemoryConsolidator(self.stm, self.ltm, self.sem, self.epi)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_import(self):
        from src.memory.consolidation import MemoryConsolidator, ConsolidationReport
        self.assertTrue(MemoryConsolidator)

    def test_consolidation_report(self):
        from src.memory.consolidation import ConsolidationReport
        r = ConsolidationReport(
            timestamp="now", stm_to_ltm=5, ltm_to_semantic=3,
            deduplicated=1, archived=2, errors=[], duration_ms=100.0,
        )
        self.assertEqual(r.stm_to_ltm, 5)

    def test_archive_old_entries(self):
        self.ltm.add("old_key", "old content", importance=0.1)
        count = self.cons.archive_old_entries(days=0)  # archive everything
        self.assertGreaterEqual(count, 1)
        self.assertIsNone(self.ltm.get("old_key"))

    def test_stm_to_ltm_consolidation(self):
        self.stm.add("stm_test", "important data to consolidate",
                      ttl=7200,
                      metadata={"importance": 0.8})
        now = time.time()
        self.stm._store["stm_test"].created_at = now - 3600
        moved = self.cons.consolidate_stm_to_ltm()
        self.assertGreaterEqual(moved, 1)
        ltm_entry = self.ltm.get("stm_test")
        self.assertIsNotNone(ltm_entry)
        self.assertEqual(ltm_entry.content, "important data to consolidate")
        self.assertIn("stm", ltm_entry.tags)
        self.assertIsNone(self.stm.get("stm_test"))


class TestForgetting(unittest.TestCase):
    """Sub-agent 2.6: Forgetting Mechanism."""

    def setUp(self):
        from src.memory.long_term import LongTermMemory
        from src.memory.semantic import SemanticMemory
        from src.memory.episodic import EpisodicMemory
        from src.memory.forgetting import ForgettingMechanism
        self.temp = tempfile.mkdtemp()
        self.ltm = LongTermMemory(db_path=os.path.join(self.temp, "forget_ltm.db"))
        self.sem = SemanticMemory(db_path=os.path.join(self.temp, "forget_sem.db"))
        self.epi = EpisodicMemory(db_path=os.path.join(self.temp, "forget_epi.db"))
        self.forget = ForgettingMechanism(
            self.ltm, self.sem, self.epi,
            archive_dir=os.path.join(self.temp, "archive"),
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_import(self):
        from src.memory.forgetting import ForgettingMechanism, ForgettingReport
        self.assertTrue(ForgettingMechanism)

    def test_calculate_decay(self):
        from src.memory.long_term import LTMEntry
        entry = LTMEntry(
            key="test", content="test", created_at=time.time() - 3600,
            accessed_at=time.time() - 3600, access_count=1,
        )
        score = self.forget.calculate_decay(entry)
        self.assertGreater(score, 0)
        self.assertLess(score, 1)

    def test_list_archives(self):
        archives = self.forget.list_archives()
        self.assertEqual(archives, [])

    def test_decay_score_decreases_with_age(self):
        from src.memory.long_term import LTMEntry
        now = time.time()
        recent = LTMEntry(
            key="recent", content="x", created_at=now - 60,
            accessed_at=now - 60, access_count=5,
        )
        old = LTMEntry(
            key="old", content="y", created_at=now - 86400 * 30,
            accessed_at=now - 86400 * 30, access_count=5,
        )
        recent_score = self.forget.calculate_decay(recent)
        old_score = self.forget.calculate_decay(old)
        self.assertGreater(recent_score, old_score)

    def test_unused_entry_decays_to_zero(self):
        from src.memory.long_term import LTMEntry
        entry = LTMEntry(
            key="unused", content="z", created_at=time.time() - 86400 * 90,
            accessed_at=time.time() - 86400 * 90, access_count=0,
        )
        score = self.forget.calculate_decay(entry)
        self.assertEqual(score, 0.0)

    def test_find_decayed_entries(self):
        now = time.time()
        import sqlite3
        with sqlite3.connect(self.ltm.db_path) as conn:
            conn.execute(
                "INSERT INTO entries (key, content, tags, metadata, created_at, accessed_at, access_count, importance) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("decayed", "forget me", "[]", "{}",
                 now - 86400 * 100, now - 86400 * 100, 0, 0.0),
            )
        found = self.forget.find_decayed_entries(threshold=0.01)
        found_keys = [e.key for e in found]
        self.assertIn("decayed", found_keys)


class TestMemoryCLI(unittest.TestCase):
    """Sub-agent 2.7: Memory CLI."""

    def setUp(self):
        from src.memory.cli import MemoryCLI
        self.temp = tempfile.mkdtemp()
        self.cli = MemoryCLI(data_dir=self.temp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_import(self):
        from src.memory.cli import MemoryCLI, main
        self.assertTrue(MemoryCLI)

    def test_add_get(self):
        self.cli.run(["add", "test_key", "test content"])
        import io, contextlib
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            self.cli.run(["get", "test_key"])
        output = f.getvalue()
        self.assertIn("test_key", output)

    def test_empty_search(self):
        import io, contextlib
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            self.cli.run(["search", "nonexistent"])
        output = f.getvalue()
        self.assertIn("No results", output)

    def test_stats(self):
        import io, contextlib
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            self.cli.run(["stats"])
        output = f.getvalue()
        self.assertIn("Memory System Stats", output)

    def test_help(self):
        import io, contextlib
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            self.cli.run([])
        output = f.getvalue()
        self.assertIn("usage:", output.lower())


class TestMemorySystem(unittest.TestCase):
    """MemorySystem integration tests."""

    def setUp(self):
        from src.memory.system import MemorySystem, MemorySystemConfig
        self.temp = tempfile.mkdtemp()
        config = MemorySystemConfig(data_dir=self.temp)
        self.ms = MemorySystem(config=config)
        self.ms.initialize()

    def tearDown(self):
        import shutil
        self.ms.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_stm_remember_and_recall(self):
        self.ms.remember("greeting", "hello world")
        result = self.ms.recall_stm("greeting")
        self.assertEqual(result, "hello world")

    def test_stm_recent(self):
        self.ms.remember("a", "alpha")
        self.ms.remember("b", "beta")
        recent = self.ms.recent_stm(2)
        self.assertEqual(len(recent), 2)

    def test_ltm_store_and_retrieve(self):
        eid = self.ms.store("test_key", "test content", tags=["test"], importance=0.8)
        self.assertGreater(eid, 0)
        result = self.ms.retrieve("test_key")
        self.assertEqual(result, "test content")

    def test_search(self):
        self.ms.store("a", "apple banana")
        self.ms.store("b", "banana cherry")
        results = self.ms.search("banana")
        self.assertGreaterEqual(len(results), 1)

    def test_semantic(self):
        eid = self.ms.store_semantic("hello world this is a test")
        self.assertGreater(eid, 0)
        results = self.ms.search_semantic("hello")
        self.assertGreaterEqual(len(results), 0)

    def test_episodic(self):
        eid = self.ms.record_episode("agent1", "decision", "chose model A", outcome="success")
        self.assertGreater(eid, 0)
        episodes = self.ms.get_episodes("agent1")
        self.assertGreaterEqual(len(episodes), 1)

    def test_consolidation(self):
        self.ms.remember("cons_key", "consolidate me")
        self.ms.store("cons_ltm", "preserved content")
        result = self.ms.consolidate(force=True)
        self.assertIn("stm_to_ltm", result)

    def test_forgetting(self):
        result = self.ms.forget()
        self.assertIn("archived", result)

    def test_stats(self):
        stats = self.ms.stats()
        self.assertIn("stm", stats)
        self.assertIn("ltm", stats)
        self.assertIn("semantic", stats)
        self.assertIn("episodic", stats)


if __name__ == "__main__":
    unittest.main()
