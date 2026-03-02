import json
import os
import pytest
from open_medicine.mcp.calculators.maintenance_iv_fluids import (
    calculate_maintenance_iv_fluids,
    MaintenanceIVFluidsParams,
)


def load_test_cases():
    data_file = os.path.join(
        os.path.dirname(__file__), "data", "maintenance_iv_fluids_test_cases.json"
    )
    if not os.path.exists(data_file):
        pytest.skip(f"Comparative validation data file missing: {data_file}")
    with open(data_file, "r") as f:
        return json.load(f)


def test_maintenance_iv_fluids_comparative_validation():
    """
    Comparative validation of the Holliday-Segar 4-2-1 maintenance IV fluid
    calculator against reference values verified with MDCalc and manual
    calculation from the original 1957 formula.
    """
    test_cases = load_test_cases()
    assert len(test_cases) > 0

    passed_count = 0
    failed_cases = []

    for idx, case in enumerate(test_cases):
        params = MaintenanceIVFluidsParams(**case["input"])
        result = calculate_maintenance_iv_fluids(params)

        tolerance = case.get("tolerance", 0.1)
        expected_hourly = case["expected_hourly"]
        actual_hourly = result.value

        if abs(expected_hourly - actual_hourly) <= tolerance:
            passed_count += 1
        else:
            failed_cases.append(
                {
                    "index": idx,
                    "description": case.get("description", ""),
                    "expected_hourly": expected_hourly,
                    "actual_hourly": actual_hourly,
                }
            )

    assert len(failed_cases) == 0, (
        f"Cross-validation failed on {len(failed_cases)} cases. "
        f"Example: {failed_cases[0]}"
    )
    assert passed_count == len(test_cases)
