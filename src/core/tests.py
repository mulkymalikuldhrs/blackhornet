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


if __name__ == "__main__":
    unittest.main()
