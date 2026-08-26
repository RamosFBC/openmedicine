import pytest
from open_medicine.mcp.calculators.sofa import SOFAParams, calculate_sofa

def test_sofa_normal_patient():
    params = SOFAParams(
        pao2_fio2=450,
        platelets=250,
        bilirubin=0.8,
        map_pressure=80,
        gcs=15,
        creatinine=0.9
    )
    result = calculate_sofa(params)
    assert result.value == 0
    assert result.evidence.source_doi == "10.1007/BF01709751"

def test_sofa_severe_patient():
    params = SOFAParams(
        pao2_fio2=80,      # Score 4
        platelets=15,      # Score 4
        bilirubin=15.0,    # Score 4
        dopamine=20,       # Score 4
        gcs=5,             # Score 4
        creatinine=6.0     # Score 4
    )
    result = calculate_sofa(params)
    assert result.value == 24
    assert result.evidence.source_doi == "10.1007/BF01709751"
    
    # Test FHIR conversion
    fhir_obs = result.to_fhir(subject_reference="Patient/123", encounter_reference="Encounter/456")
    assert fhir_obs["resourceType"] == "Observation"
    assert fhir_obs["status"] == "final"
    assert fhir_obs["subject"]["reference"] == "Patient/123"
    assert fhir_obs["encounter"]["reference"] == "Encounter/456"
    assert fhir_obs["valueInteger"] == 24
    assert fhir_obs["code"]["coding"][0]["code"] == "69442-2"
    assert fhir_obs["code"]["coding"][0]["system"] == "http://loinc.org"
    assert "Evidence:" in fhir_obs["note"][0]["text"]
    assert "10.1007/BF01709751" in fhir_obs["note"][0]["text"]

def test_sofa_missing_data():
    """All missing values should be treated as normal (SOFA 0)."""
    params = SOFAParams()
    result = calculate_sofa(params)
    assert result.value == 0
    assert "low mortality risk" in result.interpretation
