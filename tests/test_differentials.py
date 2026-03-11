"""Tests for the differential diagnosis engine."""
import pytest
from open_medicine.mcp.differentials.engine import (
    search_differentials,
    get_differential,
    DifferentialParams,
)


def test_search_differentials_returns_matches():
    """Searching for 'chest pain' should return at least one differential."""
    results = search_differentials("chest pain")
    assert len(results) > 0
    assert "differential_id" in results[0]
    assert "title" in results[0]
    assert "description" in results[0]


def test_search_differentials_no_match():
    """Searching for nonsense returns empty list."""
    results = search_differentials("xyznonexistent123")
    assert results == []


def test_get_differential_returns_clinical_result():
    """Retrieving a known differential returns a ClinicalResult."""
    from open_medicine.foundation.base import ClinicalResult
    params = DifferentialParams(
        differential_id="chest_pain",
        age=55,
        sex="male",
    )
    result = get_differential(params)
    assert isinstance(result, ClinicalResult)
    assert result.evidence.source_doi != ""
    # Value should contain diagnoses list
    assert "diagnoses" in result.value


def test_get_differential_unknown_id():
    """Unknown differential_id returns an error result."""
    params = DifferentialParams(
        differential_id="nonexistent_thing",
        age=30,
        sex="female",
    )
    result = get_differential(params)
    assert "not_found" in str(result.value)


def test_differential_diagnoses_have_required_fields():
    """Each diagnosis in the differential must have required fields."""
    params = DifferentialParams(
        differential_id="chest_pain",
        age=55,
        sex="male",
    )
    result = get_differential(params)
    for dx in result.value["diagnoses"]:
        assert "name" in dx
        assert "likelihood" in dx
        assert dx["likelihood"] in ("common", "less_common", "must_not_miss")
        assert "key_features" in dx
        assert "recommended_tests" in dx


# ---- Broadening: also_consider and clinical_reasoning_prompt tests ----


def test_all_differentials_have_also_consider():
    """Every differential must have an also_consider array with at least 5 entries."""
    for diff_id in ("chest_pain", "dyspnea"):
        params = DifferentialParams(differential_id=diff_id)
        result = get_differential(params)
        also_consider = result.value.get("also_consider", [])
        assert len(also_consider) >= 5, (
            f"{diff_id}: also_consider has {len(also_consider)} entries, need >= 5"
        )


def test_also_consider_entries_have_required_fields():
    """Every also_consider entry must have name (str) and rationale (str)."""
    for diff_id in ("chest_pain", "dyspnea"):
        params = DifferentialParams(differential_id=diff_id)
        result = get_differential(params)
        for entry in result.value.get("also_consider", []):
            assert "name" in entry and isinstance(entry["name"], str) and entry["name"], (
                f"{diff_id}: also_consider entry missing or empty 'name'"
            )
            assert "rationale" in entry and isinstance(entry["rationale"], str) and entry["rationale"], (
                f"{diff_id}: also_consider entry '{entry.get('name')}' missing or empty 'rationale'"
            )


def test_all_differentials_have_clinical_reasoning_prompt():
    """Every differential must have a non-empty clinical_reasoning_prompt."""
    for diff_id in ("chest_pain", "dyspnea"):
        params = DifferentialParams(differential_id=diff_id)
        result = get_differential(params)
        prompt = result.value.get("clinical_reasoning_prompt", "")
        assert isinstance(prompt, str) and len(prompt) > 0, (
            f"{diff_id}: clinical_reasoning_prompt is missing or empty"
        )


def test_get_differential_includes_also_consider_in_result():
    """ClinicalResult.value must contain also_consider and clinical_reasoning_prompt keys."""
    params = DifferentialParams(differential_id="chest_pain", age=55, sex="male")
    result = get_differential(params)
    assert "also_consider" in result.value, "also_consider missing from ClinicalResult.value"
    assert "clinical_reasoning_prompt" in result.value, "clinical_reasoning_prompt missing from ClinicalResult.value"


def test_interpretation_references_also_consider():
    """Interpretation text should mention also_consider count."""
    params = DifferentialParams(differential_id="chest_pain")
    result = get_differential(params)
    assert "also consider" in result.interpretation.lower() or "also_consider" in result.interpretation.lower(), (
        "Interpretation should reference the also_consider entries"
    )
