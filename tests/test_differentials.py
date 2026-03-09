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
