#!/usr/bin/env python3
"""
Market Data Agent (L1 - Data Layer)
Fetches OHLCV, economic calendar, market overview
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger("blackhornet.MarketData")


class MarketDataTool:
    """L1 Agent: Market Data - Real-time and historical market data"""

    PROVIDERS = {
        "yfinance": True,  # Always available (free)
        "mt5": False,      # Requires MT5 terminal
        "oanda": False,    # Requires OANDA API key
        "binance": False,  # Requires Binance API key
    }

    # Symbol mapping for different providers
    SYMBOL_MAP = {
        "XAUUSD": {"yfinance": "GC=F", "mt5": "XAUUSD", "binance": "XAUUSDT"},
        "EURUSD": {"yfinance": "EURUSD=X", "mt5": "EURUSD", "binance": "EURUSDT"},
        "GBPUSD": {"yfinance": "GBPUSD=X", "mt5": "GBPUSD", "binance": "GBPUSDT"},
        "USDJPY": {"yfinance": "USDJPY=X", "mt5": "USDJPY", "binance": "USDJPY"},
        "BTCUSDT": {"yfinance": "BTC-USD", "mt5": None, "binance": "BTCUSDT"},
        "SHIB": {"yfinance": "SHIB-USD", "mt5": None, "binance": "SHIBUSDT"},
        "TRX": {"yfinance": "TRX-USD", "mt5": None, "binance": "TRXUSDT"},
    }

    INTERVAL_MAP = {
        "1m": {"yfinance": "1m", "mt5": "M1"},
        "5m": {"yfinance": "5m", "mt5": "M5"},
        "15m": {"yfinance": "15m", "mt5": "M15"},
        "1h": {"yfinance": "1h", "mt5": "H1"},
        "4h": {"yfinance": "4h", "mt5": "H4"},
        "1d": {"yfinance": "1d", "mt5": "D1"},
        "1w": {"yfinance": "1wk", "mt5": "W1"},
    }

    VALID_INTERVALS = {"1m", "5m", "15m", "1h", "4h", "1d", "1w"}

    def __init__(self, cache_duration: int = 60):
        self.cache: Dict[str, tuple] = {}
        self.cache_duration = cache_duration

    @staticmethod
    def _is_valid_ohlcv(val: float) -> bool:
        import math
        return not (math.isnan(val) or math.isinf(val) or val < 0)

    def get_ohlcv(self, symbol: str = "XAUUSD", interval: str = "1h",
                  bars: int = 50) -> str:
        """
        Fetch OHLCV data for a symbol.

        Args:
            symbol: Trading symbol (XAUUSD, EURUSD, BTCUSDT, etc.)
            interval: Timeframe (1m, 5m, 15m, 1h, 4h, 1d, 1w)
            bars: Number of candles to fetch

        Returns:
            JSON string with OHLCV data
        """
        symbol = symbol.upper()
        interval = interval.lower()

        if interval not in self.VALID_INTERVALS:
            return json.dumps({
                "error": f"Invalid interval '{interval}'",
                "valid_intervals": sorted(self.VALID_INTERVALS),
                "symbol": symbol
            })

        if bars < 1 or bars > 1000:
            return json.dumps({
                "error": "bars must be between 1 and 1000",
                "symbol": symbol
            })

        cache_key = f"{symbol}:{interval}:{bars}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            from time import time
            data, ts = cached
            if time() - ts < self.cache_duration:
                return data

        try:
            import yfinance as yf
            import math

            yf_symbol = self.SYMBOL_MAP.get(symbol, {}).get("yfinance", symbol)
            yf_interval = self.INTERVAL_MAP.get(interval, {}).get("yfinance", "1h")

            # yfinance has limits on intraday data range
            period = "60d"
            if interval in ["1m"]:
                period = "7d"
            elif interval in ["5m", "15m"]:
                period = "60d"
            elif interval in ["1h", "4h"]:
                period = "730d"

            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(period=period, interval=yf_interval)

            if df.empty:
                return json.dumps({
                    "symbol": symbol,
                    "error": "No data returned",
                    "suggestion": f"Check if {symbol} is a valid symbol"
                })

            # Take last N bars
            df = df.tail(bars)

            data_rows = []
            for idx, row in df.iterrows():
                open_val = float(row["Open"])
                high_val = float(row["High"])
                low_val = float(row["Low"])
                close_val = float(row["Close"])
                vol_val = float(row["Volume"])

                if not all(self._is_valid_ohlcv(v) for v in [open_val, high_val, low_val, close_val]):
                    continue

                data_rows.append({
                    "time": str(idx),
                    "open": round(open_val, 5),
                    "high": round(high_val, 5),
                    "low": round(low_val, 5),
                    "close": round(close_val, 5),
                    "volume": int(vol_val) if vol_val > 0 else 0
                })

            if not data_rows:
                return json.dumps({
                    "symbol": symbol,
                    "error": "All data rows contain invalid OHLCV values",
                    "suggestion": "Check data integrity for this symbol"
                })

            closes = [r["close"] for r in data_rows]
            highs = [r["high"] for r in data_rows]
            lows = [r["low"] for r in data_rows]
            volumes = [r["volume"] for r in data_rows]
            avg_vol = round(sum(volumes) / len(volumes), 0) if volumes else 0

            result = {
                "symbol": symbol,
                "interval": interval,
                "bars": len(data_rows),
                "last_update": data_rows[-1]["time"],
                "data": data_rows,
                "summary": {
                    "latest_close": closes[-1],
                    "period_high": max(highs),
                    "period_low": min(lows),
                    "avg_volume": avg_vol
                }
            }

            result_json = json.dumps(result, indent=2)

            from time import time
            self.cache[cache_key] = (result_json, time())
            return result_json

        except ImportError:
            return json.dumps({
                "error": "yfinance not installed",
                "install": "pip install yfinance",
                "symbol": symbol
            })
        except Exception as e:
            return json.dumps({"error": str(e), "symbol": symbol})

    def get_market_overview(self) -> str:
        """Get overview of major markets"""
        try:
            import yfinance as yf

            symbols = {
                "XAUUSD": "GC=F",
                "EURUSD": "EURUSD=X",
                "SPX500": "^GSPC",
                "US30": "^DJI",
                "NAS100": "^IXIC",
                "BTCUSDT": "BTC-USD",
                "VIX": "^VIX",
                "US10Y": "^TNX",
                "DXY": "DX-Y.NYB"
            }

            overview = {}
            for name, yf_sym in symbols.items():
                try:
                    ticker = yf.Ticker(yf_sym)
                    hist = ticker.history(period="2d")
                    if not hist.empty:
                        close = float(hist["Close"].iloc[-1])
                        prev_close = float(hist["Close"].iloc[0]) if len(hist) > 1 else close
                        change = ((close - prev_close) / prev_close) * 100
                        overview[name] = {
                            "price": round(close, 2),
                            "change_pct": round(change, 2),
                            "direction": "UP" if change > 0 else "DOWN" if change < 0 else "FLAT"
                        }
                except Exception:
                    overview[name] = {"price": "N/A", "change_pct": "N/A", "direction": "N/A"}

            return json.dumps({
                "timestamp": datetime.now().isoformat(),
                "markets": overview
            }, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)})

    def get_economic_calendar(self) -> str:
        """Get upcoming economic events - requires external API integration"""
        return json.dumps({
            "status": "not_configured",
            "message": "Economic calendar requires additional API integration",
            "suggested_apis": ["ForexFactory", "Investing.com", "FRED"],
            "implementation": "Configure an economic calendar API in config/blackhornet.yaml to enable live data"
        })
