"""Data Provider Scanner — sub-agent 1.2.

Scans known free data APIs by sending a minimal GET probe and measuring
availability and latency.  Persists results to JSON.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

import logging

logger = logging.getLogger(__name__)


@dataclass
class DataSource:
    """Scan result for a single data API provider.

    Attributes:
        name: Internal data-source identifier (e.g. ``"yfinance"``).
        display_name: Human-readable label (e.g. ``"Yahoo Finance"``).
        base_url: API base URL.
        test_path: Endpoint path used for the availability probe.
        api_key_env: Environment variable name (empty string if no key
            is required).
        requires_key: Whether this source needs an API key.
        is_available: Whether the probe returned HTTP 200.
        latency_ms: Response time in milliseconds.
        error: Error message if the source is unavailable.
        last_checked: ISO-8601 timestamp of the last scan.
    """

    name: str
    display_name: str
    base_url: str
    test_path: str
    api_key_env: str
    requires_key: bool
    is_available: bool = False
    latency_ms: float = 0.0
    error: str = ""
    last_checked: str = ""


_DATA_SOURCES: list[dict[str, Any]] = [
    {
        "name": "yfinance",
        "display": "Yahoo Finance",
        "url": "https://query1.finance.yahoo.com",
        "test": "/v8/finance/chart/AAPL",
        "env": "",
        "key": False,
    },
    {
        "name": "coingecko",
        "display": "CoinGecko",
        "url": "https://api.coingecko.com",
        "test": "/api/v3/ping",
        "env": "",
        "key": False,
    },
    {
        "name": "binance",
        "display": "Binance",
        "url": "https://api.binance.com",
        "test": "/api/v3/ping",
        "env": "",
        "key": False,
    },
    {
        "name": "gdelt",
        "display": "GDELT Project",
        "url": "https://api.gdeltproject.org",
        "test": "/api/v2/doc/doc?query=test&mode=ArtList&maxrecords=1",
        "env": "",
        "key": False,
    },
    {
        "name": "worldbank",
        "display": "World Bank",
        "url": "https://api.worldbank.org",
        "test": "/v2/country/all/indicator/NY.GDP.MKTP.CD?format=json&per_page=1",
        "env": "",
        "key": False,
    },
    {
        "name": "fred",
        "display": "FRED",
        "url": "https://api.stlouisfed.org",
        "test": "/fred/series/observations?series_id=GDP&api_key=__test__&file_type=json",
        "env": "FRED_API_KEY",
        "key": True,
    },
    {
        "name": "alphavantage",
        "display": "Alpha Vantage",
        "url": "https://www.alphavantage.co",
        "test": "/query?function=TIME_SERIES_INTRADAY&symbol=AAPL&interval=5min&apikeys=demo",
        "env": "ALPHA_VANTAGE_API_KEY",
        "key": True,
    },
]


class DataScanner:
    """Scans known free data APIs for availability and latency.

    Sends a minimal GET request to each source's test endpoint, records
    response time, and persists the results to a JSON file.

    Args:
        data_dir: Directory for state files.  ``~`` is expanded.
    """

    def __init__(self, data_dir: str = "~/.bh/data") -> None:
        self._data_dir = os.path.expanduser(data_dir)
        os.makedirs(self._data_dir, exist_ok=True)

    # ── Public API ───────────────────────────────────────────────────────

    async def discover_all(self) -> list[DataSource]:
        """Scan all known data sources asynchronously.

        Delegates the synchronous scan to a thread so the event loop
        remains responsive during HTTP calls.

        Returns:
            List of :class:`DataSource` results, one per source.
        """
        logger.info("data_scan_started", source_count=len(_DATA_SOURCES))
        results = await asyncio.to_thread(self._discover_all_sync)
        logger.info(
            "data_scan_completed",
            total=len(results),
            available=sum(1 for r in results if r.is_available),
        )
        return results

    def save(
        self,
        results: list[DataSource],
        path: str = "providers_data.json",
    ) -> None:
        """Persist scan results to a JSON file.

        Args:
            results: List of data-source scan results.
            path: Filename relative to ``data_dir``.
        """
        filepath = os.path.join(self._data_dir, path)
        data: list[dict[str, Any]] = []
        for ds in results:
            data.append({
                "name": ds.name,
                "display_name": ds.display_name,
                "base_url": ds.base_url,
                "test_path": ds.test_path,
                "api_key_env": ds.api_key_env,
                "requires_key": ds.requires_key,
                "is_available": ds.is_available,
                "latency_ms": ds.latency_ms,
                "error": ds.error,
                "last_checked": ds.last_checked,
            })
        try:
            with open(filepath, "w") as f:
                json.dump({"sources": data}, f, indent=2)
            logger.debug("data_scan_saved", path=filepath, count=len(data))
        except OSError as exc:
            logger.error("data_scan_save_failed", path=filepath, error=str(exc))

    def load(self, path: str = "providers_data.json") -> list[DataSource]:
        """Load previously persisted scan results.

        Args:
            path: Filename relative to ``data_dir``.

        Returns:
            List of :class:`DataSource` instances, or an empty list if
            the file does not exist or cannot be parsed.
        """
        filepath = os.path.join(self._data_dir, path)
        if not os.path.isfile(filepath):
            logger.debug("data_scan_file_not_found", path=filepath)
            return []

        try:
            with open(filepath) as f:
                raw = json.load(f)
            entries = raw.get("sources", raw)
            results: list[DataSource] = []
            for entry in entries:
                if isinstance(entry, dict):
                    results.append(DataSource(**entry))
            logger.debug(
                "data_scan_loaded",
                path=filepath,
                count=len(results),
            )
            return results
        except (json.JSONDecodeError, OSError, TypeError) as exc:
            logger.warning(
                "data_scan_load_failed",
                path=filepath,
                error=str(exc),
            )
            return []

    # ── Synchronous scan ─────────────────────────────────────────────────

    def _discover_all_sync(self) -> list[DataSource]:
        """Synchronous implementation of the full data-source scan.

        Iterates over every entry in the known :data:`_DATA_SOURCES`
        list and calls :meth:`_test_source` for each.

        Returns:
            List of :class:`DataSource` results.
        """
        results: list[DataSource] = []
        for entry in _DATA_SOURCES:
            info = self._test_source(
                name=entry["name"],
                base_url=entry["url"],
                test_path=entry["test"],
                api_key_env=entry["env"],
                requires_key=entry["key"],
            )
            info.display_name = entry["display"]
            results.append(info)
        return results

    def _test_source(
        self,
        name: str,
        base_url: str,
        test_path: str,
        api_key_env: str,
        requires_key: bool,
    ) -> DataSource:
        """Test a single data source with a minimal GET probe.

        Sends a GET to ``{base_url}{test_path}`` and checks for an
        HTTP 200 response.

        Args:
            name: Data-source identifier.
            base_url: API base URL.
            test_path: Endpoint path for the probe.
            api_key_env: Environment variable for the API key (may be
                empty).
            requires_key: Whether this source requires an API key.

        Returns:
            A :class:`DataSource` with the test outcome.
        """
        api_key = os.environ.get(api_key_env, "")
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        info = DataSource(
            name=name,
            display_name=name,
            base_url=base_url,
            test_path=test_path,
            api_key_env=api_key_env,
            requires_key=requires_key,
            last_checked=now,
        )

        if requires_key and not api_key:
            info.error = f"Missing env var: {api_key_env}"
            logger.debug("data_skip_no_key", source=name, env_var=api_key_env)
            return info

        url = f"{base_url.rstrip('/')}/{test_path.lstrip('/')}"

        start = time.time()
        try:
            self._make_request(url, timeout=10)
            elapsed_ms = (time.time() - start) * 1000.0
            info.is_available = True
            info.latency_ms = round(elapsed_ms, 1)
            logger.debug(
                "data_source_ok",
                source=name,
                latency_ms=info.latency_ms,
            )
        except Exception as exc:
            elapsed_ms = (time.time() - start) * 1000.0
            info.latency_ms = round(elapsed_ms, 1)
            info.error = str(exc)
            logger.warning(
                "data_source_failed",
                source=name,
                error=info.error,
                latency_ms=info.latency_ms,
            )

        return info

    # ── HTTP helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _make_request(url: str, timeout: int = 10) -> dict[str, Any]:
        """Send a GET request via ``urllib``.

        Args:
            url: Full probe URL.
            timeout: Request timeout in seconds (default 10).

        Returns:
            Parsed JSON response as a dict.

        Raises:
            RuntimeError: On HTTP errors, connection failures, or
                malformed responses.
        """
        req = urllib.request.Request(url, method="GET")

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                pass
            raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Connection failed to {url}: {exc.reason}") from exc
        except (json.JSONDecodeError, OSError) as exc:
            raise RuntimeError(f"Invalid response from {url}: {exc}") from exc
