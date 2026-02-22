import json
import os
import pytest
from open_medicine.mcp.calculators.ascvd import calculate_ascvd, ASCVDParams

def load_test_cases():
    data_file = os.path.join(os.path.dirname(__file__), "data", "ascvd_test_cases.json")
    if not os.path.exists(data_file):
        pytest.skip(f"Comparative validation data file missing: {data_file}")
    with open(data_file, "r") as f:
        return json.load(f)

def test_ascvd_comparative_validation():
    """
    Comparative validation of our implemented ASCVD mathematical model against
    200 randomly generated patient profiles produced by the established
    PyPI 'ascvd' package.
    """
    test_cases = load_test_cases()
    assert len(test_cases) > 0

    passed_count = 0
    failed_cases = []

    for idx, case in enumerate(test_cases):
        params = ASCVDParams(
            is_male=case["isMale"],
            is_black=case["isBlack"],
            smoker=case["smoker"],
            hypertensive=case["hypertensive"],
            diabetic=case["diabetic"],
            age=case["age"],
            systolic_blood_pressure=case["systolicBloodPressure"],
            total_cholesterol=case["totalCholesterol"],
            hdl_cholesterol=case["hdl"]
        )

        result = calculate_ascvd(params)
        
        # In mathematical validation, allow a small float tolerance (e.g. 0.1 rounding diffs)
        # But we actually expect them to be identical since both round to 1 decimal.
        expected = case["expected_score"]
        actual = result.value

        if abs(expected - actual) <= 0.2: # allow tiny rounding diffs
            passed_count += 1
        else:
            failed_cases.append({
                "index": idx,
                "params": case,
                "expected": expected,
                "actual": actual
            })

    assert len(failed_cases) == 0, f"Cross-validation failed on {len(failed_cases)} cases. Example: {failed_cases[0]}"
    assert passed_count == len(test_cases)
