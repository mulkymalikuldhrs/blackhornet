"""Auto-Discovery Integration — sub-agent 1.10.

Wires together all Auto-Discovery sub-agents into a unified service:

- LLMScanner (1.1)
- DataScanner (1.2)
- LLMRouter (1.3)
- FallbackChain (1.4)
- HealthChecker (1.5)
- ConfigManager (1.6)
- CostTracker (1.7)
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from src.auto_discovery.config_manager import ConfigManager
from src.auto_discovery.cost_tracker import CostTracker
from src.auto_discovery.data_scanner import DataScanner
from src.auto_discovery.fallback import FallbackChain, FallbackResult
from src.auto_discovery.health import HealthChecker, HealthStatus
from src.auto_discovery.llm_scanner import LLMScanner, ProviderInfo
from src.auto_discovery.router import LLMRouter, RouteResult
import logging

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryState:
    """Overall state of the auto-discovery engine.

    Attributes:
        last_full_scan: ISO timestamp of the most recent full scan.
        llm_providers_found: Number of LLM providers discovered.
        data_sources_found: Number of data sources discovered.
        healthy_providers: Count of providers passing health checks.
        total_providers: Total number of configured providers.
        router_ready: Whether the router has been initialised with provider data.
        health_check_running: Whether the background health checker is active.
        errors: List of non-fatal error messages collected during operation.
    """

    last_full_scan: str = ""
    llm_providers_found: int = 0
    data_sources_found: int = 0
    healthy_providers: int = 0
    total_providers: int = 0
    router_ready: bool = False
    health_check_running: bool = False
    errors: list[str] = field(default_factory=list)


class AutoDiscoveryEngine:
    """Unified interface for the entire Auto-Discovery Engine.

    Wires together all sub-agents (LLMScanner, DataScanner, LLMRouter,
    FallbackChain, HealthChecker, ConfigManager, CostTracker) and exposes
    a single high-level API for scanning, routing, execution, and health
    management.

    Args:
        data_dir: Directory for persistent state files.  The tilde character
            is expanded to the user's home directory.
        config_path: Path to the YAML configuration file.  The tilde
            character is expanded to the user's home directory.
    """

    def __init__(
        self,
        data_dir: str = "~/.bh/data",
        config_path: str = "~/.bh/config.yaml",
    ) -> None:
        self._data_dir = os.path.expanduser(data_dir)
        os.makedirs(self._data_dir, exist_ok=True)

        providers_file = os.path.join(self._data_dir, "providers_llm.json")
        health_state = os.path.join(self._data_dir, "provider_health.json")
        cost_state = os.path.join(self._data_dir, "cost_tracker.json")

        # --- Sub-agent initialisation ---
        self.config = ConfigManager(config_path=config_path)
        self.scanner_llm = LLMScanner(data_dir=self._data_dir)
        self.scanner_data = DataScanner(data_dir=self._data_dir)
        self.router = LLMRouter(providers_file=providers_file)
        self.fallback = FallbackChain(router=self.router)
        self.health = HealthChecker(
            interval_hours=6.0,
            state_file=health_state,
            providers_file=providers_file,
        )
        self.cost_tracker = CostTracker(state_file=cost_state)

        # --- Internal state ---
        self._state: DiscoveryState = self._load_state()

    # ------------------------------------------------------------------
    # Initialisation & lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Run initial discovery if no data exists and start health checks.

        Checks whether previous scan data exists on disk.  If not, runs a
        full scan immediately.  Starts the background health checker so
        provider availability is continuously monitored.
        """
        providers_file = os.path.join(self._data_dir, "providers_llm.json")
        data_file = os.path.join(self._data_dir, "providers_data.json")

        if not os.path.isfile(providers_file) or not os.path.isfile(data_file):
            logger.info("no_previous_data_found_running_initial_scan")
            await self.full_scan()
        else:
            logger.info("previous_data_found_loading_cached_state")
            self._sync_router_from_file()

        self.health.start()
        self._state.health_check_running = True
        self._save_state()

        logger.info(
            "engine_initialised",
            llm_providers=self._state.llm_providers_found,
            data_sources=self._state.data_sources_found,
        )

    async def shutdown(self) -> None:
        """Gracefully shut down the engine.

        Stops the background health checker and persists the current
        engine state to disk.

        Safe to call multiple times.  Does not raise.
        """
        logger.info("engine_shutdown_starting")
        try:
            await self.health.stop()
        except Exception as exc:
            logger.warning("health_stop_failed_during_shutdown", error=str(exc))
        self._state.health_check_running = False
        self._save_state()
        logger.info("engine_shutdown_complete")

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    async def full_scan(self) -> None:
        """Discover all LLM providers and data sources.

        Performs a fresh scan of every known LLM provider and data API,
        persists the results to JSON files, updates the router's provider
        data, and refreshes the internal :class:`DiscoveryState`.

        All errors are captured and reported in the state rather than
        propagated as exceptions.
        """
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        errors: list[str] = []

        # 1. Scan LLM providers
        try:
            llm_results = await self.scanner_llm.discover_all()
            self.scanner_llm.save(llm_results)
            self._state.llm_providers_found = len(llm_results)
            self._state.total_providers = len(llm_results)
            self._state.healthy_providers = sum(
                1 for r in llm_results if r.is_available
            )
            logger.info(
                "llm_scan_integrated",
                found=len(llm_results),
                healthy=self._state.healthy_providers,
            )
        except Exception as exc:
            msg = f"LLM scan failed: {exc}"
            logger.error(msg)
            errors.append(msg)

        # 2. Scan data sources
        try:
            data_results = await self.scanner_data.discover_all()
            self.scanner_data.save(data_results)
            self._state.data_sources_found = len(data_results)
            logger.info("data_scan_integrated", found=len(data_results))
        except Exception as exc:
            msg = f"Data source scan failed: {exc}"
            logger.error(msg)
            errors.append(msg)

        # 3. Update router with fresh provider data
        try:
            self._sync_router_from_file()
            self._state.router_ready = True
        except Exception as exc:
            msg = f"Router update failed: {exc}"
            logger.error(msg)
            errors.append(msg)

        # 4. Finalise state
        self._state.last_full_scan = now
        if errors:
            self._state.errors = errors
        self._save_state()

        logger.info(
            "full_scan_complete",
            llm_providers=self._state.llm_providers_found,
            data_sources=self._state.data_sources_found,
            healthy=self._state.healthy_providers,
            errors=len(errors),
        )

    # ------------------------------------------------------------------
    # Routing & execution
    # ------------------------------------------------------------------

    async def route(self, prompt: str) -> RouteResult:
        """Classify and route a prompt to the best available provider.

        Args:
            prompt: The user's input prompt.

        Returns:
            A :class:`RouteResult` with the selected provider, model,
            endpoint, and API key.

        Raises:
            RuntimeError: If the router has no provider data loaded.
        """
        if not self._state.router_ready:
            raise RuntimeError(
                "Router is not ready — call full_scan() or initialize() first"
            )
        return self.router.route(prompt)

    async def execute(self, prompt: str) -> FallbackResult:
        """Route a prompt and execute it with automatic fallback.

        Classifies the prompt, routes to the best available provider,
        executes via the fallback chain, records usage metrics via the
        cost tracker, and returns the result.

        Never raises — all errors are captured in the returned
        :class:`FallbackResult`.

        Args:
            prompt: The user's input prompt.

        Returns:
            A :class:`FallbackResult` containing the response or error
            details, along with the list of attempted providers.
        """
        if not self._state.router_ready:
            return FallbackResult(
                success=False,
                error="Router is not ready — call full_scan() or initialize() first",
            )

        try:
            # 1. Classify complexity
            complexity = self.router.classify_complexity(prompt)

            # 2. Execute with automatic fallback chain
            result = await asyncio.to_thread(self.fallback.execute, prompt)

            # 3. Record usage via CostTracker
            if result.success:
                prompt_tokens = self.cost_tracker.estimate_tokens(prompt)
                completion_tokens = self.cost_tracker.estimate_tokens(result.response)
                self.cost_tracker.record_usage(
                    provider=result.provider,
                    model=result.model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    latency_ms=result.latency_ms,
                    complexity=complexity.value,
                )

            return result

        except Exception as exc:
            msg = f"Execution failed: {exc}"
            logger.error(msg)
            return FallbackResult(
                success=False,
                error=msg,
            )

    # ------------------------------------------------------------------
    # Provider testing
    # ------------------------------------------------------------------

    async def test_provider(self, name: str) -> ProviderInfo:
        """Test a single LLM provider by name.

        Looks up the provider configuration from the scanner's known
        provider list and performs a live availability test.

        Args:
            name: The provider identifier (e.g. ``"opencode_zen"``).

        Returns:
            A :class:`ProviderInfo` with the test outcome.  If the
            provider name is unknown, the returned info will have an
            error message set.
        """
        from src.auto_discovery.llm_scanner import _PROVIDERS

        entry = next(
            (p for p in _PROVIDERS if p["name"] == name),
            None,
        )
        if entry is None:
            logger.warning("test_provider_unknown", provider=name)
            return ProviderInfo(
                name=name,
                display_name=name,
                base_url="",
                api_key_env="",
                models=[],
                is_available=False,
                error=f"Unknown provider: {name}",
                last_checked=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

        info = await asyncio.to_thread(
            self.scanner_llm._test_provider,
            name=entry["name"],
            base_url=entry["url"],
            api_key_env=entry["env"],
            models=entry["models"],
        )
        info.display_name = entry.get("display", name)
        logger.info("test_provider_complete", provider=name, available=info.is_available)
        return info

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    async def health_check_now(self) -> dict[str, HealthStatus]:
        """Force an immediate health check of all configured providers.

        Returns:
            Dict mapping provider name to its :class:`HealthStatus`.
        """
        logger.info("manual_health_check_triggered")
        results = await asyncio.to_thread(self.health.check_all)
        self._state.healthy_providers = len(self.health.get_all_healthy())
        self._save_state()
        logger.info(
            "manual_health_check_complete",
            healthy=self._state.healthy_providers,
        )
        return results

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> DiscoveryState:
        """Return a snapshot of the current engine state.

        Refreshes live counters (healthy providers, health check running
        status) before returning the snapshot.

        Returns:
            A :class:`DiscoveryState` with the current state summary.
        """
        self._state.healthy_providers = len(self.health.get_all_healthy())
        return DiscoveryState(
            last_full_scan=self._state.last_full_scan,
            llm_providers_found=self._state.llm_providers_found,
            data_sources_found=self._state.data_sources_found,
            healthy_providers=self._state.healthy_providers,
            total_providers=self._state.total_providers,
            router_ready=self._state.router_ready,
            health_check_running=self._state.health_check_running,
            errors=list(self._state.errors),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sync_router_from_file(self) -> None:
        """Reload provider data into the router from the persisted JSON.

        Reads the ``providers_llm.json`` file written by the scanner and
        injects it into the router's provider dictionary so routing
        decisions reflect the latest scan results.
        """
        providers_file = os.path.join(self._data_dir, "providers_llm.json")
        if not os.path.isfile(providers_file):
            logger.warning("router_sync_no_file", path=providers_file)
            return
        try:
            with open(providers_file) as f:
                data = json.load(f)
            if isinstance(data, list):
                router_providers: dict[str, Any] = {}
                for entry in data:
                    name = entry.get("name", "")
                    router_providers[name] = {
                        "base_url": entry.get("base_url", ""),
                        "api_key_env": entry.get("api_key_env", ""),
                        "models": {m: {} for m in entry.get("models", [])},
                    }
                self.router._providers = router_providers
            else:
                self.router._providers = data
            self._state.router_ready = True
            logger.info("router_synced_from_file", path=providers_file)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("router_sync_failed", path=providers_file, error=str(exc))
        except Exception as exc:
            logger.error("router_sync_unexpected", error=str(exc))

    def _load_state(self) -> DiscoveryState:
        """Load engine state from the discovery state JSON file.

        Auto-recovery mechanism — if the engine crashed previously, the
        persisted state is restored on the next initialisation.

        Returns:
            A :class:`DiscoveryState` populated from the file, or a
            default instance if the file does not exist or is corrupt.
        """
        state_file = os.path.join(self._data_dir, "discovery_state.json")
        if not os.path.isfile(state_file):
            return DiscoveryState()

        try:
            with open(state_file) as f:
                raw: dict[str, Any] = json.load(f)
            logger.info("state_loaded", path=state_file)
            return DiscoveryState(
                last_full_scan=raw.get("last_full_scan", ""),
                llm_providers_found=raw.get("llm_providers_found", 0),
                data_sources_found=raw.get("data_sources_found", 0),
                healthy_providers=raw.get("healthy_providers", 0),
                total_providers=raw.get("total_providers", 0),
                router_ready=raw.get("router_ready", False),
                health_check_running=raw.get("health_check_running", False),
                errors=list(raw.get("errors", [])),
            )
        except (json.JSONDecodeError, OSError, TypeError) as exc:
            logger.warning("state_load_failed", path=state_file, error=str(exc))
            return DiscoveryState()

    def _save_state(self) -> None:
        """Persist the current engine state to the discovery state JSON file.

        Writes to ``discovery_state.json`` inside the configured data
        directory.  Failures are logged but not propagated.
        """
        state_file = os.path.join(self._data_dir, "discovery_state.json")
        raw: dict[str, Any] = {
            "last_full_scan": self._state.last_full_scan,
            "llm_providers_found": self._state.llm_providers_found,
            "data_sources_found": self._state.data_sources_found,
            "healthy_providers": self._state.healthy_providers,
            "total_providers": self._state.total_providers,
            "router_ready": self._state.router_ready,
            "health_check_running": self._state.health_check_running,
            "errors": list(self._state.errors),
        }
        try:
            with open(state_file, "w") as f:
                json.dump(raw, f, indent=2)
            logger.debug("state_saved", path=state_file)
        except OSError as exc:
            logger.error("state_save_failed", path=state_file, error=str(exc))
