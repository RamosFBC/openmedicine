import importlib
import json
import warnings
from unittest.mock import MagicMock, patch

import pytest

from open_medicine.graphrag.server.mcp_server import TOOL_DEFINITIONS


class TestDeprecationNotice:
    def test_module_emits_deprecation_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            import open_medicine.graphrag.server.mcp_server as mod
            importlib.reload(mod)
            deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1
            assert "open-medicine-mcp" in str(deprecation_warnings[0].message)


class TestMCPToolDefinitions:
    def test_all_clinical_tools_defined(self):
        names = [t["name"] for t in TOOL_DEFINITIONS]
        assert "check_drug_dosing" in names
        assert "check_contraindications" in names
        assert "check_drug_interaction" in names
        assert "check_monitoring_requirements" in names
        assert "find_treatment_options" in names

    def test_structured_query_tool_defined(self):
        names = [t["name"] for t in TOOL_DEFINITIONS]
        assert "query_clinical_graph" in names

    def test_evidence_retrieval_tool_defined(self):
        names = [t["name"] for t in TOOL_DEFINITIONS]
        assert "fetch_evidence_chunk" in names

    def test_list_guidelines_tool_defined(self):
        names = [t["name"] for t in TOOL_DEFINITIONS]
        assert "list_available_guidelines" in names

    def test_all_tools_have_input_schema(self):
        for t in TOOL_DEFINITIONS:
            assert "inputSchema" in t
            assert "properties" in t["inputSchema"]

    def test_total_tool_count(self):
        """7 original tools + 1 new (list_available_guidelines) = 8"""
        assert len(TOOL_DEFINITIONS) == 8


class TestMCPV2Imports:
    """Verify the MCP server uses v2 engine and types."""

    def test_imports_v2_engine(self):
        import open_medicine.graphrag.server.mcp_server as mod
        source = open(mod.__file__).read()
        assert "engine_v2" in source
        assert "from open_medicine.graphrag.reasoning.engine import" not in source

    def test_imports_v2_types(self):
        import open_medicine.graphrag.server.mcp_server as mod
        source = open(mod.__file__).read()
        assert "types_v2" in source
        assert "from open_medicine.graphrag.reasoning.types import" not in source

    def test_no_fallback_engine_import(self):
        """v2 engine has built-in vector fallback -- no separate FallbackEngine needed."""
        import open_medicine.graphrag.server.mcp_server as mod
        source = open(mod.__file__).read()
        assert "FallbackEngine" not in source


class TestMCPToolHandlers:
    """Test tool handlers with mocked graph connection."""

    @pytest.fixture
    def mock_conn(self):
        conn = MagicMock()
        conn.execute_read.return_value = []
        return conn

    @pytest.fixture
    def mock_engine(self):
        from open_medicine.graphrag.reasoning.types_v2 import GraphRAGResult
        engine = MagicMock()
        engine.query.return_value = GraphRAGResult(
            confidence="high",
            data_coverage="full",
            semantic_matches=[],
            recommendation_matches=[],
            evidence=[],
            retrieval_layers_used=["direct"],
        )
        return engine

    @pytest.fixture
    def server_and_handler(self, mock_conn, mock_engine):
        with patch("open_medicine.graphrag.server.mcp_server.GraphConnection", return_value=mock_conn), \
             patch("open_medicine.graphrag.server.mcp_server.ReasoningEngine", return_value=mock_engine):
            from open_medicine.graphrag.server.mcp_server import create_mcp_server
            server = create_mcp_server()
        return server, mock_conn, mock_engine

    def test_check_drug_dosing_intent_mapping(self):
        from open_medicine.graphrag.server.mcp_server import _INTENT_MAP
        intent, get_concepts = _INTENT_MAP["check_drug_dosing"]
        assert intent == "dosing"
        assert get_concepts({"drug": "lisinopril"}) == ["lisinopril"]

    def test_check_interaction_intent_mapping(self):
        from open_medicine.graphrag.server.mcp_server import _INTENT_MAP
        intent, get_concepts = _INTENT_MAP["check_drug_interaction"]
        assert intent == "interaction"
        assert get_concepts({"drug_a": "lisinopril", "drug_b": "spironolactone"}) == ["lisinopril", "spironolactone"]

    def test_check_contraindications_intent_mapping(self):
        from open_medicine.graphrag.server.mcp_server import _INTENT_MAP
        intent, get_concepts = _INTENT_MAP["check_contraindications"]
        assert intent == "contraindication"
        assert get_concepts({"intervention": "sacubitril_valsartan"}) == ["sacubitril_valsartan"]

    def test_check_monitoring_intent_mapping(self):
        from open_medicine.graphrag.server.mcp_server import _INTENT_MAP
        intent, get_concepts = _INTENT_MAP["check_monitoring_requirements"]
        assert intent == "monitoring"
        assert get_concepts({"intervention": "spironolactone"}) == ["spironolactone"]

    def test_find_treatments_intent_mapping(self):
        from open_medicine.graphrag.server.mcp_server import _INTENT_MAP
        intent, get_concepts = _INTENT_MAP["find_treatment_options"]
        assert intent == "treatment_selection"
        assert get_concepts({"condition": "heart_failure_reduced_ef"}) == ["heart_failure_reduced_ef"]

    def test_list_guidelines_query_routing(self, mock_conn):
        """Verify list_available_guidelines routes to ReasoningQueries.list_guidelines()."""
        mock_conn.execute_read.return_value = [
            {"id": "aha_acc_hf_2022", "title": "AHA/ACC HF 2022", "doi": "10.1161/xxx", "year": 2022}
        ]
        from open_medicine.graphrag.graph.queries_v2 import ReasoningQueries
        cypher, params = ReasoningQueries.list_guidelines()
        rows = mock_conn.execute_read(cypher, params)
        assert len(rows) == 1
        assert rows[0]["id"] == "aha_acc_hf_2022"

    def test_fetch_evidence_chunk_query_routing(self, mock_conn):
        """Verify fetch_evidence_chunk routes to ReasoningQueries.get_evidence_chunk()."""
        mock_conn.execute_read.return_value = [
            {"text": "ACEi recommended...", "section": "6.1", "doi": "10.1161/xxx"}
        ]
        from open_medicine.graphrag.graph.queries_v2 import ReasoningQueries
        cypher, params = ReasoningQueries.get_evidence_chunk("chunk_123")
        rows = mock_conn.execute_read(cypher, params)
        assert len(rows) == 1
        assert "ACEi" in rows[0]["text"]


class TestMCPResultShape:
    """Verify v2 result model shape is correct for MCP serialization."""

    def test_graphrag_result_serializes_to_json(self):
        from open_medicine.graphrag.reasoning.types_v2 import GraphRAGResult
        result = GraphRAGResult(
            confidence="high",
            data_coverage="full",
            semantic_matches=[],
            recommendation_matches=[],
            evidence=[],
            retrieval_layers_used=["direct"],
        )
        data = json.loads(result.model_dump_json(indent=2))
        assert data["confidence"] == "high"
        assert data["data_coverage"] == "full"
        assert "semantic_matches" in data
        assert "recommendation_matches" in data
        assert "evidence" in data
        assert "retrieval_layers_used" in data
        assert "hints" in data

    def test_graphrag_result_includes_safety_fields(self):
        """data_coverage and hints are critical for agents to understand result quality."""
        from open_medicine.graphrag.reasoning.types_v2 import GraphRAGResult
        result = GraphRAGResult(
            confidence="low",
            data_coverage="none",
            hints=["Try 'lisinopril' instead of 'lisnopril'"],
        )
        data = json.loads(result.model_dump_json())
        assert data["data_coverage"] == "none"
        assert len(data["hints"]) == 1
