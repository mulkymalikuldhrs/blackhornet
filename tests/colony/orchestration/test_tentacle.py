"""Tests for OctoGent-inspired Tentacle context isolation."""

import os
import unittest

from src.colony.orchestration.tentacle import Tentacle, TentaclePool


class TestTentacle(unittest.TestCase):
    def test_initialize_creates_directories(self):
        t = Tentacle(name="researcher", scope="task")
        t.initialize()
        self.assertTrue(os.path.exists(t.path))
        self.assertTrue(os.path.exists(f"{t.path}/context"))
        self.assertTrue(os.path.exists(f"{t.path}/artifacts"))
        t.cleanup()

    def test_store_and_retrieve(self):
        t = Tentacle(name="coder", scope="session")
        t.initialize()
        t.store("goal", "implement feature")
        self.assertEqual(t.retrieve("goal"), "implement feature")
        self.assertIsNone(t.retrieve("nonexistent"))
        t.cleanup()

    def test_cleanup_removes_path(self):
        t = Tentacle(name="temp", scope="task")
        t.initialize()
        path = t.path
        self.assertTrue(os.path.exists(path))
        t.cleanup()
        self.assertFalse(os.path.exists(path))

    def test_cleanup_idempotent(self):
        t = Tentacle(name="safe", scope="agent")
        t.initialize()
        t.cleanup()
        t.cleanup()  # second call should not raise


class TestTentaclePool(unittest.TestCase):
    def test_create_tentacle(self):
        pool = TentaclePool()
        t = pool.create_tentacle("agent-1", scope="task")
        self.assertIn("agent-1", pool.tentacles)
        self.assertTrue(os.path.exists(t.path))
        pool.release_tentacle("agent-1")

    def test_get_tentacle(self):
        pool = TentaclePool()
        pool.create_tentacle("agent-2")
        t = pool.get_tentacle("agent-2")
        self.assertIsNotNone(t)
        self.assertEqual(t.name, "agent-2")
        pool.release_tentacle("agent-2")

    def test_get_nonexistent_returns_none(self):
        pool = TentaclePool()
        self.assertIsNone(pool.get_tentacle("ghost"))

    def test_release_tentacle_cleans_up(self):
        pool = TentaclePool()
        t = pool.create_tentacle("ephemeral")
        path = t.path
        pool.release_tentacle("ephemeral")
        self.assertNotIn("ephemeral", pool.tentacles)
        self.assertFalse(os.path.exists(path))

    def test_release_nonexistent_does_nothing(self):
        pool = TentaclePool()
        pool.release_tentacle("ghost")  # should not raise


if __name__ == "__main__":
    unittest.main()
