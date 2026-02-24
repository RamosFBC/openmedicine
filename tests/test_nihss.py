import pytest
from open_medicine.mcp.calculators.nihss import calculate_nihss, NIHSSParams


def _make_params(**kwargs):
    defaults = dict(
        loc=0, loc_questions=0, loc_commands=0, best_gaze=0, visual_fields=0,
        facial_palsy=0, left_arm_motor=0, right_arm_motor=0, left_leg_motor=0,
        right_leg_motor=0, limb_ataxia=0, sensory=0, best_language=0,
        dysarthria=0, extinction_inattention=0,
    )
    defaults.update(kwargs)
    return NIHSSParams(**defaults)


def test_nihss_minimum_score():
    result = calculate_nihss(_make_params())
    assert result.value == 0
    assert "No stroke symptoms" in result.interpretation


def test_nihss_maximum_score():
    params = NIHSSParams(
        loc=3, loc_questions=2, loc_commands=2, best_gaze=2, visual_fields=3,
        facial_palsy=3, left_arm_motor=4, right_arm_motor=4, left_leg_motor=4,
        right_leg_motor=4, limb_ataxia=2, sensory=2, best_language=3,
        dysarthria=2, extinction_inattention=2,
    )
    result = calculate_nihss(params)
    assert result.value == 42
    assert "Severe stroke" in result.interpretation


def test_nihss_minor_stroke():
    result = calculate_nihss(_make_params(facial_palsy=1, dysarthria=1, sensory=1))
    assert result.value == 3
    assert "Minor stroke" in result.interpretation


def test_nihss_moderate_boundary():
    result = calculate_nihss(_make_params(left_arm_motor=4, best_language=1))
    assert result.value == 5
    assert "Moderate stroke" in result.interpretation


def test_nihss_moderate_severe_boundary():
    result = calculate_nihss(_make_params(
        loc=1, left_arm_motor=4, right_arm_motor=4, left_leg_motor=4, best_language=3
    ))
    assert result.value == 16
    assert "Moderate-to-severe" in result.interpretation


def test_nihss_severe_boundary():
    result = calculate_nihss(_make_params(
        loc=3, loc_questions=2, left_arm_motor=4, right_arm_motor=4,
        left_leg_motor=4, right_leg_motor=4
    ))
    assert result.value == 21
    assert "Severe stroke" in result.interpretation


def test_nihss_evidence_doi():
    result = calculate_nihss(_make_params())
    assert result.evidence.source_doi == "10.1161/01.STR.20.7.864"


def test_nihss_fhir_code():
    result = calculate_nihss(_make_params())
    assert result.fhir_code == "72089-6"
    assert result.fhir_system == "http://loinc.org"
