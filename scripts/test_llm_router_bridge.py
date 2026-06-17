"""Test LLM Router Bridge"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio


async def test():
    from src.core.llm_router_bridge import LLMRouterBridge

    bridge = LLMRouterBridge(config={"use_node": False})
    await bridge.start()

    health = await bridge.health_check()
    print(f"Health: {health['status']}, mode: {health['mode']}")

    response = await bridge.chat([
        {"role": "user", "content": "Say hello in one word"},
    ])
    print(f"Response: {response.content[:100]}")
    print(f"Provider: {response.provider}")
    print(f"Latency: {response.latency_ms:.0f}ms")
    print("TEST PASSED")


asyncio.run(test())
