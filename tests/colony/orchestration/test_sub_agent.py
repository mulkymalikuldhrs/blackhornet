"""Tests for Subagent lifecycle manager."""

from unittest import mock
import unittest

from src.colony.orchestration.sub_agent import Subagent, SubagentState


class TestSubagentLifecycle(unittest.TestCase):
    def test_starts_pending(self):
        agent = Subagent(id="test-1", task="analyze", max_retries=2, timeout=60)
        self.assertEqual(agent.state, SubagentState.PENDING)

    def test_start_transitions_to_running(self):
        agent = Subagent(id="test-1", task="analyze", max_retries=2, timeout=60)
        agent.start()
        self.assertEqual(agent.state, SubagentState.RUNNING)
        self.assertIsNotNone(agent._started_at)

    def test_complete_transitions_to_completed(self):
        agent = Subagent(id="test-1", task="analyze", max_retries=2, timeout=60)
        agent.start()
        agent.complete({"result": "ok"})
        self.assertEqual(agent.state, SubagentState.COMPLETED)
        self.assertEqual(agent.output, {"result": "ok"})

    def test_fail_within_retry_stays_running(self):
        agent = Subagent(id="test-1", task="analyze", max_retries=2, timeout=60)
        agent.start()
        agent.fail("error 1")
        self.assertEqual(agent.retry_count, 1)
        self.assertEqual(agent.state, SubagentState.RUNNING)

    def test_fail_exceeds_retry_transitions_to_failed(self):
        agent = Subagent(id="test-1", task="analyze", max_retries=2, timeout=60)
        agent.start()
        agent.fail("error 1")
        agent.fail("error 2")
        agent.fail("error 3")
        self.assertEqual(agent.state, SubagentState.FAILED)
        self.assertEqual(agent.retry_count, 3)

    def test_timeout_detection(self):
        agent = Subagent(id="test-3", task="slow op", max_retries=0, timeout=60)
        with mock.patch('time.time', return_value=100):
            agent.start()
        with mock.patch('time.time', return_value=200):
            self.assertTrue(agent.is_timed_out())

    def test_start_from_running_raises(self):
        agent = Subagent(id="test-1", task="analyze", max_retries=2, timeout=60)
        agent.start()
        with self.assertRaises(ValueError):
            agent.start()

    def test_complete_from_pending_raises(self):
        agent = Subagent(id="test-1", task="analyze", max_retries=2, timeout=60)
        with self.assertRaises(ValueError):
            agent.complete("result")

    def test_fail_from_pending_raises(self):
        agent = Subagent(id="test-1", task="analyze", max_retries=2, timeout=60)
        with self.assertRaises(ValueError):
            agent.fail("error")

    def test_illegal_transition_message(self):
        agent = Subagent(id="test-1", task="analyze", max_retries=2, timeout=60)
        with self.assertRaises(ValueError) as ctx:
            agent.complete("result")
        self.assertIn("PENDING", str(ctx.exception))
        self.assertIn("RUNNING", str(ctx.exception))

    def test_negative_max_retries_raises(self):
        with self.assertRaises(ValueError):
            Subagent(id="bad", task="x", max_retries=-1)

    def test_timeout_zero_raises(self):
        with self.assertRaises(ValueError):
            Subagent(id="bad", task="x", timeout=0)

    def test_timeout_negative_raises(self):
        with self.assertRaises(ValueError):
            Subagent(id="bad", task="x", timeout=-5)


if __name__ == "__main__":
    unittest.main()
