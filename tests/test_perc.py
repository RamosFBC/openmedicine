from open_medicine.mcp.calculators.perc import calculate_perc, PERCParams


def test_perc_all_negative():
    """All criteria negative = PE ruled out."""
    params = PERCParams()
    res = calculate_perc(params)
    assert res.value == 0
    assert "PE can be ruled out" in res.interpretation


def test_perc_maximum_score():
    """All 8 criteria positive."""
    params = PERCParams(
        age_gte_50=True,
        heart_rate_gte_100=True,
        spo2_lt_95=True,
        unilateral_leg_swelling=True,
        hemoptysis=True,
        recent_surgery_or_trauma=True,
        prior_dvt_pe=True,
        estrogen_use=True,
    )
    res = calculate_perc(params)
    assert res.value == 8
    assert "cannot be ruled out" in res.interpretation


def test_perc_single_positive():
    """One criterion positive = cannot rule out."""
    params = PERCParams(age_gte_50=True)
    res = calculate_perc(params)
    assert res.value == 1
    assert "cannot be ruled out" in res.interpretation


def test_perc_evidence_doi():
    params = PERCParams()
    res = calculate_perc(params)
    assert res.evidence.source_doi == "10.1111/j.1538-7836.2004.00985.x"


def test_perc_fhir_code():
    params = PERCParams()
    res = calculate_perc(params)
    assert res.fhir_code == "96307-8"
    assert res.fhir_system == "http://loinc.org"
