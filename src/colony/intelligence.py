"""IntelligenceBridge — unified intelligence routing for the colony.

Wraps the existing LLM routing chain (LLMRouter, FallbackChain, ProviderHub,
WebSearch, Skills) into a single interface accessible from QueenAgent.

Provides:
  - ask(query) -> answer using LLM routing + fallback
  - think(prompt, context) -> structured thinking with context injection
  - search_web(query) -> web search augmentation
  - get_providers() -> available LLM providers

Usage:
    ib = IntelligenceBridge()
    result = await ib.ask("What is the capital of France?")
    result = await ib.think("Analyze this architecture", context={"memory": ...})
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from src.config.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class IntelligenceResult:
    success: bool = False
    answer: str = ""
    provider: str = ""
    model: str = ""
    latency_ms: float = 0.0
    attempts: int = 1
    cached: bool = False
    error: str = ""
    web_search_used: bool = False


class IntelligenceBridge:
    """Unified intelligence routing for the colony.

    Wraps LLMRouter, FallbackChain, ProviderHub, web search tools,
    and skill system into one interface.

    Falls back gracefully when dependencies are not available.
    """

    def __init__(
        self,
        llm_router: Any = None,
        fallback_chain: Any = None,
        provider_hub: Any = None,
        memory_system: Any = None,
        lifecycle_recorder: Any = None,
        cache_ttl: int = 300,
    ) -> None:
        self._router = llm_router
        self._fallback = fallback_chain
        self._provider_hub = provider_hub
        self._memory = memory_system
        self._lifecycle = lifecycle_recorder

        self._cache_ttl = cache_ttl
        self._cache: dict[str, tuple[float, IntelligenceResult]] = {}
        self._ask_count = 0
        self._think_count = 0
        self._web_search_count = 0

    async def ask(
        self,
        query: str,
        complexity: Optional[str] = None,
        use_cache: bool = True,
        context: Optional[dict[str, Any]] = None,
    ) -> IntelligenceResult:
        """Ask a question and get an answer through the intelligence chain.

        Args:
            query: The question or prompt.
            complexity: Force complexity tier (simple, medium, complex, trading).
            use_cache: If True, check cache before routing.
            context: Optional context dict (memory, state, etc.) injected into prompt.

        Returns:
            IntelligenceResult with answer and metadata.
        """
        self._ask_count += 1
        start = time.time()

        cache_key = self._make_cache_key(query, complexity)
        if use_cache:
            cached = self._check_cache(cache_key)
            if cached:
                return cached

        if context:
            augmented = self._inject_context(query, context)
        else:
            augmented = query

        if self._fallback and hasattr(self._fallback, "execute"):
            try:
                if asyncio.iscoroutinefunction(self._fallback.execute):
                    result = await self._fallback.execute(augmented, complexity)
                else:
                    result = self._fallback.execute(augmented, complexity)
                ir = self._fallback_result_to_intelligence(result, query, start)
                self._set_cache(cache_key, ir)
                await self._log_lifecycle("ask", query, ir)
                return ir
            except Exception as e:
                logger.debug("intel_fallback_error err=%s", e)

        if self._router and hasattr(self._router, "route_with_fallback"):
            try:
                if asyncio.iscoroutinefunction(self._router.route_with_fallback):
                    result = await self._router.route_with_fallback(augmented)
                else:
                    result = self._router.route_with_fallback(augmented)
                ir = self._route_result_to_intelligence(result, query, start)
                self._set_cache(cache_key, ir)
                await self._log_lifecycle("ask", query, ir)
                return ir
            except Exception as e:
                logger.debug("intel_router_error err=%s", e)

        ir = IntelligenceResult(
            success=False,
            answer="",
            error="No LLM router or fallback chain available",
            latency_ms=(time.time() - start) * 1000,
        )
        await self._log_lifecycle("ask", query, ir)
        return ir

    async def think(
        self,
        prompt: str,
        context: Optional[dict[str, Any]] = None,
        temperature: float = 0.3,
    ) -> IntelligenceResult:
        """Structured thinking with context injection.

        Use for analysis, planning, reasoning tasks.
        Injects context from memory, graph, or state into the prompt.

        Args:
            prompt: The thinking prompt.
            context: Dict of context variables injected into the prompt.
            temperature: LLM temperature for thinking (lower = more focused).

        Returns:
            IntelligenceResult with thought/analysis.
        """
        self._think_count += 1
        start = time.time()

        context_str = ""
        if context:
            parts = []
            for key, value in context.items():
                if isinstance(value, str):
                    parts.append(f"[{key}]: {value[:500]}")
                elif isinstance(value, (dict, list)):
                    parts.append(f"[{key}]: {json.dumps(value, default=str)[:500]}")
                else:
                    parts.append(f"[{key}]: {str(value)[:500]}")
            context_str = "\n".join(parts)

        if self._memory:
            try:
                if hasattr(self._memory, "recent_stm"):
                    recent = self._memory.recent_stm(limit=5)
                    if recent:
                        context_str += f"\n[recent_memories]: {'; '.join(recent[:3])}"
            except Exception:
                pass

        augmented = f"Context:\n{context_str}\n\nTask:\n{prompt}" if context_str else prompt

        if self._fallback and hasattr(self._fallback, "execute"):
            try:
                if asyncio.iscoroutinefunction(self._fallback.execute):
                    result = await self._fallback.execute(augmented, "complex")
                else:
                    result = self._fallback.execute(augmented, "complex")
                ir = self._fallback_result_to_intelligence(result, prompt, start)
                await self._log_lifecycle("think", prompt, ir)
                return ir
            except Exception as e:
                logger.debug("intel_think_error err=%s", e)

        ir = IntelligenceResult(
            success=False,
            error="No fallback chain available for thinking",
            latency_ms=(time.time() - start) * 1000,
        )
        await self._log_lifecycle("think", prompt, ir)
        return ir

    async def search_web(self, query: str) -> list[dict[str, Any]]:
        """Search the web using available web search tools.

        Args:
            query: Search query string.

        Returns:
            List of search result dicts.
        """
        self._web_search_count += 1
        results: list[dict[str, Any]] = []

        try:
            from src.harness.community.ddg_search.tools import web_search
            result = web_search(query)
            if result and hasattr(result, "content"):
                results.append({"source": "ddg", "content": str(result.content)[:1000]})
        except Exception as e:
            logger.debug("web_search_ddg_error err=%s", e)

        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=5):
                    results.append({"source": "duckduckgo", "title": r.get("title", ""), "href": r.get("href", ""), "body": r.get("body", "")[:500]})
        except Exception as e:
            logger.debug("web_search_ddgs_error err=%s", e)

        if not results:
            try:
                import urllib.request
                import urllib.parse
                url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    html = resp.read().decode()
                    import re
                    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)[:5]
                    for s in snippets:
                        clean = re.sub(r'<[^>]+>', '', s).strip()
                        if clean:
                            results.append({"source": "ddg-html", "snippet": clean[:500]})
            except Exception as e:
                logger.debug("web_search_urllib_error err=%s", e)

        return results

    def get_providers(self) -> list[dict[str, Any]]:
        """Get available LLM providers."""
        providers: list[dict[str, Any]] = []

        if self._router and hasattr(self._router, "get_available_providers"):
            try:
                raw = self._router.get_available_providers()
                if isinstance(raw, list):
                    providers.extend(raw)
            except Exception as e:
                logger.debug("intel_providers_error err=%s", e)

        if self._provider_hub and hasattr(self._provider_hub, "list_providers"):
            try:
                raw = self._provider_hub.list_providers()
                if isinstance(raw, list):
                    providers.extend(raw)
            except Exception:
                pass

        return providers

    def get_stats(self) -> dict[str, Any]:
        return {
            "ask_count": self._ask_count,
            "think_count": self._think_count,
            "web_search_count": self._web_search_count,
            "cache_size": len(self._cache),
            "router_wired": self._router is not None,
            "fallback_wired": self._fallback is not None,
            "provider_hub_wired": self._provider_hub is not None,
            "memory_wired": self._memory is not None,
        }

    def clear_cache(self) -> None:
        self._cache.clear()

    def _make_cache_key(self, query: str, complexity: Optional[str] = None) -> str:
        raw = f"{complexity or ''}:{query.lower().strip()}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _check_cache(self, key: str) -> Optional[IntelligenceResult]:
        entry = self._cache.get(key)
        if entry:
            ts, result = entry
            if time.time() - ts < self._cache_ttl:
                result.cached = True
                return result
            del self._cache[key]
        return None

    def _set_cache(self, key: str, result: IntelligenceResult) -> None:
        self._cache[key] = (time.time(), result)

    def _inject_context(self, query: str, context: dict[str, Any]) -> str:
        parts = [f"Context:\n{json.dumps({k: str(v)[:200] for k, v in context.items()}, indent=2)}", "", f"Query:\n{query}"]
        return "\n".join(parts)

    def _fallback_result_to_intelligence(self, fb_result: Any, query: str, start: float) -> IntelligenceResult:
        latency = (time.time() - start) * 1000
        if hasattr(fb_result, "success") and fb_result.success:
            return IntelligenceResult(
                success=True,
                answer=getattr(fb_result, "response", getattr(fb_result, "content", str(fb_result))),
                provider=getattr(fb_result, "provider", "unknown"),
                model=getattr(fb_result, "model", "unknown"),
                latency_ms=latency,
                attempts=getattr(fb_result, "attempts", 1),
            )
        return IntelligenceResult(
            success=False,
            error=getattr(fb_result, "error", str(fb_result)),
            latency_ms=latency,
            attempts=getattr(fb_result, "attempts", 1),
        )

    def _route_result_to_intelligence(self, route_result: Any, query: str, start: float) -> IntelligenceResult:
        latency = (time.time() - start) * 1000
        if hasattr(route_result, "success") and route_result.success:
            return IntelligenceResult(
                success=True,
                answer=getattr(route_result, "response", getattr(route_result, "content", str(route_result))),
                provider=getattr(route_result, "provider", "unknown"),
                model=getattr(route_result, "model", "unknown"),
                latency_ms=latency,
            )
        return IntelligenceResult(
            success=False,
            error=getattr(route_result, "error", str(route_result)),
            latency_ms=latency,
        )

    async def _log_lifecycle(self, action: str, query: str, result: IntelligenceResult) -> None:
        if not self._lifecycle:
            return
        try:
            if hasattr(self._lifecycle, "record"):
                if asyncio.iscoroutinefunction(self._lifecycle.record):
                    await self._lifecycle.record(
                        "intel_query",
                        {
                            "action": action,
                            "query": query[:200],
                            "success": result.success,
                            "provider": result.provider,
                            "latency_ms": result.latency_ms,
                            "error": result.error[:100] if result.error else None,
                        },
                        source="intelligence",
                    )
        except Exception as e:
            logger.debug("intel_lifecycle_log_error err=%s", e)


import asyncio
