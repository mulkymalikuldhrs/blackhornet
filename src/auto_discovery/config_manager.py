"""LLM Config Manager — sub-agent 1.6.

Manages user-configurable provider preferences, routing rules, and
auto-discovery settings via a YAML configuration file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

import yaml

import logging

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """Configuration for a single LLM provider.

    Attributes:
        name: Unique provider identifier (e.g. ``"opencode_zen"``).
        enabled: Whether this provider is active and available for routing.
        priority: Lower values indicate higher priority (1 = highest).
        models: List of model identifiers available through this provider.
        max_tokens: Maximum tokens per completion request.
        timeout_seconds: Request timeout in seconds.
        retry_count: Number of automatic retries on failure.
    """

    name: str
    enabled: bool = True
    priority: int = 10
    models: list[str] = field(default_factory=list)
    max_tokens: int = 4096
    timeout_seconds: int = 30
    retry_count: int = 2


@dataclass
class RoutingConfig:
    """Routing rules for a specific complexity tier.

    Attributes:
        complexity: Complexity tier label (``"simple"``, ``"medium"``,
            ``"complex"``, ``"trading"``).
        preferred_providers: Ordered list of provider names to try first.
        fallback_providers: Ordered list of fallback providers.
        max_tokens: Maximum tokens allowed for this complexity tier.
    """

    complexity: str
    preferred_providers: list[str] = field(default_factory=list)
    fallback_providers: list[str] = field(default_factory=list)
    max_tokens: int = 4096


@dataclass
class AutoDiscoveryConfig:
    """Root configuration for the auto-discovery engine.

    Attributes:
        llm_providers: List of all configured LLM providers.
        routing: Routing rules for each complexity tier.
        health_check_interval_hours: Interval between automated health checks.
        data_dir: Directory for persistent state files.
    """

    llm_providers: list[ProviderConfig] = field(default_factory=list)
    routing: list[RoutingConfig] = field(default_factory=list)
    health_check_interval_hours: int = 6
    data_dir: str = "~/.bh/data"


# ── Default configurations (from environment research) ──────────────────

_DEFAULT_PROVIDERS: list[dict[str, Any]] = [
    {
        "name": "opencode_zen",
        "enabled": True,
        "priority": 1,
        "models": ["mimo-v2.5-free", "deepseek-v4-flash-free"],
        "max_tokens": 16384,
        "timeout_seconds": 30,
        "retry_count": 2,
    },
    {
        "name": "nvidia",
        "enabled": True,
        "priority": 2,
        "models": ["meta/llama-3.1-nemotron-70b-instruct"],
        "max_tokens": 8192,
        "timeout_seconds": 30,
        "retry_count": 2,
    },
    {
        "name": "groq",
        "enabled": True,
        "priority": 3,
        "models": ["llama-3.1-8b-instant"],
        "max_tokens": 4096,
        "timeout_seconds": 20,
        "retry_count": 2,
    },
    {
        "name": "openrouter",
        "enabled": True,
        "priority": 4,
        "models": ["meta-llama/llama-3.1-8b-instruct"],
        "max_tokens": 4096,
        "timeout_seconds": 30,
        "retry_count": 1,
    },
    {
        "name": "ollama_cloud",
        "enabled": True,
        "priority": 5,
        "models": ["llama3.1"],
        "max_tokens": 4096,
        "timeout_seconds": 30,
        "retry_count": 1,
    },
    {
        "name": "glm",
        "enabled": True,
        "priority": 6,
        "models": ["glm-4"],
        "max_tokens": 4096,
        "timeout_seconds": 30,
        "retry_count": 1,
    },
]

_DEFAULT_ROUTING: list[dict[str, Any]] = [
    {
        "complexity": "simple",
        "preferred_providers": ["opencode_zen", "groq"],
        "fallback_providers": ["nvidia"],
        "max_tokens": 1024,
    },
    {
        "complexity": "medium",
        "preferred_providers": ["opencode_zen", "nvidia"],
        "fallback_providers": ["groq", "openrouter"],
        "max_tokens": 4096,
    },
    {
        "complexity": "complex",
        "preferred_providers": ["opencode_zen", "openrouter"],
        "fallback_providers": ["nvidia", "groq"],
        "max_tokens": 8192,
    },
    {
        "complexity": "trading",
        "preferred_providers": ["nvidia", "opencode_zen"],
        "fallback_providers": ["openrouter", "groq"],
        "max_tokens": 16384,
    },
]


class ConfigManager:
    """Manages LLM provider and routing configuration via YAML.

    Provides load/save semantics with sensible defaults based on the
    actual provider environment discovered during research.  Configuration
    is persisted at ``~/.bh/config.yaml`` by default.

    Args:
        config_path: Path to the YAML configuration file.  The tilde
            character is expanded to the user's home directory.
    """

    def __init__(self, config_path: str = "~/.bh/config.yaml") -> None:
        self._config_path = os.path.expanduser(config_path)
        self._config: AutoDiscoveryConfig = self.get_default()

    # ── Public API ───────────────────────────────────────────────────────

    def load(self) -> AutoDiscoveryConfig:
        """Load configuration from the YAML file.

        Returns the parsed :class:`AutoDiscoveryConfig`.  If the file
        does not exist or cannot be parsed, sensible defaults are returned
        and a warning is logged.

        Returns:
            The loaded or default configuration.
        """
        if not os.path.isfile(self._config_path):
            logger.info("config_file_not_found", path=self._config_path, using="defaults")
            self._config = self.get_default()
            return self._config

        try:
            with open(self._config_path) as f:
                raw: dict[str, Any] = yaml.safe_load(f) or {}

            providers_raw: list[dict[str, Any]] = raw.get("llm_providers", [])
            routing_raw: list[dict[str, Any]] = raw.get("routing", [])

            self._config = AutoDiscoveryConfig(
                llm_providers=[ProviderConfig(**p) for p in providers_raw],
                routing=[RoutingConfig(**r) for r in routing_raw],
                health_check_interval_hours=raw.get("health_check_interval_hours", 6),
                data_dir=raw.get("data_dir", "~/.bh/data"),
            )

            logger.info("config_loaded", path=self._config_path, providers=len(self._config.llm_providers))
            return self._config

        except (yaml.YAMLError, OSError, TypeError, ValueError) as exc:
            logger.warning("config_load_failed", path=self._config_path, error=str(exc), using="defaults")
            self._config = self.get_default()
            return self._config

    def save(self, config: AutoDiscoveryConfig) -> None:
        """Write configuration to the YAML file.

        Creates the parent directory if it does not exist.

        Args:
            config: The configuration to persist.
        """
        config_dir = os.path.dirname(self._config_path)
        os.makedirs(config_dir, exist_ok=True)

        raw: dict[str, Any] = {
            "llm_providers": [asdict(p) for p in config.llm_providers],
            "routing": [asdict(r) for r in config.routing],
            "health_check_interval_hours": config.health_check_interval_hours,
            "data_dir": config.data_dir,
        }

        try:
            with open(self._config_path, "w") as f:
                yaml.safe_dump(raw, f, default_flow_style=False, sort_keys=False)
            logger.info("config_saved", path=self._config_path)
        except OSError as exc:
            logger.error("config_save_failed", path=self._config_path, error=str(exc))
            raise

    @staticmethod
    def get_default() -> AutoDiscoveryConfig:
        """Generate the default configuration.

        Returns:
            An :class:`AutoDiscoveryConfig` populated with the default
            provider and routing settings discovered during research.
        """
        return AutoDiscoveryConfig(
            llm_providers=[ProviderConfig(**p) for p in _DEFAULT_PROVIDERS],
            routing=[RoutingConfig(**r) for r in _DEFAULT_ROUTING],
            health_check_interval_hours=6,
            data_dir="~/.bh/data",
        )

    def get_provider_config(self, name: str) -> ProviderConfig:
        """Get the configuration for a single provider.

        Args:
            name: Provider name to look up.

        Returns:
            The matching :class:`ProviderConfig`.

        Raises:
            ValueError: If no provider with the given name is configured.
        """
        for provider in self._config.llm_providers:
            if provider.name == name:
                return provider
        raise ValueError(f"Provider '{name}' is not configured")

    def update_provider(self, name: str, **kwargs: Any) -> None:
        """Update a provider configuration in place and persist.

        Accepts any field of :class:`ProviderConfig` as a keyword argument.
        After updating, the configuration is immediately saved to disk.

        Args:
            name: Provider name to update.
            **kwargs: Field names and their new values (e.g.
                ``enabled=False``, ``priority=3``).

        Raises:
            ValueError: If no provider with the given name is configured.
        """
        provider = self.get_provider_config(name)
        for key, value in kwargs.items():
            if hasattr(provider, key):
                setattr(provider, key, value)
            else:
                logger.warning("update_provider_unknown_field", provider=name, field=key)
        self.save(self._config)
        logger.info("provider_updated", provider=name, changes=set(kwargs.keys()))

    def get_routing(self, complexity: str) -> RoutingConfig:
        """Get routing configuration for a specific complexity tier.

        Args:
            complexity: The complexity tier label (``"simple"``,
                ``"medium"``, ``"complex"``, ``"trading"``).

        Returns:
            The matching :class:`RoutingConfig`.

        Raises:
            ValueError: If no routing config exists for the given
                complexity level.
        """
        for route in self._config.routing:
            if route.complexity == complexity:
                return route
        raise ValueError(f"No routing config for complexity '{complexity}'")
