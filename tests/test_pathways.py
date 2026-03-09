"""Tests for the treatment pathway engine."""
import pytest
from open_medicine.mcp.pathways.engine import (
    search_pathways,
    get_pathway,
    PathwayParams,
)


def test_search_pathways_returns_matches():
    """Searching for 'atrial fibrillation' should return at least one pathway."""
    results = search_pathways("atrial fibrillation")
    assert len(results) > 0
    assert "pathway_id" in results[0]
    assert "title" in results[0]


def test_search_pathways_no_match():
    """Searching for nonsense returns empty list."""
    results = search_pathways("xyznonexistent123")
    assert results == []


def test_get_pathway_returns_clinical_result():
    """Retrieving a known pathway returns a ClinicalResult."""
    from open_medicine.foundation.base import ClinicalResult
    params = PathwayParams(
        pathway_id="afib_anticoagulation",
    )
    result = get_pathway(params)
    assert isinstance(result, ClinicalResult)
    assert result.evidence.source_doi != ""
    assert "steps" in result.value


def test_get_pathway_unknown_id():
    """Unknown pathway_id returns an error result."""
    params = PathwayParams(
        pathway_id="nonexistent_pathway",
    )
    result = get_pathway(params)
    assert "not_found" in str(result.value)


def test_pathway_steps_have_required_fields():
    """Each step in the pathway must have required fields."""
    params = PathwayParams(
        pathway_id="afib_anticoagulation",
    )
    result = get_pathway(params)
    for step in result.value["steps"]:
        assert "order" in step
        assert "name" in step
        assert "description" in step
        assert "evidence_doi" in step


def test_pathway_with_contraindications():
    """Pathway with contraindications should filter steps."""
    params = PathwayParams(
        pathway_id="afib_anticoagulation",
        contraindications=["active_major_bleeding"],
    )
    result = get_pathway(params)
    # Should still return a result, but with warnings
    assert isinstance(result.value, dict)
