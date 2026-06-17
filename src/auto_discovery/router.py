"""Router Engine — sub-agent 1.3.

Classifies prompt complexity and selects the optimal LLM provider based on
a configurable routing table with fallback support.  Uses only stdlib for HTTP.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import logging

logger = logging.getLogger(__name__)

# ── Keyword sets for complexity classification ─────────────────────────

_SIMPLE_KEYWORDS: set[str] = {
    "hello", "hi", "hey", "greetings", "good morning", "good evening",
    "thanks", "thank you", "bye", "goodbye", "yes", "no", "ok", "okay",
    "what is", "who is", "where is", "when is", "help", "commands",
}

_MEDIUM_KEYWORDS: set[str] = {
    "write", "create", "generate", "implement", "refactor", "debug",
    "analyze", "explain", "summarize", "translate", "convert", "parse",
    "function", "class", "method", "test", "script", "query", "sort",
    "filter", "map", "reduce", "transform", "validate", "format",
}

_COMPLEX_KEYWORDS: set[str] = {
    "architecture", "design pattern", "system design", "distributed",
    "research", "deep dive", "comparative analysis", "trade-off",
    "scalability", "optimization strategy", "migration plan",
    "technical specification", "protocol", "consensus", "orchestration",
    "pipeline", "workflow engine", "event sourcing", "cqrs",
}

_TRADING_KEYWORDS: set[str] = {
    "risk", "kelly", "portfolio", "hedge", "volatility", "sharpe",
    "drawdown", "backtest", "alpha", "beta", "gamma", "theta", "vega",
    "option pricing", "black-scholes", "monte carlo", "var", "cvar",
    "position sizing", "stop loss", "take profit", "market making",
    "arbitrage", "momentum", "mean reversion", "pair trading",
    "correlation", "covariance", "efficient frontier", "capm",
    "futures", "derivatives", "swap", "yield curve", "duration",
}


class ComplexityLevel(Enum):
    """Prompt complexity tiers for provider routing."""

    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    TRADING = "trading"


@dataclass
class RouteResult:
    """Result of a routing decision.

    Attributes:
        provider: Selected provider name.
        model: Model identifier to use.
        endpoint: Full API endpoint URL.
        api_key: API key for authentication.
        estimated_cost: Rough cost estimate in USD for the request.
    """

    provider: str
    model: str
    endpoint: str
    api_key: str
    estimated_cost: float = 0.0


@dataclass
class RouterConfig:
    """Configuration for the LLM router.

    Attributes:
        complexity_map: Maps complexity-level string to an ordered list of
            provider entries.  Each entry has at least ``provider`` and
            ``model`` keys.
        default_fallback: Provider name to use when no route matches.
    """

    complexity_map: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    default_fallback: str = "opencode_zen"


# ── Default routing table (from environment research) ──────────────────

_DEFAULT_ROUTING_TABLE: dict[str, list[dict[str, str]]] = {
    "simple": [
        {"provider": "opencode_zen", "model": "mimo-v2.5-free"},
        {"provider": "groq", "model": "llama-3.1-8b-instant"},
    ],
    "medium": [
        {"provider": "opencode_zen", "model": "deepseek-v4-flash-free"},
        {"provider": "nvidia", "model": "meta/llama-3.1-nemotron-70b-instruct"},
    ],
    "complex": [
        {"provider": "opencode_zen", "model": "nemotron-3-ultra-free"},
        {"provider": "openrouter", "model": "meta-llama/llama-3.1-8b-instruct"},
    ],
    "trading": [
        {"provider": "nvidia", "model": "meta/llama-3.1-nemotron-70b-instruct"},
        {"provider": "openrouter", "model": "meta-llama/llama-3.1-8b-instruct"},
    ],
}


class LLMRouter:
    """Routes prompts to the best available LLM provider.

    Classifies prompt complexity by keyword analysis, then selects the
    first available provider from the routing chain for that tier.

    Attributes:
        providers_file: Path to the JSON file with provider configurations.
        config: :class:`RouterConfig` instance; uses defaults when ``None``.
    """

    def __init__(
        self,
        providers_file: str = "providers_llm.json",
        config: Optional[RouterConfig] = None,
    ) -> None:
        self.providers_file = providers_file
        self._config = config or RouterConfig(
            complexity_map=_DEFAULT_ROUTING_TABLE,
        )
        self._providers: dict[str, Any] = {}
        self._load_providers()

    # ── Public API ───────────────────────────────────────────────────────

    @staticmethod
    def classify_complexity(prompt: str) -> ComplexityLevel:
        """Classify a prompt into a complexity tier based on keywords.

        Args:
            prompt: The user's input prompt.

        Returns:
            The matching :class:`ComplexityLevel`.
        """
        lower = prompt.lower()
        tokens = lower.split()
        token_count = len(tokens)

        # Trading keywords take precedence (quantitative finance)
        if any(kw in lower for kw in _TRADING_KEYWORDS):
            return ComplexityLevel.TRADING

        # Check for complex keywords first
        if any(kw in lower for kw in _COMPLEX_KEYWORDS):
            return ComplexityLevel.COMPLEX

        # Simple if very short or only simple keywords
        if token_count < 50:
            if any(kw in lower for kw in _SIMPLE_KEYWORDS) or token_count < 10:
                return ComplexityLevel.SIMPLE

        # Medium by default for code or analysis tasks
        if any(kw in lower for kw in _MEDIUM_KEYWORDS):
            return ComplexityLevel.MEDIUM

        # Length-based fallback
        if token_count < 50:
            return ComplexityLevel.SIMPLE
        if token_count <= 500:
            return ComplexityLevel.MEDIUM
        if token_count <= 2000:
            return ComplexityLevel.COMPLEX

        return ComplexityLevel.COMPLEX

    def route(self, prompt: str) -> RouteResult:
        """Classify and route a prompt to the best available provider.

        Args:
            prompt: The user's input prompt.

        Returns:
            A :class:`RouteResult` with the selected provider details.

        Raises:
            RuntimeError: If no providers are available for the classified
                complexity level.
        """
        complexity = self.classify_complexity(prompt)
        chain = self._config.complexity_map.get(complexity.value, [])
        return self._resolve_chain(chain, complexity)

    def route_with_fallback(
        self,
        prompt: str,
        fallback_chain: list[str],
    ) -> RouteResult:
        """Route a prompt using an explicit fallback chain of provider names.

        Args:
            prompt: The user's input prompt.
            fallback_chain: Ordered list of provider names to try.

        Returns:
            A :class:`RouteResult` with the first available provider.

        Raises:
            RuntimeError: If none of the providers in the chain are available.
        """
        complexity = self.classify_complexity(prompt)

        for provider_name in fallback_chain:
            provider_cfg = self._providers.get(provider_name)
            if provider_cfg is None:
                logger.warning("provider_not_found", provider=provider_name)
                continue

            model = self._first_model(provider_cfg)
            if model is None:
                logger.warning("provider_no_models", provider=provider_name)
                continue

            api_key = os.environ.get(provider_cfg.get("api_key_env", ""), "")
            endpoint = provider_cfg.get("base_url", "")

            logger.debug(
                "routing_with_fallback",
                provider=provider_name,
                model=model,
                complexity=complexity.value,
            )

            return RouteResult(
                provider=provider_name,
                model=model,
                endpoint=endpoint,
                api_key=api_key,
            )

        raise RuntimeError(
            f"No available providers in fallback chain: {fallback_chain}"
        )

    def get_available_providers(self) -> list[dict[str, Any]]:
        """Return list of provider configs that have API keys configured.

        Returns:
            List of provider configuration dicts.
        """
        available: list[dict[str, Any]] = []
        for name, cfg in self._providers.items():
            env_var = cfg.get("api_key_env", "")
            if os.environ.get(env_var):
                available.append({"name": name, **cfg})
        return available

    # ── Internal helpers ─────────────────────────────────────────────────

    def _resolve_chain(
        self,
        chain: list[dict[str, str]],
        complexity: ComplexityLevel,
    ) -> RouteResult:
        """Walk the routing chain and return the first available provider."""
        for entry in chain:
            provider_name = entry.get("provider", "")
            model = entry.get("model", "")
            provider_cfg = self._providers.get(provider_name)

            if provider_cfg is None:
                logger.debug("provider_unknown", provider=provider_name)
                continue

            api_key = os.environ.get(provider_cfg.get("api_key_env", ""), "")
            if not api_key:
                logger.debug("provider_no_api_key", provider=provider_name)
                continue

            endpoint = provider_cfg.get("base_url", "")

            logger.debug(
                "routing_decision",
                provider=provider_name,
                model=model,
                complexity=complexity.value,
            )

            return RouteResult(
                provider=provider_name,
                model=model,
                endpoint=endpoint,
                api_key=api_key,
            )

        # Fallback to default provider
        default = self._config.default_fallback
        provider_cfg = self._providers.get(default)
        if provider_cfg is None:
            raise RuntimeError(
                f"No providers available for complexity '{complexity.value}' "
                f"and default fallback '{default}' is not configured"
            )

        model = self._first_model(provider_cfg) or ""
        api_key = os.environ.get(provider_cfg.get("api_key_env", ""), "")
        endpoint = provider_cfg.get("base_url", "")

        logger.info(
            "routing_fallback_to_default",
            provider=default,
            model=model,
        )

        return RouteResult(
            provider=default,
            model=model,
            endpoint=endpoint,
            api_key=api_key,
        )

    @staticmethod
    def _first_model(provider_cfg: dict[str, Any]) -> Optional[str]:
        """Return the first model name from a provider config, if any."""
        models = provider_cfg.get("models", {})
        if isinstance(models, dict):
            for model_name in models:
                return model_name
        return None

    def _load_providers(self) -> None:
        """Load provider configurations from the JSON file.

        Falls back to an embedded default configuration when the file
        cannot be read.
        """
        if os.path.isfile(self.providers_file):
            try:
                with open(self.providers_file) as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self._providers = {}
                    for entry in data:
                        name = entry.get("name", "")
                        self._providers[name] = {
                            "base_url": entry.get("base_url", ""),
                            "api_key_env": entry.get("api_key_env", ""),
                            "models": {m: {} for m in entry.get("models", [])},
                        }
                else:
                    self._providers = data.get("providers", data)
                logger.info(
                    "providers_loaded",
                    path=self.providers_file,
                    count=len(self._providers),
                )
                return
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning(
                    "providers_load_failed",
                    path=self.providers_file,
                    error=str(exc),
                )

        self._providers = {
            "opencode_zen": {
                "base_url": "https://api.opencode.ai/v1/chat/completions",
                "api_key_env": "OPENCODE_ZEN_API_KEY",
                "models": {
                    "mimo-v2.5-free": {},
                    "deepseek-v4-flash-free": {},
                    "nemotron-3-ultra-free": {},
                },
            },
            "groq": {
                "base_url": "https://api.groq.com/openai/v1/chat/completions",
                "api_key_env": "GROQ_API_KEY",
                "models": {
                    "llama-3.1-8b-instant": {},
                },
            },
            "nvidia": {
                "base_url": "https://api.nvcf.nvidia.com/v1/chat/completions",
                "api_key_env": "NVIDIA_API_KEY",
                "models": {
                    "meta/llama-3.1-nemotron-70b-instruct": {},
                },
            },
            "openrouter": {
                "base_url": "https://openrouter.ai/api/v1/chat/completions",
                "api_key_env": "OPENROUTER_API_KEY",
                "models": {
                    "meta-llama/llama-3.1-8b-instruct": {},
                },
            },
        }
        logger.info(
            "providers_loaded_defaults",
            count=len(self._providers),
        )
