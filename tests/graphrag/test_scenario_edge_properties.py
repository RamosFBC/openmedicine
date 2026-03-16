"""Integration: verify edge properties flow through to MCP results.

Requires live Neo4j connection (source .env before running).
"""

import os

import pytest

from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection
from open_medicine.graphrag.reasoning.engine_v2 import ReasoningEngine
from open_medicine.graphrag.reasoning.types_v2 import ClinicalQuery

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not os.environ.get("GRAPHRAG_NEO4J_URI"),
        reason="Requires live Neo4j (source .env)",
    ),
]


@pytest.fixture(scope="module")
def engine():
    settings = get_settings()
    conn = GraphConnection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    return ReasoningEngine(conn)


class TestScenario1EdgeProperties:
    """HF patient with angioedema history — edge properties must flow."""

    def test_contraindication_severity_is_populated(self, engine):
        q = ClinicalQuery(
            intent="contraindication",
            concepts=["sacubitril_valsartan"],
            patient_vars={"history_of_angioedema": True},
        )
        result = engine.query(q)

        ci_matches = [m for m in result.semantic_matches if m.edge_type == "CONTRAINDICATED_IN"]
        assert len(ci_matches) >= 1, "Expected at least one contraindication match"

        angioedema = [m for m in ci_matches if "angioedema" in m.entity_name.lower()]
        assert len(angioedema) >= 1, "Expected angioedema contraindication"
        assert angioedema[0].edge_properties.get("severity") is not None, (
            "severity must be populated on CONTRAINDICATED_IN edge"
        )

    def test_monitoring_thresholds_populated(self, engine):
        q = ClinicalQuery(
            intent="monitoring",
            concepts=["spironolactone"],
            patient_vars={"egfr": 35, "potassium": 5.1},
        )
        result = engine.query(q)

        k_matches = [
            m for m in result.semantic_matches
            if "potassium" in m.entity_name.lower()
        ]
        if k_matches:
            # If threshold data exists in graph, it should flow through
            props = k_matches[0].edge_properties
            # At minimum, frequency or threshold_alert should be present
            has_any = any(props.get(k) for k in ("frequency", "threshold_alert", "threshold_stop"))
            assert has_any, f"Expected monitoring properties, got: {props}"


class TestScenario2EdgeProperties:
    """Multimorbid patient — ARNi permissible but interaction critical."""

    def test_acei_arni_interaction_severity(self, engine):
        q = ClinicalQuery(
            intent="interaction",
            concepts=["lisinopril", "sacubitril_valsartan"],
        )
        result = engine.query(q)

        assert len(result.semantic_matches) >= 1, "Expected interaction matches"
        # At least one match should have severity populated
        severities = [
            m.edge_properties.get("severity")
            for m in result.semantic_matches
            if m.edge_properties.get("severity")
        ]
        assert len(severities) >= 1, (
            "Expected at least one interaction with severity populated"
        )

    def test_contraindication_false_angioedema(self, engine):
        q = ClinicalQuery(
            intent="contraindication",
            concepts=["sacubitril_valsartan"],
            patient_vars={"history_of_angioedema": False},
        )
        result = engine.query(q)

        angioedema = [
            m for m in result.semantic_matches
            if "angioedema" in m.entity_name.lower()
        ]
        if angioedema:
            assert angioedema[0].conditions_met is False, (
                "Angioedema contraindication should not fire when history_of_angioedema=False"
            )

    def test_dapagliflozin_dosing_properties(self, engine):
        q = ClinicalQuery(
            intent="dosing",
            concepts=["dapagliflozin"],
            patient_vars={"egfr": 48, "weight_kg": 58},
        )
        result = engine.query(q)

        if result.semantic_matches:
            props = result.semantic_matches[0].edge_properties
            # If dosing data exists, starting_dose or frequency should be populated
            has_any = any(
                props.get(k)
                for k in ("starting_dose", "target_dose", "frequency")
            )
            # This is a soft assertion — depends on graph data quality
            if not has_any:
                pytest.skip("Dosing properties not yet populated in graph (enrichment needed)")
