import json
from unittest.mock import patch

from open_medicine.graphrag.ingestion.extractor_v2 import (
    VALID_ENTITY_TYPES,
    VALID_REC_TYPES,
    ExtractionResult,
    _normalize_entity_type,
    _strip_code_fences,
    _validate_evidence_quality,
    _validate_strength,
    extract_recommendations,
)


class TestStripCodeFences:
    def test_no_fences(self):
        assert _strip_code_fences("[{}]") == "[{}]"

    def test_json_fences(self):
        assert _strip_code_fences("```json\n[{}]\n```") == "[{}]"

    def test_plain_fences(self):
        assert _strip_code_fences("```\n[{}]\n```") == "[{}]"


class TestNormalizeEntityType:
    def test_direct_types(self):
        assert _normalize_entity_type("drug") == "drug"
        assert _normalize_entity_type("disease") == "disease"
        assert _normalize_entity_type("lab") == "lab"
        assert _normalize_entity_type("procedure") == "procedure"
        assert _normalize_entity_type("device") == "device"
        assert _normalize_entity_type("symptom") == "symptom"
        assert _normalize_entity_type("drug_class") == "drug_class"

    def test_legacy_mappings(self):
        assert _normalize_entity_type("condition") == "disease"
        assert _normalize_entity_type("sign") == "symptom"
        assert _normalize_entity_type("biomarker") == "lab"
        assert _normalize_entity_type("vital") == "lab"
        assert _normalize_entity_type("test") == "procedure"

    def test_case_insensitive(self):
        assert _normalize_entity_type("Drug") == "drug"
        assert _normalize_entity_type("DISEASE") == "disease"


class TestValidateStrength:
    def test_valid_values(self):
        assert _validate_strength("strong_for") == "strong_for"
        assert _validate_strength("moderate_for") == "moderate_for"
        assert _validate_strength("weak_for") == "weak_for"
        assert _validate_strength("strong_against") == "strong_against"
        assert _validate_strength("no_benefit") == "no_benefit"

    def test_legacy_format(self):
        assert _validate_strength("Strong/A") == "strong_for"
        assert _validate_strength("Moderate/B") == "moderate_for"
        assert _validate_strength("Weak/C") == "weak_for"

    def test_unknown_defaults(self):
        assert _validate_strength("unknown") == "moderate_for"


class TestValidateEvidenceQuality:
    def test_valid_values(self):
        assert _validate_evidence_quality("high") == "high"
        assert _validate_evidence_quality("moderate") == "moderate"
        assert _validate_evidence_quality("low") == "low"
        assert _validate_evidence_quality("very_low") == "very_low"
        assert _validate_evidence_quality("expert") == "expert"

    def test_legacy_format(self):
        assert _validate_evidence_quality("A") == "high"
        assert _validate_evidence_quality("B-R") == "moderate"
        assert _validate_evidence_quality("B-NR") == "low"
        assert _validate_evidence_quality("C-LD") == "very_low"
        assert _validate_evidence_quality("C-EO") == "expert"


class TestValidTypes:
    def test_all_rec_types(self):
        expected = {
            "treatment_selection", "dosing", "contraindication", "interaction",
            "monitoring", "diagnostic_criteria", "prevention", "referral",
            "device_therapy", "lifestyle", "discharge", "follow_up",
            "safety_warning",
        }
        assert VALID_REC_TYPES == expected

    def test_all_entity_types(self):
        expected = {"drug", "drug_class", "disease", "symptom", "lab", "procedure", "device"}
        assert VALID_ENTITY_TYPES == expected


class TestExtractRecommendations:
    def _mock_llm_response(self, data: list[dict]) -> str:
        return json.dumps(data)

    @patch("open_medicine.graphrag.ingestion.extractor_v2._call_llm_with_retry")
    def test_basic_extraction(self, mock_llm):
        mock_llm.return_value = self._mock_llm_response([
            {
                "id": "rec_test_001",
                "type": "treatment_selection",
                "action": "Prescribe ARNi",
                "action_detail": "ARNi is recommended for HFrEF",
                "strength": "strong_for",
                "evidence_quality": "high",
                "conditions": [{"variable": "LVEF", "operator": "<=", "threshold": 40, "unit": "%"}],
                "guideline_id": "test_2024",
                "page": 42,
                "concepts": [
                    {"name": "Sacubitril/Valsartan", "type": "drug", "role": "subject"},
                    {"name": "HFrEF", "type": "disease", "role": "target"},
                ],
                "relationships": [
                    {
                        "rel_type": "INDICATED_FOR",
                        "source_name": "Sacubitril/Valsartan",
                        "source_type": "drug",
                        "target_name": "HFrEF",
                        "target_type": "disease",
                        "properties": {},
                    }
                ],
            }
        ])

        results = extract_recommendations("test text", "Treatment", "test_2024", 42)
        assert len(results) == 1
        r = results[0]
        assert r.rec_type == "treatment_selection"
        assert r.strength == "strong_for"
        assert r.evidence_quality == "high"
        assert len(r.concepts) == 2
        assert r.concepts[0].name == "Sacubitril/Valsartan"
        assert r.concepts[0].type == "drug"
        assert r.concepts[0].role == "subject"
        assert len(r.relationships) == 1
        assert r.relationships[0].rel_type == "INDICATED_FOR"

    @patch("open_medicine.graphrag.ingestion.extractor_v2._call_llm_with_retry")
    def test_empty_extraction(self, mock_llm):
        mock_llm.return_value = "[]"
        results = extract_recommendations("no rules here", "Intro", "test_2024", 1)
        assert results == []

    @patch("open_medicine.graphrag.ingestion.extractor_v2._call_llm_with_retry")
    def test_invalid_json(self, mock_llm):
        mock_llm.return_value = "not json"
        results = extract_recommendations("test", "test", "g1", 1)
        assert results == []

    @patch("open_medicine.graphrag.ingestion.extractor_v2._call_llm_with_retry")
    def test_code_fences_stripped(self, mock_llm):
        mock_llm.return_value = "```json\n[]\n```"
        results = extract_recommendations("test", "test", "g1", 1)
        assert results == []

    @patch("open_medicine.graphrag.ingestion.extractor_v2._call_llm_with_retry")
    def test_invalid_rec_type_skipped(self, mock_llm):
        mock_llm.return_value = self._mock_llm_response([
            {
                "id": "rec_bad",
                "type": "invalid_type",
                "action": "test",
                "action_detail": "test",
                "strength": "strong_for",
                "evidence_quality": "high",
                "guideline_id": "g1",
                "page": 1,
                "concepts": [],
                "relationships": [],
            }
        ])
        results = extract_recommendations("test", "test", "g1", 1)
        assert len(results) == 0

    @patch("open_medicine.graphrag.ingestion.extractor_v2._call_llm_with_retry")
    def test_legacy_entity_types_normalized(self, mock_llm):
        mock_llm.return_value = self._mock_llm_response([
            {
                "id": "rec_001",
                "type": "treatment_selection",
                "action": "test",
                "action_detail": "test",
                "strength": "strong_for",
                "evidence_quality": "high",
                "guideline_id": "g1",
                "page": 1,
                "concepts": [
                    {"name": "HF", "type": "condition"},
                    {"name": "BNP", "type": "biomarker"},
                ],
                "relationships": [],
            }
        ])
        results = extract_recommendations("test", "test", "g1", 1)
        assert len(results) == 1
        assert results[0].concepts[0].type == "disease"
        assert results[0].concepts[1].type == "lab"

    @patch("open_medicine.graphrag.ingestion.extractor_v2._call_llm_with_retry")
    def test_llm_failure_returns_empty(self, mock_llm):
        mock_llm.side_effect = Exception("API error")
        results = extract_recommendations("test", "test", "g1", 1)
        assert results == []
