from unittest.mock import MagicMock

from open_medicine.graphrag.graph.schema_v2 import Guideline
from open_medicine.graphrag.ingestion.chunker import Chunk
from open_medicine.graphrag.ingestion.extractor_v2 import (
    ConceptRef,
    ExtractedRelationship,
    ExtractionResult,
)
from open_medicine.graphrag.ingestion.loader_v2 import (
    LoadableGuideline,
    _extract_year,
    detect_conflicts,
    load_guideline,
)


class TestExtractYear:
    def test_year_at_end(self):
        assert _extract_year("acc_aha_hf_2022") == 2022

    def test_year_in_middle(self):
        assert _extract_year("2023_aha_af") == 2023

    def test_no_year(self):
        assert _extract_year("no_year_here") == 0

    def test_short_numbers_ignored(self):
        assert _extract_year("test_42_data") == 0


class TestDetectConflicts:
    def _make_extraction(
        self,
        rec_id: str,
        action: str,
        strength: str,
        concept_name: str,
        rec_type: str = "treatment_selection",
        guideline_id: str = "g_2022",
    ) -> ExtractionResult:
        return ExtractionResult(
            rec_id=rec_id,
            rec_type=rec_type,
            action=action,
            action_detail="detail",
            strength=strength,
            evidence_quality="high",
            concepts=[ConceptRef(concept_name, "drug", "subject")],
            guideline_id=guideline_id,
        )

    def test_no_conflicts(self):
        extractions = [
            self._make_extraction("r1", "prescribe", "strong_for", "Drug A"),
            self._make_extraction("r2", "prescribe", "strong_for", "Drug B"),
        ]
        assert detect_conflicts(extractions) == []

    def test_prescribe_vs_avoid(self):
        extractions = [
            self._make_extraction("r1", "prescribe ARNi", "strong_for", "ARNi"),
            self._make_extraction("r2", "avoid ARNi", "weak_for", "ARNi"),
        ]
        conflicts = detect_conflicts(extractions)
        assert len(conflicts) == 1
        winner, loser, resolution = conflicts[0]
        assert winner == "r1"
        assert loser == "r2"
        assert resolution == "stronger"

    def test_newer_guideline_wins(self):
        extractions = [
            self._make_extraction("r1", "prescribe X", "strong_for", "X", guideline_id="g_2020"),
            self._make_extraction("r2", "avoid X", "strong_for", "X", guideline_id="g_2024"),
        ]
        conflicts = detect_conflicts(extractions)
        assert len(conflicts) == 1
        winner, loser, _ = conflicts[0]
        assert winner == "r2"
        assert loser == "r1"

    def test_different_concepts_no_conflict(self):
        extractions = [
            self._make_extraction("r1", "prescribe", "strong_for", "Drug A"),
            self._make_extraction("r2", "avoid", "strong_for", "Drug B"),
        ]
        assert detect_conflicts(extractions) == []


class TestLoadGuideline:
    def test_creates_typed_nodes(self):
        """Verify that load_guideline produces typed node queries."""
        conn = MagicMock()

        guideline = Guideline(
            id="test_hf_2022",
            title="Test HF Guideline",
            doi="10.1234/test",
            year=2022,
            organization="Test Org",
        )

        chunks = [
            Chunk(
                id="chunk_001",
                text="ARNi is recommended for HFrEF",
                guideline_id="test_hf_2022",
                section="Treatment",
            ),
        ]

        extractions = [
            ExtractionResult(
                rec_id="rec_test_001",
                rec_type="treatment_selection",
                action="Prescribe ARNi",
                action_detail="ARNi recommended for HFrEF",
                strength="strong_for",
                evidence_quality="high",
                conditions=[{"variable": "LVEF", "operator": "<=", "threshold": 40, "unit": "%"}],
                concepts=[
                    ConceptRef("Sacubitril/Valsartan", "drug", "subject"),
                    ConceptRef("HFrEF", "disease", "target"),
                ],
                relationships=[],
                source_chunk_id="chunk_001",
                guideline_id="test_hf_2022",
                page=42,
            ),
        ]

        data = LoadableGuideline(
            guideline=guideline,
            chunks=chunks,
            extractions=extractions,
        )

        load_guideline(conn, data)

        # Verify execute_write_tx was called once with a list of queries
        conn.execute_write_tx.assert_called_once()
        all_queries = conn.execute_write_tx.call_args[0][0]
        all_cypher = " ".join(q[0] for q in all_queries)

        # Should have typed node labels (not Concept)
        assert "Drug {id:" in all_cypher or "Drug {id: $id}" in all_cypher or "MERGE (d:Drug" in all_cypher
        assert "Disease" in all_cypher
        assert "Recommendation" in all_cypher
        assert "EvidenceChunk" in all_cypher

        # Should NOT have generic Concept or LogicNode
        assert "Concept {" not in all_cypher
        assert "LogicNode {" not in all_cypher
        assert "PARTICIPATES_IN" not in all_cypher

        # Should have semantic edges
        assert "INDICATED_FOR" in all_cypher
        assert "RECOMMENDS" in all_cypher
        assert "DEFINED_BY" in all_cypher
        assert "SOURCED_FROM" in all_cypher
        assert "FOR_CONDITION" in all_cypher

    def test_creates_patient_variable_with_measures(self):
        """Verify that PatientVariable nodes get MEASURES edges to Lab nodes."""
        conn = MagicMock()

        guideline = Guideline(
            id="test_2022", title="Test", doi="10.x/y", year=2022, organization="Org"
        )

        extractions = [
            ExtractionResult(
                rec_id="rec_001",
                rec_type="monitoring",
                action="Monitor potassium",
                action_detail="Check K+ levels",
                strength="strong_for",
                evidence_quality="moderate",
                conditions=[{"variable": "Potassium", "operator": ">", "threshold": 5.5, "unit": "mEq/L"}],
                concepts=[
                    ConceptRef("Spironolactone", "drug", "subject"),
                    ConceptRef("Potassium", "lab", "target"),
                ],
                relationships=[],
                guideline_id="test_2022",
                page=10,
            ),
        ]

        data = LoadableGuideline(guideline=guideline, chunks=[], extractions=extractions)
        load_guideline(conn, data)

        all_queries = conn.execute_write_tx.call_args[0][0]
        all_cypher = " ".join(q[0] for q in all_queries)

        assert "PatientVariable" in all_cypher
        assert "EVALUATES" in all_cypher
        assert "MEASURES" in all_cypher

    def test_explicit_relationship_creates_semantic_edge(self):
        """Verify that explicit relationships from extractor create semantic edges."""
        conn = MagicMock()

        guideline = Guideline(
            id="test_2022", title="Test", doi="10.x/y", year=2022, organization="Org"
        )

        extractions = [
            ExtractionResult(
                rec_id="rec_001",
                rec_type="contraindication",
                action="Avoid in pregnancy",
                action_detail="ACEi contraindicated in pregnancy",
                strength="strong_against",
                evidence_quality="high",
                concepts=[
                    ConceptRef("ACE Inhibitor", "drug_class", "subject"),
                ],
                relationships=[
                    ExtractedRelationship(
                        rel_type="CONTRAINDICATED_IN",
                        source_name="ACE Inhibitor",
                        source_type="drug_class",
                        target_name="Angioedema",
                        target_type="disease",
                        properties={"severity": "absolute"},
                    ),
                ],
                guideline_id="test_2022",
                page=55,
            ),
        ]

        data = LoadableGuideline(guideline=guideline, chunks=[], extractions=extractions)
        load_guideline(conn, data)

        all_queries = conn.execute_write_tx.call_args[0][0]
        all_cypher = " ".join(q[0] for q in all_queries)

        assert "CONTRAINDICATED_IN" in all_cypher
        assert "DrugClass" in all_cypher
        assert "Disease" in all_cypher


class TestDiagnosedByEdgeDerivation:
    """Fix 4: DIAGNOSED_BY edges are derived from diagnostic_criteria extractions."""

class TestEvidenceQualityOnEdges:
    """C2: evidence_quality must be propagated to CONTRAINDICATED_IN and INTERACTS_WITH edges."""

    def test_contraindicated_in_includes_evidence_quality(self):
        conn = MagicMock()
        guideline = Guideline(
            id="test_2022", title="Test", doi="10.x/y", year=2022, organization="Org"
        )
        extractions = [
            ExtractionResult(
                rec_id="rec_ci_001",
                rec_type="contraindication",
                action="Avoid ACEi in angioedema",
                action_detail="ACEi contraindicated in angioedema",
                strength="strong_against",
                evidence_quality="high",
                concepts=[
                    ConceptRef("ACE Inhibitor", "drug_class", "subject"),
                    ConceptRef("Angioedema", "disease", "target"),
                ],
                guideline_id="test_2022",
            ),
        ]
        data = LoadableGuideline(guideline=guideline, chunks=[], extractions=extractions)
        load_guideline(conn, data)

        all_queries = conn.execute_write_tx.call_args[0][0]
        # Find the CONTRAINDICATED_IN query and check its params include evidence_quality
        ci_queries = [
            (c, p) for c, p in all_queries
            if "CONTRAINDICATED_IN" in c and "evidence_quality" in c
        ]
        assert len(ci_queries) >= 1, "CONTRAINDICATED_IN edge must include evidence_quality"
        _, params = ci_queries[0]
        assert params.get("eq") == "high"

    def test_interacts_with_includes_evidence_quality(self):
        conn = MagicMock()
        guideline = Guideline(
            id="test_2022", title="Test", doi="10.x/y", year=2022, organization="Org"
        )
        extractions = [
            ExtractionResult(
                rec_id="rec_ix_001",
                rec_type="interaction",
                action="Warfarin interacts with Aspirin",
                action_detail="Increased bleeding risk",
                strength="strong_against",
                evidence_quality="moderate",
                concepts=[
                    ConceptRef("Warfarin", "drug", "subject"),
                    ConceptRef("Aspirin", "drug", "subject"),
                ],
                guideline_id="test_2022",
            ),
        ]
        data = LoadableGuideline(guideline=guideline, chunks=[], extractions=extractions)
        load_guideline(conn, data)

        all_queries = conn.execute_write_tx.call_args[0][0]
        iw_queries = [
            (c, p) for c, p in all_queries
            if "INTERACTS_WITH" in c and "evidence_quality" in c
        ]
        assert len(iw_queries) >= 1, "INTERACTS_WITH edge must include evidence_quality"
        _, params = iw_queries[0]
        assert params.get("eq") == "moderate"


class TestDiagnosedByEdgeDerivation:
    """Fix 4: DIAGNOSED_BY edges are derived from diagnostic_criteria extractions."""

    def test_diagnostic_criteria_creates_diagnosed_by(self):
        """Extraction with rec_type=diagnostic_criteria should create DIAGNOSED_BY edge."""
        conn = MagicMock()
        guideline = Guideline(
            id="test_2022", title="Test", doi="10.1234/test", year=2022,
            organization="Test Org",
        )
        extractions = [
            ExtractionResult(
                rec_id="test_diag_1",
                rec_type="diagnostic_criteria",
                action="diagnose",
                action_detail="Use BNP to diagnose Heart Failure",
                strength="strong_for",
                evidence_quality="high",
                concepts=[
                    ConceptRef("Heart Failure", "disease", "subject"),
                    ConceptRef("BNP", "lab", "subject"),
                ],
                guideline_id="test_2022",
            ),
        ]

        data = LoadableGuideline(guideline=guideline, chunks=[], extractions=extractions)
        load_guideline(conn, data)

        all_queries = conn.execute_write_tx.call_args[0][0]
        all_cypher = " ".join(q[0] for q in all_queries)

        assert "DIAGNOSED_BY" in all_cypher

    def test_diagnostic_criteria_with_procedure(self):
        """DIAGNOSED_BY should also work for Disease → Procedure."""
        conn = MagicMock()
        guideline = Guideline(
            id="test_2022", title="Test", doi="10.1234/test", year=2022,
            organization="Test Org",
        )
        extractions = [
            ExtractionResult(
                rec_id="test_diag_2",
                rec_type="diagnostic_criteria",
                action="diagnose",
                action_detail="Use echocardiography for HF diagnosis",
                strength="strong_for",
                evidence_quality="high",
                concepts=[
                    ConceptRef("Heart Failure", "disease", "subject"),
                    ConceptRef("Echocardiography", "procedure", "subject"),
                ],
                guideline_id="test_2022",
            ),
        ]

        data = LoadableGuideline(guideline=guideline, chunks=[], extractions=extractions)
        load_guideline(conn, data)

        all_queries = conn.execute_write_tx.call_args[0][0]
        all_cypher = " ".join(q[0] for q in all_queries)

        assert "DIAGNOSED_BY" in all_cypher


class TestDefaultSeverityIsUnknown:
    """C3/C4: Default severity should be UNKNOWN, not MODERATE/ABSOLUTE."""

    def test_contraindication_defaults_to_unknown(self):
        """When action_detail has no severity keywords, severity should be UNKNOWN."""
        conn = MagicMock()
        guideline = Guideline(
            id="test_2022", title="Test", doi="10.x/y", year=2022, organization="Org"
        )
        extractions = [
            ExtractionResult(
                rec_id="rec_ci_unk",
                rec_type="contraindication",
                action="Restrict use",
                action_detail="This drug is restricted in certain populations",
                strength="strong_against",
                evidence_quality="moderate",
                concepts=[
                    ConceptRef("TestDrug", "drug", "subject"),
                    ConceptRef("TestDisease", "disease", "target"),
                ],
                guideline_id="test_2022",
            ),
        ]
        data = LoadableGuideline(guideline=guideline, chunks=[], extractions=extractions)
        load_guideline(conn, data)

        all_queries = conn.execute_write_tx.call_args[0][0]
        ci_queries = [
            (c, p) for c, p in all_queries
            if "CONTRAINDICATED_IN" in c
        ]
        assert len(ci_queries) >= 1
        _, params = ci_queries[0]
        assert params.get("severity") == "unknown", (
            "Contraindication severity should default to UNKNOWN, not ABSOLUTE"
        )

    def test_interaction_defaults_to_unknown(self):
        """When action_detail has no severity keywords, severity should be UNKNOWN."""
        conn = MagicMock()
        guideline = Guideline(
            id="test_2022", title="Test", doi="10.x/y", year=2022, organization="Org"
        )
        extractions = [
            ExtractionResult(
                rec_id="rec_ix_unk",
                rec_type="interaction",
                action="DrugA interacts with DrugB",
                action_detail="These two drugs interact in some way",
                strength="strong_against",
                evidence_quality="low",
                concepts=[
                    ConceptRef("DrugA", "drug", "subject"),
                    ConceptRef("DrugB", "drug", "subject"),
                ],
                guideline_id="test_2022",
            ),
        ]
        data = LoadableGuideline(guideline=guideline, chunks=[], extractions=extractions)
        load_guideline(conn, data)

        all_queries = conn.execute_write_tx.call_args[0][0]
        iw_queries = [
            (c, p) for c, p in all_queries
            if "INTERACTS_WITH" in c
        ]
        assert len(iw_queries) >= 1
        _, params = iw_queries[0]
        assert params.get("severity") == "unknown", (
            "Interaction severity should default to UNKNOWN, not MODERATE"
        )

    def test_contraindication_enrichment_absolute(self):
        """When action_detail contains 'avoid', enrichment should set ABSOLUTE."""
        conn = MagicMock()
        guideline = Guideline(
            id="test_2022", title="Test", doi="10.x/y", year=2022, organization="Org"
        )
        extractions = [
            ExtractionResult(
                rec_id="rec_ci_abs",
                rec_type="contraindication",
                action="Avoid in angioedema",
                action_detail="ACEi should be avoided in patients with angioedema history",
                strength="strong_against",
                evidence_quality="high",
                concepts=[
                    ConceptRef("ACE Inhibitor", "drug_class", "subject"),
                    ConceptRef("Angioedema", "disease", "target"),
                ],
                guideline_id="test_2022",
            ),
        ]
        data = LoadableGuideline(guideline=guideline, chunks=[], extractions=extractions)
        load_guideline(conn, data)

        all_queries = conn.execute_write_tx.call_args[0][0]
        ci_queries = [
            (c, p) for c, p in all_queries
            if "CONTRAINDICATED_IN" in c
        ]
        assert len(ci_queries) >= 1
        _, params = ci_queries[0]
        assert params.get("severity") == "absolute", (
            "Enrichment should detect 'avoid' and set severity to ABSOLUTE"
        )

    def test_interaction_enrichment_major(self):
        """When action_detail contains 'avoid', enrichment should set MAJOR."""
        conn = MagicMock()
        guideline = Guideline(
            id="test_2022", title="Test", doi="10.x/y", year=2022, organization="Org"
        )
        extractions = [
            ExtractionResult(
                rec_id="rec_ix_maj",
                rec_type="interaction",
                action="Avoid concurrent use",
                action_detail="Avoid concurrent use due to increased hypotension risk",
                strength="strong_against",
                evidence_quality="high",
                concepts=[
                    ConceptRef("DrugX", "drug", "subject"),
                    ConceptRef("DrugY", "drug", "subject"),
                ],
                guideline_id="test_2022",
            ),
        ]
        data = LoadableGuideline(guideline=guideline, chunks=[], extractions=extractions)
        load_guideline(conn, data)

        all_queries = conn.execute_write_tx.call_args[0][0]
        iw_queries = [
            (c, p) for c, p in all_queries
            if "INTERACTS_WITH" in c
        ]
        assert len(iw_queries) >= 1
        _, params = iw_queries[0]
        assert params.get("severity") == "major", (
            "Enrichment should detect 'avoid' and set severity to MAJOR"
        )

    def test_contraindication_enrichment_relative(self):
        """When action_detail contains 'caution', enrichment should set RELATIVE."""
        conn = MagicMock()
        guideline = Guideline(
            id="test_2022", title="Test", doi="10.x/y", year=2022, organization="Org"
        )
        extractions = [
            ExtractionResult(
                rec_id="rec_ci_rel",
                rec_type="contraindication",
                action="Use with caution",
                action_detail="Use with caution in patients with renal impairment",
                strength="moderate_for",
                evidence_quality="moderate",
                concepts=[
                    ConceptRef("TestDrug", "drug", "subject"),
                    ConceptRef("Renal Impairment", "disease", "target"),
                ],
                guideline_id="test_2022",
            ),
        ]
        data = LoadableGuideline(guideline=guideline, chunks=[], extractions=extractions)
        load_guideline(conn, data)

        all_queries = conn.execute_write_tx.call_args[0][0]
        ci_queries = [
            (c, p) for c, p in all_queries
            if "CONTRAINDICATED_IN" in c
        ]
        assert len(ci_queries) >= 1
        _, params = ci_queries[0]
        assert params.get("severity") == "relative", (
            "Enrichment should detect 'caution' and set severity to RELATIVE"
        )
