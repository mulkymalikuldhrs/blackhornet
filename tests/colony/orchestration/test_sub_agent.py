"""Tests for SubAgent lifecycle manager."""

import time
import unittest

from src.colony.orchestration.sub_agent import SubAgent, SubAgentState


class TestSubAgentLifecycle(unittest.TestCase):
    def test_starts_pending(self):
        agent = SubAgent(id="test-1", task="analyze", max_retries=2, timeout=60)
        self.assertEqual(agent.state, SubAgentState.PENDING)

    def test_start_transitions_to_running(self):
        agent = SubAgent(id="test-1", task="analyze", max_retries=2, timeout=60)
        agent.start()
        self.assertEqual(agent.state, SubAgentState.RUNNING)
        self.assertIsNotNone(agent._started_at)

    def test_complete_transitions_to_completed(self):
        agent = SubAgent(id="test-1", task="analyze", max_retries=2, timeout=60)
        agent.start()
        agent.complete({"result": "ok"})
        self.assertEqual(agent.state, SubAgentState.COMPLETED)
        self.assertEqual(agent.output, {"result": "ok"})

    def test_fail_within_retry_stays_running(self):
        agent = SubAgent(id="test-1", task="analyze", max_retries=2, timeout=60)
        agent.start()
        agent.fail("error 1")
        self.assertEqual(agent.retry_count, 1)
        self.assertEqual(agent.state, SubAgentState.RUNNING)

    def test_fail_exceeds_retry_transitions_to_failed(self):
        agent = SubAgent(id="test-1", task="analyze", max_retries=2, timeout=60)
        agent.start()
        agent.fail("error 1")
        agent.fail("error 2")
        agent.fail("error 3")
        self.assertEqual(agent.state, SubAgentState.FAILED)
        self.assertEqual(agent.retry_count, 3)

    def test_timeout_detection(self):
        agent = SubAgent(id="test-1", task="analyze", max_retries=0, timeout=1)
        agent.start()
        time.sleep(1.5)
        self.assertTrue(agent.is_timed_out())


if __name__ == "__main__":
    unittest.main()
