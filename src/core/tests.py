"""Tests for src/core — core package init and exports."""

from __future__ import annotations

import os
import sys
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestCorePackage(unittest.TestCase):
    """Core package __init__ exports."""

    def test_core_import(self):
        import src.core
        self.assertTrue(hasattr(src.core, "__all__"))

    def test_core_has_base_agent(self):
        import src.core
        self.assertTrue(hasattr(src.core, "BaseAgent"))

    def test_core_has_tool_registry(self):
        import src.core
        self.assertTrue(hasattr(src.core, "ToolRegistry"))

    def test_core_has_event_bus(self):
        import src.core
        self.assertTrue(hasattr(src.core, "EventBus"))

    def test_core_has_llm_provider(self):
        import src.core
        self.assertTrue(hasattr(src.core, "LLMProvider"))

    def test_core_has_circuit_breaker(self):
        import src.core
        self.assertTrue(hasattr(src.core, "CircuitBreaker"))

    def test_core_all_defined(self):
        import src.core
        self.assertIsInstance(src.core.__all__, list)
        self.assertGreater(len(src.core.__all__), 10)

    def test_core_all_items_importable(self):
        import src.core
        for name in src.core.__all__:
            with self.subTest(symbol=name):
                self.assertTrue(hasattr(src.core, name), f"Missing {name}")

    # === BaseAgent lifecycle hooks ===

    def test_base_agent_on_start_hook_exists(self):
        from src.core import BaseAgent
        agent = BaseAgent()
        self.assertTrue(hasattr(agent, "on_start"))
        self.assertTrue(hasattr(agent.on_start, "__call__"))

    def test_base_agent_on_pause_hook_exists(self):
        from src.core import BaseAgent
        agent = BaseAgent()
        self.assertTrue(hasattr(agent, "on_pause"))
        self.assertTrue(hasattr(agent.on_pause, "__call__"))

    def test_base_agent_on_resume_hook_exists(self):
        from src.core import BaseAgent
        agent = BaseAgent()
        self.assertTrue(hasattr(agent, "on_resume"))
        self.assertTrue(hasattr(agent.on_resume, "__call__"))

    def test_base_agent_on_shutdown_hook_exists(self):
        from src.core import BaseAgent
        agent = BaseAgent()
        self.assertTrue(hasattr(agent, "on_shutdown"))
        self.assertTrue(hasattr(agent.on_shutdown, "__call__"))

    # === FunctionTool initialization ===

    def test_function_tool_has_id(self):
        """FunctionTool must call super().__init__() to have _id."""
        from src.core.tool_registry import FunctionTool
        from src.colony_types.tools import ToolDefinition, ToolType
        definition = ToolDefinition(name="test", description="test", tool_type=ToolType.SHELL)
        tool = FunctionTool(func=lambda: "ok", definition=definition)
        self.assertTrue(hasattr(tool, "id"))
        self.assertIsInstance(tool.id, str)
        self.assertEqual(len(tool.id), 36)  # UUID4 length

    # === AgentTimeoutError milliseconds ===

    def test_agent_timeout_error_timeout_ms(self):
        from src.exceptions import AgentTimeoutError
        err = AgentTimeoutError("timeout", timeout_ms=5000)
        self.assertEqual(err.timeout_ms, 5000)

    def test_agent_timeout_error_no_extra_kwargs(self):
        """AgentTimeoutError does not accept agent_id kwarg."""
        from src.exceptions import AgentTimeoutError
        with self.assertRaises(TypeError):
            AgentTimeoutError("msg", agent_id="bad")  # type: ignore[call-arg]

    # === AgentStateError ===

    def test_agent_state_error_no_extra_kwargs(self):
        """AgentStateError does not accept agent_id or current_state kwargs."""
        from src.exceptions import AgentStateError
        with self.assertRaises(TypeError):
            AgentStateError("msg", agent_id="bad")  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            AgentStateError("msg", current_state="bad")  # type: ignore[call-arg]


if __name__ == "__main__":
    unittest.main()
