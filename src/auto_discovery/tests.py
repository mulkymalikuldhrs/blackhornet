"""Tests for the Auto-Discovery Engine.

Run: python3 src/auto_discovery/tests.py -v
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestLLMScanner(unittest.TestCase):
    """Tests for LLMScanner (sub-agent 1.1)."""

    def setUp(self):
        from src.auto_discovery.llm_scanner import LLMScanner
        self.temp_dir = tempfile.mkdtemp()
        self.scanner = LLMScanner(data_dir=self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_import(self):
        from src.auto_discovery.llm_scanner import LLMScanner, ProviderInfo
        self.assertTrue(LLMScanner)
        self.assertTrue(ProviderInfo)

    def test_provider_info_dataclass(self):
        from src.auto_discovery.llm_scanner import ProviderInfo
        p = ProviderInfo(
            name="test", display_name="Test", base_url="https://example.com",
            api_key_env="TEST_KEY", models=["model-1"], is_available=False,
            latency_ms=0.0, error="", last_checked="",
        )
        self.assertEqual(p.name, "test")

    def test_known_providers(self):
        from src.auto_discovery.llm_scanner import _PROVIDERS
        self.assertGreater(len(_PROVIDERS), 0)
        names = [p["name"] for p in _PROVIDERS]
        self.assertIn("opencode_zen", names)
        self.assertIn("nvidia", names)

    def test_save_load(self):
        from src.auto_discovery.llm_scanner import ProviderInfo
        results = [
            ProviderInfo(name="test", display_name="Test", base_url="https://e.com",
                         api_key_env="K", models=["m"], is_available=True,
                         latency_ms=10.0, error="", last_checked="2026-01-01"),
        ]
        filepath = os.path.join(self.temp_dir, "test_providers.json")
        self.scanner.save(results, filepath)
        self.assertTrue(os.path.exists(filepath))
        loaded = self.scanner.load(filepath)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].name, "test")

    def test_load_nonexistent(self):
        result = self.scanner.load("nonexistent.json")
        self.assertEqual(result, [])

    @patch("urllib.request.urlopen")
    def test_make_request_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"status": "ok"}'
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp
        from src.auto_discovery.llm_scanner import LLMScanner
        result = LLMScanner._make_request("https://example.com", {}, "test-key")
        self.assertEqual(result, {"status": "ok"})

    @patch("urllib.request.urlopen")
    def test_make_request_failure(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("test error")
        from src.auto_discovery.llm_scanner import LLMScanner
        with self.assertRaises(RuntimeError):
            LLMScanner._make_request("https://example.com", {}, "test-key")


class TestDataScanner(unittest.TestCase):
    """Tests for DataScanner (sub-agent 1.2)."""

    def setUp(self):
        from src.auto_discovery.data_scanner import DataScanner
        self.temp_dir = tempfile.mkdtemp()
        self.scanner = DataScanner(data_dir=self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_import(self):
        from src.auto_discovery.data_scanner import DataScanner, DataSource
        self.assertTrue(DataScanner)
        self.assertTrue(DataSource)

    def test_source_dataclass(self):
        from src.auto_discovery.data_scanner import DataSource
        d = DataSource(
            name="test", display_name="Test", base_url="https://e.com",
            test_path="/ping", api_key_env="", requires_key=False,
            is_available=False, latency_ms=0.0, error="", last_checked="",
        )
        self.assertEqual(d.name, "test")

    def test_save_load(self):
        from src.auto_discovery.data_scanner import DataSource
        results = [DataSource(name="test", display_name="Test", base_url="https://e.com",
                              test_path="/ping", api_key_env="", requires_key=False,
                              is_available=True, latency_ms=5.0, error="",
                              last_checked="2026-01-01")]
        filepath = os.path.join(self.temp_dir, "test_sources.json")
        self.scanner.save(results, filepath)
        loaded = self.scanner.load(filepath)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].name, "test")

    def test_load_nonexistent(self):
        result = self.scanner.load("nonexistent.json")
        self.assertEqual(result, [])


class TestRouter(unittest.TestCase):
    """Tests for LLMRouter (sub-agent 1.3)."""

    def setUp(self):
        from src.auto_discovery.router import LLMRouter
        self.router = LLMRouter()

    def test_import(self):
        from src.auto_discovery.router import LLMRouter, ComplexityLevel, RouteResult
        self.assertTrue(LLMRouter)
        self.assertTrue(ComplexityLevel)
        self.assertTrue(RouteResult)

    def test_classify_simple(self):
        result = self.router.classify_complexity("hello, how are you?")
        from src.auto_discovery.router import ComplexityLevel
        self.assertEqual(result, ComplexityLevel.SIMPLE)

    def test_classify_medium(self):
        result = self.router.classify_complexity(
            "write a Python function to sort a list using merge sort algorithm "
            "and also implement a test case for it"
        )
        from src.auto_discovery.router import ComplexityLevel
        self.assertEqual(result, ComplexityLevel.MEDIUM)

    def test_classify_trading(self):
        result = self.router.classify_complexity(
            "calculate the Sharpe ratio and Kelly criterion for this portfolio"
        )
        from src.auto_discovery.router import ComplexityLevel
        self.assertEqual(result, ComplexityLevel.TRADING)

    def test_route_returns_result(self):
        result = self.router.route("hello")
        from src.auto_discovery.router import RouteResult
        self.assertIsInstance(result, RouteResult)
        self.assertTrue(result.provider)
        self.assertTrue(result.model)

    def test_route_trading(self):
        result = self.router.route("calculate portfolio risk and backtest strategy")
        # Trading should route to a valid provider
        self.assertTrue(result.provider)
        self.assertTrue(result.model)

    def test_classify_complex_long(self):
        prompt = ("architecture design " * 60)  # >50 tokens with complex keyword
        result = self.router.classify_complexity(prompt)
        from src.auto_discovery.router import ComplexityLevel
        self.assertEqual(result, ComplexityLevel.COMPLEX)


class TestFallback(unittest.TestCase):
    """Tests for FallbackChain (sub-agent 1.4)."""

    def setUp(self):
        from src.auto_discovery.router import LLMRouter
        from src.auto_discovery.fallback import FallbackChain
        self.router = LLMRouter()
        self.fallback = FallbackChain(router=self.router, timeout=5)

    def test_import(self):
        from src.auto_discovery.fallback import FallbackChain, FallbackResult
        self.assertTrue(FallbackChain)
        self.assertTrue(FallbackResult)

    def test_fallback_result(self):
        from src.auto_discovery.fallback import FallbackResult
        r = FallbackResult(
            success=False, provider="", model="", response="",
            error="timeout", latency_ms=0.0, attempts=[],
        )
        self.assertFalse(r.success)
        self.assertEqual(r.error, "timeout")


class TestHealth(unittest.TestCase):
    """Tests for HealthChecker (sub-agent 1.5)."""

    def setUp(self):
        from src.auto_discovery.health import HealthChecker, HealthStatus
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.temp_dir, "health.json")
        self.checker = HealthChecker(interval_hours=24, state_file=self.state_file)
        self.HealthStatus = HealthStatus

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_import(self):
        from src.auto_discovery.health import HealthChecker, HealthStatus
        self.assertTrue(HealthChecker)
        self.assertTrue(HealthStatus)

    def test_health_status(self):
        h = self.HealthStatus(
            provider="test", model="m", status="ok", latency_ms=10.0,
            last_check=1000.0, consecutive_failures=0,
        )
        self.assertEqual(h.status, "ok")

    def test_save_load_state(self):
        self.checker._health["test"] = self.HealthStatus(
            provider="test", model="m", status="ok", latency_ms=10.0,
            last_check=1000.0, consecutive_failures=0,
        )
        self.checker._save_state()
        self.assertTrue(os.path.exists(self.state_file))
        self.checker._health = {}
        self.checker._load_state()
        self.assertIn("test", self.checker._health)


class TestConfigManager(unittest.TestCase):
    """Tests for ConfigManager (sub-agent 1.6)."""

    def setUp(self):
        from src.auto_discovery.config_manager import ConfigManager
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "config.yaml")
        self.manager = ConfigManager(config_path=self.config_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_import(self):
        from src.auto_discovery.config_manager import (ConfigManager, AutoDiscoveryConfig,
                                                       ProviderConfig, RoutingConfig)
        self.assertTrue(ConfigManager)
        self.assertTrue(AutoDiscoveryConfig)
        self.assertTrue(ProviderConfig)
        self.assertTrue(RoutingConfig)

    def test_get_default(self):
        config = self.manager.get_default()
        self.assertIsNotNone(config)
        self.assertGreater(len(config.llm_providers), 0)

    def test_load_returns_default_when_no_file(self):
        config = self.manager.load()
        self.assertIsNotNone(config)
        self.assertGreater(len(config.llm_providers), 0)

    def test_save_and_load(self):
        config = self.manager.get_default()
        self.manager.save(config)
        loaded = self.manager.load()
        self.assertEqual(len(loaded.llm_providers), len(config.llm_providers))

    def test_get_provider_config(self):
        pc = self.manager.get_provider_config("opencode_zen")
        self.assertIsNotNone(pc)
        self.assertEqual(pc.name, "opencode_zen")

    def test_get_routing(self):
        rc = self.manager.get_routing("medium")
        self.assertIsNotNone(rc)
        self.assertEqual(rc.complexity, "medium")


class TestCostTracker(unittest.TestCase):
    """Tests for CostTracker (sub-agent 1.7)."""

    def setUp(self):
        from src.auto_discovery.cost_tracker import CostTracker
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.temp_dir, "cost.json")
        self.tracker = CostTracker(state_file=self.state_file)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_import(self):
        from src.auto_discovery.cost_tracker import CostTracker, UsageRecord, ProviderStats
        self.assertTrue(CostTracker)
        self.assertTrue(UsageRecord)
        self.assertTrue(ProviderStats)

    def test_record_and_stats(self):
        self.tracker.record_usage("test_p", "test-m", 100, 50, 200.0, "simple")
        stats = self.tracker.get_provider_stats("test_p")
        self.assertIsNotNone(stats)
        self.assertEqual(stats.total_requests, 1)
        self.assertEqual(stats.total_tokens, 150)

    def test_get_all_stats(self):
        self.tracker.record_usage("p1", "m1", 100, 20, 100.0, "simple")
        self.tracker.record_usage("p2", "m2", 200, 30, 200.0, "medium")
        all_stats = self.tracker.get_all_stats()
        self.assertEqual(len(all_stats), 2)

    def test_persistence(self):
        self.tracker.record_usage("test_p", "test-m", 100, 50, 200.0, "simple")
        from src.auto_discovery.cost_tracker import CostTracker
        tracker2 = CostTracker(state_file=self.state_file)
        self.assertEqual(tracker2.get_provider_stats("test_p").total_requests, 1)

    def test_estimate_tokens(self):
        tokens = self.tracker.estimate_tokens("Hello world, this is a test")
        self.assertGreater(tokens, 0)

    def test_reset(self):
        self.tracker.record_usage("p1", "m1", 100, 20, 100.0, "simple")
        self.tracker.reset()
        self.assertEqual(self.tracker.get_total_tokens(), 0)


class TestIntegration(unittest.TestCase):
    """Tests for AutoDiscoveryEngine (sub-agent 1.10)."""

    def setUp(self):
        from src.auto_discovery.integration import AutoDiscoveryEngine
        self.temp_dir = tempfile.mkdtemp()
        self.engine = AutoDiscoveryEngine(
            data_dir=self.temp_dir,
            config_path=os.path.join(self.temp_dir, "config.yaml"),
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_import(self):
        from src.auto_discovery.integration import AutoDiscoveryEngine, DiscoveryState
        self.assertTrue(AutoDiscoveryEngine)
        self.assertTrue(DiscoveryState)

    def test_get_status(self):
        status = self.engine.get_status()
        self.assertIsNotNone(status)

    def test_initialize_and_route(self):
        """Initialize engine with mock provider data, then route a prompt."""
        providers_file = os.path.join(self.temp_dir, "providers_llm.json")
        mock_providers = [
            {
                "name": "opencode_zen", "display_name": "OpenCode Zen",
                "base_url": "https://opencode.ai/zen/v1",
                "api_key_env": "OPENCODE_ZEN_API_KEY",
                "models": ["mimo-v2.5-free"],
                "is_available": True, "latency_ms": 100.0,
                "error": "", "last_checked": "2026-01-01",
            },
            {
                "name": "groq", "display_name": "Groq",
                "base_url": "https://api.groq.com/openai/v1",
                "api_key_env": "GROQ_API_KEY",
                "models": ["llama-3.1-8b-instant"],
                "is_available": True, "latency_ms": 200.0,
                "error": "", "last_checked": "2026-01-01",
            },
        ]
        with open(providers_file, "w") as f:
            json.dump(mock_providers, f)

        data_file = os.path.join(self.temp_dir, "providers_data.json")
        with open(data_file, "w") as f:
            json.dump([], f)

        async def run():
            await self.engine.initialize()
            result = await self.engine.route("hello")
            return result
        result = asyncio.run(run())
        from src.auto_discovery.router import RouteResult
        self.assertIsInstance(result, RouteResult)
        self.assertTrue(result.provider)
        self.assertTrue(result.model)


if __name__ == "__main__":
    unittest.main()
