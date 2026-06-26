"""Tests for DeerFlow message gateway."""
from __future__ import annotations

import unittest

from src.colony.orchestration.message_gateway import (
    Message,
    MessageGateway,
    MessagePriority,
    MessageType,
)


class TestMessageDataclass(unittest.TestCase):
    def test_default_msg_id_generated(self):
        m = Message(msg_id="", msg_type=MessageType.TASK, source="a1", target="a2",
                    payload={"key": "val"})
        self.assertTrue(m.msg_id.startswith("msg-"))
        self.assertEqual(len(m.msg_id), 12)  # "msg-" + 8 hex chars

    def test_provided_msg_id_kept(self):
        m = Message(msg_id="custom-1", msg_type=MessageType.TASK, source="a1",
                    target="a2", payload={})
        self.assertEqual(m.msg_id, "custom-1")

    def test_default_priority(self):
        m = Message(msg_id="1", msg_type=MessageType.TASK, source="a1",
                    target="a2", payload={})
        self.assertEqual(m.priority, MessagePriority.NORMAL)

    def test_default_timestamp(self):
        m = Message(msg_id="1", msg_type=MessageType.TASK, source="a1",
                    target="a2", payload={})
        self.assertIsNotNone(m.timestamp)

    def test_custom_priority(self):
        m = Message(msg_id="1", msg_type=MessageType.TASK, source="a1",
                    target="a2", payload={},
                    priority=MessagePriority.CRITICAL)
        self.assertEqual(m.priority, MessagePriority.CRITICAL)


class TestMessageGateway(unittest.TestCase):
    def setUp(self):
        self.gateway = MessageGateway()

    def test_subscribe_adds_handler(self):
        def handler(msg):
            pass
        self.gateway.subscribe("agent-1", handler)
        self.assertIn("agent-1", self.gateway.subscribers)
        self.assertIn(handler, self.gateway.subscribers["agent-1"])

    def test_unsubscribe_removes_handler(self):
        def handler(msg):
            pass
        self.gateway.subscribe("channel", handler)
        self.gateway.unsubscribe("channel", handler)
        self.assertNotIn(handler, self.gateway.subscribers["channel"])

    def test_unsubscribe_nonexistent_does_not_raise(self):
        def handler(msg):
            pass
        self.gateway.unsubscribe("nonexistent", handler)

    def test_publish_adds_to_log(self):
        m = Message(msg_id="m1", msg_type=MessageType.TASK, source="a1",
                    target="a2", payload={})
        self.gateway.publish(m)
        self.assertIn(m, self.gateway.message_log)
        self.assertEqual(len(self.gateway.message_log), 1)

    def test_publish_dispatches_to_subscriber(self):
        received = []
        def handler(msg):
            received.append(msg)
        self.gateway.subscribe("target-agent", handler)
        m = Message(msg_id="m1", msg_type=MessageType.TASK, source="a1",
                    target="target-agent", payload={"data": 42})
        self.gateway.publish(m)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].payload, {"data": 42})

    def test_publish_with_wildcard(self):
        received = []
        def handler(msg):
            received.append(msg)
        self.gateway.subscribe("*", handler)
        m = Message(msg_id="m1", msg_type=MessageType.TASK, source="a1",
                    target="any-agent", payload={})
        self.gateway.publish(m)
        self.assertEqual(len(received), 1)

    def test_publish_dispatches_by_type_when_no_target(self):
        received = []
        def handler(msg):
            received.append(msg)
        self.gateway.subscribe("broadcast", handler)
        m = Message(msg_id="m1", msg_type=MessageType.BROADCAST, source="a1",
                    target=None, payload={})
        self.gateway.publish(m)
        self.assertEqual(len(received), 1)

    def test_handler_exception_moves_to_pending(self):
        def failing(msg):
            raise ValueError("boom")
        self.gateway.subscribe("target", failing)
        m = Message(msg_id="m1", msg_type=MessageType.TASK, source="a1",
                    target="target", payload={})
        self.gateway.publish(m)
        self.assertIn(m, self.gateway.pending)

    def test_send_to_agent_creates_and_publishes(self):
        msg_id = self.gateway.send_to_agent("agent-42", {"cmd": "analyze"})
        self.assertTrue(msg_id.startswith("msg-"))
        self.assertEqual(len(self.gateway.message_log), 1)
        self.assertEqual(self.gateway.message_log[0].target, "agent-42")
        self.assertEqual(self.gateway.message_log[0].payload, {"cmd": "analyze"})

    def test_broadcast_creates_and_publishes(self):
        msg_id = self.gateway.broadcast({"alert": "system check"})
        self.assertTrue(msg_id.startswith("msg-"))
        self.assertEqual(len(self.gateway.message_log), 1)
        self.assertIsNone(self.gateway.message_log[0].target)

    def test_send_to_agent_with_custom_type(self):
        msg_id = self.gateway.send_to_agent(
            "agent-7", {"q": "status"},
            msg_type=MessageType.QUERY,
        )
        msg = self.gateway.message_log[0]
        self.assertEqual(msg.msg_type, MessageType.QUERY)
        self.assertEqual(msg.source, "gateway")

    def test_get_stats_empty(self):
        stats = self.gateway.get_stats()
        self.assertEqual(stats["total_messages"], 0)
        self.assertEqual(stats["pending"], 0)
        self.assertEqual(stats["subscribers"], 0)
        self.assertEqual(stats["channels"], [])

    def test_get_stats_with_activity(self):
        def handler(msg):
            pass
        self.gateway.subscribe("ch1", handler)
        self.gateway.subscribe("ch2", handler)
        self.gateway.send_to_agent("ch1", {"x": 1})
        stats = self.gateway.get_stats()
        self.assertEqual(stats["total_messages"], 1)
        self.assertEqual(stats["subscribers"], 2)
        self.assertIn("ch1", stats["channels"])
        self.assertIn("ch2", stats["channels"])

    def test_multiple_subscribers_same_channel(self):
        received = []
        def h1(msg):
            received.append("h1")
        def h2(msg):
            received.append("h2")
        self.gateway.subscribe("shared", h1)
        self.gateway.subscribe("shared", h2)
        m = Message(msg_id="m1", msg_type=MessageType.TASK, source="a1",
                    target="shared", payload={})
        self.gateway.publish(m)
        self.assertEqual(len(received), 2)

    def test_target_routing_does_not_fallback_to_type(self):
        received_target = []
        received_type = []
        def target_handler(msg):
            received_target.append(msg)
        def type_handler(msg):
            received_type.append(msg)
        self.gateway.subscribe("specific-agent", target_handler)
        self.gateway.subscribe("task", type_handler)
        m = Message(msg_id="m1", msg_type=MessageType.TASK, source="a1",
                    target="specific-agent", payload={})
        self.gateway.publish(m)
        self.assertEqual(len(received_target), 1)
        self.assertEqual(len(received_type), 0)

    def test_publish_multiple_messages(self):
        for i in range(5):
            m = Message(msg_id=f"m{i}", msg_type=MessageType.TASK,
                        source="a1", target=f"a{i}", payload={})
            self.gateway.publish(m)
        self.assertEqual(len(self.gateway.message_log), 5)

    def test_unsubscribe_nonexistent_handler_noop(self):
        def h1(msg):
            pass
        def h2(msg):
            pass
        self.gateway.subscribe("ch", h1)
        self.gateway.unsubscribe("ch", h2)
        self.assertIn(h1, self.gateway.subscribers["ch"])


if __name__ == "__main__":
    unittest.main()
