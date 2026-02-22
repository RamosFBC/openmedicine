from open_medicine.mcp.calculators.ckd_epi import calculate_ckd_epi, CKDEPIParams

def test_ckd_epi_female_low_creatinine():
    params = CKDEPIParams(age=50, is_female=True, serum_creatinine=0.6)
    res = calculate_ckd_epi(params)
    assert res.value > 90
    assert "G1: Normal or high" in res.interpretation
    assert res.evidence.source_doi == "10.1056/NEJMoa2102953"

def test_ckd_epi_male_high_creatinine():
    params = CKDEPIParams(age=65, is_female=False, serum_creatinine=2.0)
    res = calculate_ckd_epi(params)
    # A 65yo male with 2.0 creatinine has poor kidney function (~35 eGFR)
    assert 30 <= res.value <= 45
    assert "G3b" in res.interpretation

def test_ckd_epi_extreme_age():
    # 90yo female with moderately high creatinine
    params = CKDEPIParams(age=90, is_female=True, serum_creatinine=1.4)
    res = calculate_ckd_epi(params)
    assert res.value < 45 # Old age significantly reduces eGFR

def test_ckd_epi_kidney_failure():
    params = CKDEPIParams(age=60, is_female=False, serum_creatinine=8.0)
    res = calculate_ckd_epi(params)
    assert res.value < 15
    assert "G5: Kidney failure" in res.interpretation
