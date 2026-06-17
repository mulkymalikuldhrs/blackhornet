"""LLM Provider Scanner — sub-agent 1.1.

Scans known free LLM providers by sending a minimal probe request and
measuring availability and latency.  Persists results to JSON.
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
class ProviderInfo:
    """Scan result for a single LLM provider.

    Attributes:
        name: Internal provider identifier (e.g. ``"opencode_zen"``).
        display_name: Human-readable label (e.g. ``"OpenCode Zen"``).
        base_url: API endpoint URL.
        api_key_env: Environment variable name expected to hold the key.
        models: List of available free model identifiers.
        is_available: Whether the provider responded successfully.
        latency_ms: Response time in milliseconds.
        error: Error message if the provider is unavailable.
        last_checked: ISO-8601 timestamp of the last scan.
    """

    name: str
    display_name: str
    base_url: str
    api_key_env: str
    models: list[str]
    is_available: bool = False
    latency_ms: float = 0.0
    error: str = ""
    last_checked: str = ""


_PROVIDERS: list[dict[str, Any]] = [
    {
        "name": "opencode_zen",
        "display": "OpenCode Zen",
        "url": "https://opencode.ai/zen/v1",
        "env": "OPENCODE_ZEN_API_KEY",
        "models": [
            "mimo-v2.5-free",
            "deepseek-v4-flash-free",
            "qwen3.6-plus-free",
            "minimax-m3-free",
            "nemotron-3-ultra-free",
            "north-mini-code-free",
        ],
    },
    {
        "name": "nvidia",
        "display": "NVIDIA NIM",
        "url": "https://integrate.api.nvidia.com/v1",
        "env": "NVIDIA_API_KEY",
        "models": [
            "meta/llama-3.1-nemotron-70b-instruct",
            "mistralai/mistral-7b-instruct-v0.3",
        ],
    },
    {
        "name": "groq",
        "display": "Groq",
        "url": "https://api.groq.com/openai/v1",
        "env": "GROQ_API_KEY",
        "models": ["llama-3.1-8b-instant", "mixtral-8x7b-32768"],
    },
    {
        "name": "openrouter",
        "display": "OpenRouter",
        "url": "https://openrouter.ai/api/v1",
        "env": "OPENROUTER_API_KEY",
        "models": ["meta-llama/llama-3.1-8b-instruct"],
    },
    {
        "name": "ollama_cloud",
        "display": "Ollama Cloud",
        "url": "https://ollama.com/v1",
        "env": "OLLAMA_API_KEY",
        "models": ["llama3.1"],
    },
    {
        "name": "glm",
        "display": "GLM (z.ai)",
        "url": "https://api.z.ai/api/paas/v4",
        "env": "GLM_API_KEY",
        "models": ["glm-4"],
    },
]


class LLMScanner:
    """Scans known free LLM providers for availability and latency.

    Sends a minimal ``chat/completions`` probe to each provider, records
    response time, and persists the results to a JSON file.

    Args:
        data_dir: Directory for state files.  ``~`` is expanded.
    """

    def __init__(self, data_dir: str = "~/.bh/data") -> None:
        self._data_dir = os.path.expanduser(data_dir)
        os.makedirs(self._data_dir, exist_ok=True)

    # ── Public API ───────────────────────────────────────────────────────

    async def discover_all(self) -> list[ProviderInfo]:
        """Scan all known providers asynchronously.

        Delegates the synchronous scan to a thread so the event loop
        remains responsive during HTTP calls.

        Returns:
            List of :class:`ProviderInfo` results, one per provider.
        """
        logger.info("llm_scan_started", provider_count=len(_PROVIDERS))
        results = await asyncio.to_thread(self._discover_all_sync)
        logger.info(
            "llm_scan_completed",
            total=len(results),
            available=sum(1 for r in results if r.is_available),
        )
        return results

    def save(
        self,
        results: list[ProviderInfo],
        path: str = "providers_llm.json",
    ) -> None:
        """Persist scan results to a JSON file.

        Args:
            results: List of provider scan results.
            path: Filename relative to ``data_dir``.
        """
        filepath = os.path.join(self._data_dir, path)
        data: list[dict[str, Any]] = []
        for p in results:
            data.append({
                "name": p.name,
                "display_name": p.display_name,
                "base_url": p.base_url,
                "api_key_env": p.api_key_env,
                "models": p.models,
                "is_available": p.is_available,
                "latency_ms": p.latency_ms,
                "error": p.error,
                "last_checked": p.last_checked,
            })
        try:
            with open(filepath, "w") as f:
                json.dump({"providers": data}, f, indent=2)
            logger.debug("llm_scan_saved", path=filepath, count=len(data))
        except OSError as exc:
            logger.error("llm_scan_save_failed", path=filepath, error=str(exc))

    def load(self, path: str = "providers_llm.json") -> list[ProviderInfo]:
        """Load previously persisted scan results.

        Args:
            path: Filename relative to ``data_dir``.

        Returns:
            List of :class:`ProviderInfo` instances, or an empty list if
            the file does not exist or cannot be parsed.
        """
        filepath = os.path.join(self._data_dir, path)
        if not os.path.isfile(filepath):
            logger.debug("llm_scan_file_not_found", path=filepath)
            return []

        try:
            with open(filepath) as f:
                raw = json.load(f)
            entries = raw.get("providers", raw)
            results: list[ProviderInfo] = []
            for entry in entries:
                if isinstance(entry, dict):
                    results.append(ProviderInfo(**entry))
            logger.debug(
                "llm_scan_loaded",
                path=filepath,
                count=len(results),
            )
            return results
        except (json.JSONDecodeError, OSError, TypeError) as exc:
            logger.warning(
                "llm_scan_load_failed",
                path=filepath,
                error=str(exc),
            )
            return []

    # ── Synchronous scan ─────────────────────────────────────────────────

    def _discover_all_sync(self) -> list[ProviderInfo]:
        """Synchronous implementation of the full provider scan.

        Iterates over every entry in the known :data:`_PROVIDERS` list
        and calls :meth:`_test_provider` for each.

        Returns:
            List of :class:`ProviderInfo` results.
        """
        results: list[ProviderInfo] = []
        for entry in _PROVIDERS:
            info = self._test_provider(
                name=entry["name"],
                base_url=entry["url"],
                api_key_env=entry["env"],
                models=entry["models"],
            )
            info.display_name = entry["display"]
            results.append(info)
        return results

    def _test_provider(
        self,
        name: str,
        base_url: str,
        api_key_env: str,
        models: list[str],
    ) -> ProviderInfo:
        """Test a single provider with a minimal probe request.

        Sends a POST to ``{base_url}/chat/completions`` with a one-token
        ``"ping"`` message and measures the response time.

        Args:
            name: Provider identifier.
            base_url: API base URL.
            api_key_env: Environment variable for the API key.
            models: List of model names to register for this provider.

        Returns:
            A :class:`ProviderInfo` with the test outcome.
        """
        api_key = os.environ.get(api_key_env, "")
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        info = ProviderInfo(
            name=name,
            display_name=name,
            base_url=base_url,
            api_key_env=api_key_env,
            models=models,
            last_checked=now,
        )

        if not api_key:
            info.error = f"Missing env var: {api_key_env}"
            logger.debug("llm_skip_no_key", provider=name, env_var=api_key_env)
            return info

        model = models[0] if models else "unknown"
        url = f"{base_url.rstrip('/')}/chat/completions"
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
        }

        start = time.time()
        try:
            self._make_request(url, payload, api_key)
            elapsed_ms = (time.time() - start) * 1000.0
            info.is_available = True
            info.latency_ms = round(elapsed_ms, 1)
            logger.debug(
                "llm_provider_ok",
                provider=name,
                model=model,
                latency_ms=info.latency_ms,
            )
        except Exception as exc:
            elapsed_ms = (time.time() - start) * 1000.0
            info.latency_ms = round(elapsed_ms, 1)
            info.error = str(exc)
            logger.warning(
                "llm_provider_failed",
                provider=name,
                error=info.error,
                latency_ms=info.latency_ms,
            )

        return info

    # ── HTTP helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _make_request(
        url: str,
        payload: dict[str, Any],
        api_key: str,
        timeout: int = 10,
    ) -> dict[str, Any]:
        """Send a POST request via ``urllib``.

        Args:
            url: Full API endpoint URL.
            payload: JSON-serialisable request body.
            api_key: Bearer token for the ``Authorization`` header.
            timeout: Request timeout in seconds (default 10).

        Returns:
            Parsed JSON response as a dict.

        Raises:
            RuntimeError: On HTTP errors, connection failures, or
                malformed responses.
        """
        body = json.dumps(payload).encode("utf-8")
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")

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
