"""Test MCP server"""
import sys; import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import json
import asyncio

from src.mcp.mcp_server import LightweightMCPServer, MCPIntegration

async def test():
    # Test server creation
    server = LightweightMCPServer()
    
    # Register a test tool
    server.register_tool("ping", "Test tool", lambda: {"pong": True})
    
    # Test JSON-RPC handling
    response = await server.handle_request({
        "jsonrpc": "2.0", "id": 1, "method": "initialize"
    })
    assert "result" in response
    assert response["result"]["serverName"] == "blackhornet-mcp"
    print("Initialize OK")
    
    # Test tool listing
    response = await server.handle_request({
        "jsonrpc": "2.0", "id": 2, "method": "tools/list"
    })
    assert len(response["result"]["tools"]) >= 1
    print(f"Tools list: {len(response['result']['tools'])} tools")
    
    # Test tool call
    response = await server.handle_request({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "ping", "arguments": {}}
    })
    assert "result" in response
    print("Tool call OK")
    
    # Test MCPIntegration
    integration = MCPIntegration(server=server)
    status = await integration._get_agent_status()
    assert status["status"] == "running"
    print("Integration OK")
    
    print("ALL MCP TESTS PASSED")

asyncio.run(test())
