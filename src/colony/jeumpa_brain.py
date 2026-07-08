"""Jeumpa Brain — Zero-cost LLM providers for BlackHornet colony.

Port of Autonomous Organism's JeumpaBrain (TypeScript → Python).
Provides 5 no-auth free LLM providers that work with ZERO API keys,
plus task-aware routing with automatic fallback.

Providers:
  - pollinations (priority 1) — models: openai, openai-fast, gpt-oss
  - ovhcloud_anon (priority 2) — models: Qwen3, Mistral, Llama, etc.
  - keylessai (priority 3) — models: openai-fast, gpt-4o, claude, etc.
  - api_airforce (priority 4) — models: grok-4.1, step-3.5, etc.
  - llm7 (priority 5) — models: deepseek-r1, qwen-2.5-coder

Usage:
    brain = JeumpaBrain()
    result = await brain.chat("Hello", task="chat")
    result = await brain.chat("Write code for...", task="coding")
"""

from __future__ import annotations

import asyncio
import json
import time
import hashlib
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urljoin

from src.config.logging_config import get_logger

logger = get_logger(__name__)


# ── Types ──────────────────────────────────────────────────────────────

@dataclass
class ProviderConfig:
    name: str
    base_url: str
    api_key: str  # empty for no-auth providers
    models: list[str]  # ["*"] for wildcard
    priority: int  # 1 = highest
    timeout_ms: int
    category: str  # "noauth" | "byokey"


@dataclass
class ProviderState:
    config: ProviderConfig
    status: str = "online"  # online | offline | degraded | rate_limited
    latency_ms: float = 0.0
    total_requests: int = 0
    failed_requests: int = 0
    last_error: str | None = None
    last_used: float = 0.0  # epoch
    cooldown_until: float = 0.0
    consecutive_failures: int = 0
    consecutive_successes: int = 0


@dataclass
class ChatMessage:
    role: str  # system | user | assistant
    content: str


@dataclass
class JeumpaResult:
    success: bool = False
    content: str = ""
    provider: str = ""
    model: str = ""
    latency_ms: float = 0.0
    fallbacks_used: list[str] = field(default_factory=list)
    error: str = ""
    cached: bool = False


# ── Task Profiles ──────────────────────────────────────────────────────

TASK_PROFILES: dict[str, dict[str, Any]] = {
    "coding": {
        "model": "pollinations/openai-fast",
        "fallback": ["ovhcloud_anon/Qwen3-Coder-30B-A3B-Instruct", "keylessai/gpt-4o-mini", "pollinations/openai"],
        "timeout": 120,
    },
    "reasoning": {
        "model": "pollinations/openai",
        "fallback": ["ovhcloud_anon/Meta-Llama-3_3-70B-Instruct", "keylessai/gpt-4o", "llm7/deepseek-r1"],
        "timeout": 120,
    },
    "fast": {
        "model": "pollinations/openai-fast",
        "fallback": ["ovhcloud_anon/Mistral-Nemo-Instruct-2407", "keylessai/openai-fast"],
        "timeout": 30,
    },
    "chat": {
        "model": "pollinations/openai-fast",
        "fallback": ["ovhcloud_anon/Mistral-Nemo-Instruct-2407", "keylessai/gpt-4o-mini"],
        "timeout": 60,
    },
    "balanced": {
        "model": "pollinations/openai",
        "fallback": ["ovhcloud_anon/Qwen3-32B", "keylessai/gpt-4o", "llm7/qwen-2.5-coder"],
        "timeout": 60,
    },
    "creative": {
        "model": "ovhcloud_anon/Mistral-Nemo-Instruct-2407",
        "fallback": ["pollinations/openai", "keylessai/claude-3.5-sonnet", "pollinations/openai-fast"],
        "timeout": 120,
    },
    "brainstorming": {
        "model": "pollinations/openai",
        "fallback": ["ovhcloud_anon/Mistral-Nemo-Instruct-2407", "keylessai/gpt-4o", "pollinations/openai-fast"],
        "timeout": 120,
    },
    "long_task": {
        "model": "pollinations/openai",
        "fallback": ["ovhcloud_anon/Qwen3-32B", "keylessai/gpt-4o", "llm7/deepseek-r1"],
        "timeout": 300,
    },
    "default": {
        "model": "pollinations/openai-fast",
        "fallback": ["ovhcloud_anon/Mistral-Nemo-Instruct-2407", "keylessai/gpt-4o-mini", "pollinations/openai"],
        "timeout": 60,
    },
}


# ── No-Auth Providers ──────────────────────────────────────────────────

NOAUTH_PROVIDERS: list[ProviderConfig] = [
    ProviderConfig(
        name="pollinations",
        base_url="https://text.pollinations.ai/openai/v1",
        api_key="",
        models=["openai", "openai-fast", "gpt-oss"],
        priority=1,
        timeout_ms=45000,
        category="noauth",
    ),
    ProviderConfig(
        name="ovhcloud_anon",
        base_url="https://oai.endpoints.kepler.ai.cloud.ovh.net/v1",
        api_key="",
        models=[
            "Qwen3-Coder-30B-A3B-Instruct", "Qwen3-32B",
            "Mistral-Nemo-Instruct-2407", "Mistral-Small-3.2-24B-Instruct-2506",
            "Meta-Llama-3_3-70B-Instruct", "gpt-oss-20b",
            "Mistral-7B-Instruct-v0.3", "Qwen3.5-9B",
        ],
        priority=2,
        timeout_ms=45000,
        category="noauth",
    ),
    ProviderConfig(
        name="keylessai",
        base_url="https://keylessai.thryx.workers.dev/v1",
        api_key="",
        models=[
            "openai-fast", "gpt-4o-mini", "gpt-4o", "gpt-4",
            "gpt-3.5-turbo", "claude-3.5-sonnet", "claude-3-haiku",
        ],
        priority=3,
        timeout_ms=30000,
        category="noauth",
    ),
    ProviderConfig(
        name="api_airforce",
        base_url="https://api.airforce/v1",
        api_key="",
        models=["grok-4.1-mini:free", "step-3.5-flash:free", "gpt-oss-120b"],
        priority=4,
        timeout_ms=30000,
        category="noauth",
    ),
    ProviderConfig(
        name="llm7",
        base_url="https://api.llm7.io/v1",
        api_key="",
        models=["deepseek-r1", "qwen-2.5-coder", "llama-3.3-70b"],
        priority=5,
        timeout_ms=30000,
        category="noauth",
    ),
]


# ── Main Brain Class ───────────────────────────────────────────────────

class JeumpaBrain:
    """Zero-cost LLM gateway with task-aware routing and auto-fallback.

    Uses 5 no-auth providers. No API keys required.
    Automatically falls back through providers when one fails.
    Tracks provider health, cooldowns, and latency.
    """

    def __init__(self, cache_ttl: int = 300):
        self._providers: dict[str, ProviderState] = {}
        self._rr_index: dict[str, int] = {}
        self._cache: dict[str, tuple[float, JeumpaResult]] = {}
        self._cache_ttl = cache_ttl
        self._total_calls = 0
        self._register_providers()

    def _register_providers(self) -> None:
        for cfg in NOAUTH_PROVIDERS:
            self._providers[cfg.name] = ProviderState(config=cfg)
        logger.info(
            "jeumpa_brain_registered providers=%d names=%s",
            len(self._providers), list(self._providers.keys()),
        )

    def get_provider_list(self) -> list[dict[str, Any]]:
        """Return list of registered providers with status."""
        return [
            {
                "name": p.config.name,
                "status": p.status,
                "models": p.config.models,
                "priority": p.config.priority,
                "latency_ms": p.latency_ms,
                "category": p.config.category,
                "total_requests": p.total_requests,
                "failed_requests": p.failed_requests,
                "consecutive_failures": p.consecutive_failures,
            }
            for p in self._providers.values()
        ]

    async def chat(
        self,
        message: str,
        system_prompt: str | None = None,
        task: str = "default",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        use_cache: bool = True,
    ) -> JeumpaResult:
        """Send a chat message through Jeumpa Brain with task-aware routing.

        Args:
            message: The user message.
            system_prompt: Optional system instruction.
            task: Task profile (coding, reasoning, fast, chat, etc.).
            temperature: LLM temperature.
            max_tokens: Max tokens in response.
            use_cache: Whether to check cache first.

        Returns:
            JeumpaResult with the response and metadata.
        """
        self._total_calls += 1
        start = time.time()

        cache_key = self._make_cache_key(message, task)
        if use_cache:
            cached = self._check_cache(cache_key)
            if cached:
                return cached

        profile = TASK_PROFILES.get(task, TASK_PROFILES["default"])
        model_ref = profile["model"]
        fallback_chain = profile["fallback"]
        timeout_s = profile["timeout"]

        messages = self._build_messages(message, system_prompt)
        fallbacks_used: list[str] = []
        last_error: str = ""

        # Try primary
        result = await self._try_model(model_ref, messages, temperature, max_tokens, timeout_s)
        if result and result.success:
            result.fallbacks_used = fallbacks_used
            self._set_cache(cache_key, result)
            return result

        if result and result.error:
            last_error = result.error
        fallbacks_used.append(model_ref)

        # Try fallbacks
        for fallback_ref in fallback_chain:
            result = await self._try_model(fallback_ref, messages, temperature, max_tokens, timeout_s)
            if result and result.success:
                result.fallbacks_used = fallbacks_used
                self._set_cache(cache_key, result)
                return result
            if result and result.error:
                last_error = result.error
            fallbacks_used.append(fallback_ref)

        latency = (time.time() - start) * 1000
        result = JeumpaResult(
            success=False,
            error=f"All providers failed. Last error: {last_error}",
            latency_ms=latency,
            fallbacks_used=fallbacks_used,
        )
        return result

    async def chat_messages(
        self,
        messages: list[dict[str, str]],
        task: str = "default",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> JeumpaResult:
        """Send a list of formatted messages through Jeumpa Brain.

        Args:
            messages: List of {role, content} dicts.
            task: Task profile.
            temperature: LLM temperature.
            max_tokens: Max tokens.

        Returns:
            JeumpaResult with the response.
        """
        profile = TASK_PROFILES.get(task, TASK_PROFILES["default"])
        model_ref = profile["model"]
        fallback_chain = profile["fallback"]
        timeout_s = profile["timeout"]

        fallbacks_used: list[str] = []

        # Try primary
        result = await self._try_model(model_ref, messages, temperature, max_tokens, timeout_s)
        if result and result.success:
            result.fallbacks_used = fallbacks_used
            return result
        fallbacks_used.append(model_ref)

        for fallback_ref in fallback_chain:
            result = await self._try_model(fallback_ref, messages, temperature, max_tokens, timeout_s)
            if result and result.success:
                result.fallbacks_used = fallbacks_used
                return result
            fallbacks_used.append(fallback_ref)

        return JeumpaResult(success=False, error="All providers failed", fallbacks_used=fallbacks_used)

    async def _try_model(
        self,
        model_ref: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        timeout_s: int,
    ) -> JeumpaResult | None:
        """Try a specific model reference (e.g. 'pollinations/openai-fast')."""
        try:
            provider_name, model = self._parse_model_ref(model_ref)
            if not provider_name or not model:
                return None

            provider = self._providers.get(provider_name)
            if not provider:
                logger.debug("jeumpa_unknown_provider provider=%s", provider_name)
                return None

            # Check cooldown
            if provider.cooldown_until > time.time():
                logger.debug("jeumpa_provider_cooldown provider=%s until=%.0f", provider_name, provider.cooldown_until)
                return JeumpaResult(success=False, error=f"Provider {provider_name} in cooldown", provider=provider_name)

            # Check health
            if provider.status == "offline" and provider.consecutive_failures > 5:
                return None

            start = time.time()

            body = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            }

            headers = {"Content-Type": "application/json"}
            if provider.config.api_key:
                headers["Authorization"] = f"Bearer {provider.config.api_key}"

            async with asyncio.timeout(timeout_s):
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        urljoin(provider.config.base_url.rstrip("/") + "/", "chat/completions"),
                        headers=headers,
                        json=body,
                    ) as resp:
                        latency = (time.time() - start) * 1000
                        provider.total_requests += 1
                        provider.latency_ms = latency
                        provider.last_used = time.time()

                        if resp.status == 429:
                            provider.consecutive_failures += 1
                            provider.consecutive_successes = 0
                            provider.status = "rate_limited"
                            provider.cooldown_until = time.time() + 60
                            provider.failed_requests += 1
                            return JeumpaResult(
                                success=False, error="Rate limited",
                                provider=provider_name, model=model, latency_ms=latency,
                            )

                        if resp.status == 503 or resp.status == 502:
                            provider.consecutive_failures += 1
                            provider.consecutive_successes = 0
                            provider.failed_requests += 1
                            provider.cooldown_until = time.time() + 30
                            return JeumpaResult(
                                success=False, error=f"HTTP {resp.status}",
                                provider=provider_name, model=model, latency_ms=latency,
                            )

                        data = await resp.json()

                        if not resp.ok:
                            provider.consecutive_failures += 1
                            provider.consecutive_successes = 0
                            provider.failed_requests += 1
                            err_msg = data.get("error", {}).get("message", str(data))[:200]
                            if resp.status >= 500:
                                provider.cooldown_until = time.time() + 60
                            return JeumpaResult(
                                success=False, error=err_msg,
                                provider=provider_name, model=model, latency_ms=latency,
                            )

                        # Success
                        provider.consecutive_failures = 0
                        provider.consecutive_successes += 1
                        provider.status = "online"
                        content = (data.get("choices", [{}])[0].get("message", {}).get("content", "") or "")
                        provider_name_used = data.get("model", provider_name)

                        return JeumpaResult(
                            success=True,
                            content=content,
                            provider=provider_name,
                            model=provider_name_used,
                            latency_ms=latency,
                        )

        except asyncio.TimeoutError:
            logger.debug("jeumpa_timeout model=%s", model_ref)
            provider_name, _ = self._parse_model_ref(model_ref)
            if provider_name and provider_name in self._providers:
                p = self._providers[provider_name]
                p.consecutive_failures += 1
                p.failed_requests += 1
                p.status = "degraded"
                p.cooldown_until = time.time() + 15
            return JeumpaResult(success=False, error="Timeout", provider=provider_name or "unknown")

        except Exception as e:
            logger.debug("jeumpa_error model=%s err=%s", model_ref, e)
            provider_name, _ = self._parse_model_ref(model_ref)
            if provider_name and provider_name in self._providers:
                p = self._providers[provider_name]
                p.consecutive_failures += 1
                p.failed_requests += 1
                if p.consecutive_failures > 3:
                    p.status = "offline"
                    p.cooldown_until = time.time() + 120
            return JeumpaResult(success=False, error=str(e)[:200], provider=provider_name or "unknown")

    def _parse_model_ref(self, ref: str) -> tuple[str | None, str | None]:
        """Parse 'provider/model' into (provider_name, model_name)."""
        if "/" in ref:
            parts = ref.split("/", 1)
            return parts[0], parts[1]
        # Try to match provider name directly
        if ref in self._providers:
            return ref, self._providers[ref].config.models[0] if self._providers[ref].config.models else None
        return None, None

    def _build_messages(
        self, message: str, system_prompt: str | None,
    ) -> list[dict[str, str]]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})
        return messages

    def _make_cache_key(self, message: str, task: str) -> str:
        raw = f"{task}:{message.lower().strip()}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _check_cache(self, key: str) -> JeumpaResult | None:
        entry = self._cache.get(key)
        if entry:
            ts, result = entry
            if time.time() - ts < self._cache_ttl:
                result.cached = True
                return result
            del self._cache[key]
        return None

    def _set_cache(self, key: str, result: JeumpaResult) -> None:
        self._cache[key] = (time.time(), result)

    def get_stats(self) -> dict[str, Any]:
        """Return usage statistics."""
        return {
            "total_calls": self._total_calls,
            "cache_size": len(self._cache),
            "providers": self.get_provider_list(),
        }
