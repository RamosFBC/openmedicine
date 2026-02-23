import pytest
from open_medicine.mcp.calculators.insulin_basal_dosing import (
    calculate_insulin_basal_dosing, InsulinBasalDosingParams
)


# --- Starting dose tests ---

def test_starting_dose_light_patient():
    """40kg patient: 0.2*40=8, but minimum is 10"""
    params = InsulinBasalDosingParams(weight_kg=40)
    result = calculate_insulin_basal_dosing(params)
    assert result.value == 10.0


def test_starting_dose_average_patient():
    """80kg patient: 0.2*80=16"""
    params = InsulinBasalDosingParams(weight_kg=80)
    result = calculate_insulin_basal_dosing(params)
    assert result.value == 16.0


def test_starting_dose_heavy_patient():
    """120kg patient: 0.2*120=24"""
    params = InsulinBasalDosingParams(weight_kg=120)
    result = calculate_insulin_basal_dosing(params)
    assert result.value == 24.0


# --- Titration tests ---

def test_titration_above_180():
    """FG >180 → increase by 4"""
    params = InsulinBasalDosingParams(weight_kg=80, current_dose=20, fasting_glucose=200)
    result = calculate_insulin_basal_dosing(params)
    assert result.value == 24.0


def test_titration_141_180():
    """FG 141-180 → increase by 2"""
    params = InsulinBasalDosingParams(weight_kg=80, current_dose=20, fasting_glucose=160)
    result = calculate_insulin_basal_dosing(params)
    assert result.value == 22.0


def test_titration_111_140():
    """FG 111-140 → increase by 1"""
    params = InsulinBasalDosingParams(weight_kg=80, current_dose=20, fasting_glucose=125)
    result = calculate_insulin_basal_dosing(params)
    assert result.value == 21.0


def test_titration_at_target():
    """FG 70-110 → no change"""
    params = InsulinBasalDosingParams(weight_kg=80, current_dose=20, fasting_glucose=95)
    result = calculate_insulin_basal_dosing(params)
    assert result.value == 20.0


def test_titration_mild_hypo():
    """FG 54-69 → decrease by 2"""
    params = InsulinBasalDosingParams(weight_kg=80, current_dose=20, fasting_glucose=60)
    result = calculate_insulin_basal_dosing(params)
    assert result.value == 18.0


def test_titration_severe_hypo():
    """FG <54 → decrease by 4"""
    params = InsulinBasalDosingParams(weight_kg=80, current_dose=20, fasting_glucose=45)
    result = calculate_insulin_basal_dosing(params)
    assert result.value == 16.0


def test_titration_no_negative_dose():
    """Very low dose + hypo shouldn't go negative"""
    params = InsulinBasalDosingParams(weight_kg=80, current_dose=2, fasting_glucose=45)
    result = calculate_insulin_basal_dosing(params)
    assert result.value == 0


def test_titration_boundary_180():
    """FG exactly 180 → 141-180 bracket (increase by 2)"""
    params = InsulinBasalDosingParams(weight_kg=80, current_dose=20, fasting_glucose=180)
    result = calculate_insulin_basal_dosing(params)
    assert result.value == 22.0


def test_titration_boundary_141():
    """FG exactly 141 → 141-180 bracket"""
    params = InsulinBasalDosingParams(weight_kg=80, current_dose=20, fasting_glucose=141)
    result = calculate_insulin_basal_dosing(params)
    assert result.value == 22.0


def test_titration_boundary_111():
    """FG exactly 111 → 111-140 bracket"""
    params = InsulinBasalDosingParams(weight_kg=80, current_dose=20, fasting_glucose=111)
    result = calculate_insulin_basal_dosing(params)
    assert result.value == 21.0


def test_titration_boundary_70():
    """FG exactly 70 → target range"""
    params = InsulinBasalDosingParams(weight_kg=80, current_dose=20, fasting_glucose=70)
    result = calculate_insulin_basal_dosing(params)
    assert result.value == 20.0


def test_titration_boundary_54():
    """FG exactly 54 → mild hypo bracket"""
    params = InsulinBasalDosingParams(weight_kg=80, current_dose=20, fasting_glucose=54)
    result = calculate_insulin_basal_dosing(params)
    assert result.value == 18.0


# --- Current dose without glucose ---

def test_current_dose_no_glucose():
    """Current dose provided but no fasting glucose"""
    params = InsulinBasalDosingParams(weight_kg=80, current_dose=20)
    result = calculate_insulin_basal_dosing(params)
    assert result.value == 20.0
    assert "provide fasting glucose" in result.interpretation.lower()


# --- Evidence ---

def test_evidence_doi():
    params = InsulinBasalDosingParams(weight_kg=80)
    result = calculate_insulin_basal_dosing(params)
    assert result.evidence.source_doi == "10.2337/dc24-S009"


def test_fhir_code():
    params = InsulinBasalDosingParams(weight_kg=80)
    result = calculate_insulin_basal_dosing(params)
    assert result.fhir_code == "46716-4"
    assert result.fhir_system == "http://loinc.org"
