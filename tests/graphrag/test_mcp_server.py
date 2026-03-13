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

    def test_all_tools_have_input_schema(self):
        for t in TOOL_DEFINITIONS:
            assert "inputSchema" in t
            assert "properties" in t["inputSchema"]

    def test_total_tool_count(self):
        assert len(TOOL_DEFINITIONS) == 7
