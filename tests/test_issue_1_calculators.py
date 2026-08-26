import pytest
from pydantic import ValidationError

from open_medicine.mcp.base import ClinicalError, ResultStatus
from open_medicine.mcp.calculators.cockcroft_gault import CockcroftGaultParams, calculate_cockcroft_gault
from open_medicine.mcp.calculators.ckd_epi import CKDEPIParams, calculate_ckd_epi
from open_medicine.mcp.calculators.gcs import GCSParams, calculate_gcs
from open_medicine.mcp.calculators.chadsvasc import CHADSVAScParams, calculate_chadsvasc
from open_medicine.mcp.calculators.renal_dose_adjustment import RenalDoseAdjustmentParams, calculate_renal_dose_adjustment


@pytest.mark.parametrize("field,value", [("age", 17), ("age", 121), ("weight", 0), ("serum_creatinine", 0)])
def test_cockcroft_gault_rejects_out_of_scope_bounds(field, value):
    args = dict(age=50, weight=70, weight_type="actual", is_female=False, serum_creatinine=1)
    args[field] = value
    with pytest.raises(ValidationError):
        CockcroftGaultParams(**args)


def test_cockcroft_requires_actual_weight_type_and_has_no_dosing_advice():
    with pytest.raises(ValidationError):
        CockcroftGaultParams(age=50, weight=70, is_female=False, serum_creatinine=1)
    result = calculate_cockcroft_gault(CockcroftGaultParams(
        age=50, weight=70, weight_type="actual", is_female=False, serum_creatinine=1
    ))
    assert result.component_breakdown["weight_type"] == "actual"
    assert "dose" not in result.interpretation.lower()
    assert "not validated in acute kidney injury" in result.interpretation.lower()


def test_ckd_epi_requires_stability_and_rejects_bounds():
    with pytest.raises(ValidationError):
        CKDEPIParams(age=50, is_female=False, serum_creatinine=1)
    with pytest.raises(ValidationError):
        CKDEPIParams(age=17, is_female=False, serum_creatinine=1, renal_function_stable=True)


def test_ckd_epi_has_no_drug_recommendation():
    result = calculate_ckd_epi(CKDEPIParams(age=50, is_female=False, serum_creatinine=1, renal_function_stable=True))
    assert "drug" not in result.interpretation.lower()


def test_renal_metric_mismatch_is_typed_error_without_dose_by_default():
    result = calculate_renal_dose_adjustment(RenalDoseAdjustmentParams(drug_name="vancomycin", renal_value=80, renal_metric="egfr"))
    assert result.status.value == "error"
    assert result.errors[0].code == "renal_metric_mismatch"
    assert result.value is None


def test_drug_not_found_is_typed_error():
    result = calculate_renal_dose_adjustment(RenalDoseAdjustmentParams(drug_name="missing", renal_value=80, renal_metric="crcl"))
    assert result.errors[0].code == "drug_not_found"
    assert result.evidence.source_doi is None
    assert "N/A" not in result.model_dump_json()


def test_gcs_non_testable_component_suppresses_total_and_has_breakdown():
    result = calculate_gcs(GCSParams(eye_response=4, verbal_non_testable_reason="intubated", motor_response=6))
    assert result.status.value == "insufficient_data"
    assert result.value is None
    assert result.component_breakdown["verbal"]["non_testable_reason"] == "intubated"


def test_gcs_insufficient_data_has_typed_component_reasons():
    result = calculate_gcs(
        GCSParams(
            eye_non_testable_reason="orbital swelling",
            verbal_non_testable_reason="intubated",
            motor_response=6,
        )
    )
    assert result.status is ResultStatus.INSUFFICIENT_DATA
    assert result.value is None
    assert result.errors == [
        ClinicalError(
            code="non_testable_component",
            message="One or more GCS components are non-testable.",
            details={
                "non_testable_components": {
                    "eye": "orbital swelling",
                    "verbal": "intubated",
                }
            },
        )
    ]
    assert result.component_breakdown["eye"]["non_testable_reason"] == "orbital swelling"


def test_gcs_score_xor_reason_and_official_terms():
    with pytest.raises(ValidationError):
        GCSParams(eye_response=2, eye_non_testable_reason="swelling", verbal_response=5, motor_response=6)
    result = calculate_gcs(GCSParams(eye_response=2, verbal_response=2, motor_response=5))
    assert result.component_breakdown["eye"]["term"] == "to pressure"
    assert result.component_breakdown["verbal"]["term"] == "sounds"
    assert "intubat" not in result.interpretation.lower()


def test_chadsvasc_missing_or_unknown_component_is_insufficient_data():
    result = calculate_chadsvasc(CHADSVAScParams(age=70, female_sex=False, congestive_heart_failure=None,
        hypertension=False, diabetes=False, stroke_tia_thromboembolism=False, vascular_disease=False))
    assert result.status.value == "insufficient_data"
    assert result.value is None
    assert result.component_breakdown["congestive_heart_failure"] is None


def test_chadsvasc_components_required_and_complete_has_breakdown_without_advice():
    with pytest.raises(ValidationError):
        CHADSVAScParams(age=70, female_sex=False)
    result = calculate_chadsvasc(CHADSVAScParams(age=75, female_sex=False, congestive_heart_failure=False,
        hypertension=False, diabetes=False, stroke_tia_thromboembolism=False, vascular_disease=False))
    assert result.value == 2
    assert result.component_breakdown["age"] == 2
    assert "anticoag" not in result.interpretation.lower()
    assert result.evidence.source_doi == "10.1161/CIR.0000000000001193"
