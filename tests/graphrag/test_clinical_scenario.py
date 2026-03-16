"""Realistic clinical scenario: consume the live GraphRAG to make clinical decisions.

Queries the existing AHA/ACC/HFSA Heart Failure guideline graph — no data loading.
Each test class represents a real clinical decision a physician would make for a
complex HFrEF patient, validating that the graph returns complete, precise,
and actionable information.

Clinical scenario:
──────────────────
Patient: 68-year-old male
Diagnosis: HFrEF (LVEF 30%), Stage C
Comorbidities: CKD stage 3 (eGFR 38), Type 2 Diabetes
Current meds: Lisinopril 10mg, Metoprolol Succinate 50mg, Furosemide 40mg
Clinical question: Optimize GDMT per 2022 AHA/ACC/HFSA guidelines

Run with:
  source .env && uv run python -m pytest tests/graphrag/test_clinical_scenario.py -v
"""

import os

import pytest

from open_medicine.graphrag.reasoning.types_v2 import ClinicalQuery


def _neo4j_uri() -> str:
    """Resolve Neo4j URI, fixing SSL for Aura (neo4j+s → neo4j+ssc)."""
    uri = os.environ.get("GRAPHRAG_NEO4J_URI", os.environ.get("NEO4J_URI", ""))
    # Neo4j Aura uses self-signed certs that macOS Python can't verify
    if "neo4j+s://" in uri:
        uri = uri.replace("neo4j+s://", "neo4j+ssc://")
    return uri


pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not _neo4j_uri(),
        reason="GRAPHRAG_NEO4J_URI / NEO4J_URI not set — skipping integration tests",
    ),
]


@pytest.fixture(scope="module")
def conn():
    from open_medicine.graphrag.graph.connection import GraphConnection

    uri = _neo4j_uri()
    user = os.environ.get("GRAPHRAG_NEO4J_USER", os.environ.get("NEO4J_USER", "neo4j"))
    password = os.environ.get(
        "GRAPHRAG_NEO4J_PASSWORD", os.environ.get("NEO4J_PASSWORD", "openmedicine")
    )
    c = GraphConnection(uri, user, password)
    yield c
    c.close()


@pytest.fixture(scope="module")
def engine(conn):
    from open_medicine.graphrag.reasoning.engine_v2 import ReasoningEngine

    return ReasoningEngine(conn)


# ═══════════════════════════════════════════════════════════════════════
# DECISION 1: What treatments are indicated for this patient's HFrEF?
#
# The 4 pillars of GDMT: ARNi, Beta Blocker, MRA, SGLT2i
# All should be Class I (strong_for) with Level A (high) evidence.
# ═══════════════════════════════════════════════════════════════════════


class TestTreatmentSelection:
    """Clinician asks: 'What GDMT should this HFrEF patient be on?'"""

    def test_all_four_pillars_returned(self, engine):
        result = engine.query(ClinicalQuery(
            intent="treatment_selection",
            concepts=["HFrEF"],
            patient_vars={"LVEF": 30},
            include_evidence=False,
        ))

        assert result.confidence == "high"
        names = {m.entity_name for m in result.semantic_matches}

        # All 4 GDMT pillars must be present
        assert any("ARNi" in n or "Sacubitril" in n for n in names), (
            f"ARNi missing from HFrEF treatments. Got: {names}"
        )
        assert "Beta Blocker" in names, f"Beta Blocker missing. Got: {names}"
        assert "MRA" in names, f"MRA missing. Got: {names}"
        assert "SGLT2 Inhibitor" in names, f"SGLT2i missing. Got: {names}"

    def test_arni_is_strong_for_with_high_evidence(self, engine):
        """ARNi should be Class I / Level A — the strongest recommendation."""
        result = engine.query(ClinicalQuery(
            intent="treatment_selection",
            concepts=["HFrEF"],
            patient_vars={"LVEF": 30},
            include_evidence=False,
        ))

        arni = next(
            (m for m in result.semantic_matches if "ARNi" in m.entity_name),
            None,
        )
        assert arni is not None, "ARNi not found in treatment results"
        assert arni.strength == "strong_for", f"ARNi strength should be strong_for, got {arni.strength}"
        assert arni.evidence_quality == "high", f"ARNi evidence should be high, got {arni.evidence_quality}"

    def test_individual_drugs_also_returned(self, engine):
        """Besides drug classes, individual drugs like Carvedilol, Dapagliflozin
        should appear — giving the clinician concrete prescribing options."""
        result = engine.query(ClinicalQuery(
            intent="treatment_selection",
            concepts=["HFrEF"],
            patient_vars={"LVEF": 30},
            include_evidence=False,
        ))

        names = {m.entity_name for m in result.semantic_matches}
        # At least some individual drugs should appear
        individual_drugs = names & {
            "Sacubitril/Valsartan", "Carvedilol", "Metoprolol Succinate",
            "Bisoprolol", "Spironolactone", "Eplerenone",
            "Dapagliflozin", "Empagliflozin",
        }
        assert len(individual_drugs) >= 3, (
            f"Expected individual drug names, only found: {individual_drugs}"
        )

    def test_evidence_available_in_graph(self, conn):
        """Recommendations should have evidence chains (SOURCED_FROM → EvidenceChunk)
        with DOIs traceable via DEFINED_BY → Guideline."""
        rows = conn.execute_read(
            "MATCH (rec:Recommendation)-[:RECOMMENDS]->(e {name: 'ARNi'}) "
            "MATCH (rec)-[:DEFINED_BY]->(g:Guideline) "
            "OPTIONAL MATCH (rec)-[:SOURCED_FROM]->(ec:EvidenceChunk) "
            "RETURN rec.id AS rid, g.doi AS doi, ec.text AS text LIMIT 3"
        )
        assert len(rows) > 0, "No recommendations found for ARNi"
        for row in rows:
            assert row["doi"], f"Recommendation {row['rid']} missing DOI"


# ═══════════════════════════════════════════════════════════════════════
# DECISION 2: Lisinopril dosing — does this patient need dose adjustment?
#
# The graph has Lisinopril DOSED_FOR HFrEF with conditions on LVEF and
# HF_stage. The engine should find and evaluate these.
# ═══════════════════════════════════════════════════════════════════════


class TestDosingDecision:
    """Clinician asks: 'What dose of Lisinopril for this HFrEF patient?'"""

    def test_lisinopril_dosing_found(self, engine):
        result = engine.query(ClinicalQuery(
            intent="dosing",
            concepts=["Lisinopril", "HFrEF"],
            patient_vars={"LVEF": 30},
            include_evidence=False,
        ))

        assert result.confidence != "low", (
            f"Dosing query should find results. Got confidence={result.confidence}"
        )
        assert len(result.semantic_matches) > 0, "No dosing matches found"

    def test_dosing_conditions_evaluated(self, engine):
        """The LVEF ≤40 condition on lisinopril dosing should be evaluated."""
        result = engine.query(ClinicalQuery(
            intent="dosing",
            concepts=["Lisinopril", "HFrEF"],
            patient_vars={"LVEF": 30, "HF_stage": "C"},
            include_evidence=False,
        ))

        conditional_matches = [m for m in result.semantic_matches if m.conditions_json]
        assert len(conditional_matches) > 0, "No conditional dosing found"
        # LVEF=30 meets ≤40 and HF_stage=C meets ==C
        assert any(m.conditions_met for m in conditional_matches), (
            "Patient with LVEF=30, HF_stage=C should meet dosing conditions"
        )


# ═══════════════════════════════════════════════════════════════════════
# DECISION 3: Drug interactions — is it safe to combine these drugs?
#
# Real data: ACEi ↔ ARNi (36h washout required),
#            Sacubitril/Valsartan ↔ ACEi/ARB/MRA,
#            NSAID ↔ Loop Diuretic
# ═══════════════════════════════════════════════════════════════════════


class TestDrugInteractions:
    """Clinician asks: 'Any interactions with the current regimen?'"""

    def test_acei_arni_interaction_detected(self, engine):
        """ACEi + ARNi is a critical interaction (36h washout required)."""
        result = engine.query(ClinicalQuery(
            intent="interaction",
            concepts=["ACE Inhibitor"],
            include_evidence=False,
        ))

        interacting = {m.entity_name for m in result.semantic_matches}
        assert any("ARNi" in n or "Sacubitril" in n for n in interacting), (
            f"ACEi-ARNi interaction not detected. Found: {interacting}"
        )

    def test_sacubitril_valsartan_interactions_comprehensive(self, engine):
        """Sacubitril/Valsartan interacts with multiple drug classes."""
        result = engine.query(ClinicalQuery(
            intent="interaction",
            concepts=["Sacubitril/Valsartan"],
            include_evidence=False,
        ))

        interacting = {m.entity_name for m in result.semantic_matches}
        assert len(interacting) >= 2, (
            f"Expected multiple interactions for Sacubitril/Valsartan. Got: {interacting}"
        )

    def test_nsaid_loop_diuretic_interaction_in_graph(self, conn):
        """NSAIDs + Loop Diuretics reduce diuretic efficacy — important for HF.

        Note: The NSAID node in the graph was created with a non-canonical ID
        (drug_class:nsaid vs atc:M01A), so the engine can't resolve it via
        link_entity. We verify the edge exists directly in the graph to confirm
        the clinical data is present — the ID mismatch is a known ingestion gap.
        """
        rows = conn.execute_read(
            "MATCH (n)-[:INTERACTS_WITH]-(m) "
            "WHERE toLower(n.name) CONTAINS 'nsaid' "
            "RETURN m.name AS interactor"
        )
        interactors = {r["interactor"] for r in rows}
        assert "Loop Diuretic" in interactors, (
            f"NSAID-Loop Diuretic interaction not in graph. Got: {interactors}"
        )


# ═══════════════════════════════════════════════════════════════════════
# DECISION 4: Contraindications — what can't we prescribe?
#
# Real data: ACEi/ARB/ARNi → Angioedema (absolute)
#            Cox-2 Inhibitor → HFrEF (strong_against)
# ═══════════════════════════════════════════════════════════════════════


class TestContraindications:
    """Clinician asks: 'Any contraindications for this patient?'"""

    def test_acei_contraindicated_in_angioedema(self, engine):
        """ACEi is absolutely contraindicated in patients with angioedema history."""
        result = engine.query(ClinicalQuery(
            intent="contraindication",
            concepts=["ACE Inhibitor"],
            include_evidence=False,
        ))

        contraindicated = {m.entity_name for m in result.semantic_matches}
        assert "Angioedema" in contraindicated, (
            f"ACEi-Angioedema contraindication not found. Got: {contraindicated}"
        )

    def test_lisinopril_inherits_acei_contraindication(self, engine):
        """Lisinopril (Drug) should inherit ACEi (DrugClass) contraindications.

        This is the critical class inheritance test — without Fix 1,
        querying Lisinopril would return NO contraindications because
        the edge lives on the ACE Inhibitor class node.
        """
        result = engine.query(ClinicalQuery(
            intent="contraindication",
            concepts=["Lisinopril"],
            include_evidence=False,
        ))

        contraindicated = {m.entity_name for m in result.semantic_matches}
        assert "Angioedema" in contraindicated, (
            f"Lisinopril should inherit Angioedema contraindication from ACEi class. "
            f"Got: {contraindicated}"
        )
        # Verify it came from the expanded layer (class inheritance)
        angioedema_match = next(
            m for m in result.semantic_matches if m.entity_name == "Angioedema"
        )
        assert angioedema_match.source_layer == "expanded", (
            "Inherited contraindication should be marked as 'expanded' layer"
        )


# ═══════════════════════════════════════════════════════════════════════
# DECISION 5: What labs need monitoring?
#
# Real data: Spironolactone → K+, Creatinine, eGFR
#            Dapagliflozin/Empagliflozin → eGFR
#            Digoxin → Digoxin Level
# ═══════════════════════════════════════════════════════════════════════


class TestMonitoringRequirements:
    """Clinician asks: 'What labs do I need to watch?'"""

    def test_spironolactone_monitoring(self, engine):
        """Spironolactone requires K+, Creatinine, and eGFR monitoring."""
        result = engine.query(ClinicalQuery(
            intent="monitoring",
            concepts=["Spironolactone"],
            include_evidence=False,
        ))

        labs = {m.entity_name for m in result.semantic_matches}
        assert "Potassium" in labs, f"Spironolactone K+ monitoring missing. Got: {labs}"
        assert "Creatinine" in labs, f"Spironolactone Creatinine monitoring missing. Got: {labs}"
        assert "eGFR" in labs, f"Spironolactone eGFR monitoring missing. Got: {labs}"

    def test_sglt2i_monitoring(self, engine):
        """SGLT2 inhibitors require eGFR monitoring."""
        result = engine.query(ClinicalQuery(
            intent="monitoring",
            concepts=["Dapagliflozin"],
            include_evidence=False,
        ))

        labs = {m.entity_name for m in result.semantic_matches}
        assert "eGFR" in labs, f"Dapagliflozin eGFR monitoring missing. Got: {labs}"

    def test_spironolactone_member_of_mra(self, conn):
        """Verify Spironolactone→MRA class membership is in the graph,
        enabling future class-level monitoring edge propagation."""
        rows = conn.execute_read(
            "MATCH (d:Drug {name: 'Spironolactone'})-[:MEMBER_OF]->(c:DrugClass) "
            "RETURN c.name AS class_name"
        )
        classes = {r["class_name"] for r in rows}
        assert "MRA" in classes, (
            f"Spironolactone should be MEMBER_OF MRA. Got: {classes}"
        )


# ═══════════════════════════════════════════════════════════════════════
# DECISION 6: Variable alias resolution
#
# Patient data comes from EHRs with inconsistent naming. The engine
# must normalize aliases to canonical variable names.
# ═══════════════════════════════════════════════════════════════════════


class TestVariableAliases:
    """Verify the engine handles EHR variable naming inconsistencies."""

    def test_ejection_fraction_alias(self, engine):
        """'ejection_fraction' → 'lvef' — both should evaluate LVEF conditions."""
        result = engine.query(ClinicalQuery(
            intent="treatment_selection",
            concepts=["HFrEF"],
            patient_vars={"ejection_fraction": 30},
            include_evidence=False,
        ))

        # Should have matches — LVEF ≤40 conditions should evaluate
        assert result.confidence != "low", "ejection_fraction alias should resolve"
        conditional = [
            m for m in result.semantic_matches
            if m.conditions_json and "LVEF" in m.conditions_json
        ]
        for m in conditional:
            assert "LVEF" not in m.missing_variables, (
                "LVEF should not be missing when 'ejection_fraction' is provided"
            )

    def test_k_alias_for_potassium(self, engine):
        """'k' should resolve to 'potassium' for condition evaluation."""
        result = engine.query(ClinicalQuery(
            intent="dosing",
            concepts=["Lisinopril", "HFrEF"],
            patient_vars={"LVEF": 30, "HF_stage": "C", "k": 4.5},
            include_evidence=False,
        ))

        # The engine should accept 'k' as potassium — no missing var errors for it
        for m in result.semantic_matches:
            if m.conditions_json and "potassium" in m.conditions_json.lower():
                assert "potassium" not in m.missing_variables


# ═══════════════════════════════════════════════════════════════════════
# DECISION 7: Graph completeness — can the graph support clinical work?
# ═══════════════════════════════════════════════════════════════════════


class TestGraphCompleteness:
    """Verify the graph has enough data for real clinical decision support."""

    def test_unknown_drug_returns_low_confidence(self, engine):
        """Unknown drug should return low confidence, not crash."""
        result = engine.query(ClinicalQuery(
            intent="monitoring",
            concepts=["Xylomethazoline"],
            include_evidence=False,
        ))
        assert result.confidence == "low"

    def test_missing_patient_vars_reported(self, engine):
        """Conditions that can't be evaluated should report missing variables."""
        result = engine.query(ClinicalQuery(
            intent="treatment_selection",
            concepts=["HFrEF"],
            patient_vars={},  # No variables provided
            include_evidence=False,
        ))

        all_missing = set()
        for m in result.semantic_matches:
            all_missing.update(m.missing_variables)

        # At least LVEF should be missing — it's on many HFrEF recommendations
        assert len(all_missing) > 0, "Should report at least some missing variables"

    def test_graph_has_sufficient_edge_coverage(self, conn):
        """The loaded graph must have all critical semantic edge types."""
        critical_edges = [
            "INDICATED_FOR",
            "CONTRAINDICATED_IN",
            "DOSED_FOR",
            "MONITORED_BY",
            "INTERACTS_WITH",
            "MEMBER_OF",
        ]
        for etype in critical_edges:
            rows = conn.execute_read(
                f"MATCH ()-[r:{etype}]->() RETURN count(r) AS cnt"
            )
            count = rows[0]["cnt"] if rows else 0
            assert count > 0, f"No {etype} edges in graph — clinical gap"

    def test_graph_has_sufficient_node_coverage(self, conn):
        """Must have all clinical node types populated."""
        for label in ["Drug", "DrugClass", "Disease", "Lab"]:
            rows = conn.execute_read(
                f"MATCH (n:{label}) RETURN count(n) AS cnt"
            )
            count = rows[0]["cnt"] if rows else 0
            assert count > 0, f"No {label} nodes in graph"

    def test_member_of_edges_enable_inheritance(self, conn):
        """Drugs must be linked to their classes for inheritance to work."""
        rows = conn.execute_read(
            "MATCH (d:Drug)-[:MEMBER_OF]->(c:DrugClass) "
            "RETURN c.name AS class, count(d) AS members "
            "ORDER BY members DESC LIMIT 5"
        )
        assert len(rows) > 0, "No MEMBER_OF edges — class inheritance will fail"
        # Verify at least Lisinopril → ACE Inhibitor exists
        rows = conn.execute_read(
            "MATCH (d:Drug {name: 'Lisinopril'})-[:MEMBER_OF]->(c:DrugClass) "
            "RETURN c.name AS class_name"
        )
        classes = {r["class_name"] for r in rows}
        assert "ACE Inhibitor" in classes, (
            f"Lisinopril should be MEMBER_OF ACE Inhibitor. Got: {classes}"
        )
