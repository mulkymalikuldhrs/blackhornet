"""
MCP (Model Context Protocol) Server for BlackHornet.
Implements a lightweight MCP server that exposes BH agent capabilities
as MCP tools/resources. Enables LLMs to interact with BH directly.

Reference: https://modelcontextprotocol.io/
"""
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
import asyncio
import sys

logger = logging.getLogger(__name__)

try:
    from mcp.server import Server as MCPServer
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent, Resource
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    logger.warning("MCP SDK not available, using lightweight MCP implementation")


@dataclass
class MCPTool:
    name: str
    description: str
    handler: Callable
    input_schema: Dict[str, Any] = field(default_factory=lambda: {
        "type": "object",
        "properties": {},
    })


class LightweightMCPServer:
    """
    Lightweight MCP server implementation.
    Uses stdin/stdout JSON-RPC protocol for MCP communication.
    Falls back if MCP SDK is not available.
    """
    
    def __init__(self, server_name: str = "blackhornet-mcp", 
                 server_version: str = "1.0.0"):
        self.server_name = server_name
        self.server_version = server_version
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, Callable] = {}
        self._running = False
    
    def register_tool(self, name: str, description: str, 
                       handler: Callable, input_schema: Optional[Dict] = None):
        """Register an MCP tool"""
        self.tools[name] = MCPTool(
            name=name,
            description=description,
            handler=handler,
            input_schema=input_schema or {"type": "object", "properties": {}},
        )
        logger.info(f"MCP tool registered: {name}")
    
    def register_resource(self, uri: str, handler: Callable):
        """Register an MCP resource"""
        self.resources[uri] = handler
        logger.info(f"MCP resource registered: {uri}")
    
    async def handle_request(self, request: Dict) -> Dict:
        """Handle a JSON-RPC request"""
        method = request.get("method", "")
        req_id = request.get("id", None)
        params = request.get("params", {})
        
        if method == "initialize":
            return self._json_rpc_response(req_id, {
                "serverName": self.server_name,
                "serverVersion": self.server_version,
                "capabilities": {
                    "tools": {},
                    "resources": {},
                },
            })
        
        elif method == "shutdown":
            self._running = False
            return self._json_rpc_response(req_id, {})
        
        elif method == "tools/list":
            return self._json_rpc_response(req_id, {
                "tools": [
                    {
                        "name": t.name,
                        "description": t.description,
                        "inputSchema": t.input_schema,
                    }
                    for t in self.tools.values()
                ],
            })
        
        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            
            if tool_name not in self.tools:
                return self._json_rpc_error(req_id, -32601, f"Tool not found: {tool_name}")
            
            try:
                tool = self.tools[tool_name]
                result = await tool.handler(**arguments) if asyncio.iscoroutinefunction(tool.handler) else tool.handler(**arguments)
                return self._json_rpc_response(req_id, {
                    "content": [{"type": "text", "text": json.dumps(result) if not isinstance(result, str) else result}],
                })
            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")
                return self._json_rpc_error(req_id, -32603, str(e))
        
        elif method == "resources/list":
            return self._json_rpc_response(req_id, {
                "resources": [
                    {"uri": uri, "name": uri.split("/")[-1]}
                    for uri in self.resources.keys()
                ],
            })
        
        elif method == "resources/read":
            uri = params.get("uri", "")
            if uri not in self.resources:
                return self._json_rpc_error(req_id, -32601, f"Resource not found: {uri}")
            try:
                handler = self.resources[uri]
                result = await handler() if asyncio.iscoroutinefunction(handler) else handler()
                return self._json_rpc_response(req_id, {
                    "contents": [{"uri": uri, "text": json.dumps(result)}],
                })
            except Exception as e:
                return self._json_rpc_error(req_id, -32603, str(e))
        
        return self._json_rpc_error(req_id, -32601, f"Unknown method: {method}")
    
    def _json_rpc_response(self, req_id: Any, result: Dict) -> Dict:
        return {"jsonrpc": "2.0", "id": req_id, "result": result}
    
    def _json_rpc_error(self, req_id: Any, code: int, message: str) -> Dict:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}
    
    async def start(self):
        """Start MCP server (reads JSON-RPC from stdin, writes to stdout)"""
        self._running = True
        logger.info(f"MCP server '{self.server_name}' started")
        
        while self._running:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: sys.stdin.readline()
                )
                if not line:
                    break
                request = json.loads(line)
                response = await self.handle_request(request)
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
            except json.JSONDecodeError:
                logger.warning("Invalid JSON-RPC request")
            except Exception as e:
                logger.error(f"MCP server error: {e}")
    
    async def stop(self):
        self._running = False


class MCPIntegration:
    """
    Integrates BH agent capabilities as MCP tools and resources.
    Bridges MCP protocol with BH internal modules.
    """
    
    def __init__(self, server: Optional[LightweightMCPServer] = None,
                 tool_registry=None, colony_bridge=None):
        self.server = server or LightweightMCPServer()
        self.tool_registry = tool_registry
        self.colony_bridge = colony_bridge
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default BH tools"""
        
        # Agent status tool
        self.server.register_tool(
            name="agent_status",
            description="Get status of all BH agents",
            handler=self._get_agent_status,
            input_schema={"type": "object", "properties": {}},
        )
        
        # Colony info tool
        self.server.register_tool(
            name="colony_info",
            description="Get colony bridge capabilities",
            handler=self._get_colony_info,
            input_schema={"type": "object", "properties": {}},
        )
        
        # Execute task tool
        self.server.register_tool(
            name="execute_task",
            description="Execute a task through an agent",
            handler=self._execute_task,
            input_schema={
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Task description"},
                    "agent_type": {"type": "string", "description": "Agent type (optional)"},
                },
                "required": ["task"],
            },
        )
        
        # Memory tools
        self.server.register_tool(
            name="memory_search",
            description="Search agent memory",
            handler=self._memory_search,
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "description": "Max results"},
                },
                "required": ["query"],
            },
        )
        
        # Register default resources
        self.server.register_resource("mcp://blackhornet/status", self._get_agent_status)
        self.server.register_resource("mcp://blackhornet/capabilities", self._get_colony_info)
    
    async def _get_agent_status(self) -> Dict:
        """Get agent status"""
        return {
            "status": "running",
            "timestamp": datetime.now().isoformat(),
            "agents": ["blackhornet", "manus", "planner", "executor"],
        }
    
    async def _get_colony_info(self) -> Dict:
        """Get colony bridge capabilities"""
        if self.colony_bridge:
            try:
                caps = self.colony_bridge.get_capabilities() if hasattr(self.colony_bridge, 'get_capabilities') else []
                return {"capabilities": caps}
            except Exception:
                pass
        return {"capabilities": []}
    
    async def _execute_task(self, task: str, agent_type: str = "blackhornet") -> Dict:
        """Execute a task"""
        return {
            "status": "queued",
            "task": task,
            "agent": agent_type,
            "timestamp": datetime.now().isoformat(),
        }
    
    async def _memory_search(self, query: str, limit: int = 10) -> Dict:
        """Search agent memory"""
        return {
            "query": query,
            "results": [],
            "count": 0,
        }
    
    def get_server(self) -> LightweightMCPServer:
        return self.server
