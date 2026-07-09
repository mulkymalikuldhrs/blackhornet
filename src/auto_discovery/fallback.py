"""Fallback Chain — sub-agent 1.4.

Tries multiple LLM providers in sequence until one returns a successful
response.  Caches successful results briefly to avoid redundant calls.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Optional

from src.auto_discovery.router import ComplexityLevel, LLMRouter
import logging

logger = logging.getLogger(__name__)

_CACHE_TTL: float = 300.0  # 5 minutes


@dataclass
class FallbackResult:
    """Result of a fallback chain execution.

    Attributes:
        success: Whether a provider returned a successful response.
        provider: Name of the provider that succeeded (empty if all failed).
        model: Model that produced the response.
        response: The LLM response content.
        error: Error message if all attempts failed.
        latency_ms: Response time in milliseconds for the successful call.
        attempts: Ordered list of provider names that were tried.
    """

    success: bool = False
    provider: str = ""
    model: str = ""
    response: str = ""
    error: str = ""
    latency_ms: float = 0.0
    attempts: list[str] = field(default_factory=list)


class FallbackChain:
    """Execute LLM requests with automatic fallback across providers.

    Args:
        router: An :class:`LLMRouter` instance for provider resolution.
        timeout: Per-provider request timeout in seconds (default 30).
    """

    def __init__(self, router: LLMRouter, timeout: int = 30) -> None:
        self._router = router
        self._timeout = timeout
        self._cache: dict[str, tuple[float, FallbackResult]] = {}

    # ── Public API ───────────────────────────────────────────────────────

    def execute(
        self,
        prompt: str,
        complexity: Optional[ComplexityLevel] = None,
    ) -> FallbackResult:
        """Execute a prompt with automatic complexity-based fallback.

        Args:
            prompt: The user input prompt.
            complexity: Optional explicit complexity level.  When ``None``,
                the router classifies the prompt automatically.

        Returns:
            A :class:`FallbackResult` with the response or error.
        """
        # Check cache
        cached = self._check_cache(prompt)
        if cached is not None:
            logger.debug("cache_hit", prompt_preview=prompt[:60])
            return cached

        route = self._router.route(prompt)
        chain: list[dict[str, str]] = []

        if complexity is not None:
            chain = self._router._config.complexity_map.get(
                complexity.value,
                [],
            )
        else:
            classified = self._router.classify_complexity(prompt)
            chain = self._router._config.complexity_map.get(
                classified.value,
                [],
            )

        result = self._try_chain(prompt, chain)
        self._set_cache(prompt, result)
        return result

    def execute_with_chain(
        self,
        prompt: str,
        chain: list[str],
    ) -> FallbackResult:
        """Execute a prompt using an explicit provider chain.

        Args:
            prompt: The user input prompt.
            chain: Ordered list of provider names to attempt.

        Returns:
            A :class:`FallbackResult` with the response or error.
        """
        cached = self._check_cache(prompt)
        if cached is not None:
            logger.debug("cache_hit", prompt_preview=prompt[:60])
            return cached

        route = self._router.route(prompt)
        chain_entries: list[dict[str, str]] = [
            {"provider": name, "model": ""}
            for name in chain
        ]

        result = self._try_chain(prompt, chain_entries)
        self._set_cache(prompt, result)
        return result

    # ── Provider execution ───────────────────────────────────────────────

    def _try_chain(
        self,
        prompt: str,
        chain: list[dict[str, str]],
    ) -> FallbackResult:
        """Walk the provider chain until one succeeds."""
        attempts: list[str] = []

        for entry in chain:
            provider_name = entry.get("provider", "")
            model = entry.get("model", "")
            attempts.append(provider_name)

            try:
                content, latency = self._call_provider(provider_name, model, prompt)
                logger.info(
                    "provider_success",
                    provider=provider_name,
                    model=model,
                    latency_ms=round(latency * 1000, 1),
                )
                return FallbackResult(
                    success=True,
                    provider=provider_name,
                    model=model,
                    response=content,
                    latency_ms=round(latency * 1000, 1),
                    attempts=attempts,
                )
            except Exception as exc:
                logger.warning(
                    "provider_failed",
                    provider=provider_name,
                    model=model,
                    error=str(exc),
                )

        return FallbackResult(
            success=False,
            error=f"All providers failed: {', '.join(attempts)}",
            attempts=attempts,
        )

    def _call_provider(
        self,
        provider_name: str,
        model: str,
        prompt: str,
    ) -> tuple[str, float]:
        """Call a single provider and return (content, latency_seconds).

        Args:
            provider_name: Name of the provider to call.
            model: Model identifier to use.
            prompt: The user input prompt.

        Returns:
            Tuple of (response_text, latency_in_seconds).

        Raises:
            RuntimeError: If the provider is not configured or the API
                call fails.
        """
        provider_cfg = self._router._providers.get(provider_name)
        if provider_cfg is None:
            raise RuntimeError(f"Provider '{provider_name}' is not configured")

        base_url = provider_cfg.get("base_url", "")
        api_key_env = provider_cfg.get("api_key_env", "")
        api_key = ""

        import os
        api_key = os.environ.get(api_key_env, "")

        if not api_key:
            raise RuntimeError(
                f"No API key found for '{provider_name}' "
                f"(env var: {api_key_env})"
            )

        start = time.time()

        response_data = self._make_llm_request(
            url=base_url,
            api_key=api_key,
            model=model,
            prompt=prompt,
        )

        elapsed = time.time() - start

        # Parse OpenAI-compatible response
        content = ""
        try:
            choices = response_data.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                content = message.get("content", "") or ""
        except (IndexError, KeyError, TypeError) as exc:
            raise RuntimeError(
                f"Failed to parse response from '{provider_name}': {exc}"
            ) from exc

        if not content:
            raise RuntimeError(
                f"Empty response from '{provider_name}' (model: {model})"
            )

        return content, elapsed

    @staticmethod
    def _make_llm_request(
        url: str,
        api_key: str,
        model: str,
        prompt: str,
    ) -> dict[str, Any]:
        """Send a chat completion request via urllib.

        Uses the OpenAI-compatible chat completions format.

        Args:
            url: Full API endpoint URL.
            api_key: Bearer token for authorization.
            model: Model identifier.
            prompt: User message content.

        Returns:
            Parsed JSON response dict.

        Raises:
            RuntimeError: On HTTP or connection errors.
        """
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 4096,
        }

        body = json.dumps(payload).encode("utf-8")
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        req = urllib.request.Request(
            url,
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                pass
            raise RuntimeError(
                f"HTTP {exc.code} from {url}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Connection failed to {url}: {exc.reason}"
            ) from exc
        except (json.JSONDecodeError, OSError) as exc:
            raise RuntimeError(
                f"Invalid response from {url}: {exc}"
            ) from exc

    # ── Cache helpers ────────────────────────────────────────────────────

    def _check_cache(self, prompt: str) -> Optional[FallbackResult]:
        """Return cached result if it exists and is still fresh."""
        entry = self._cache.get(prompt)
        if entry is None:
            return None
        timestamp, result = entry
        if time.monotonic() - timestamp < _CACHE_TTL:
            return result
        del self._cache[prompt]
        return None

    def _set_cache(self, prompt: str, result: FallbackResult) -> None:
        """Store a successful result in the cache."""
        if result.success:
            self._cache[prompt] = (time.monotonic(), result)

    def clear_cache(self) -> None:
        """Clear all cached responses."""
        self._cache.clear()
        logger.debug("cache_cleared")
