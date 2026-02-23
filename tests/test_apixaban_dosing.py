import pytest
from open_medicine.mcp.calculators.apixaban_dosing import calculate_apixaban_dosing, ApixabanDosingParams

def test_apixaban_standard_dose():
    params = ApixabanDosingParams(age=74, weight_kg=68.0, serum_creatinine=1.12)
    result = calculate_apixaban_dosing(params)
    assert "5 mg twice daily" in result.interpretation

def test_apixaban_reduced_dose_age_weight():
    params = ApixabanDosingParams(age=82, weight_kg=55.0, serum_creatinine=1.2)
    result = calculate_apixaban_dosing(params)
    assert "2.5 mg twice daily" in result.interpretation

def test_apixaban_reduced_dose_weight_scr():
    params = ApixabanDosingParams(age=75, weight_kg=58.0, serum_creatinine=1.8)
    result = calculate_apixaban_dosing(params)
    assert "2.5 mg twice daily" in result.interpretation

def test_apixaban_reduced_dose_all_three():
    params = ApixabanDosingParams(age=85, weight_kg=45.0, serum_creatinine=2.1)
    result = calculate_apixaban_dosing(params)
    assert "2.5 mg twice daily" in result.interpretation

def test_apixaban_one_criterion_only():
    params = ApixabanDosingParams(age=81, weight_kg=70.0, serum_creatinine=1.0)
    result = calculate_apixaban_dosing(params)
    assert "5 mg twice daily" in result.interpretation
