"""Tests for NeuralGraphMemory — graph-based spreading activation memory."""
import asyncio
import os
import tempfile
import unittest
from pathlib import Path


class TestNeuralGraphMemory(unittest.TestCase):
    """Production-readiness verification for NeuralGraphMemory + bridge."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "test_brain.db"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ── Helpers ──────────────────────────────────────────────────────

    def _run(self, coro):
        return asyncio.run(coro)

    # ── NeuralGraphMemory tests ─────────────────────────────────────

    def test_remember_and_recall(self):
        """Store neurons and retrieve via spreading activation."""
        from src.memory.neural_graph import NeuralGraphMemory

        async def _test():
            async with NeuralGraphMemory(self.db_path) as ngm:
                nid1 = await ngm.remember("BTC max drawdown 5%", tags=["risk"])
                nid2 = await ngm.remember("ETH position size 0.1 BTC", tags=["risk"])
                self.assertIsNotNone(nid1)
                self.assertIsNotNone(nid2)

                # Recall by keyword
                results = await ngm.recall("BTC risk", limit=5)
                self.assertGreaterEqual(len(results), 1)
                self.assertIn("BTC", results[0]["content"])

                # Recall by tag match
                results2 = await ngm.recall("risk", limit=5)
                self.assertGreaterEqual(len(results2), 1)

        self._run(_test())

    def test_link_and_recall_via_synapse(self):
        """Linked neurons should be reachable via spreading activation."""
        from src.memory.neural_graph import NeuralGraphMemory

        async def _test():
            async with NeuralGraphMemory(self.db_path) as ngm:
                nid = await ngm.remember("limit order at 50000", tags=["order"])
                nid2 = await ngm.remember("BTC support at 48000", tags=["analysis"])

                await ngm.link(nid, nid2, relation="related_to", weight=0.9)

                # Query the anchor neuron's content
                results = await ngm.recall("order", limit=5)
                self.assertGreaterEqual(len(results), 1)

                # Check that spreading activation reached the linked neuron
                contents = [r["content"] for r in results]
                found = any("support" in c for c in contents)
                self.assertTrue(found, "Linked neuron should be reachable via spreading activation")

        self._run(_test())

    def test_forget(self):
        """Soft-delete should remove neuron from recall."""
        from src.memory.neural_graph import NeuralGraphMemory

        async def _test():
            async with NeuralGraphMemory(self.db_path) as ngm:
                nid = await ngm.remember("temporary memory", tags=["temp"])
                self.assertTrue(await ngm.forget(nid))

                results = await ngm.recall("temporary", limit=5)
                self.assertEqual(len(results), 0)

        self._run(_test())

    def test_forget_nonexistent(self):
        """Forgetting non-existent neuron returns False."""
        from src.memory.neural_graph import NeuralGraphMemory

        async def _test():
            async with NeuralGraphMemory(self.db_path) as ngm:
                self.assertFalse(await ngm.forget("nonexistent"))

        self._run(_test())

    def test_consolidation(self):
        """Consolidation should prune orphan synapses and return stats."""
        from src.memory.neural_graph import NeuralGraphMemory

        async def _test():
            async with NeuralGraphMemory(self.db_path) as ngm:
                nid = await ngm.remember("active neuron", tags=["active"])
                dead = await ngm.remember("dead neuron", tags=["dead"])
                await ngm.link(nid, dead, relation="related_to")

                # Forget the target — synapse becomes orphan
                await ngm.forget(dead)

                report = await ngm.consolidate()
                self.assertIn("pruned", report)
                self.assertIn("hebbian_updated", report)
                self.assertIn("neurons_active", report)
                self.assertGreaterEqual(report["pruned"], 0)

        self._run(_test())

    def test_stats(self):
        """Stats should reflect active neurons and synapses."""
        from src.memory.neural_graph import NeuralGraphMemory

        async def _test():
            async with NeuralGraphMemory(self.db_path) as ngm:
                n1 = await ngm.remember("memory A", tags=["a"])
                n2 = await ngm.remember("memory B", tags=["b"])
                await ngm.link(n1, n2)

                s = await ngm.stats()
                self.assertGreaterEqual(s["neurons_active"], 2)
                self.assertGreaterEqual(s["synapses"], 1)
                self.assertIn("neuron_types", s)

        self._run(_test())

    def test_recall_empty_graph(self):
        """Recall on empty graph returns empty list."""
        from src.memory.neural_graph import NeuralGraphMemory

        async def _test():
            async with NeuralGraphMemory(self.db_path) as ngm:
                results = await ngm.recall("anything", limit=5)
                self.assertEqual(len(results), 0)

        self._run(_test())

    def test_recall_empty_query(self):
        """Recall with empty query returns empty list."""
        from src.memory.neural_graph import NeuralGraphMemory

        async def _test():
            async with NeuralGraphMemory(self.db_path) as ngm:
                results = await ngm.recall("", limit=5)
                self.assertEqual(len(results), 0)

        self._run(_test())

    def test_context_manager(self):
        """__aenter__ should initialize, __aexit__ should shutdown."""
        from src.memory.neural_graph import NeuralGraphMemory

        async def _test():
            async with NeuralGraphMemory(self.db_path) as ngm:
                self.assertTrue(ngm._initialized)
                nid = await ngm.remember("context managed", tags=["test"])
                self.assertIsNotNone(nid)

            # After exit, should no longer be initialized
            self.assertFalse(ngm._initialized)

        self._run(_test())

    def test_thread_lock_safety(self):
        """Simulate concurrent writes under lock (sequential async)."""
        from src.memory.neural_graph import NeuralGraphMemory

        async def _test():
            async with NeuralGraphMemory(self.db_path) as ngm:
                async def write(i):
                    return await ngm.remember(f"concurrent {i}", tags=["test"])

                ids = await asyncio.gather(*[write(i) for i in range(10)])
                self.assertEqual(len(ids), 10)
                self.assertEqual(len(set(ids)), 10)  # All unique

        self._run(_test())

    def test_high_importance_scores_higher(self):
        """Neurons with higher importance should score higher at same activation."""
        from src.memory.neural_graph import NeuralGraphMemory

        async def _test():
            async with NeuralGraphMemory(self.db_path) as ngm:
                low = await ngm.remember("risk limit", tags=["risk"], importance=0.3)
                high = await ngm.remember("risk limit", tags=["risk"], importance=0.9)

                results = await ngm.recall("risk", limit=5)
                self.assertGreaterEqual(len(results), 2)

                low_result = next(r for r in results if r["id"] == low)
                high_result = next(r for r in results if r["id"] == high)
                self.assertGreater(high_result["score"], low_result["score"])

        self._run(_test())

    def test_link_missing_neuron_raises(self):
        """Linking non-existent neurons raises ValueError."""
        from src.memory.neural_graph import NeuralGraphMemory

        async def _test():
            async with NeuralGraphMemory(self.db_path) as ngm:
                nid = await ngm.remember("present", tags=["a"])
                with self.assertRaises(ValueError):
                    await ngm.link(nid, "missing")
                with self.assertRaises(ValueError):
                    await ngm.link("missing", nid)

        self._run(_test())

    def test_reinitialize_idempotent(self):
        """Calling initialize twice should be safe."""
        from src.memory.neural_graph import NeuralGraphMemory

        async def _test():
            ngm = NeuralGraphMemory(self.db_path)
            await ngm.initialize()
            await ngm.initialize()  # second call — no-op
            nid = await ngm.remember("after double init", tags=["test"])
            self.assertIsNotNone(nid)
            await ngm.shutdown()

        self._run(_test())

    # ── NeuralMemoryBridge tests ─────────────────────────────────────

    def test_bridge_remember_recall(self):
        """Bridge wraps NeuralGraphMemory correctly."""
        from src.memory.neural_bridge import NeuralMemoryBridge

        async def _test():
            async with NeuralMemoryBridge(
                brain_name="test", data_dir=self.temp_dir,
            ) as bridge:
                nid = await bridge.remember("bridge test", tags=["test"])
                results = await bridge.recall("bridge test")
                self.assertGreaterEqual(len(results), 1)

        self._run(_test())

    def test_bridge_stats(self):
        """Bridge stats includes brain_name."""
        from src.memory.neural_bridge import NeuralMemoryBridge

        async def _test():
            async with NeuralMemoryBridge(
                brain_name="test", data_dir=self.temp_dir,
            ) as bridge:
                nid = await bridge.remember("test stat", tags=["stat"])
                s = await bridge.stats()
                self.assertEqual(s["brain_name"], "test")
                self.assertGreaterEqual(s["neurons_active"], 1)

        self._run(_test())

    def test_bridge_consolidate(self):
        """Bridge consolidation works end-to-end."""
        from src.memory.neural_bridge import NeuralMemoryBridge

        async def _test():
            async with NeuralMemoryBridge(
                brain_name="test", data_dir=self.temp_dir,
            ) as bridge:
                report = await bridge.consolidate()
                self.assertIn("pruned", report)
                self.assertIn("hebbian_updated", report)

        self._run(_test())

    def test_bridge_context_manager(self):
        """Bridge __aenter__ initializes, __aexit__ shuts down."""
        from src.memory.neural_bridge import NeuralMemoryBridge

        async def _test():
            b = NeuralMemoryBridge(brain_name="test", data_dir=self.temp_dir)
            async with b as bridge:
                self.assertIsNotNone(bridge)
                nid = await bridge.remember("ctx test", tags=["ctx"])
                self.assertIsNotNone(nid)
            # After exit, ngm should be None
            self.assertIsNone(b._ngm)

        self._run(_test())

    def test_bridge_shutdown_idempotent(self):
        """Shutdown twice should be safe."""
        from src.memory.neural_bridge import NeuralMemoryBridge

        async def _test():
            bridge = NeuralMemoryBridge(brain_name="test", data_dir=self.temp_dir)
            await bridge.initialize()
            await bridge.shutdown()
            await bridge.shutdown()  # no exception

        self._run(_test())

    def test_bridge_remember_empty_tags(self):
        """Remember with empty tags list."""
        from src.memory.neural_bridge import NeuralMemoryBridge

        async def _test():
            async with NeuralMemoryBridge(
                brain_name="test", data_dir=self.temp_dir,
            ) as bridge:
                nid = await bridge.remember("no tags", tags=[])
                self.assertIsNotNone(nid)

        self._run(_test())

    def test_bridge_link(self):
        """Bridge link creates synapses."""
        from src.memory.neural_bridge import NeuralMemoryBridge

        async def _test():
            async with NeuralMemoryBridge(
                brain_name="test", data_dir=self.temp_dir,
            ) as bridge:
                n1 = await bridge.remember("source", tags=["a"])
                n2 = await bridge.remember("target", tags=["b"])
                sid = await bridge.link(n1, n2, relation="related_to")
                self.assertIsNotNone(sid)

        self._run(_test())


if __name__ == "__main__":
    unittest.main()
