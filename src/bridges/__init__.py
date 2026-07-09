"""Bridges — cross-language, cross-platform bridge system.

Inspired by Autonomous Organism's BaseBridge architecture.
Supports TS bridge compatibility, Python bridges, and cross-colony communication.
"""

from src.bridges.ts_bridge import TypeScriptBridge, BridgeMessage

__all__ = ["TypeScriptBridge", "BridgeMessage"]
