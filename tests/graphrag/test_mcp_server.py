from open_medicine.graphrag.server.mcp_server import TOOL_DEFINITIONS


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
