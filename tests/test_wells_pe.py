from open_medicine.mcp.calculators.wells_pe import calculate_wells_pe, WellsPEParams


def test_wells_pe_minimum_score():
    """All criteria absent = score 0, PE unlikely."""
    params = WellsPEParams()
    res = calculate_wells_pe(params)
    assert res.value == 0.0
    assert "PE unlikely" in res.interpretation


def test_wells_pe_maximum_score():
    """All criteria present = score 12.5."""
    params = WellsPEParams(
        clinical_signs_dvt=True,
        pe_most_likely_diagnosis=True,
        heart_rate_gt_100=True,
        immobilization_or_surgery=True,
        previous_dvt_pe=True,
        hemoptysis=True,
        malignancy=True,
    )
    res = calculate_wells_pe(params)
    assert res.value == 12.5
    assert "PE likely" in res.interpretation


def test_wells_pe_unlikely_boundary():
    """Score 4.0 = PE unlikely (boundary)."""
    params = WellsPEParams(
        heart_rate_gt_100=True,
        immobilization_or_surgery=True,
        hemoptysis=True,
    )
    res = calculate_wells_pe(params)
    assert res.value == 4.0
    assert "PE unlikely" in res.interpretation


def test_wells_pe_likely_boundary():
    """Score 4.5 = PE likely (just above threshold)."""
    params = WellsPEParams(
        heart_rate_gt_100=True,
        immobilization_or_surgery=True,
        previous_dvt_pe=True,
    )
    res = calculate_wells_pe(params)
    assert res.value == 4.5
    assert "PE likely" in res.interpretation


def test_wells_pe_evidence_doi():
    params = WellsPEParams()
    res = calculate_wells_pe(params)
    assert res.evidence.source_doi == "10.1055/s-0037-1613870"


def test_wells_pe_fhir_code():
    params = WellsPEParams()
    res = calculate_wells_pe(params)
    assert res.fhir_code == "96308-6"
    assert res.fhir_system == "http://loinc.org"
