import pytest
from open_medicine.mcp.calculators.hunt_hess import calculate_hunt_hess, HuntHessParams


@pytest.mark.parametrize("grade,desc_fragment,mortality", [
    (1, "Asymptomatic", "1%"),
    (2, "Moderate-to-severe headache", "5%"),
    (3, "Drowsiness", "19%"),
    (4, "Stupor", "42%"),
    (5, "Deep coma", "77%"),
])
def test_hunt_hess_each_grade(grade, desc_fragment, mortality):
    result = calculate_hunt_hess(HuntHessParams(grade=grade))
    assert result.value == grade
    assert desc_fragment in result.interpretation
    assert mortality in result.interpretation


def test_hunt_hess_minimum():
    result = calculate_hunt_hess(HuntHessParams(grade=1))
    assert result.value == 1


def test_hunt_hess_maximum():
    result = calculate_hunt_hess(HuntHessParams(grade=5))
    assert result.value == 5


def test_hunt_hess_evidence():
    result = calculate_hunt_hess(HuntHessParams(grade=1))
    assert result.evidence.source_doi == "10.3171/jns.1968.28.1.0014"


def test_hunt_hess_fhir():
    result = calculate_hunt_hess(HuntHessParams(grade=1))
    assert result.fhir_system == "http://loinc.org"


def test_hunt_hess_invalid_grade():
    with pytest.raises(Exception):
        HuntHessParams(grade=0)
    with pytest.raises(Exception):
        HuntHessParams(grade=6)
