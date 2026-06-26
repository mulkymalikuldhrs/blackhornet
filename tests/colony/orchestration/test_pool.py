"""Tests for SubagentPool and Sandbox."""

import unittest

from src.colony.orchestration.sub_agent import Subagent, SubagentState
from src.colony.orchestration.pool import SubagentPool
from src.colony.orchestration.sandbox import Sandbox


class TestSubagentPool(unittest.TestCase):
    def test_pool_submit_dispatches(self):
        pool = SubagentPool(max_concurrent=5)
        agent = Subagent(id="a1", task="task1", max_retries=0, timeout=30)
        pool.submit(agent)
        self.assertIn(agent, pool.agents)

    def test_pool_capacity_limit(self):
        pool = SubagentPool(max_concurrent=2)
        agents = [Subagent(id=f"a{i}", task=f"t{i}", max_retries=0, timeout=30) for i in range(5)]
        for a in agents:
            pool.submit(a)
        running = [a for a in agents if a.state == SubagentState.RUNNING]
        self.assertLessEqual(len(running), 2)

    def test_pool_dispatch_idle_agents(self):
        pool = SubagentPool(max_concurrent=3)
        agents = [Subagent(id=f"a{i}", task=f"t{i}", max_retries=0, timeout=30) for i in range(2)]
        for a in agents:
            pool.submit(a)
        running = [a for a in agents if a.state == SubagentState.RUNNING]
        self.assertEqual(len(running), 2)


class TestSandbox(unittest.TestCase):
    def test_sandbox_creates_temp_dir(self):
        import os
        sandbox = Sandbox("agent-1")
        with sandbox as path:
            self.assertIsNotNone(path)
            self.assertTrue(os.path.exists(path))
            self.assertIn("agent-1", str(path))

    def test_sandbox_cleans_up(self):
        import os
        sandbox = Sandbox("agent-2")
        with sandbox as path:
            self.assertTrue(os.path.exists(path))
        self.assertFalse(os.path.exists(path))


if __name__ == "__main__":
    unittest.main()
