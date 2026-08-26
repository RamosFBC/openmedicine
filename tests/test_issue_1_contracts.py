import asyncio
import hashlib
import json
from pathlib import Path
import tomllib

import pytest
from pydantic import BaseModel, ValidationError

from open_medicine import __version__
from open_medicine.mcp.base import ClinicalError, ClinicalResult, Evidence, ResultStatus
from open_medicine.mcp.calculators.chadsvasc import CHADSVAScParams
from open_medicine.mcp.calculators.gcs import GCSParams
from open_medicine.mcp.registry import CALCULATOR_REGISTRY, RegisteredTool
from open_medicine.mcp.server import handle_call_tool


def _payload(result):
    return json.loads(result[0].text)


def test_package_caps_mcp_before_breaking_v2():
    project = tomllib.loads(Path("pyproject.toml").read_text())["project"]
    mcp_requirement = next(
        requirement for requirement in project["dependencies"] if requirement.startswith("mcp")
    )
    assert "<2" in mcp_requirement


def test_evidence_supports_document_provenance_without_a_doi():
    evidence = Evidence(
        authority="FDA", url="https://example.test/label", document_id="label-1",
        version_date="2025-01-01", section="2.3", retrieved_at="2026-08-26T00:00:00Z",
        content_hash="sha256:abc", level="regulatory", description="Label",
    )
    assert evidence.source_doi is None
    assert evidence.authority == "FDA"

    result = ClinicalResult(value=1, interpretation="ok", evidence=evidence)
    note = result.to_fhir("Patient/1")["note"][0]["text"]
    assert "Evidence: Label" in note
    assert "Level: regulatory" in note
    assert "DOI:" not in note
    assert "None" not in note


def test_clinical_result_requires_evidence():
    with pytest.raises(ValidationError):
        ClinicalResult(value=1, interpretation="ok")


def test_successful_result_has_typed_success_status_and_remains_constructible():
    result = ClinicalResult(value=1, interpretation="ok", evidence=Evidence(level="x", description="y"))
    assert result.status is ResultStatus.SUCCESS
    assert result.errors == []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"status": ResultStatus.SUCCESS, "value": None, "errors": []},
        {
            "status": ResultStatus.SUCCESS,
            "value": 1,
            "errors": [ClinicalError(code="warning", message="unexpected")],
        },
        {"status": ResultStatus.INSUFFICIENT_DATA, "value": None, "errors": []},
        {
            "status": ResultStatus.INSUFFICIENT_DATA,
            "value": 1,
            "errors": [ClinicalError(code="missing", message="missing")],
        },
        {"status": ResultStatus.ERROR, "value": None, "errors": []},
        {
            "status": ResultStatus.ERROR,
            "value": 1,
            "errors": [ClinicalError(code="failure", message="failed")],
        },
    ],
)
def test_result_status_invariants_reject_invalid_value_and_error_combinations(kwargs):
    with pytest.raises(ValidationError):
        ClinicalResult(
            interpretation="failed",
            evidence=Evidence(level="test", description="test evidence"),
            **kwargs,
        )


@pytest.mark.parametrize(
    "status,expected_absent_code",
    [
        (ResultStatus.INSUFFICIENT_DATA, "not-performed"),
        (ResultStatus.ERROR, "error"),
    ],
)
def test_non_success_fhir_uses_data_absent_reason(status, expected_absent_code):
    result = ClinicalResult(
        status=status,
        errors=[ClinicalError(code="not_available", message="No result available")],
        value=None,
        interpretation="No numeric result is available.",
        evidence=Evidence(level="test", description="test evidence"),
    )

    observation = result.to_fhir("Patient/1")

    assert "valueQuantity" not in observation
    assert observation["dataAbsentReason"]["coding"][0]["system"] == (
        "http://terminology.hl7.org/CodeSystem/data-absent-reason"
    )
    assert observation["dataAbsentReason"]["coding"][0]["code"] == expected_absent_code


def test_unknown_calculator_has_machine_readable_error_envelope():
    data = _payload(asyncio.run(handle_call_tool("execute_clinical_calculator", {
        "calculator_id": "missing", "parameters": {}
    })))
    assert data["status"] == "error"
    assert data["errors"][0]["code"] == "unknown_calculator"


def test_validation_failure_has_machine_readable_details():
    data = _payload(asyncio.run(handle_call_tool("execute_clinical_calculator", {
        "calculator_id": "calculate_bmi", "parameters": {"weight_kg": -1}
    })))
    assert data["status"] == "error"
    assert data["errors"][0]["code"] == "validation_error"
    assert data["errors"][0]["details"]


def test_model_validator_failure_is_json_safe_without_raw_exception_details():
    result = asyncio.run(handle_call_tool("execute_clinical_calculator", {
        "calculator_id": "calculate_gcs",
        "parameters": {
            "eye_response": 2,
            "eye_non_testable_reason": "swelling",
            "verbal_response": 5,
            "motor_response": 6,
        },
    }))

    serialized = result[0].text
    data = json.loads(serialized)
    error = data["errors"][0]
    assert error["code"] == "validation_error"
    assert set(error["details"][0]) == {"loc", "msg", "type"}
    assert error["details"][0]["loc"] == []
    assert "exactly one" in error["details"][0]["msg"].lower()
    assert error["details"][0]["type"] == "value_error"
    assert "ValueError(" not in serialized
    assert "Traceback" not in serialized


@pytest.mark.parametrize(
    "calculator_id,parameters,missing_field",
    [
        (
            "calculate_cockcroft_gault",
            {"age": 50, "weight": 70, "is_female": False, "serum_creatinine": 1},
            "weight_type",
        ),
        (
            "calculate_ckd_epi",
            {"age": 50, "is_female": False, "serum_creatinine": 1},
            "renal_function_stable",
        ),
    ],
)
def test_mcp_requires_explicit_renal_assumptions(calculator_id, parameters, missing_field):
    data = _payload(asyncio.run(handle_call_tool("execute_clinical_calculator", {
        "calculator_id": calculator_id,
        "parameters": parameters,
    })))
    assert data["errors"][0]["code"] == "validation_error"
    assert data["errors"][0]["details"][0]["loc"] == [missing_field]
    assert data["errors"][0]["details"][0]["type"] == "missing"


def test_execution_failure_does_not_serialize_exception_secrets():
    class RaisingParams(BaseModel):
        pass

    secret = "patient-secret-4938"

    def raise_secret(_params):
        raise RuntimeError(secret)

    calculator_id = "_test_secret_raising_calculator"
    CALCULATOR_REGISTRY[calculator_id] = RegisteredTool(
        description="Temporary test calculator",
        pydantic_model=RaisingParams,
        execute_function=raise_secret,
    )
    try:
        result = asyncio.run(
            handle_call_tool(
                "execute_clinical_calculator",
                {"calculator_id": calculator_id, "parameters": {}},
            )
        )
        serialized = result[0].text
        data = json.loads(serialized)
        assert data["errors"][0] == {
            "code": "execution_error",
            "message": "Calculator execution failed.",
            "details": {"exception_type": "RuntimeError"},
        }
        assert secret not in serialized
    finally:
        CALCULATOR_REGISTRY.pop(calculator_id, None)


def test_search_discovery_has_version_and_deterministic_schema_provenance():
    first = _payload(asyncio.run(handle_call_tool("search_clinical_calculators", {"query": "kidney"})))
    second = _payload(asyncio.run(handle_call_tool("search_clinical_calculators", {"query": "kidney"})))
    assert first["package_version"] == __version__
    assert first == second
    match = first["matches"][0]
    canonical = json.dumps(match["required_schema"], sort_keys=True, separators=(",", ":"))
    assert match["schema_hash"] == "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()
    assert match["provenance"]["package"] == "open-medicine"


def test_gcs_and_chadsvasc_schemas_describe_nullable_inputs():
    gcs_properties = GCSParams.model_json_schema()["properties"]
    chadsvasc_properties = CHADSVAScParams.model_json_schema()["properties"]

    assert all(field.get("description") for field in gcs_properties.values())
    assert all(field.get("description") for field in chadsvasc_properties.values())
    assert all(
        "non-testable" in gcs_properties[name]["description"].lower()
        for name in gcs_properties
    )
    assert all(
        "required" in chadsvasc_properties[name]["description"].lower()
        for name in chadsvasc_properties
    )
    for name in chadsvasc_properties:
        if name != "age":
            assert "null" in chadsvasc_properties[name]["description"].lower()
