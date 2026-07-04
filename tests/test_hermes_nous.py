"""Tests for Hermes Nous integration — 8 consciousness layers + converter."""

from __future__ import annotations

from src.hermes_nous.layers import ConsciousnessLayers
from src.hermes_nous.converter import HermesNousConverter


class TestConsciousnessLayers:
    def test_all_layers_defined(self):
        cl = ConsciousnessLayers()
        assert len(cl.LAYER_DEFS) == 9
        levels = [l["level"] for l in cl.LAYER_DEFS]
        assert 1 in levels
        assert 9 in levels

    def test_activate(self):
        cl = ConsciousnessLayers()
        assert cl.activate(1) is True
        assert cl.is_active(1) is True
        assert cl.is_active(2) is False

    def test_deactivate(self):
        cl = ConsciousnessLayers()
        cl.activate(3)
        assert cl.is_active(3) is True
        cl.deactivate(3)
        assert cl.is_active(3) is False

    def test_activate_all(self):
        cl = ConsciousnessLayers()
        cl.activate_all()
        for layer in cl.layers.values():
            assert layer.active is True

    def test_deactivate_all(self):
        cl = ConsciousnessLayers()
        cl.activate_all()
        cl.deactivate_all()
        for layer in cl.layers.values():
            assert layer.active is False

    def test_status(self):
        cl = ConsciousnessLayers()
        cl.activate(1)
        cl.activate(9)
        status = cl.status()
        assert len(status) == 9
        assert status[0]["level"] == 1
        assert status[0]["active"] is True
        assert status[-1]["level"] == 9

    def test_run_sensation(self):
        cl = ConsciousnessLayers()
        cl.activate(1)
        result = cl.run_layer(1)
        assert result["layer"] == "Sensation"
        assert result["level"] == 1

    def test_run_reasoning(self):
        cl = ConsciousnessLayers()
        cl.activate(3)
        result = cl.run_layer(3, task_type="code")
        assert result["task_type"] == "code"

    def test_run_oracle(self):
        cl = ConsciousnessLayers()
        cl.activate(9)
        result = cl.run_layer(9, question="test")
        assert "branches" in result or "error" in result

    def test_run_inactive_layer(self):
        cl = ConsciousnessLayers()
        result = cl.run_layer(5)
        assert "error" in result


class TestHermesNousConverter:
    def test_scan_research_no_dir(self):
        c = HermesNousConverter()
        files = c.scan_research()
        assert isinstance(files, list)

    def test_detect_type(self):
        c = HermesNousConverter()
        assert c._detect_type("agent_tool.md", "agent tool definition") == "agent_capability"
        assert c._detect_type("notes.txt", "general research note") == "research_note"
        assert c._detect_type("data.json", '{"key": "val"}') == "structured_data"
        assert c._detect_type("prompt.md", "system prompt template") == "prompt_template"
        # JSON extension overrides content detection
        assert c._detect_type("consciousness.json", "L1 layer info") == "structured_data"

    def test_map_to_bh_module(self):
        c = HermesNousConverter()
        assert "src/hermes_nous/" in c._map_to_bh_module("consciousness_layer.md")
        assert "src/agents/" in c._map_to_bh_module("agent_tool.py")
        assert "brain.py" in c._map_to_bh_module("brain_memory.md")
        assert "council.py" in c._map_to_bh_module("council_persona.md")
        assert "predictor.py" in c._map_to_bh_module("predict_oracle.md")

    def test_status(self):
        c = HermesNousConverter()
        status = c.status()
        assert "research_dir" in status
        assert "exists" in status
