"""TradingView MCP integration for chart analysis."""

from __future__ import annotations

import json
import logging
import subprocess
from typing import Any, Dict, List, Optional

from src.agent_tools.base import MCPTool, RateLimitConfig

logger = logging.getLogger(__name__)


class TradingViewTool(MCPTool):
    """MCP tool that wraps a tradingview-mcp server for chart data & indicators."""

    def __init__(self, mcp_server_path: str = "tradingview-mcp") -> None:
        super().__init__()
        self.mcp_server_path = mcp_server_path
        self._server: Optional[subprocess.Popen] = None
        self._start_server()

    # ── MCPTool interface ──────────────────────────────────────────

    def name(self) -> str:
        return "tradingview.get_indicators"

    def category(self) -> str:
        return "tradingview"

    def autonomy_level(self) -> int:
        return 0  # read-only data

    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Ticker symbol, e.g. BTCUSD, AAPL",
                },
                "indicators": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of indicator names, e.g. RSI, MACD, SMA",
                },
            },
            "required": ["symbol", "indicators"],
        }

    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "indicators": {"type": "object"},
                "chart": {"type": "object"},
                "error": {"type": "string"},
            },
        }

    def rate_limit(self) -> RateLimitConfig:
        return RateLimitConfig(calls_per_minute=30, burst=5)

    # ── Server lifecycle ───────────────────────────────────────────

    def _start_server(self) -> None:
        try:
            self._server = subprocess.Popen(
                [self.mcp_server_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logger.info("TradingView MCP server started (pid=%d)", self._server.pid)
        except FileNotFoundError:
            logger.warning("tradingview-mcp not installed — using mock fallback")

    async def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        symbol = params.get("symbol", "")
        indicators = params.get("indicators", [])

        if not self._server:
            return {
                "symbol": symbol,
                "indicators": {},
                "chart": {},
                "error": "MCP server not available; install tradingview-mcp",
            }

        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_indicators",
                    "arguments": {"symbol": symbol, "indicators": indicators},
                },
                "id": 1,
            }
            self._server.stdin.write(json.dumps(payload) + "\n")
            self._server.stdin.flush()
            line = self._server.stdout.readline()
            result = json.loads(line).get("result", {})
            return {"symbol": symbol, "indicators": result, "chart": {}, "error": ""}
        except Exception as exc:
            logger.exception("TradingView MCP call failed")
            return {
                "symbol": symbol,
                "indicators": {},
                "chart": {},
                "error": str(exc),
            }
