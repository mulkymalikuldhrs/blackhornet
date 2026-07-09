"""FastAPI API layer for AI-MultiColony.

Provides the FastAPI application, middleware, Pydantic schemas,
route handlers, and WebSocket support.

Gracefully degrades when optional dependencies are missing.
"""

from __future__ import annotations

import logging as _logging

_logger = _logging.getLogger(__name__)

_api_available = False
try:
    from .app import FastAPIApp, create_app, lifespan
    from .schemas import (
        # Agent schemas
        AgentCreateRequest,
        AgentCreateResponse,
        AgentStatusResponse,
        AgentListResponse,
        AgentExecuteRequest,
        AgentExecuteResponse,
        AgentDeleteResponse,
        # Colony schemas
        ColonyCreateRequest,
        ColonyCreateResponse,
        ColonyStatusResponse,
        ColonyListResponse,
        ColonyScaleRequest,
        ColonyScaleResponse,
        # Tool schemas
        ToolListResponse,
        ToolDescribeResponse,
        ToolCallRequest,
        ToolCallResponse,
        # Memory schemas
        MemoryStoreRequest,
        MemoryStoreResponse,
        MemoryQueryRequest,
        MemoryQueryResponse,
        MemoryCompactRequest,
        MemoryCompactResponse,
        MemoryPagesResponse,
        # Task schemas
        TaskCreateRequest,
        TaskCreateResponse,
        TaskStatusResponse,
        TaskResultResponse,
        # Health/Error schemas
        HealthResponse,
        ErrorResponse,
        # WebSocket schemas
        WSMessage,
        WSTaskUpdate,
        WSHeartbeat,
        WSAlert,
        WSLog,
    )
    from .middleware import (
        AuthMiddleware,
        RateLimitMiddleware,
        RequestLoggingMiddleware,
        ErrorHandlingMiddleware,
    )
    from .routes import (
        AgentRoutes,
        ColonyRoutes,
        ToolRoutes,
        MemoryRoutes,
        TaskRoutes,
        WebSocketHandler,
    )
    _api_available = True
except ImportError as _e:
    _logger.warning("API module unavailable (install starlette+fastapi+prometheus_client): %s", _e)
    FastAPIApp = None  # type: ignore
    create_app = None  # type: ignore
    lifespan = None  # type: ignore
    AgentCreateRequest = None  # type: ignore
    AgentCreateResponse = None  # type: ignore
    AgentStatusResponse = None  # type: ignore
    AgentListResponse = None  # type: ignore
    AgentExecuteRequest = None  # type: ignore
    AgentExecuteResponse = None  # type: ignore
    AgentDeleteResponse = None  # type: ignore
    ColonyCreateRequest = None  # type: ignore
    ColonyCreateResponse = None  # type: ignore
    ColonyStatusResponse = None  # type: ignore
    ColonyListResponse = None  # type: ignore
    ColonyScaleRequest = None  # type: ignore
    ColonyScaleResponse = None  # type: ignore
    ToolListResponse = None  # type: ignore
    ToolDescribeResponse = None  # type: ignore
    ToolCallRequest = None  # type: ignore
    ToolCallResponse = None  # type: ignore
    MemoryStoreRequest = None  # type: ignore
    MemoryStoreResponse = None  # type: ignore
    MemoryQueryRequest = None  # type: ignore
    MemoryQueryResponse = None  # type: ignore
    MemoryCompactRequest = None  # type: ignore
    MemoryCompactResponse = None  # type: ignore
    MemoryPagesResponse = None  # type: ignore
    TaskCreateRequest = None  # type: ignore
    TaskCreateResponse = None  # type: ignore
    TaskStatusResponse = None  # type: ignore
    TaskResultResponse = None  # type: ignore
    HealthResponse = None  # type: ignore
    ErrorResponse = None  # type: ignore
    WSMessage = None  # type: ignore
    WSTaskUpdate = None  # type: ignore
    WSHeartbeat = None  # type: ignore
    WSAlert = None  # type: ignore
    WSLog = None  # type: ignore
    AuthMiddleware = None  # type: ignore
    RateLimitMiddleware = None  # type: ignore
    RequestLoggingMiddleware = None  # type: ignore
    ErrorHandlingMiddleware = None  # type: ignore
    AgentRoutes = None  # type: ignore
    ColonyRoutes = None  # type: ignore
    ToolRoutes = None  # type: ignore
    MemoryRoutes = None  # type: ignore
    TaskRoutes = None  # type: ignore
    WebSocketHandler = None  # type: ignore

__all__ = [
    # App
    "FastAPIApp",
    "create_app",
    "lifespan",
    # Agent schemas
    "AgentCreateRequest",
    "AgentCreateResponse",
    "AgentStatusResponse",
    "AgentListResponse",
    "AgentExecuteRequest",
    "AgentExecuteResponse",
    "AgentDeleteResponse",
    # Colony schemas
    "ColonyCreateRequest",
    "ColonyCreateResponse",
    "ColonyStatusResponse",
    "ColonyListResponse",
    "ColonyScaleRequest",
    "ColonyScaleResponse",
    # Tool schemas
    "ToolListResponse",
    "ToolDescribeResponse",
    "ToolCallRequest",
    "ToolCallResponse",
    # Memory schemas
    "MemoryStoreRequest",
    "MemoryStoreResponse",
    "MemoryQueryRequest",
    "MemoryQueryResponse",
    "MemoryCompactRequest",
    "MemoryCompactResponse",
    "MemoryPagesResponse",
    # Task schemas
    "TaskCreateRequest",
    "TaskCreateResponse",
    "TaskStatusResponse",
    "TaskResultResponse",
    # Health/Error schemas
    "HealthResponse",
    "ErrorResponse",
    # WebSocket schemas
    "WSMessage",
    "WSTaskUpdate",
    "WSHeartbeat",
    "WSAlert",
    "WSLog",
    # Middleware
    "AuthMiddleware",
    "RateLimitMiddleware",
    "RequestLoggingMiddleware",
    "ErrorHandlingMiddleware",
    # Routes
    "AgentRoutes",
    "ColonyRoutes",
    "ToolRoutes",
    "MemoryRoutes",
    "TaskRoutes",
    "WebSocketHandler",
]
