import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.aa_gradient import calculate_aa_gradient, AaGradientParams


def test_normal_room_air():
    """FiO2=0.21, PaO2=100, PaCO2=40, Patm=760. A-a = 0.21*(760-47) - 40/0.8 - 100 = 149.73 - 50 - 100 = -0.3"""
    result = calculate_aa_gradient(AaGradientParams(fio2=0.21, pao2=100, paco2=40))
    # PAO2 = 0.21 * 713 = 149.73; A-a = 149.73 - 50 - 100 = -0.3
    assert result.value == pytest.approx(-0.3, abs=0.1)

def test_typical_young_healthy():
    """FiO2=0.21, PaO2=95, PaCO2=40. A-a ≈ 4.7"""
    result = calculate_aa_gradient(AaGradientParams(fio2=0.21, pao2=95, paco2=40))
    expected = 0.21 * (760 - 47) - (40 / 0.8) - 95
    assert result.value == round(expected, 1)

def test_elevated_gradient():
    """FiO2=0.21, PaO2=60, PaCO2=40. A-a ≈ 39.7"""
    result = calculate_aa_gradient(AaGradientParams(fio2=0.21, pao2=60, paco2=40))
    expected = round(0.21 * 713 - 50 - 60, 1)
    assert result.value == expected
    assert "Elevated" in result.interpretation

def test_with_age_normal():
    """Age 20, expected upper limit = 20/4+4 = 9. A-a = 5 → normal."""
    result = calculate_aa_gradient(AaGradientParams(fio2=0.21, pao2=94.7, paco2=40, age=20))
    assert "Normal A-a gradient for age" in result.interpretation

def test_with_age_elevated():
    """Age 20, expected limit 9. Give PaO2=60 → A-a ≈ 39.7 → elevated."""
    result = calculate_aa_gradient(AaGradientParams(fio2=0.21, pao2=60, paco2=40, age=20))
    assert "Elevated" in result.interpretation

def test_high_fio2():
    """FiO2=1.0, PaO2=300, PaCO2=40."""
    result = calculate_aa_gradient(AaGradientParams(fio2=1.0, pao2=300, paco2=40))
    expected = round(1.0 * 713 - 50 - 300, 1)
    assert result.value == expected

def test_altitude():
    """Denver ~630 mmHg atmospheric pressure."""
    result = calculate_aa_gradient(AaGradientParams(fio2=0.21, pao2=80, paco2=35, atmospheric_pressure=630))
    pao2_alv = 0.21 * (630 - 47) - 35 / 0.8
    expected = round(pao2_alv - 80, 1)
    assert result.value == expected

def test_evidence():
    result = calculate_aa_gradient(AaGradientParams(fio2=0.21, pao2=95, paco2=40))
    assert result.evidence.source_doi
    assert result.fhir_code == "19994-3"
    assert result.fhir_system == "http://loinc.org"


@given(
    fio2=st.floats(min_value=0.21, max_value=1.0),
    pao2=st.floats(min_value=20, max_value=600),
    paco2=st.floats(min_value=10, max_value=100),
)
@settings(max_examples=500)
def test_aa_gradient_fuzz(fio2, pao2, paco2):
    result = calculate_aa_gradient(AaGradientParams(fio2=fio2, pao2=pao2, paco2=paco2))
    assert result.value is not None
    assert isinstance(result.value, float)
    assert result.interpretation
