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
