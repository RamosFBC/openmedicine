import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from open_medicine.graphrag.reasoning.types import GraphRAGResult


@pytest.fixture
def client():
    with patch("open_medicine.graphrag.server.rest_api.get_settings") as mock_settings:
        settings = MagicMock()
        settings.valid_api_keys = {"test-key"}
        settings.neo4j_uri = "bolt://localhost:7687"
        settings.neo4j_user = "neo4j"
        settings.neo4j_password = "test"
        settings.voyage_api_key = "test-voyage-key"
        mock_settings.return_value = settings

        with patch("open_medicine.graphrag.server.rest_api.GraphConnection"):
            with patch("open_medicine.graphrag.server.rest_api.ReasoningEngine") as mock_engine_cls:
                mock_engine = MagicMock()
                mock_engine.query.return_value = GraphRAGResult(
                    source="graph_traversal", matches=[], synthesis=None,
                    evidence=[], confidence="low", missing_variables=[],
                )
                mock_engine_cls.return_value = mock_engine

                with patch("open_medicine.graphrag.server.rest_api.FallbackEngine") as mock_fb_cls:
                    mock_fb = MagicMock()
                    mock_fb.query.return_value = GraphRAGResult(
                        source="llm_synthesis", matches=[], synthesis=None,
                        evidence=[], confidence="low", missing_variables=[],
                    )
                    mock_fb_cls.return_value = mock_fb

                    from open_medicine.graphrag.server.rest_api import create_app
                    app = create_app()
                    yield TestClient(app)


class TestRESTAPI:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_dosing_requires_auth(self, client):
        resp = client.post("/v1/dosing", json={"drug": "apixaban"})
        assert resp.status_code == 401

    def test_dosing_with_auth(self, client):
        resp = client.post(
            "/v1/dosing",
            json={"drug": "apixaban", "patient_vars": {"eGFR": 20}},
            headers={"Authorization": "Bearer test-key"},
        )
        assert resp.status_code == 200
        assert "source" in resp.json()

    def test_contraindications_endpoint(self, client):
        resp = client.post(
            "/v1/contraindications",
            json={"intervention": "lisinopril", "patient_vars": {}},
            headers={"Authorization": "Bearer test-key"},
        )
        assert resp.status_code == 200

    def test_query_endpoint(self, client):
        resp = client.post(
            "/v1/query",
            json={"intent": "dosing", "concepts": ["apixaban"], "patient_vars": {"eGFR": 20}},
            headers={"Authorization": "Bearer test-key"},
        )
        assert resp.status_code == 200

    def test_guidelines_list(self, client):
        resp = client.get(
            "/v1/guidelines",
            headers={"Authorization": "Bearer test-key"},
        )
        assert resp.status_code == 200
