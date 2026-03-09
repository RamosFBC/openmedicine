"""Tests for the clinical routing engine."""
import pytest
from open_medicine.mcp.routing.engine import (
    assess_clinical_scenario,
    ScenarioParams,
)
from open_medicine.foundation.base import ClinicalResult


def test_assess_afib_scenario():
    """AFib scenario should recommend CHA2DS2-VASc, HAS-BLED, and AF guideline."""
    params = ScenarioParams(
        conditions=["atrial_fibrillation"],
        age=65,
        sex="male",
    )
    result = assess_clinical_scenario(params)
    assert isinstance(result, ClinicalResult)
    actions = result.value["recommended_actions"]
    action_ids = [a["tool_id"] for a in actions]
    assert "calculate_chadsvasc" in action_ids
    assert "calculate_hasbled" in action_ids


def test_assess_unknown_condition():
    """Unknown condition returns empty recommendations (no crash)."""
    params = ScenarioParams(
        conditions=["totally_made_up_condition"],
        age=40,
        sex="female",
    )
    result = assess_clinical_scenario(params)
    assert isinstance(result, ClinicalResult)
    assert result.value["recommended_actions"] == []


def test_assess_multiple_conditions():
    """Multiple conditions should aggregate recommendations."""
    params = ScenarioParams(
        conditions=["atrial_fibrillation", "ckd"],
        age=70,
        sex="male",
    )
    result = assess_clinical_scenario(params)
    actions = result.value["recommended_actions"]
    action_ids = [a["tool_id"] for a in actions]
    # Should include both AF and CKD tools
    assert "calculate_chadsvasc" in action_ids
    assert "calculate_ckd_epi" in action_ids


def test_recommendations_are_prioritized():
    """Recommendations should have priority ordering."""
    params = ScenarioParams(
        conditions=["atrial_fibrillation"],
        age=65,
        sex="male",
    )
    result = assess_clinical_scenario(params)
    actions = result.value["recommended_actions"]
    priorities = [a["priority"] for a in actions]
    assert priorities == sorted(priorities)


def test_recommendations_have_required_fields():
    """Each recommendation should have required fields."""
    params = ScenarioParams(
        conditions=["atrial_fibrillation"],
        age=65,
        sex="male",
    )
    result = assess_clinical_scenario(params)
    for action in result.value["recommended_actions"]:
        assert "priority" in action
        assert "action" in action
        assert "tool_id" in action
        assert "reason" in action
