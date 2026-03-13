import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from open_medicine.graphrag.server.auth import require_api_key


class TestAuth:
    def _make_app(self, valid_keys: set[str]) -> TestClient:
        app = FastAPI()

        @app.get("/protected")
        async def protected(api_key: str = require_api_key(valid_keys)):
            return {"status": "ok"}

        @app.get("/health")
        async def health():
            return {"status": "healthy"}

        return TestClient(app)

    def test_valid_key_allowed(self):
        client = self._make_app({"test-key-123"})
        resp = client.get("/protected", headers={"Authorization": "Bearer test-key-123"})
        assert resp.status_code == 200

    def test_missing_key_rejected(self):
        client = self._make_app({"test-key-123"})
        resp = client.get("/protected")
        assert resp.status_code == 401

    def test_invalid_key_rejected(self):
        client = self._make_app({"test-key-123"})
        resp = client.get("/protected", headers={"Authorization": "Bearer wrong-key"})
        assert resp.status_code == 403

    def test_health_no_auth(self):
        client = self._make_app({"test-key-123"})
        resp = client.get("/health")
        assert resp.status_code == 200
