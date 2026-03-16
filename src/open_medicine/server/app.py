"""Unified Starlette app mounting MCP Streamable HTTP + health endpoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount

from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

from open_medicine.mcp.server import server as mcp_server
from open_medicine.mcp.graphrag_tools import GRAPHRAG_TOOL_DEFINITIONS
from open_medicine.server.config import ServiceConfig
from open_medicine.server.auth import create_verifier

logger = logging.getLogger(__name__)

_TOOL_COUNT = 2 + len(GRAPHRAG_TOOL_DEFINITIONS)


def create_app(config: ServiceConfig | None = None) -> Starlette:
    """Create the unified Starlette application."""
    if config is None:
        config = ServiceConfig()

    session_manager = StreamableHTTPSessionManager(
        app=mcp_server,
        json_response=False,
        stateless=False,
    )

    @asynccontextmanager
    async def lifespan(app):
        async with session_manager.run():
            logger.info("OpenMedicine service started (auth=%s)", config.auth_mode)
            yield
        logger.info("OpenMedicine service stopped")

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({
            "status": "healthy",
            "tools": _TOOL_COUNT,
            "auth_mode": config.auth_mode,
        })

    routes: list = [
        Route("/health", endpoint=health, methods=["GET"]),
    ]

    verifier = create_verifier(config)

    if verifier is not None:
        from mcp.server.auth.middleware.bearer_auth import (
            BearerAuthBackend,
            RequireAuthMiddleware,
        )

        mcp_app = RequireAuthMiddleware(
            app=session_manager.handle_request,
            required_scopes=[],
        )
        routes.append(Mount("/mcp", app=mcp_app))
    else:
        routes.append(Mount("/mcp", app=session_manager.handle_request))

    middleware = []
    if verifier is not None:
        from starlette.middleware import Middleware
        from starlette.middleware.authentication import AuthenticationMiddleware
        from mcp.server.auth.middleware.bearer_auth import BearerAuthBackend

        middleware.append(
            Middleware(AuthenticationMiddleware, backend=BearerAuthBackend(verifier))
        )

    return Starlette(
        debug=False,
        routes=routes,
        middleware=middleware,
        lifespan=lifespan,
    )
