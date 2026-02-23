import pytest
from open_medicine.mcp.calculators.child_pugh import (
    calculate_child_pugh, ChildPughParams, AscitesGrade, EncephalopathyGrade
)


def test_child_pugh_minimum_score():
    """All best values → score 5, Class A."""
    params = ChildPughParams(
        bilirubin=1.0, albumin=4.0, inr=1.0,
        ascites=AscitesGrade.NONE, encephalopathy=EncephalopathyGrade.NONE
    )
    res = calculate_child_pugh(params)
    assert res.value == 5
    assert "Class A" in res.interpretation


def test_child_pugh_maximum_score():
    """All worst values → score 15, Class C."""
    params = ChildPughParams(
        bilirubin=5.0, albumin=2.0, inr=3.0,
        ascites=AscitesGrade.SEVERE, encephalopathy=EncephalopathyGrade.GRADE_3_4
    )
    res = calculate_child_pugh(params)
    assert res.value == 15
    assert "Class C" in res.interpretation


def test_child_pugh_class_a_boundary():
    """Score 6 → still Class A."""
    params = ChildPughParams(
        bilirubin=2.5, albumin=4.0, inr=1.0,
        ascites=AscitesGrade.NONE, encephalopathy=EncephalopathyGrade.NONE
    )
    res = calculate_child_pugh(params)
    assert res.value == 6
    assert "Class A" in res.interpretation


def test_child_pugh_class_b_boundary_low():
    """Score 7 → Class B."""
    params = ChildPughParams(
        bilirubin=2.5, albumin=3.0, inr=1.0,
        ascites=AscitesGrade.NONE, encephalopathy=EncephalopathyGrade.NONE
    )
    res = calculate_child_pugh(params)
    assert res.value == 7
    assert "Class B" in res.interpretation


def test_child_pugh_class_b_boundary_high():
    """Score 9 → still Class B."""
    params = ChildPughParams(
        bilirubin=2.5, albumin=3.0, inr=2.0,
        ascites=AscitesGrade.MILD, encephalopathy=EncephalopathyGrade.NONE
    )
    res = calculate_child_pugh(params)
    assert res.value == 9
    assert "Class B" in res.interpretation


def test_child_pugh_class_c_boundary():
    """Score 10 → Class C."""
    params = ChildPughParams(
        bilirubin=2.5, albumin=3.0, inr=2.0,
        ascites=AscitesGrade.MILD, encephalopathy=EncephalopathyGrade.GRADE_1_2
    )
    res = calculate_child_pugh(params)
    assert res.value == 10
    assert "Class C" in res.interpretation


def test_child_pugh_pbc_bilirubin():
    """PBC uses different bilirubin thresholds."""
    params = ChildPughParams(
        bilirubin=5.0, albumin=4.0, inr=1.0,
        ascites=AscitesGrade.NONE, encephalopathy=EncephalopathyGrade.NONE,
        is_primary_biliary_cholangitis=True
    )
    res = calculate_child_pugh(params)
    # PBC: bili 5.0 → 2 points (4-10 range); standard would be 3 points (>3)
    assert res.value == 6  # 2+1+1+1+1

    params_standard = ChildPughParams(
        bilirubin=5.0, albumin=4.0, inr=1.0,
        ascites=AscitesGrade.NONE, encephalopathy=EncephalopathyGrade.NONE,
        is_primary_biliary_cholangitis=False
    )
    res_std = calculate_child_pugh(params_standard)
    assert res_std.value == 7  # 3+1+1+1+1


def test_child_pugh_evidence_doi():
    params = ChildPughParams(
        bilirubin=1.0, albumin=4.0, inr=1.0,
        ascites=AscitesGrade.NONE, encephalopathy=EncephalopathyGrade.NONE
    )
    res = calculate_child_pugh(params)
    assert res.evidence.source_doi == "10.1002/bjs.1800600817"


def test_child_pugh_fhir_code():
    params = ChildPughParams(
        bilirubin=1.0, albumin=4.0, inr=1.0,
        ascites=AscitesGrade.NONE, encephalopathy=EncephalopathyGrade.NONE
    )
    res = calculate_child_pugh(params)
    assert res.fhir_code == "80204-3"
    assert res.fhir_system == "http://loinc.org"
