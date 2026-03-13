import json
import pytest
from unittest.mock import MagicMock
from open_medicine.graphrag.reasoning.engine import ReasoningEngine
from open_medicine.graphrag.reasoning.types import ClinicalQuery


def _mock_conn_with_results(read_results: list[dict], conflict_results: list[dict] | None = None) -> MagicMock:
    conn = MagicMock()
    if conflict_results is not None:
        conn.execute_read.side_effect = [read_results, conflict_results]
    else:
        conn.execute_read.side_effect = [read_results, []]
    return conn


class TestConditionEvaluation:
    def test_numeric_less_than_matches(self):
        engine = ReasoningEngine.__new__(ReasoningEngine)
        cond = {"variable": "eGFR", "operator": "<", "threshold": 30}
        assert engine._evaluate_condition(cond, {"eGFR": 20}) is True

    def test_numeric_less_than_no_match(self):
        engine = ReasoningEngine.__new__(ReasoningEngine)
        cond = {"variable": "eGFR", "operator": "<", "threshold": 30}
        assert engine._evaluate_condition(cond, {"eGFR": 50}) is False

    def test_equals_string(self):
        engine = ReasoningEngine.__new__(ReasoningEngine)
        cond = {"variable": "pregnancy", "operator": "==", "threshold": "true"}
        assert engine._evaluate_condition(cond, {"pregnancy": "true"}) is True

    def test_missing_variable(self):
        engine = ReasoningEngine.__new__(ReasoningEngine)
        cond = {"variable": "weight_kg", "operator": ">", "threshold": 60}
        result = engine._evaluate_condition(cond, {"eGFR": 20})
        assert result is None


class TestReasoningEngine:
    def test_query_returns_graph_traversal_on_match(self):
        mock_results = [
            {
                "ln_id": "ln_001", "ln_type": "dosing", "ln_action": "contraindicated",
                "ln_detail": "Do not use", "ln_strength": "Strong/A",
                "ln_conditions": json.dumps([{"variable": "eGFR", "operator": "<", "threshold": 25}]),
                "ln_page": 47,
                "ec_id": "c1", "ec_text": "Source text here",
                "g_title": "AF Guideline", "g_doi": "10.1234/af", "g_year": 2023,
                "ec_section": "dosing",
            }
        ]
        conn = _mock_conn_with_results(mock_results)
        engine = ReasoningEngine(conn)
        query = ClinicalQuery(intent="dosing", concepts=["apixaban"], patient_vars={"eGFR": 20})
        result = engine.query(query)
        assert result.source == "graph_traversal"
        assert len(result.matches) == 1
        assert result.matches[0].conditions_met is True
        assert result.confidence == "high"

    def test_partial_match_flagged(self):
        mock_results = [
            {
                "ln_id": "ln_001", "ln_type": "dosing", "ln_action": "dose_adjust",
                "ln_detail": "Reduce dose", "ln_strength": "Strong/A",
                "ln_conditions": json.dumps([
                    {"variable": "eGFR", "operator": "<", "threshold": 30},
                    {"variable": "weight_kg", "operator": "<", "threshold": 60},
                ]),
                "ln_page": 47,
                "ec_id": "c1", "ec_text": "Source",
                "g_title": "Guideline", "g_doi": "10.1/x", "g_year": 2023,
                "ec_section": "dosing",
            }
        ]
        conn = _mock_conn_with_results(mock_results)
        engine = ReasoningEngine(conn)
        query = ClinicalQuery(intent="dosing", concepts=["apixaban"], patient_vars={"eGFR": 20})
        result = engine.query(query)
        assert result.matches[0].conditions_met is False
        assert "weight_kg" in result.matches[0].missing_variables

    def test_no_matches_returns_empty(self):
        conn = _mock_conn_with_results([])
        engine = ReasoningEngine(conn)
        query = ClinicalQuery(intent="dosing", concepts=["unknowndrug"])
        result = engine.query(query)
        assert result.source == "graph_traversal"
        assert len(result.matches) == 0
        assert result.confidence == "low"

    def test_results_ranked_by_year_and_strength(self):
        mock_results = [
            {
                "ln_id": "ln_old", "ln_type": "dosing", "ln_action": "initiate",
                "ln_detail": "Old rec", "ln_strength": "Weak/C",
                "ln_conditions": json.dumps([]),
                "ln_page": 10,
                "ec_id": "c1", "ec_text": "Old",
                "g_title": "Old Guide", "g_doi": "10.1/old", "g_year": 2018,
                "ec_section": "dosing",
            },
            {
                "ln_id": "ln_new", "ln_type": "dosing", "ln_action": "initiate",
                "ln_detail": "New rec", "ln_strength": "Strong/A",
                "ln_conditions": json.dumps([]),
                "ln_page": 20,
                "ec_id": "c2", "ec_text": "New",
                "g_title": "New Guide", "g_doi": "10.1/new", "g_year": 2023,
                "ec_section": "dosing",
            },
        ]
        conn = _mock_conn_with_results(mock_results)
        engine = ReasoningEngine(conn)
        query = ClinicalQuery(intent="dosing", concepts=["drug"])
        result = engine.query(query)
        assert result.matches[0].logic_node_id == "ln_new"

    def test_deduplication_by_logic_node_id(self):
        """Same LogicNode appearing via two EvidenceChunks should be deduplicated."""
        mock_results = [
            {
                "ln_id": "ln_001", "ln_type": "dosing", "ln_action": "dose_adjust",
                "ln_detail": "Reduce", "ln_strength": "Strong/A",
                "ln_conditions": json.dumps([]),
                "ln_page": 10,
                "ec_id": "c1", "ec_text": "Source 1",
                "g_title": "Guide", "g_doi": "10.1/x", "g_year": 2023,
                "ec_section": "dosing",
            },
            {
                "ln_id": "ln_001", "ln_type": "dosing", "ln_action": "dose_adjust",
                "ln_detail": "Reduce", "ln_strength": "Strong/A",
                "ln_conditions": json.dumps([]),
                "ln_page": 10,
                "ec_id": "c2", "ec_text": "Source 2",
                "g_title": "Guide", "g_doi": "10.1/x", "g_year": 2023,
                "ec_section": "dosing",
            },
        ]
        conn = _mock_conn_with_results(mock_results)
        engine = ReasoningEngine(conn)
        query = ClinicalQuery(intent="dosing", concepts=["drug"])
        result = engine.query(query)
        assert len(result.matches) == 1
        assert len(result.evidence) == 2  # both citations kept
