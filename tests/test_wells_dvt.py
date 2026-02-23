from open_medicine.mcp.calculators.wells_dvt import calculate_wells_dvt, WellsDVTParams


def test_wells_dvt_minimum_score():
    """All criteria absent, alternative diagnosis likely = score -2 (low)."""
    params = WellsDVTParams(alternative_diagnosis_likely=True)
    res = calculate_wells_dvt(params)
    assert res.value == -2
    assert "Low probability" in res.interpretation


def test_wells_dvt_all_absent():
    """All criteria absent = score 0 (low)."""
    params = WellsDVTParams()
    res = calculate_wells_dvt(params)
    assert res.value == 0
    assert "Low probability" in res.interpretation


def test_wells_dvt_maximum_score():
    """All positive criteria present, alternative not likely = score 9."""
    params = WellsDVTParams(
        active_cancer=True,
        paralysis_or_casting=True,
        bedridden_or_major_surgery=True,
        tenderness_along_deep_veins=True,
        entire_leg_swollen=True,
        calf_swelling_gt_3cm=True,
        pitting_edema=True,
        collateral_superficial_veins=True,
        previously_documented_dvt=True,
        alternative_diagnosis_likely=False,
    )
    res = calculate_wells_dvt(params)
    assert res.value == 9
    assert "High probability" in res.interpretation


def test_wells_dvt_moderate_boundary_low():
    """Score 1 = moderate probability."""
    params = WellsDVTParams(active_cancer=True)
    res = calculate_wells_dvt(params)
    assert res.value == 1
    assert "Moderate probability" in res.interpretation


def test_wells_dvt_moderate_boundary_high():
    """Score 2 = moderate probability."""
    params = WellsDVTParams(active_cancer=True, pitting_edema=True)
    res = calculate_wells_dvt(params)
    assert res.value == 2
    assert "Moderate probability" in res.interpretation


def test_wells_dvt_high_boundary():
    """Score 3 = high probability."""
    params = WellsDVTParams(
        active_cancer=True,
        pitting_edema=True,
        tenderness_along_deep_veins=True,
    )
    res = calculate_wells_dvt(params)
    assert res.value == 3
    assert "High probability" in res.interpretation


def test_wells_dvt_alternative_diagnosis_subtraction():
    """Alternative diagnosis subtracts 2 points."""
    params = WellsDVTParams(
        active_cancer=True,
        pitting_edema=True,
        alternative_diagnosis_likely=True,
    )
    res = calculate_wells_dvt(params)
    assert res.value == 0
    assert "Low probability" in res.interpretation


def test_wells_dvt_evidence_doi():
    params = WellsDVTParams()
    res = calculate_wells_dvt(params)
    assert res.evidence.source_doi == "10.1056/NEJMoa023153"


def test_wells_dvt_fhir_code():
    params = WellsDVTParams()
    res = calculate_wells_dvt(params)
    assert res.fhir_code == "96309-4"
    assert res.fhir_system == "http://loinc.org"
