import json

from open_medicine.graphrag.graph.queries import LoaderQueries, ReasoningQueries
from open_medicine.graphrag.graph.schema import (
    Guideline, LogicNode, LogicNodeType, Condition,
)


class TestLoaderQueries:
    def test_delete_guideline_returns_two_queries(self):
        queries = LoaderQueries.delete_guideline("g1")
        assert len(queries) == 2
        assert all("DELETE" in q[0] for q in queries)
        assert all(q[1]["gid"] == "g1" for q in queries)

    def test_create_guideline(self):
        g = Guideline(id="g1", title="T", doi="10.1/x", year=2024, organization="O", total_pages=10)
        cypher, params = LoaderQueries.create_guideline(g)
        assert "Guideline" in cypher
        assert params["id"] == "g1"

    def test_create_evidence_chunk(self):
        cypher, params = LoaderQueries.create_evidence_chunk("c1", "text", "g1", "s1")
        assert "EvidenceChunk" in cypher
        assert params["id"] == "c1"

    def test_create_sourced_from(self):
        cypher, params = LoaderQueries.create_sourced_from("ln1", "c1")
        assert "SOURCED_FROM" in cypher
        assert params["lid"] == "ln1"
        assert params["cid"] == "c1"

    def test_create_evaluates(self):
        cypher, params = LoaderQueries.create_evaluates("ln1", "eGFR")
        assert "EVALUATES" in cypher
        assert params["lid"] == "ln1"
        assert params["vid"] == "eGFR"

    def test_create_patient_variable(self):
        cypher, params = LoaderQueries.create_patient_variable("eGFR", "eGFR", "mL/min/1.73m2", "77147-7", "continuous")
        assert "PatientVariable" in cypher
        assert "MERGE" in cypher

    def test_create_conflicts_with(self):
        cypher, params = LoaderQueries.create_conflicts_with("ln1", "ln2", "newer")
        assert "CONFLICTS_WITH" in cypher
        assert params["resolution"] == "newer"

    def test_create_interacts_with(self):
        cypher, params = LoaderQueries.create_interacts_with("drug_a", "drug_b")
        assert "INTERACTS_WITH" in cypher

    def test_create_belongs_to(self):
        cypher, params = LoaderQueries.create_belongs_to("c1", "g1")
        assert "BELONGS_TO" in cypher

    def test_create_child_of(self):
        cypher, params = LoaderQueries.create_child_of("child", "parent")
        assert "CHILD_OF" in cypher

    def test_create_defined_by(self):
        cypher, params = LoaderQueries.create_defined_by("ln1", "g1")
        assert "DEFINED_BY" in cypher

    def test_create_participates_in(self):
        cypher, params = LoaderQueries.create_participates_in("c1", "ln1", "intervention")
        assert "PARTICIPATES_IN" in cypher
        assert params["role"] == "intervention"

    def test_create_logic_node(self):
        conds_json = json.dumps([{"variable": "eGFR", "operator": "<", "threshold": 25}])
        cypher, params = LoaderQueries.create_logic_node("ln1", "dosing", conds_json, "contraindicated", "Detail", "Strong/A", "g1", 10)
        assert "LogicNode" in cypher
        assert params["type"] == "dosing"

    def test_create_concept(self):
        cypher, params = LoaderQueries.create_concept("apixaban", "Apixaban", "drug", "703899003", None)
        assert "MERGE" in cypher
        assert "Concept" in cypher


class TestReasoningQueries:
    def test_find_logic_nodes_basic(self):
        cypher, params = ReasoningQueries.find_logic_nodes("dosing", ["apixaban"])
        assert "PARTICIPATES_IN" in cypher
        assert "SOURCED_FROM" in cypher
        assert params["intent"] == "dosing"
        assert params["concepts"] == ["apixaban"]

    def test_find_logic_nodes_with_filter(self):
        cypher, params = ReasoningQueries.find_logic_nodes("dosing", ["apixaban"], guideline_filter="af_2023")
        assert "gfilter" in params
        assert "guideline_id" in cypher

    def test_find_logic_nodes_returns_distinct(self):
        cypher, _ = ReasoningQueries.find_logic_nodes("dosing", ["x"])
        assert "DISTINCT" in cypher

    def test_vector_search(self):
        cypher, params = ReasoningQueries.vector_search([0.1, 0.2], limit=5)
        assert "vector" in cypher.lower()
        assert params["limit"] == 5

    def test_graph_enhanced_context(self):
        cypher, params = ReasoningQueries.graph_enhanced_context("c1")
        assert "CHILD_OF" in cypher
        assert "SOURCED_FROM" in cypher
        assert params["id"] == "c1"

    def test_get_evidence_chunk(self):
        cypher, params = ReasoningQueries.get_evidence_chunk("c1")
        assert "EvidenceChunk" in cypher
        assert params["id"] == "c1"

    def test_list_guidelines(self):
        cypher, params = ReasoningQueries.list_guidelines()
        assert "Guideline" in cypher

    def test_find_conflicts(self):
        cypher, params = ReasoningQueries.find_conflicts(["ln1", "ln2"])
        assert "CONFLICTS_WITH" in cypher
