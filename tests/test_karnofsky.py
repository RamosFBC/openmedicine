import pytest
from pydantic import ValidationError
from open_medicine.mcp.calculators.karnofsky import calculate_karnofsky, KarnofskyParams


# --- Tier 1: Deterministic Unit Tests ---


def test_karnofsky_maximum_score():
    """Test KPS 100 -- fully functional, no evidence of disease."""
    params = KarnofskyParams(kps_score=100)
    result = calculate_karnofsky(params)
    assert result.value == 100
    assert "100%" in result.interpretation
    assert "Normal" in result.interpretation
    assert "no evidence of disease" in result.interpretation
    assert "Able to carry on normal activity and to work" in result.interpretation


def test_karnofsky_minimum_score():
    """Test KPS 0 -- dead."""
    params = KarnofskyParams(kps_score=0)
    result = calculate_karnofsky(params)
    assert result.value == 0
    assert "0%" in result.interpretation
    assert "Dead" in result.interpretation
    assert "Unable to care for self" in result.interpretation


def test_karnofsky_score_90():
    """Test KPS 90 -- minor signs or symptoms."""
    params = KarnofskyParams(kps_score=90)
    result = calculate_karnofsky(params)
    assert result.value == 90
    assert "90%" in result.interpretation
    assert "minor signs or symptoms" in result.interpretation
    assert "Able to carry on normal activity and to work" in result.interpretation


def test_karnofsky_score_80():
    """Test KPS 80 -- normal activity with effort."""
    params = KarnofskyParams(kps_score=80)
    result = calculate_karnofsky(params)
    assert result.value == 80
    assert "80%" in result.interpretation
    assert "Normal activity with effort" in result.interpretation
    assert "Able to carry on normal activity and to work" in result.interpretation


def test_karnofsky_score_70():
    """Test KPS 70 -- boundary into 'unable to work' category."""
    params = KarnofskyParams(kps_score=70)
    result = calculate_karnofsky(params)
    assert result.value == 70
    assert "70%" in result.interpretation
    assert "Cares for self" in result.interpretation
    assert "unable to carry on normal activity" in result.interpretation
    assert "Unable to work" in result.interpretation


def test_karnofsky_score_60():
    """Test KPS 60 -- requires occasional assistance."""
    params = KarnofskyParams(kps_score=60)
    result = calculate_karnofsky(params)
    assert result.value == 60
    assert "60%" in result.interpretation
    assert "occasional assistance" in result.interpretation
    assert "Unable to work" in result.interpretation


def test_karnofsky_score_50():
    """Test KPS 50 -- requires considerable assistance (lowest in mid category)."""
    params = KarnofskyParams(kps_score=50)
    result = calculate_karnofsky(params)
    assert result.value == 50
    assert "50%" in result.interpretation
    assert "considerable assistance" in result.interpretation
    assert "Unable to work" in result.interpretation


def test_karnofsky_score_40():
    """Test KPS 40 -- boundary into 'institutional care' category."""
    params = KarnofskyParams(kps_score=40)
    result = calculate_karnofsky(params)
    assert result.value == 40
    assert "40%" in result.interpretation
    assert "Disabled" in result.interpretation
    assert "Unable to care for self" in result.interpretation


def test_karnofsky_score_30():
    """Test KPS 30 -- severely disabled, hospitalization indicated."""
    params = KarnofskyParams(kps_score=30)
    result = calculate_karnofsky(params)
    assert result.value == 30
    assert "30%" in result.interpretation
    assert "Severely disabled" in result.interpretation
    assert "hospital admission" in result.interpretation


def test_karnofsky_score_20():
    """Test KPS 20 -- very sick, hospitalization necessary."""
    params = KarnofskyParams(kps_score=20)
    result = calculate_karnofsky(params)
    assert result.value == 20
    assert "20%" in result.interpretation
    assert "Very sick" in result.interpretation


def test_karnofsky_score_10():
    """Test KPS 10 -- moribund."""
    params = KarnofskyParams(kps_score=10)
    result = calculate_karnofsky(params)
    assert result.value == 10
    assert "10%" in result.interpretation
    assert "Moribund" in result.interpretation
    assert "Unable to care for self" in result.interpretation


def test_karnofsky_all_valid_scores():
    """Test that every valid KPS score (0-100 in increments of 10) returns a result."""
    for score in range(0, 110, 10):
        params = KarnofskyParams(kps_score=score)
        result = calculate_karnofsky(params)
        assert result.value == score
        assert len(result.interpretation) > 0
        assert f"{score}%" in result.interpretation


def test_karnofsky_invalid_score_not_multiple_of_10():
    """Test that a score not a multiple of 10 returns value=None with explanation."""
    params = KarnofskyParams(kps_score=55)
    result = calculate_karnofsky(params)
    assert result.value is None
    assert "Invalid KPS score" in result.interpretation
    assert "increments of 10" in result.interpretation


def test_karnofsky_invalid_score_15():
    """Test another non-multiple-of-10 value."""
    params = KarnofskyParams(kps_score=15)
    result = calculate_karnofsky(params)
    assert result.value is None
    assert "Invalid KPS score" in result.interpretation


def test_karnofsky_pydantic_rejects_negative():
    """Test that Pydantic rejects negative scores."""
    with pytest.raises(ValidationError):
        KarnofskyParams(kps_score=-10)


def test_karnofsky_pydantic_rejects_above_100():
    """Test that Pydantic rejects scores above 100."""
    with pytest.raises(ValidationError):
        KarnofskyParams(kps_score=110)


def test_karnofsky_evidence_doi():
    """Verify DOI is the Schag 1984 validation study."""
    params = KarnofskyParams(kps_score=70)
    result = calculate_karnofsky(params)
    assert result.evidence.source_doi == "10.1200/JCO.1984.2.3.187"
    assert result.evidence.level == "Validation Study"
    assert "Schag" in result.evidence.description


def test_karnofsky_fhir_code():
    """Verify FHIR code represents the KPS output concept."""
    params = KarnofskyParams(kps_score=80)
    result = calculate_karnofsky(params)
    assert result.fhir_code == "89243-0"
    assert result.fhir_system == "http://loinc.org"
    assert result.fhir_display == "Karnofsky Performance Status score"


# --- Functional category boundary tests ---


def test_karnofsky_category_boundary_80_vs_70():
    """Test the boundary between 'able to work' (>=80) and 'unable to work' (<=70)."""
    result_80 = calculate_karnofsky(KarnofskyParams(kps_score=80))
    result_70 = calculate_karnofsky(KarnofskyParams(kps_score=70))
    assert "Able to carry on normal activity and to work" in result_80.interpretation
    assert "Unable to work" in result_70.interpretation


def test_karnofsky_category_boundary_50_vs_40():
    """Test the boundary between 'self-care possible' (>=50) and 'institutional care' (<=40)."""
    result_50 = calculate_karnofsky(KarnofskyParams(kps_score=50))
    result_40 = calculate_karnofsky(KarnofskyParams(kps_score=40))
    assert "Unable to work" in result_50.interpretation
    assert "Unable to care for self" in result_40.interpretation


def test_karnofsky_to_fhir_export():
    """Test FHIR Observation export structure."""
    params = KarnofskyParams(kps_score=60)
    result = calculate_karnofsky(params)
    fhir = result.to_fhir(subject_reference="Patient/123")
    assert fhir["resourceType"] == "Observation"
    assert fhir["status"] == "final"
    assert fhir["valueQuantity"]["value"] == 60
    assert fhir["code"]["coding"][0]["code"] == "89243-0"
    assert fhir["code"]["coding"][0]["system"] == "http://loinc.org"
