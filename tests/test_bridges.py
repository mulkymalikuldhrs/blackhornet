"""Tests for bridge system — TS bridge compatibility."""

from __future__ import annotations

from src.bridges.ts_bridge import TypeScriptBridge, BridgeMessage, BridgeDirection


class TestTypeScriptBridge:
    def test_create_bridge(self):
        bridge = TypeScriptBridge("bridge-1", "ts", "Test Bridge")
        assert bridge.id == "bridge-1"
        assert bridge.name == "Test Bridge"
        assert bridge.enabled is True

    def test_connect(self):
        bridge = TypeScriptBridge("bridge-2", "ts", "Connector")
        result = bridge.connect()
        assert result is True
        assert bridge.status()["connected"] is True

    def test_send(self):
        bridge = TypeScriptBridge("bridge-3", "ts", "Sender")
        msg = bridge.send("target-agent", "hello", "text")
        assert msg.direction == BridgeDirection.OUTBOUND
        assert msg.target == "target-agent"
        assert msg.content == "hello"

    def test_receive(self):
        bridge = TypeScriptBridge("bridge-4", "ts", "Receiver")
        msg = bridge.receive("source-agent", "world", "command")
        assert msg.direction == BridgeDirection.INBOUND
        assert msg.source == "source-agent"
        assert msg.content == "world"

    def test_get_messages(self):
        bridge = TypeScriptBridge("bridge-5", "ts", "Logger")
        assert len(bridge.get_messages()) == 0
        bridge.send("t", "m1")
        bridge.receive("s", "m2")
        assert len(bridge.get_messages()) == 2

    def test_status(self):
        bridge = TypeScriptBridge("bridge-6", "ts", "Status")
        status = bridge.status()
        assert status["id"] == "bridge-6"
        assert status["connected"] is False

    def test_on_handler(self):
        bridge = TypeScriptBridge("bridge-7", "ts", "Handler")
        calls = []

        def handler(payload):
            calls.append(payload)

        bridge.on("test.event", handler)
        assert True

    def test_disabled_bridge(self):
        bridge = TypeScriptBridge("bridge-8", "ts", "Disabled", enabled=False)
        result = bridge.connect()
        assert result is False
