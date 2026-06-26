"""Hermes Agent-inspired subagent RPC pipeline for inter-agent communication."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import json
import uuid

class RPCMethod(Enum):
    EXECUTE = "execute"
    QUERY = "query"
    STATUS = "status"
    CANCEL = "cancel"

@dataclass
class RPCRequest:
    method: RPCMethod
    params: Dict[str, Any] = field(default_factory=dict)
    request_id: str = ""
    source: str = ""

    def __post_init__(self):
        if not self.request_id:
            self.request_id = f"rpc-{uuid.uuid4().hex[:8]}"

@dataclass
class RPCResponse:
    request_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None

class RPCPipeline:
    """Pipelines RPC requests between subagents with routing and response handling."""

    def __init__(self):
        self.handlers: Dict[RPCMethod, Callable] = {}
        self.pending: Dict[str, RPCRequest] = {}
        self.results: Dict[str, RPCResponse] = {}

    def register_handler(self, method: RPCMethod, handler: Callable):
        self.handlers[method] = handler

    def send_request(self, request: RPCRequest) -> str:
        self.pending[request.request_id] = request
        return request.request_id

    def process_request(self, request: RPCRequest) -> RPCResponse:
        handler = self.handlers.get(request.method)
        if not handler:
            return RPCResponse(request_id=request.request_id, success=False, error=f"No handler for {request.method}")
        try:
            result = handler(**request.params)
            response = RPCResponse(request_id=request.request_id, success=True, result=result)
            self.results[request.request_id] = response
            return response
        except Exception as e:
            return RPCResponse(request_id=request.request_id, success=False, error=str(e))

    def get_response(self, request_id: str) -> Optional[RPCResponse]:
        return self.results.get(request_id)

    def cleanup(self, max_age: int = 300):
        """Clean up old pending requests."""
        self.pending.clear()
