"""
LLM Router Python Bridge
Communicates with the JavaScript LLM Router via child process IPC.
Provides Pythonic interface while leveraging the JS router's intelligence.

Architecture:
    Python Agent <--> LLMRouterBridge <--> Node.js LLM Router <--> Multiple LLM Providers

Fallback:
    If Node.js is unavailable, falls back to direct Python LLM calls via LLMProvider.
"""
import asyncio
import json
import logging
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional, AsyncIterator
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RouterResponse:
    content: str
    provider: str
    model: str
    usage: Dict[str, int]
    latency_ms: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class LLMRouterBridge:
    """
    Bridge between Python agents and JavaScript LLM Router.

    The JS router handles:
    - Provider selection (NVIDIA, Groq, OpenCode Zen, etc.)
    - Load balancing across providers
    - Failover when providers are down
    - Token usage tracking and cost optimization
    - Request prioritization
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.router_path = self.config.get(
            "router_path",
            os.path.join(os.path.dirname(__file__), "..", "llm_router"),
        )
        self.node_path = self.config.get("node_path", "node")
        self._process: Optional[subprocess.Popen] = None
        self._ready = False
        self._timeout = self.config.get("timeout", 60)
        self._use_node = self.config.get("use_node", self._check_node_available())

        self._fallback_provider = None

        self.stats = {
            "requests": 0,
            "success": 0,
            "fallback": 0,
            "failures": 0,
        }

    def _check_node_available(self) -> bool:
        """Check if Node.js is available"""
        try:
            result = subprocess.run(
                [self.node_path, "--version"],
                capture_output=True, text=True, timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning("Node.js not available, using Python fallback LLM")
            return False

    async def start(self):
        """Start the Node.js router process"""
        if not self._use_node:
            logger.info("Using Python fallback (Node.js not available)")
            from .llm_provider import LLMProvider
            self._fallback_provider = LLMProvider(config=self.config)
            self._ready = True
            return

        main_js = os.path.join(self.router_path, "index.mjs")
        if not os.path.exists(main_js):
            main_js = os.path.join(self.router_path, "router.mjs")
        if not os.path.exists(main_js):
            import glob
            mjs_files = glob.glob(os.path.join(self.router_path, "*.mjs"))
            if mjs_files:
                main_js = mjs_files[0]
            else:
                logger.error(f"No router .mjs found in {self.router_path}")
                self._use_node = False
                from .llm_provider import LLMProvider
                self._fallback_provider = LLMProvider(config=self.config)
                self._ready = True
                return

        try:
            self._process = await asyncio.create_subprocess_exec(
                self.node_path, main_js,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, **self.config.get("env", {})},
            )
            self._ready = True
            logger.info(f"LLM Router started (PID: {self._process.pid})")
        except Exception as e:
            logger.error(f"Failed to start LLM Router: {e}")
            self._use_node = False
            from .llm_provider import LLMProvider
            self._fallback_provider = LLMProvider(config=self.config)
            self._ready = True

    async def chat(self, messages: List[Dict], **kwargs) -> RouterResponse:
        """Send chat request to router or fallback"""
        self.stats["requests"] += 1

        if self._use_node and self._process:
            try:
                return await self._node_chat(messages, **kwargs)
            except Exception as e:
                logger.warning(f"Node router failed, falling back: {e}")
                self.stats["fallback"] += 1

        return await self._python_chat(messages, **kwargs)

    async def _node_chat(self, messages: List[Dict], **kwargs) -> RouterResponse:
        """Send request to Node.js router"""
        request = {
            "type": "chat",
            "messages": messages,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 4096),
                "model": kwargs.get("model", None),
                "provider": kwargs.get("provider", None),
                "stream": kwargs.get("stream", False),
            },
        }

        import time
        start_time = time.time()

        request_json = json.dumps(request) + "\n"
        self._process.stdin.write(request_json.encode())
        await self._process.stdin.drain()

        response_line = await asyncio.wait_for(
            self._process.stdout.readline(),
            timeout=self._timeout,
        )

        elapsed = (time.time() - start_time) * 1000

        if not response_line:
            raise ConnectionError("Router process closed")

        response = json.loads(response_line.decode())

        if response.get("type") == "error":
            self.stats["failures"] += 1
            return RouterResponse(
                content="",
                provider="router",
                model="unknown",
                usage={},
                latency_ms=elapsed,
                error=response.get("message", "Unknown error"),
            )

        self.stats["success"] += 1
        return RouterResponse(
            content=response.get("content", ""),
            provider=response.get("provider", "unknown"),
            model=response.get("model", "unknown"),
            usage=response.get("usage", {}),
            latency_ms=elapsed,
            metadata=response.get("metadata", {}),
        )

    async def _python_chat(self, messages: List[Dict], **kwargs) -> RouterResponse:
        """Fallback: use Python LLM provider directly"""
        import time
        start_time = time.time()

        try:
            result = await self._fallback_provider.chat(
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 4096),
                model=kwargs.get("model"),
            )

            elapsed = (time.time() - start_time) * 1000
            self.stats["success"] += 1

            return RouterResponse(
                content=result.content,
                provider="python-fallback",
                model=result.model,
                usage={
                    "prompt_tokens": result.usage.prompt_tokens,
                    "completion_tokens": result.usage.completion_tokens,
                    "total_tokens": result.usage.total_tokens,
                },
                latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            self.stats["failures"] += 1
            return RouterResponse(
                content="",
                provider="python-fallback",
                model="unknown",
                usage={},
                latency_ms=elapsed,
                error=str(e),
            )

    async def get_providers(self) -> List[Dict]:
        """Get list of available providers from router"""
        if not self._use_node or not self._process:
            return [{"name": "python-fallback", "status": "available"}]

        request = json.dumps({"type": "get_providers"}) + "\n"
        self._process.stdin.write(request.encode())
        await self._process.stdin.drain()

        response = await asyncio.wait_for(
            self._process.stdout.readline(),
            timeout=10,
        )
        result = json.loads(response.decode())
        return result.get("providers", [])

    async def health_check(self) -> Dict[str, Any]:
        """Check router health"""
        if self._use_node and self._process:
            try:
                providers = await self.get_providers()
                return {
                    "status": "healthy",
                    "mode": "node-router",
                    "providers": providers,
                    "stats": self.stats,
                }
            except Exception as e:
                return {
                    "status": "degraded",
                    "mode": "python-fallback",
                    "error": str(e),
                    "stats": self.stats,
                }
        else:
            return {
                "status": "healthy",
                "mode": "python-fallback",
                "stats": self.stats,
            }

    async def stop(self):
        """Stop the router process"""
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5)
                logger.info("LLM Router stopped")
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
                logger.warning("LLM Router killed (didn't terminate gracefully)")
            self._process = None
        self._ready = False


def create_router(config: Optional[Dict] = None) -> LLMRouterBridge:
    return LLMRouterBridge(config=config)
