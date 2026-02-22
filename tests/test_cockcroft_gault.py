from open_medicine.mcp.calculators.cockcroft_gault import calculate_cockcroft_gault, CockcroftGaultParams

def test_cockcroft_gault_healthy_young_male():
    # 30yo male, 80kg, normal creatinine (1.0)
    # math: ((140 - 30) * 80) / (72 * 1.0) = 110 * 80 / 72 = 8800 / 72 = ~122.2
    params = CockcroftGaultParams(age=30, weight=80.0, is_female=False, serum_creatinine=1.0)
    res = calculate_cockcroft_gault(params)
    assert 120 <= res.value <= 125 
    assert ">50" in res.interpretation

def test_cockcroft_gault_elderly_low_weight_female():
    # 85yo female, 45kg, elevated creatinine (2.0) indicates severe impairment
    params = CockcroftGaultParams(age=85, weight=45.0, is_female=True, serum_creatinine=2.0)
    res = calculate_cockcroft_gault(params)
    assert res.value < 15
    assert "<10 mL/min suggests severe renal impairment or dialysis dependency" in res.interpretation \
           or "10-50 mL/min typically requires moderate dosage reduction" in res.interpretation

def test_cockcroft_gault_middle_aged_impaired():
    # 55yo male, 100kg, moderately high creatinine (1.8)
    params = CockcroftGaultParams(age=55, weight=100.0, is_female=False, serum_creatinine=1.8)
    res = calculate_cockcroft_gault(params)
    # Output should fall nicely into the moderate dosing band (10-50 mL/min) or just above
    assert "mL/min" in res.interpretation
    assert res.evidence.source_doi == "10.1159/000180580"
