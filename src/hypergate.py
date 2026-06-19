#!/usr/bin/env python3
"""
HYPERGATE — Autonomous LLM Gateway Bridge
==========================================
Integrates ProxyGateLLM into HermesQuantOS as the primary LLM access layer.

ProxyGateLLM provides:
  - 9+ free LLM providers with auto-failover
  - SHA256 caching (no duplicate API calls)
  - Health-check + automatic provider rotation
  - OpenAI-compatible API

This bridge:
  - Auto-discovers ProxyGateLLM (local or remote)
  - Routes all agent LLM calls through ProxyGateLLM
  - Falls back to direct API if ProxyGateLLM unavailable
  - Caches responses locally (secondary cache layer)
  - Reports provider health to swarm

This ELIMINATES the single-provider rate-limit problem.
Agents ALWAYS have a working LLM connection.
"""

import os
import sys
import json
import time
import hashlib
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone

logger = logging.getLogger("HyperGate")

# ── Configuration ──────────────────────────────────────────────────────
PROXYGATE_DIR = Path(os.getenv("PROXYGATE_DIR", 
    Path(__file__).parent.parent.parent / "ProxyGateLLM"))
PROXYGATE_PORT = int(os.getenv("PROXYGATE_PORT", "3000"))
PROXYGATE_HOST = os.getenv("PROXYGATE_HOST", "localhost")
PROXYGATE_URL = os.getenv("PROXYGATE_URL", 
    f"http://{PROXYGATE_HOST}:{PROXYGATE_PORT}")

# ── Direct API fallbacks ────────────────────────────────────────────────
DIRECT_PROVIDERS = {
    "nvidia": {
        "api_key": os.getenv("NVIDIA_API_KEY", ""),
        "base_url": "https://integrate.api.nvidia.com/v1",
        "model": "moonshotai/kimi-k2.6",
    },
    "groq": {
        "api_key": os.getenv("GROQ_API_KEY", ""),
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.1-8b-instant",
    },
    "openrouter": {
        "api_key": os.getenv("OPENROUTER_API_KEY", ""),
        "base_url": "https://openrouter.ai/api/v1",
        "model": "anthropic/claude-haiku",
    },
}


class HyperGate:
    """
    Universal LLM access layer.
    Primary: ProxyGateLLM (auto-failover, caching)
    Fallback: Direct API providers
    """

    def __init__(self):
        self.proxygate_available = False
        self.proxygate_process = None
        self.active_provider = None
        self.cache: Dict[str, Dict] = {}
        self.stats = {
            "requests_total": 0,
            "requests_cached": 0,
            "requests_proxygate": 0,
            "requests_direct": 0,
            "failovers": 0,
        }
        self._ensure_proxygate()

    # ── ProxyGateLLM Management ───────────────────────────────────────

    def _ensure_proxygate(self) -> bool:
        """Start ProxyGateLLM if available, or discover remote instance."""
        # Check if already running
        if self._check_proxygate_health():
            self.proxygate_available = True
            logger.info(f"ProxyGateLLM found at {PROXYGATE_URL}")
            return True

        # Try to start locally
        if PROXYGATE_DIR.exists():
            logger.info("Starting ProxyGateLLM locally...")
            try:
                # Node.js check
                node_bin = subprocess.run(
                    ["which", "node"], capture_output=True, text=True
                ).stdout.strip() or "node"

                self.proxygate_process = subprocess.Popen(
                    [node_bin, "index.js"],
                    cwd=str(PROXYGATE_DIR),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env={**os.environ, "PORT": str(PROXYGATE_PORT)}
                )
                # Wait for startup
                for _ in range(10):
                    time.sleep(1)
                    if self._check_proxygate_health():
                        self.proxygate_available = True
                        logger.info(f"ProxyGateLLM started on port {PROXYGATE_PORT}")
                        return True

                logger.warning("ProxyGateLLM started but not responding")
            except Exception as e:
                logger.warning(f"Could not start ProxyGateLLM: {e}")

        logger.info("ProxyGateLLM unavailable — using direct API fallback")
        return False

    def _check_proxygate_health(self) -> bool:
        """Check if ProxyGateLLM is healthy."""
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{PROXYGATE_URL}/health",
                headers={"User-Agent": "HermesQuantOS/4.0"}
            )
            resp = urllib.request.urlopen(req, timeout=3)
            return resp.status == 200
        except Exception:
            return False

    # ── Provider Discovery ────────────────────────────────────────────

    def discover_providers(self) -> List[Dict]:
        """Discover all available LLM providers (ProxyGate + direct)."""
        providers = []

        # ProxyGateLLM provides 9+ providers
        if self.proxygate_available:
            try:
                import urllib.request
                req = urllib.request.Request(
                    f"{PROXYGATE_URL}/providers",
                    headers={"User-Agent": "HermesQuantOS/4.0"}
                )
                resp = urllib.request.urlopen(req, timeout=5)
                data = json.loads(resp.read())
                for p in data.get("providers", []):
                    providers.append({
                        "name": p.get("name", "unknown"),
                        "status": p.get("status", "unknown"),
                        "source": "proxygate",
                        "free": p.get("free", False),
                    })
            except Exception:
                pass

        # Direct providers
        for name, config in DIRECT_PROVIDERS.items():
            if config["api_key"]:
                providers.append({
                    "name": name,
                    "status": "configured",
                    "source": "direct",
                    "model": config["model"],
                })

        return providers

    # ── Smart Completion ───────────────────────────────────────────────

    def complete(self, messages: List[Dict], 
                 model: str = None,
                 max_tokens: int = 1000,
                 temperature: float = 0.7,
                 cache: bool = True) -> Optional[Dict]:
        """
        Get LLM completion — routes through ProxyGateLLM first,
        falls back to direct API providers.

        Returns: {"content": "...", "model": "...", "provider": "..."}
        """
        self.stats["requests_total"] += 1

        # Check cache
        if cache:
            cache_key = self._cache_key(messages, model, temperature)
            if cache_key in self.cache:
                self.stats["requests_cached"] += 1
                return self.cache[cache_key]

        # Try ProxyGateLLM first
        if self.proxygate_available:
            result = self._call_proxygate(messages, model, max_tokens, temperature)
            if result:
                self.stats["requests_proxygate"] += 1
                if cache:
                    self.cache[self._cache_key(messages, model, temperature)] = result
                return result

        # Fallback to direct providers
        result = self._call_direct(messages, model, max_tokens, temperature)
        if result:
            self.stats["requests_direct"] += 1
            self.stats["failovers"] += 1
            if cache:
                self.cache[self._cache_key(messages, model, temperature)] = result
            return result

        logger.error("All LLM providers failed")
        return None

    # ── ProxyGateLLM Call ─────────────────────────────────────────────

    def _call_proxygate(self, messages: List[Dict], model: str,
                        max_tokens: int, temperature: float) -> Optional[Dict]:
        """Call ProxyGateLLM OpenAI-compatible endpoint."""
        try:
            import urllib.request
            body = json.dumps({
                "model": model or "auto",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }).encode()
            req = urllib.request.Request(
                f"{PROXYGATE_URL}/v1/chat/completions",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "HermesQuantOS/4.0"
                },
                method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=60)
            data = json.loads(resp.read())
            choice = data["choices"][0]["message"]
            return {
                "content": choice["content"],
                "model": data.get("model", "unknown"),
                "provider": f"proxygate/{data.get('provider', 'auto')}",
                "usage": data.get("usage", {}),
            }
        except Exception as e:
            logger.debug(f"ProxyGateLLM call failed: {e}")
            return None

    # ── Direct API Call ────────────────────────────────────────────────

    def _call_direct(self, messages: List[Dict], model: str,
                     max_tokens: int, temperature: float) -> Optional[Dict]:
        """Call direct API providers in priority order."""
        for name, config in DIRECT_PROVIDERS.items():
            if not config["api_key"]:
                continue
            try:
                result = self._call_openai_compatible(
                    config["base_url"], config["api_key"],
                    model or config["model"], messages,
                    max_tokens, temperature
                )
                if result:
                    result["provider"] = f"direct/{name}"
                    return result
            except Exception as e:
                logger.debug(f"Direct {name} failed: {e}")
        return None

    def _call_openai_compatible(self, base_url: str, api_key: str,
                                 model: str, messages: List[Dict],
                                 max_tokens: int, temperature: float) -> Optional[Dict]:
        """Generic OpenAI-compatible API call."""
        import urllib.request
        body = json.dumps({
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode()
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=60)
        data = json.loads(resp.read())
        return {
            "content": data["choices"][0]["message"]["content"],
            "model": data.get("model", model),
            "usage": data.get("usage", {}),
        }

    # ── Cache ─────────────────────────────────────────────────────────

    def _cache_key(self, messages: List[Dict], model: str, temp: float) -> str:
        raw = json.dumps({"m": messages, "md": model, "t": temp}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    # ── Status ─────────────────────────────────────────────────────────

    def status(self) -> Dict:
        return {
            "proxygate_available": self.proxygate_available,
            "proxygate_url": PROXYGATE_URL if self.proxygate_available else None,
            "providers_available": len(self.discover_providers()),
            "cache_entries": len(self.cache),
            "stats": self.stats,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def stop(self):
        if self.proxygate_process:
            self.proxygate_process.terminate()
            logger.info("ProxyGateLLM stopped")


# ── Standalone ────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="HyperGate — LLM Gateway Bridge")
    parser.add_argument("--status", action="store_true", help="Show gateway status")
    parser.add_argument("--providers", action="store_true", help="List available providers")
    parser.add_argument("--start", action="store_true", help="Start ProxyGateLLM")
    parser.add_argument("--test", action="store_true", help="Test LLM connectivity")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, 
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')

    gate = HyperGate()

    if args.status:
        print(json.dumps(gate.status(), indent=2, default=str))
    elif args.providers:
        print(json.dumps(gate.discover_providers(), indent=2))
    elif args.test:
        result = gate.complete(
            [{"role": "user", "content": "Say HERMES ONLINE in one word"}],
            max_tokens=10
        )
        if result:
            print(f"✅ {result['content']} (via {result['provider']})")
        else:
            print("❌ All providers failed")
    elif args.start:
        gate._ensure_proxygate()
        print(f"ProxyGateLLM: {'ONLINE' if gate.proxygate_available else 'OFFLINE'}")
    else:
        print("Usage: hypergate.py [--status|--providers|--test|--start]")

    gate.stop()


if __name__ == "__main__":
    main()
