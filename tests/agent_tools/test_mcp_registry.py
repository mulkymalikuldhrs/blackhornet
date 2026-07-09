"""Tests for OWL-inspired MCP Registry (dynamic tool discovery)."""

import importlib.util
import unittest
import sys
import os

_src = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
_spec = importlib.util.spec_from_file_location(
    'mcp_registry',
    os.path.join(_src, 'agent_tools', 'mcp_registry.py'),
)
_mcp_registry = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mcp_registry)

MCPRegistry = _mcp_registry.MCPRegistry
MCPServerDef = _mcp_registry.MCPServerDef
MCPToolDef = _mcp_registry.MCPToolDef


class TestMCPRegistry(unittest.TestCase):

    def setUp(self):
        self.registry = MCPRegistry()

    def test_register_server(self):
        server = MCPServerDef(name="test-server", command="echo")
        self.registry.register_server(server)
        self.assertIn("test-server", self.registry.servers)

    def test_register_duplicate_server_overwrites(self):
        s1 = MCPServerDef(name="dup", command="echo")
        s2 = MCPServerDef(name="dup", command="cat")
        self.registry.register_server(s1)
        self.registry.register_server(s2)
        self.assertEqual(self.registry.servers["dup"].command, "cat")

    def test_list_tools_empty(self):
        self.assertEqual(self.registry.list_tools(), [])

    def test_discover_tools_unknown_server_returns_empty(self):
        tools = self.registry.discover_tools("nonexistent")
        self.assertEqual(tools, [])

    def test_call_tool_unknown_raises(self):
        with self.assertRaises(ValueError):
            self.registry.call_tool("ghost", {})

    def test_call_tool_no_connection_raises(self):
        self.registry.tools["orphan"] = MCPToolDef(
            name="orphan", description="", input_schema={}, server_name="nope"
        )
        with self.assertRaises(RuntimeError):
            self.registry.call_tool("orphan", {})

    def test_cleanup_clears_processes(self):
        self.registry._processes = {"stale": "placeholder"}
        self.registry.cleanup()
        self.assertEqual(self.registry._processes, {})

    def test_mcp_tool_def_defaults(self):
        t = MCPToolDef(name="x", description="desc", input_schema={}, server_name="srv")
        self.assertEqual(t.name, "x")
        self.assertEqual(t.server_name, "srv")

    def test_mcp_server_def_defaults(self):
        s = MCPServerDef(name="s", command="/bin/true")
        self.assertEqual(s.args, [])
        self.assertEqual(s.env, {})

    def test_registry_repr(self):
        self.assertIsInstance(self.registry.list_tools(), list)


if __name__ == "__main__":
    unittest.main()
