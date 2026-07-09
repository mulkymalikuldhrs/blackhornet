"""Tests for src/config — settings module."""

from __future__ import annotations

import os
import sys
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestSettings(unittest.TestCase):
    """Settings singleton and sub-configs."""

    def setUp(self):
        from src.config.settings import reset_settings
        reset_settings()

    def test_get_settings(self):
        from src.config.settings import get_settings
        s = get_settings()
        self.assertEqual(s.app_name, "ai-multicolony")
        self.assertEqual(s.version, "0.2.0")

    def test_colony_settings(self):
        from src.config.settings import get_settings
        s = get_settings()
        self.assertEqual(s.colony.heartbeat_interval_ms, 30_000)
        self.assertEqual(s.colony.max_agents, 50)

    def test_mcp_settings(self):
        from src.config.settings import get_settings
        s = get_settings()
        self.assertEqual(s.mcp.server_port, 8081)
        self.assertEqual(s.mcp.transport, "stdio")

    def test_memory_settings(self):
        from src.config.settings import get_settings
        s = get_settings()
        self.assertEqual(s.memory.page_size, 4096)
        self.assertEqual(s.memory.working_set_size, 1024)

    def test_api_settings(self):
        from src.config.settings import get_settings
        s = get_settings()
        self.assertEqual(s.api.port, 8000)
        self.assertIn("http://localhost:3000", s.api.cors_origins)

    def test_channel_settings(self):
        from src.config.settings import get_settings
        s = get_settings()
        self.assertEqual(s.channel.telegram_bot_token, "")
        self.assertEqual(s.channel.telegram_api_url, "https://api.telegram.org")

    def test_security_settings(self):
        from src.config.settings import get_settings
        s = get_settings()
        self.assertEqual(s.security.audit_level, "full")
        self.assertEqual(s.security.audit_storage, "memory")

    def test_llm_settings(self):
        from src.config.settings import get_settings
        s = get_settings()
        self.assertEqual(s.llm_provider, "openai")
        self.assertEqual(s.llm_model, "gpt-4o")
        self.assertEqual(s.llm_temperature, 0.7)

    def test_sandbox_settings(self):
        from src.config.settings import get_settings
        s = get_settings()
        self.assertTrue(s.sandbox_docker_enabled)
        self.assertEqual(s.sandbox_startup_timeout, 30)

    def test_browser_settings(self):
        from src.config.settings import get_settings
        s = get_settings()
        self.assertTrue(s.browser_stealth_mode)
        self.assertTrue(s.browser_headless)
        self.assertEqual(s.browser_pool_size, 5)

    def test_reset_settings(self):
        from src.config.settings import get_settings, reset_settings
        s1 = get_settings()
        reset_settings()
        s2 = get_settings()
        self.assertIsNot(s1, s2)

    def test_settings_singleton(self):
        from src.config.settings import get_settings
        s1 = get_settings()
        s2 = get_settings()
        self.assertIs(s1, s2)


if __name__ == "__main__":
    unittest.main()
