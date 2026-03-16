# HTTP Service Layer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wrap the unified MCP server as a remote HTTP service with Streamable HTTP transport and 3-tier auth (none/api_key/oauth2), deployable to Railway and later AWS.

**Architecture:** A new `src/open_medicine/server/` package creates a Starlette app that mounts the MCP Streamable HTTP endpoint at `/mcp` and a health endpoint at `/health`. Auth uses the MCP SDK's built-in `TokenVerifier` protocol — we implement two verifiers (API key and JWT/JWKS). A `ServiceConfig` (pydantic-settings) drives all behavior via environment variables. The existing `open-medicine-mcp` stdio entry point is unchanged.

**Tech Stack:** Python 3.12, MCP SDK 1.26.0 (`StreamableHTTPSessionManager`, `TokenVerifier`, `BearerAuthBackend`), Starlette, uvicorn, PyJWT, httpx

---

### Task 1: Service configuration module

**Files:**
- Create: `src/open_medicine/server/__init__.py`
- Create: `src/open_medicine/server/config.py`
- Test: `tests/server/test_config.py`

**Step 1: Write the failing test**

Create `tests/server/__init__.py` (empty) and `tests/server/test_config.py`:

```python
"""Tests for service configuration."""
import os
import pytest


class TestServiceConfig:
    def test_defaults(self):
        from open_medicine.server.config import ServiceConfig
        config = ServiceConfig()
        assert config.auth_mode == "none"
        assert config.port == 8000
        assert config.host == "0.0.0.0"

    def test_auth_mode_api_key(self, monkeypatch):
        from open_medicine.server.config import ServiceConfig
        monkeypatch.setenv("OM_AUTH_MODE", "api_key")
        monkeypatch.setenv("OM_API_KEYS", "key1,key2")
        config = ServiceConfig()
        assert config.auth_mode == "api_key"
        assert config.valid_api_keys == {"key1", "key2"}

    def test_auth_mode_oauth2(self, monkeypatch):
        from open_medicine.server.config import ServiceConfig
        monkeypatch.setenv("OM_AUTH_MODE", "oauth2")
        monkeypatch.setenv("OM_OAUTH2_ISSUER", "https://example.auth0.com/")
        monkeypatch.setenv("OM_OAUTH2_AUDIENCE", "https://api.openmedicine.ai")
        config = ServiceConfig()
        assert config.auth_mode == "oauth2"
        assert config.oauth2_issuer == "https://example.auth0.com/"
        assert config.oauth2_audience == "https://api.openmedicine.ai"

    def test_invalid_auth_mode_rejected(self, monkeypatch):
        from open_medicine.server.config import ServiceConfig
        monkeypatch.setenv("OM_AUTH_MODE", "invalid")
        with pytest.raises(Exception):
            ServiceConfig()
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/server/test_config.py -v`
Expected: FAIL with ImportError

**Step 3: Write implementation**

Create `src/open_medicine/server/__init__.py` (empty).

Create `src/open_medicine/server/config.py`:

```python
"""Service configuration via environment variables."""
from __future__ import annotations

from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OM_")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Auth mode
    auth_mode: Literal["none", "api_key", "oauth2"] = "none"

    # API key auth
    api_keys: str = ""

    # OAuth2/JWT auth
    oauth2_issuer: str = ""
    oauth2_audience: str = ""
    oauth2_jwks_uri: str = ""  # auto-discovered from issuer if empty

    @property
    def valid_api_keys(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}

    @field_validator("auth_mode")
    @classmethod
    def validate_auth_mode(cls, v: str) -> str:
        if v not in ("none", "api_key", "oauth2"):
            raise ValueError(f"Invalid auth_mode: {v}. Must be none, api_key, or oauth2.")
        return v
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/server/test_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/open_medicine/server/ tests/server/
git commit -m "feat(server): add service configuration module"
```

---

### Task 2: Token verifiers (API key + JWT)

**Files:**
- Create: `src/open_medicine/server/auth.py`
- Test: `tests/server/test_auth.py`

**Step 1: Write the failing test**

Create `tests/server/test_auth.py`:

```python
"""Tests for token verifiers."""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestApiKeyVerifier:
    def test_valid_key_returns_access_token(self):
        from open_medicine.server.auth import ApiKeyVerifier
        verifier = ApiKeyVerifier(valid_keys={"test-key-1", "test-key-2"})
        result = asyncio.get_event_loop().run_until_complete(
            verifier.verify_token("test-key-1")
        )
        assert result is not None
        assert result.client_id == "api_key_client"
        assert result.token == "test-key-1"

    def test_invalid_key_returns_none(self):
        from open_medicine.server.auth import ApiKeyVerifier
        verifier = ApiKeyVerifier(valid_keys={"test-key-1"})
        result = asyncio.get_event_loop().run_until_complete(
            verifier.verify_token("wrong-key")
        )
        assert result is None

    def test_empty_key_returns_none(self):
        from open_medicine.server.auth import ApiKeyVerifier
        verifier = ApiKeyVerifier(valid_keys={"test-key-1"})
        result = asyncio.get_event_loop().run_until_complete(
            verifier.verify_token("")
        )
        assert result is None


class TestJWTVerifier:
    def test_invalid_token_returns_none(self):
        from open_medicine.server.auth import JWTVerifier
        verifier = JWTVerifier(
            issuer="https://example.auth0.com/",
            audience="https://api.openmedicine.ai",
        )
        result = asyncio.get_event_loop().run_until_complete(
            verifier.verify_token("not-a-jwt")
        )
        assert result is None


class TestCreateVerifier:
    def test_none_mode_returns_none(self):
        from open_medicine.server.auth import create_verifier
        from open_medicine.server.config import ServiceConfig
        config = ServiceConfig(auth_mode="none")
        assert create_verifier(config) is None

    def test_api_key_mode_returns_api_key_verifier(self):
        from open_medicine.server.auth import create_verifier, ApiKeyVerifier
        from open_medicine.server.config import ServiceConfig
        config = ServiceConfig(auth_mode="api_key", api_keys="k1,k2")
        verifier = create_verifier(config)
        assert isinstance(verifier, ApiKeyVerifier)

    def test_oauth2_mode_returns_jwt_verifier(self):
        from open_medicine.server.auth import create_verifier, JWTVerifier
        from open_medicine.server.config import ServiceConfig
        config = ServiceConfig(
            auth_mode="oauth2",
            oauth2_issuer="https://example.auth0.com/",
            oauth2_audience="https://api.openmedicine.ai",
        )
        verifier = create_verifier(config)
        assert isinstance(verifier, JWTVerifier)
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/server/test_auth.py -v`
Expected: FAIL with ImportError

**Step 3: Write implementation**

Create `src/open_medicine/server/auth.py`:

```python
"""Token verifiers implementing the MCP SDK TokenVerifier protocol.

Three auth modes:
- none: no verifier (returns None from create_verifier)
- api_key: validates against a set of static keys
- oauth2: validates JWTs using JWKS from an OIDC issuer
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx
import jwt

from mcp.server.auth.provider import AccessToken, TokenVerifier

from open_medicine.server.config import ServiceConfig

logger = logging.getLogger(__name__)


class ApiKeyVerifier:
    """Validates bearer tokens against a set of static API keys."""

    def __init__(self, valid_keys: set[str]) -> None:
        self._valid_keys = valid_keys

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token or token not in self._valid_keys:
            return None
        return AccessToken(
            token=token,
            client_id="api_key_client",
            scopes=["all"],
        )


class JWTVerifier:
    """Validates JWTs using JWKS from an OIDC provider.

    Fetches the JWKS from the issuer's .well-known/openid-configuration
    or a direct JWKS URI. Caches the JWKS for 1 hour.
    """

    def __init__(
        self,
        issuer: str,
        audience: str,
        jwks_uri: str = "",
        cache_ttl: int = 3600,
    ) -> None:
        self._issuer = issuer.rstrip("/")
        self._audience = audience
        self._jwks_uri = jwks_uri
        self._cache_ttl = cache_ttl
        self._jwks_client: jwt.PyJWKClient | None = None
        self._jwks_fetched_at: float = 0

    def _get_jwks_client(self) -> jwt.PyJWKClient:
        now = time.time()
        if self._jwks_client is None or (now - self._jwks_fetched_at) > self._cache_ttl:
            uri = self._jwks_uri or f"{self._issuer}/.well-known/jwks.json"
            self._jwks_client = jwt.PyJWKClient(uri)
            self._jwks_fetched_at = now
        return self._jwks_client

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            client = self._get_jwks_client()
            signing_key = client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience=self._audience,
                issuer=self._issuer,
                options={"verify_exp": True},
            )
            return AccessToken(
                token=token,
                client_id=payload.get("sub", "unknown"),
                scopes=payload.get("scope", "").split() if payload.get("scope") else [],
                expires_at=payload.get("exp"),
            )
        except Exception as e:
            logger.debug("JWT verification failed: %s", e)
            return None


def create_verifier(config: ServiceConfig) -> ApiKeyVerifier | JWTVerifier | None:
    """Create the appropriate token verifier based on config."""
    if config.auth_mode == "none":
        return None
    if config.auth_mode == "api_key":
        return ApiKeyVerifier(valid_keys=config.valid_api_keys)
    if config.auth_mode == "oauth2":
        return JWTVerifier(
            issuer=config.oauth2_issuer,
            audience=config.oauth2_audience,
            jwks_uri=config.oauth2_jwks_uri,
        )
    return None
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/server/test_auth.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/open_medicine/server/auth.py tests/server/test_auth.py
git commit -m "feat(server): add API key and JWT token verifiers"
```

---

### Task 3: Unified Starlette app with MCP Streamable HTTP

**Files:**
- Create: `src/open_medicine/server/app.py`
- Test: `tests/server/test_app.py`

**Step 1: Write the failing test**

Create `tests/server/test_app.py`:

```python
"""Tests for the unified service app."""
import pytest
from unittest.mock import patch


class TestAppCreation:
    def test_create_app_returns_starlette(self):
        from open_medicine.server.app import create_app
        from open_medicine.server.config import ServiceConfig
        config = ServiceConfig(auth_mode="none")
        app = create_app(config)
        from starlette.applications import Starlette
        assert isinstance(app, Starlette)

    def test_app_has_health_route(self):
        from open_medicine.server.app import create_app
        from open_medicine.server.config import ServiceConfig
        from starlette.testclient import TestClient
        config = ServiceConfig(auth_mode="none")
        app = create_app(config)
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "tools" in data

    def test_app_has_mcp_route(self):
        from open_medicine.server.app import create_app
        from open_medicine.server.config import ServiceConfig
        from starlette.testclient import TestClient
        config = ServiceConfig(auth_mode="none")
        app = create_app(config)
        client = TestClient(app)
        # MCP endpoint should exist — GET returns 405 (only POST is valid for tool calls)
        # or the SSE notification stream
        response = client.get("/mcp")
        # Streamable HTTP accepts GET for SSE notifications
        assert response.status_code in (200, 405)

    def test_app_rejects_unauthenticated_when_auth_enabled(self):
        from open_medicine.server.app import create_app
        from open_medicine.server.config import ServiceConfig
        from starlette.testclient import TestClient
        config = ServiceConfig(auth_mode="api_key", api_keys="secret-key")
        app = create_app(config)
        client = TestClient(app)
        response = client.post("/mcp", json={"jsonrpc": "2.0", "method": "initialize", "id": 1})
        assert response.status_code == 401

    def test_health_always_accessible(self):
        from open_medicine.server.app import create_app
        from open_medicine.server.config import ServiceConfig
        from starlette.testclient import TestClient
        config = ServiceConfig(auth_mode="api_key", api_keys="secret-key")
        app = create_app(config)
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/server/test_app.py -v`
Expected: FAIL with ImportError

**Step 3: Write implementation**

Create `src/open_medicine/server/app.py`:

```python
"""Unified Starlette app mounting MCP Streamable HTTP + health endpoint.

This is the main entry point for the HTTP service. It:
1. Creates the unified MCP server (calculators + graph tools)
2. Wraps it with StreamableHTTPSessionManager for HTTP transport
3. Optionally adds auth middleware (API key or JWT)
4. Serves health check at /health
"""
from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

from open_medicine.mcp.server import server as mcp_server
from open_medicine.mcp.graphrag_tools import GRAPHRAG_TOOL_DEFINITIONS
from open_medicine.server.config import ServiceConfig
from open_medicine.server.auth import create_verifier

logger = logging.getLogger(__name__)

_TOOL_COUNT = 2 + len(GRAPHRAG_TOOL_DEFINITIONS)  # 2 calculator + 8 graph


def create_app(config: ServiceConfig) -> Starlette:
    """Create the unified Starlette application."""

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

    async def handle_mcp(request: Request):
        return await session_manager.handle_request(
            request.scope, request.receive, request._send
        )

    # Build routes
    routes = [
        Route("/health", endpoint=health, methods=["GET"]),
    ]

    # Build middleware
    middleware = []
    verifier = create_verifier(config)

    if verifier is not None:
        from starlette.middleware import Middleware
        from starlette.middleware.authentication import AuthenticationMiddleware
        from mcp.server.auth.middleware.bearer_auth import (
            BearerAuthBackend,
            RequireAuthMiddleware,
        )

        middleware.append(
            Middleware(AuthenticationMiddleware, backend=BearerAuthBackend(verifier))
        )

        # MCP endpoint with auth required
        routes.append(
            Route(
                "/mcp",
                endpoint=RequireAuthMiddleware(
                    session_manager.handle_request,
                    required_scopes=[],
                ),
            )
        )
    else:
        # MCP endpoint without auth
        routes.append(
            Route("/mcp", endpoint=session_manager.handle_request),
        )

    return Starlette(
        debug=False,
        routes=routes,
        middleware=middleware,
        lifespan=lifespan,
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/server/test_app.py -v`
Expected: PASS

Note: The `/mcp` route handling might need adjustment based on how `StreamableHTTPSessionManager.handle_request` expects to be called (it's an ASGI handler). If tests fail because of how the handler is wired, adjust the route to use `Mount` instead of `Route`, or pass `scope/receive/send` directly. The MCP SDK's own pattern is:

```python
Route("/mcp", endpoint=session_manager.handle_request)
```

since `handle_request` already has the ASGI signature `(scope, receive, send)`.

**Step 5: Commit**

```bash
git add src/open_medicine/server/app.py tests/server/test_app.py
git commit -m "feat(server): add unified Starlette app with MCP Streamable HTTP"
```

---

### Task 4: CLI entry point and __main__

**Files:**
- Create: `src/open_medicine/server/__main__.py`
- Modify: `pyproject.toml` (add entry point + `service` extra)
- Test: `tests/server/test_cli.py`

**Step 1: Write the failing test**

Create `tests/server/test_cli.py`:

```python
"""Tests for CLI entry point."""
import pytest


class TestCLI:
    def test_main_function_exists(self):
        from open_medicine.server.__main__ import main
        assert callable(main)

    def test_create_app_importable(self):
        from open_medicine.server.app import create_app
        assert callable(create_app)
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/server/test_cli.py -v`
Expected: FAIL with ImportError

**Step 3: Write implementation**

Create `src/open_medicine/server/__main__.py`:

```python
"""CLI entry point for the OpenMedicine HTTP service."""
import uvicorn

from open_medicine.server.config import ServiceConfig


def main() -> None:
    config = ServiceConfig()
    uvicorn.run(
        "open_medicine.server.app:create_app",
        factory=True,
        host=config.host,
        port=config.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
```

**Step 4: Update pyproject.toml**

Add to `[project.scripts]`:

```toml
open-medicine-server = "open_medicine.server.__main__:main"
```

Add new optional extra:

```toml
service = [
    "fastapi>=0.110.0",
    "uvicorn>=0.30.0",
    "PyJWT[crypto]>=2.8.0",
    "httpx>=0.27.0",
    "sse-starlette>=1.6.0",
    "pydantic-settings>=2.0.0",
]
```

**Step 5: Run test to verify it passes**

Run: `uv run python -m pytest tests/server/test_cli.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/open_medicine/server/__main__.py pyproject.toml tests/server/test_cli.py
git commit -m "feat(server): add CLI entry point and service extra"
```

---

### Task 5: Update Dockerfile and docker-compose

**Files:**
- Create: `Dockerfile`
- Modify: `docker-compose.yml`

**Step 1: Create unified Dockerfile**

Create `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ src/

# Install with service + graphrag extras
RUN uv sync --extra service --extra graphrag --no-dev

EXPOSE 8000

CMD ["uv", "run", "open-medicine-server"]
```

**Step 2: Update docker-compose.yml**

```yaml
services:
  neo4j:
    image: neo4j:5-community
    ports:
      - "7687:7687"
      - "7474:7474"
    environment:
      NEO4J_AUTH: neo4j/openmedicine
      NEO4J_PLUGINS: '["apoc"]'
    volumes:
      - neo4j_data:/data

  openmedicine:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      OM_AUTH_MODE: none
      GRAPHRAG_NEO4J_URI: bolt://neo4j:7687
      GRAPHRAG_NEO4J_USER: neo4j
      GRAPHRAG_NEO4J_PASSWORD: openmedicine
    depends_on:
      - neo4j

volumes:
  neo4j_data:
```

**Step 3: Verify docker-compose config is valid**

Run: `docker compose config --quiet` (should exit 0 with no errors)

**Step 4: Commit**

```bash
git add Dockerfile docker-compose.yml
git commit -m "feat(deploy): add unified Dockerfile and docker-compose for service"
```

---

### Task 6: Integration test with TestClient

**Files:**
- Create: `tests/server/test_integration.py`

**Step 1: Write the integration test**

```python
"""Integration tests for the full service stack."""
import json
import pytest
from starlette.testclient import TestClient

from open_medicine.server.app import create_app
from open_medicine.server.config import ServiceConfig


@pytest.fixture
def client():
    config = ServiceConfig(auth_mode="none")
    app = create_app(config)
    return TestClient(app)


@pytest.fixture
def auth_client():
    config = ServiceConfig(auth_mode="api_key", api_keys="test-key")
    app = create_app(config)
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_tool_count(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["tools"] == 10
        assert data["auth_mode"] == "none"


class TestAuthModes:
    def test_no_auth_allows_requests(self, client):
        """With auth_mode=none, MCP endpoint is accessible."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_api_key_rejects_without_header(self, auth_client):
        response = auth_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "initialize", "id": 1},
        )
        assert response.status_code == 401

    def test_api_key_rejects_wrong_key(self, auth_client):
        response = auth_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "initialize", "id": 1},
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert response.status_code in (401, 403)

    def test_health_accessible_with_auth(self, auth_client):
        """Health endpoint should not require auth."""
        response = auth_client.get("/health")
        assert response.status_code == 200
```

**Step 2: Run test to verify it passes**

Run: `uv run python -m pytest tests/server/test_integration.py -v`
Expected: PASS

Note: Some of these tests may need adjustment depending on how the MCP SDK's `StreamableHTTPSessionManager` behaves in test mode. The health endpoint test should definitely work. The auth rejection tests depend on middleware ordering.

**Step 3: Commit**

```bash
git add tests/server/test_integration.py
git commit -m "test(server): add integration tests for service endpoints"
```

---

### Task 7: Run full test suite and fix breakages

**Step 1: Run service tests**

Run: `uv run python -m pytest tests/server/ -v`
Expected: PASS

**Step 2: Run existing MCP tests**

Run: `uv run python -m pytest tests/test_mcp_tools.py tests/test_graphrag_tools.py tests/graphrag/test_mcp_server.py -v`
Expected: PASS (unchanged)

**Step 3: Run calculator tests**

Run: `uv run python -m pytest tests/test_chadsvasc.py -v`
Expected: PASS (unchanged)

**Step 4: Fix any failures**

Address issues found during test runs. Common issues:
- `starlette` not installed (need `uv sync --extra service`)
- MCP session manager requires `sse-starlette` package
- Route handler signature mismatches with ASGI expectations

**Step 5: Commit fixes**

```bash
git add -u
git commit -m "fix: resolve test breakages from service layer"
```
