"""Tests for the unified service app."""
import pytest
from starlette.testclient import TestClient
from open_medicine.server.config import ServiceConfig


class TestAppCreation:
    def test_create_app_returns_starlette(self):
        from open_medicine.server.app import create_app

        config = ServiceConfig(auth_mode="none")
        app = create_app(config)
        from starlette.applications import Starlette

        assert isinstance(app, Starlette)


class TestHealthEndpoint:
    def test_health_returns_200(self):
        from open_medicine.server.app import create_app

        config = ServiceConfig(auth_mode="none")
        app = create_app(config)
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["tools"] == 10
        assert data["auth_mode"] == "none"

    def test_health_accessible_with_auth_enabled(self):
        from open_medicine.server.app import create_app

        config = ServiceConfig(auth_mode="api_key", api_keys="secret")
        app = create_app(config)
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200


class TestAuthEnforcement:
    def test_mcp_rejects_unauthenticated_when_auth_enabled(self):
        from open_medicine.server.app import create_app

        config = ServiceConfig(auth_mode="api_key", api_keys="secret")
        app = create_app(config)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "initialize", "id": 1},
        )
        assert response.status_code == 401
