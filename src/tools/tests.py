"""Tests for src/tools — MarketDataTool and ChartVisionTool."""

from __future__ import annotations

import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.tools.market_data_tool import MarketDataTool
from src.tools.chart_vision_tool import ChartVisionTool


class TestMarketDataToolValidation(unittest.TestCase):
    """MarketDataTool input validation and edge cases."""

    def setUp(self):
        self.tool = MarketDataTool()

    def test_invalid_interval_returns_error(self):
        result = json.loads(self.tool.get_ohlcv("XAUUSD", "invalid"))
        self.assertIn("error", result)
        self.assertIn("valid_intervals", result)

    def test_bars_too_low_returns_error(self):
        result = json.loads(self.tool.get_ohlcv("XAUUSD", "1h", 0))
        self.assertIn("error", result)

    def test_bars_too_high_returns_error(self):
        result = json.loads(self.tool.get_ohlcv("XAUUSD", "1h", 1001))
        self.assertIn("error", result)

    def test_valid_intervals_accepted(self):
        for interval in ["1m", "5m", "15m", "1h", "4h", "1d", "1w"]:
            result = json.loads(self.tool.get_ohlcv("EURUSD", interval, 1))
            self.assertIn("error", result, f"Expected error for {interval} (no yfinance)")
            self.assertNotEqual(result.get("error", ""), f"Invalid interval '{interval}'")

    def test_symbol_normalized_to_upper(self):
        result = json.loads(self.tool.get_ohlcv("eurusd", "1h", 1))
        self.assertEqual(result.get("symbol"), "EURUSD")

    def test_is_valid_ohlcv_rejects_nan(self):
        import math
        self.assertFalse(self.tool._is_valid_ohlcv(float("nan")))

    def test_is_valid_ohlcv_rejects_inf(self):
        self.assertFalse(self.tool._is_valid_ohlcv(float("inf")))

    def test_is_valid_ohlcv_rejects_negative(self):
        self.assertFalse(self.tool._is_valid_ohlcv(-1.0))

    def test_is_valid_ohlcv_accepts_zero(self):
        self.assertTrue(self.tool._is_valid_ohlcv(0.0))

    def test_is_valid_ohlcv_accepts_positive(self):
        self.assertTrue(self.tool._is_valid_ohlcv(1.23456))

    def test_economic_calendar_returns_not_configured(self):
        result = json.loads(self.tool.get_economic_calendar())
        self.assertEqual(result["status"], "not_configured")

    def test_cache_hits_on_repeated_call(self):
        self.tool.cache_duration = 300
        cache_key = "TEST:1h:1"
        self.tool.cache[cache_key] = ('{"cached": true}', 9999999999)
        result = self.tool.get_ohlcv("TEST", "1h", 1)
        self.assertEqual(json.loads(result), {"cached": True})


class TestMarketDataToolAPIErrorHandling(unittest.TestCase):
    """MarketDataTool behavior when API calls fail."""

    def setUp(self):
        self.tool = MarketDataTool()

    @patch("src.tools.market_data_tool.MarketDataTool.get_ohlcv")
    def test_api_exception_returns_json_error(self, mock_get):
        mock_get.return_value = json.dumps({"error": "API failure", "symbol": "XAUUSD"})
        result = json.loads(self.tool.get_ohlcv("XAUUSD"))
        self.assertIn("error", result)
        self.assertEqual(result["symbol"], "XAUUSD")

    @staticmethod
    def _make_mock_df(rows, empty=False):
        """Build a mock DataFrame-like object with .empty, .tail(), .iterrows()."""
        class MockRow:
            def __init__(self, d):
                self._d = d
            def __getitem__(self, key):
                return self._d[key]

        class MockDF:
            def __init__(self, rows, empty=False):
                self._rows = rows
                self.empty = empty
            def tail(self, n):
                return MockDF(self._rows[-n:]) if self._rows else self
            def __iter__(self):
                return iter(self._rows)
            def iterrows(self):
                for i, r in enumerate(self._rows):
                    yield f"2024-01-01 {i:02d}:00:00", MockRow(r)
            def __getitem__(self, key):
                vals = [r[key] for r in self._rows]
                class MockSeries:
                    def __init__(self, vals):
                        self._vals = vals
                    def iloc(self, idx):
                        return self._vals[idx]
                    def max(self):
                        return max(self._vals)
                    def min(self):
                        return min(self._vals)
                    def mean(self):
                        return sum(self._vals) / len(self._vals)
                return MockSeries(vals)

        return MockDF(rows, empty=empty)

    def _mock_yfinance(self, mock_df):
        mock_yf = MagicMock()
        mock_instance = MagicMock()
        mock_instance.history.return_value = mock_df
        mock_yf.Ticker.return_value = mock_instance
        return patch.dict("sys.modules", {"yfinance": mock_yf})

    def test_empty_dataframe_handling(self):
        mock_df = self._make_mock_df([], empty=True)
        with self._mock_yfinance(mock_df):
            result = json.loads(self.tool.get_ohlcv("XAUUSD", "1h", 50))
            self.assertIn("error", result)
            self.assertEqual(result["error"], "No data returned")


class TestMarketDataToolSummary(unittest.TestCase):
    """MarketDataTool summary computation correctness."""

    def setUp(self):
        self.tool = MarketDataTool()

    @staticmethod
    def _make_mock_df(rows):
        class MockRow:
            def __init__(self, d):
                self._d = d
            def __getitem__(self, key):
                return self._d[key]

        class MockDF:
            def __init__(self, rows):
                self._rows = rows
                self.empty = len(rows) == 0
            def tail(self, n):
                return MockDF(self._rows[-n:]) if self._rows else self
            def iterrows(self):
                for i, r in enumerate(self._rows):
                    yield f"2024-01-01 {i:02d}:00:00", MockRow(r)
            @property
            def iloc(self):
                class IlocHelper:
                    def __init__(self, rows):
                        self._rows = rows
                    def __getitem__(self, idx):
                        vals = [r[c] for r in self._rows for c in r]
                        return vals[0]
                return IlocHelper(self._rows)

        return MockDF(rows)

    def _mock_yfinance(self, mock_df):
        mock_yf = MagicMock()
        mock_instance = MagicMock()
        mock_instance.history.return_value = mock_df
        mock_yf.Ticker.return_value = mock_instance
        return patch.dict("sys.modules", {"yfinance": mock_yf})

    def test_avg_volume_is_always_numeric(self):
        self.tool.cache_duration = 0
        self.tool.cache.clear()
        rows = [
            {"Open": 150.0, "High": 155.0, "Low": 148.0, "Close": 152.0, "Volume": 1000},
            {"Open": 152.0, "High": 158.0, "Low": 151.0, "Close": 157.0, "Volume": 2000},
            {"Open": 157.0, "High": 160.0, "Low": 155.0, "Close": 158.0, "Volume": 1500},
        ]

        with self._mock_yfinance(self._make_mock_df(rows)):
            result = json.loads(self.tool.get_ohlcv("XAUUSD", "1h", 10))
            summary = result.get("summary", {})
            self.assertIsInstance(summary.get("avg_volume"), (int, float))

    def test_nan_rows_are_filtered(self):
        self.tool.cache_duration = 0
        self.tool.cache.clear()
        rows = [
            {"Open": 100.0, "High": 105.0, "Low": 99.0, "Close": 102.0, "Volume": 1000},
            {"Open": 101.0, "High": 106.0, "Low": 100.0, "Close": 103.0, "Volume": 2000},
            {"Open": float("nan"), "High": 107.0, "Low": 101.0, "Close": 104.0, "Volume": 3000},
            {"Open": 103.0, "High": 108.0, "Low": 102.0, "Close": float("nan"), "Volume": 4000},
            {"Open": 104.0, "High": 109.0, "Low": 103.0, "Close": 105.0, "Volume": 5000},
        ]

        with self._mock_yfinance(self._make_mock_df(rows)):

            result = json.loads(self.tool.get_ohlcv("XAUUSD", "1h", 5))
            self.assertEqual(result["bars"], 3)


class TestChartVisionTool(unittest.TestCase):
    """ChartVisionTool initialization and edge cases."""

    def test_init_reads_env_vars(self):
        with patch.dict(os.environ, {"VISION_PROVIDER": "test_prov", "OPENAI_VISION_KEY": "test_key"}):
            tool = ChartVisionTool()
            self.assertEqual(tool.vision_provider, "test_prov")
            self.assertEqual(tool.api_key, "test_key")

    def test_analyze_chart_missing_file(self):
        tool = ChartVisionTool()
        result = json.loads(tool.analyze_chart("/nonexistent/image.png"))
        self.assertIn("error", result)

    def test_analyze_chart_fallback_when_no_api_key(self):
        with patch.dict(os.environ, {"OPENAI_VISION_KEY": ""}):
            tool = ChartVisionTool()
            with patch("os.path.exists", return_value=True):
                result = json.loads(tool.analyze_chart("/fake/chart.png"))
                self.assertIn("checklist", result)
                self.assertEqual(result["analysis"], "Vision API not available. Manual analysis required.")


if __name__ == "__main__":
    unittest.main()
