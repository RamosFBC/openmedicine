import pytest
from open_medicine.mcp.calculators.fisher_grade import calculate_fisher_grade, FisherGradeParams


@pytest.mark.parametrize("grade,ct_fragment,risk_fragment", [
    (1, "No blood detected", "Low vasospasm risk"),
    (2, "Diffuse thin", "Low-moderate vasospasm risk"),
    (3, "Localized clot", "High vasospasm risk"),
    (4, "Intracerebral or intraventricular", "Low-moderate vasospasm risk"),
])
def test_fisher_each_grade(grade, ct_fragment, risk_fragment):
    result = calculate_fisher_grade(FisherGradeParams(grade=grade))
    assert result.value == grade
    assert ct_fragment in result.interpretation
    assert risk_fragment in result.interpretation


def test_fisher_minimum():
    result = calculate_fisher_grade(FisherGradeParams(grade=1))
    assert result.value == 1


def test_fisher_maximum():
    result = calculate_fisher_grade(FisherGradeParams(grade=4))
    assert result.value == 4


def test_fisher_evidence():
    result = calculate_fisher_grade(FisherGradeParams(grade=1))
    assert "Fisher" in result.evidence.source_doi
    assert "1980" in result.evidence.source_doi


def test_fisher_fhir():
    result = calculate_fisher_grade(FisherGradeParams(grade=1))
    assert result.fhir_system == "http://loinc.org"


def test_fisher_invalid_grade():
    with pytest.raises(Exception):
        FisherGradeParams(grade=0)
    with pytest.raises(Exception):
        FisherGradeParams(grade=5)
