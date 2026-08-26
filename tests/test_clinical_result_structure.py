import ast
import json
from pathlib import Path

import pytest

from open_medicine.mcp.base import ClinicalResult, Evidence
from open_medicine.mcp.calculators.chadsvasc import CHADSVAScParams, calculate_chadsvasc
from open_medicine.mcp.calculators.gcs import GCSParams, calculate_gcs
from open_medicine.mcp.calculators.renal_dose_adjustment import (
    RenalDoseAdjustmentParams,
    RenalMetric,
    calculate_renal_dose_adjustment,
)


CALCULATOR_DIR = Path("src/open_medicine/mcp/calculators")


def test_none_valued_clinical_results_declare_failure_contract():
    offenders = []

    for module in sorted(CALCULATOR_DIR.glob("*.py")):
        tree = ast.parse(module.read_text(), filename=str(module))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            is_clinical_result = (
                isinstance(function, ast.Name) and function.id == "ClinicalResult"
            ) or (
                isinstance(function, ast.Attribute)
                and function.attr == "ClinicalResult"
            )
            if not is_clinical_result:
                continue

            keywords = {keyword.arg: keyword.value for keyword in node.keywords}
            value = keywords.get("value")
            if not (isinstance(value, ast.Constant) and value.value is None):
                continue

            missing = [name for name in ("status", "errors") if name not in keywords]
            if missing:
                offenders.append(
                    f"{module}:{node.lineno}: missing {', '.join(missing)}"
                )

    assert not offenders, (
        "ClinicalResult(value=None) must declare explicit status and errors:\n"
        + "\n".join(offenders)
    )


def test_fhir_gcs_and_chadsvasc_success_use_integer_values():
    gcs = calculate_gcs(GCSParams(eye_response=4, verbal_response=5, motor_response=6))
    chads = calculate_chadsvasc(
        CHADSVAScParams(
            congestive_heart_failure=False, hypertension=False, age=50,
            diabetes=False, stroke_tia_thromboembolism=False,
            vascular_disease=False, female_sex=False,
        )
    )
    assert gcs.to_fhir("Patient/1")["valueInteger"] == 15
    assert chads.to_fhir("Patient/1")["valueInteger"] == 0


def test_fhir_gcs_absent_data_has_reason_and_no_value():
    result = calculate_gcs(
        GCSParams(
            eye_response=None, eye_non_testable_reason="swelling",
            verbal_response=5, motor_response=6,
        )
    )
    observation = result.to_fhir("Patient/1")
    assert "dataAbsentReason" in observation
    assert not any(key.startswith("value") for key in observation)
    assert "code" in observation


def test_fhir_structured_value_is_deterministic_json_string():
    result = ClinicalResult(
        value={"z": [2, 1], "a": {"b": True}}, interpretation="structured",
        evidence=Evidence(level="test", description="test"),
        fhir_code="test", fhir_system="urn:test",
    )
    observation = result.to_fhir("Patient/1")
    assert observation["valueString"] == json.dumps(
        result.value, sort_keys=True, separators=(",", ":")
    )
    assert "valueQuantity" not in observation


def test_renal_structured_result_fails_closed_without_valid_code():
    result = calculate_renal_dose_adjustment(
        RenalDoseAdjustmentParams(
            drug_name="vancomycin", renal_value=49.5,
            renal_metric=RenalMetric.CRCL,
        )
    )
    with pytest.raises(ValueError, match="FHIR code and system are required"):
        result.to_fhir("Patient/1")


@pytest.mark.parametrize("value", [float("nan"), float("inf"), {1, 2}])
def test_fhir_rejects_nonfinite_or_unsupported_values(value):
    result = ClinicalResult(
        value=value, interpretation="invalid",
        evidence=Evidence(level="test", description="test"),
        fhir_code="test", fhir_system="urn:test",
    )
    with pytest.raises(ValueError, match="Unsupported FHIR observation value"):
        result.to_fhir("Patient/1")


def test_fhir_requires_both_code_and_system():
    result = ClinicalResult(
        value=True, interpretation="boolean",
        evidence=Evidence(level="test", description="test"),
    )
    with pytest.raises(ValueError, match="FHIR code and system are required"):
        result.to_fhir("Patient/1")
