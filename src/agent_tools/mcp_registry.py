"""OWL/CAMEL-inspired dynamic MCP toolkit registry."""
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import subprocess

logger = logging.getLogger(__name__)


@dataclass
class MCPToolDef:
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str


@dataclass
class MCPServerDef:
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)


class MCPRegistry:
    """Dynamic MCP toolkit registry - agents can discover and call tools from external servers."""

    def __init__(self):
        self.servers: Dict[str, MCPServerDef] = {}
        self.tools: Dict[str, MCPToolDef] = {}
        self._processes: Dict[str, Any] = {}

    def register_server(self, server: MCPServerDef):
        self.servers[server.name] = server

    def discover_tools(self, server_name: str) -> List[MCPToolDef]:
        """Connect to MCP server and discover available tools."""
        server = self.servers.get(server_name)
        if not server:
            logger.warning(f"Server {server_name} not registered")
            return []

        try:
            proc = subprocess.Popen(
                [server.command] + server.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**__import__('os').environ, **server.env} if server.env else None,
            )
            self._processes[server_name] = proc

            req = json.dumps({"jsonrpc": "2.0", "method": "tools/list", "id": 1})
            proc.stdin.write(req + "\n")
            proc.stdin.flush()

            resp = proc.stdout.readline()
            result = json.loads(resp)
            tools = []
            for t in result.get("result", {}).get("tools", []):
                tool = MCPToolDef(
                    name=t["name"],
                    description=t.get("description", ""),
                    input_schema=t.get("inputSchema", {}),
                    server_name=server_name,
                )
                self.tools[t["name"]] = tool
                tools.append(tool)
            return tools
        except Exception as e:
            logger.error(f"Failed to discover tools from {server_name}: {e}")
            return []

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on its registered MCP server."""
        tool = self.tools.get(tool_name)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")
        proc = self._processes.get(tool.server_name)
        if not proc:
            raise RuntimeError(f"Server {tool.server_name} not connected")

        req = json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": 1,
        })
        proc.stdin.write(req + "\n")
        proc.stdin.flush()

        resp = proc.stdout.readline()
        return json.loads(resp)

    def list_tools(self) -> List[MCPToolDef]:
        return list(self.tools.values())

    def cleanup(self):
        for proc in self._processes.values():
            try:
                proc.terminate()
            except Exception:
                pass
        self._processes.clear()
