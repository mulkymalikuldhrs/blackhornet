"""Health Check Cron — sub-agent 1.5.

Periodically checks the health of all configured LLM providers by sending
minimal API requests and measuring latency.  Persists state to JSON.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Optional

import logging

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Current health snapshot for a single provider.

    Attributes:
        provider: Provider name.
        model: Model used for the health probe.
        status: One of ``"ok"``, ``"degraded"``, or ``"down"``.
        latency_ms: Response time in milliseconds for the last check.
        last_check: Unix timestamp of the last health check.
        consecutive_failures: Count of sequential failures (resets on
            success, triggers ``"down"`` at 3).
    """

    provider: str
    model: str
    status: str = "ok"
    latency_ms: float = 0.0
    last_check: float = 0.0
    consecutive_failures: int = 0


# ── Thresholds ──────────────────────────────────────────────────────────

_OK_LATENCY_MS: float = 2000.0
_DEGRADED_LATENCY_MS: float = 5000.0
_DOWN_THRESHOLD: int = 3


class HealthChecker:
    """Periodically checks provider health in a background async task.

    Args:
        interval_hours: How often to run the full health check (default 6).
        state_file: Path to the JSON file for persisting health state.
        providers_file: Path to the provider configuration JSON (same
            format as :class:`LLMRouter` uses).
    """

    def __init__(
        self,
        interval_hours: float = 6.0,
        state_file: str = "provider_health.json",
        providers_file: str = "providers_llm.json",
    ) -> None:
        self._interval = interval_hours * 3600.0
        self._state_file = state_file
        self._providers_file = providers_file
        self._running = False
        self._task: Optional[asyncio.Task[None]] = None
        self._health: dict[str, HealthStatus] = {}
        self._providers: dict[str, Any] = {}
        self._load_state()
        self._load_providers()

    # ── Lifecycle ────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the background health check loop.

        Creates an asyncio task that runs :meth:`_health_loop`.
        Safe to call multiple times (no-op if already running).
        """
        if self._running:
            logger.debug("health_checker_already_running")
            return
        self._running = True
        self._task = asyncio.create_task(self._health_loop())
        logger.info("health_checker_started", interval_hours=self._interval / 3600.0)

    async def stop(self) -> None:
        """Stop the background health check loop."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._save_state()
        logger.info("health_checker_stopped")

    # ── Health checks ────────────────────────────────────────────────────

    def check_all(self) -> dict[str, HealthStatus]:
        """Check health of every configured provider.

        Returns:
            Dict mapping provider name to its :class:`HealthStatus`.
        """
        for name, config in self._providers.items():
            self.check_provider(name, config)
        self._save_state()
        return dict(self._health)

    def check_provider(
        self,
        name: str,
        config: dict[str, Any],
    ) -> HealthStatus:
        """Check the health of a single provider.

        Sends a minimal probe request and measures latency.  Updates the
        internal health state.

        Args:
            name: Provider name.
            config: Provider configuration dict (must have ``base_url``
                and ``api_key_env`` keys).

        Returns:
            The updated :class:`HealthStatus`.
        """
        base_url = config.get("base_url", "")
        api_key_env = config.get("api_key_env", "")
        api_key = os.environ.get(api_key_env, "")

        models = config.get("models", {})
        model = next(iter(models)) if isinstance(models, dict) else ""

        status = HealthStatus(
            provider=name,
            model=model,
        )

        if not api_key:
            status.status = "down"
            status.consecutive_failures = self._get_failures(name) + 1
            logger.warning("health_no_api_key", provider=name, env_var=api_key_env)
            self._health[name] = status
            return status

        start = time.time()
        try:
            self._probe_provider(base_url, api_key, model)
            elapsed_ms = (time.time() - start) * 1000.0

            status.latency_ms = round(elapsed_ms, 1)
            status.last_check = time.time()
            status.consecutive_failures = 0

            if elapsed_ms < _OK_LATENCY_MS:
                status.status = "ok"
            elif elapsed_ms < _DEGRADED_LATENCY_MS:
                status.status = "degraded"
            else:
                status.status = "down"

            if status.status != "ok":
                logger.warning(
                    "health_degraded",
                    provider=name,
                    latency_ms=status.latency_ms,
                    status=status.status,
                )
            else:
                logger.debug(
                    "health_ok",
                    provider=name,
                    latency_ms=status.latency_ms,
                )

        except Exception as exc:
            elapsed_ms = (time.time() - start) * 1000.0
            failures = self._get_failures(name) + 1

            status.latency_ms = round(elapsed_ms, 1)
            status.last_check = time.time()
            status.consecutive_failures = failures

            if failures >= _DOWN_THRESHOLD:
                status.status = "down"
            else:
                status.status = "degraded"

            logger.warning(
                "health_failed",
                provider=name,
                error=str(exc),
                consecutive_failures=failures,
            )

        self._health[name] = status
        return status

    # ── Queries ──────────────────────────────────────────────────────────

    def get_health(self, name: str) -> Optional[HealthStatus]:
        """Get the cached health status for a provider.

        Args:
            name: Provider name.

        Returns:
            The :class:`HealthStatus` if known, otherwise ``None``.
        """
        return self._health.get(name)

    def get_all_healthy(self) -> list[str]:
        """Return names of all providers currently marked as ``"ok"``.

        Returns:
            List of healthy provider names.
        """
        return [
            name
            for name, hs in self._health.items()
            if hs.status == "ok"
        ]

    # ── Internal background loop ─────────────────────────────────────────

    async def _health_loop(self) -> None:
        """Main health check loop — runs in a background task."""
        while self._running:
            try:
                self.check_all()
            except Exception as exc:
                logger.error("health_loop_error", error=str(exc))

            await asyncio.sleep(self._interval)

    # ── Probe request ────────────────────────────────────────────────────

    @staticmethod
    def _probe_provider(
        url: str,
        api_key: str,
        model: str,
    ) -> None:
        """Send a minimal probe request to verify provider availability.

        Args:
            url: API endpoint URL.
            api_key: Bearer token.
            model: Model identifier.

        Raises:
            RuntimeError: If the probe fails.
        """
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
            "temperature": 0.0,
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
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()  # discard payload; we only care that it succeeded
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                pass
            raise RuntimeError(
                f"HTTP {exc.code} from {url}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Connection failed to {url}: {exc.reason}"
            ) from exc
        except OSError as exc:
            raise RuntimeError(
                f"Network error for {url}: {exc}"
            ) from exc

    # ── Persistence helpers ──────────────────────────────────────────────

    def _get_failures(self, name: str) -> int:
        """Get the current consecutive failure count for a provider."""
        existing = self._health.get(name)
        return existing.consecutive_failures if existing else 0

    def _load_state(self) -> None:
        """Load persisted health state from the JSON file."""
        if not os.path.isfile(self._state_file):
            return
        try:
            with open(self._state_file) as f:
                data = json.load(f)
            for entry in data.get("health", []):
                hs = HealthStatus(**entry)
                self._health[hs.provider] = hs
            logger.info(
                "health_state_loaded",
                path=self._state_file,
                count=len(self._health),
            )
        except (json.JSONDecodeError, OSError, TypeError) as exc:
            logger.warning(
                "health_state_load_failed",
                path=self._state_file,
                error=str(exc),
            )

    def _save_state(self) -> None:
        """Persist current health state to the JSON file."""
        try:
            data: list[dict[str, Any]] = []
            for hs in self._health.values():
                data.append({
                    "provider": hs.provider,
                    "model": hs.model,
                    "status": hs.status,
                    "latency_ms": hs.latency_ms,
                    "last_check": hs.last_check,
                    "consecutive_failures": hs.consecutive_failures,
                })
            with open(self._state_file, "w") as f:
                json.dump({"health": data}, f, indent=2)
            logger.debug("health_state_saved", path=self._state_file)
        except OSError as exc:
            logger.error(
                "health_state_save_failed",
                path=self._state_file,
                error=str(exc),
            )

    def _load_providers(self) -> None:
        """Load provider configurations for health checking."""
        if not os.path.isfile(self._providers_file):
            logger.debug("no_providers_file", path=self._providers_file)
            return
        try:
            with open(self._providers_file) as f:
                data = json.load(f)
            self._providers = data.get("providers", data)
            logger.info(
                "providers_loaded_for_health",
                count=len(self._providers),
            )
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "providers_load_failed_for_health",
                path=self._providers_file,
                error=str(exc),
            )
