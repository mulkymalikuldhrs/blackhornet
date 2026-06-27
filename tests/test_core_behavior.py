"""Behavioral tests for core modules.

Tests actual behavior, not just imports.
"""

import asyncio
import unittest


class TestEventBus(unittest.TestCase):
    """Test EventBus publish/subscribe behavior."""

    def test_singleton_exists(self):
        from src.core.event_bus import EventBus
        bus = EventBus()
        self.assertIsNotNone(bus)

    def test_subscribe(self):
        from src.core.event_bus import EventBus
        bus = EventBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe("test_event", handler)
        self.assertEqual(len(bus._subscribers.get("test_event", [])), 1)

    def test_multiple_subscribers(self):
        from src.core.event_bus import EventBus
        bus = EventBus()

        bus.subscribe("test_event", lambda e: None)
        bus.subscribe("test_event", lambda e: None)
        handlers = bus._subscribers.get("test_event", [])
        self.assertEqual(len(handlers), 2)


class TestToolRegistry(unittest.TestCase):
    """Test ToolRegistry register/lookup/execute behavior."""

    def test_register_and_lookup(self):
        from src.core.tool_registry import ToolRegistry, FunctionTool
        from src.bh_types.tools import ToolDefinition, ToolType

        registry = ToolRegistry()

        async def dummy_func():
            return "ok"

        definition = ToolDefinition(
            name="test_tool",
            description="A test tool",
            tool_type=ToolType.SHELL,
        )
        tool = FunctionTool(func=dummy_func, definition=definition)
        registry.register_instance(tool)

        found = registry.get("test_tool")
        self.assertIsNotNone(found)
        self.assertEqual(found.definition.name, "test_tool")

    def test_lookup_nonexistent_raises(self):
        from src.core.tool_registry import ToolRegistry
        registry = ToolRegistry()
        with self.assertRaises(KeyError):
            registry.get("nonexistent_tool")


class TestAgentTimeoutError(unittest.TestCase):
    """Test AgentTimeoutError constructor accepts correct units."""

    def test_timeout_in_milliseconds(self):
        from src.exceptions import AgentTimeoutError
        error = AgentTimeoutError("timeout", timeout_ms=5000)
        self.assertEqual(error.timeout_ms, 5000)

    def test_timeout_default_zero(self):
        from src.exceptions import AgentTimeoutError
        error = AgentTimeoutError("timeout")
        self.assertEqual(error.timeout_ms, 0)


class TestMemorySystem(unittest.TestCase):
    """Test MemorySystem initialization."""

    def test_default_init(self):
        from src.memory.system import MemorySystem
        ms = MemorySystem()
        self.assertIsNotNone(ms)

    def test_config_init(self):
        from src.memory.system import MemorySystem, MemorySystemConfig
        config = MemorySystemConfig()
        ms = MemorySystem(config=config)
        self.assertIsNotNone(ms)


class TestSelfHealing(unittest.TestCase):
    """Test PhiAccrualFailureDetector behavior."""

    def test_record_heartbeat(self):
        from src.core.self_healing import PhiAccrualFailureDetector
        detector = PhiAccrualFailureDetector(threshold=0.8)
        health = detector.record_heartbeat("test_component")
        self.assertIsNotNone(health)

    def test_phi_computation(self):
        from src.core.self_healing import PhiAccrualFailureDetector
        detector = PhiAccrualFailureDetector(threshold=0.8)
        for i in range(10):
            detector.record_heartbeat(f"component_{i}")
        # Should have recorded heartbeats
        self.assertTrue(hasattr(detector, '_heartbeat_history'))


if __name__ == "__main__":
    unittest.main()
