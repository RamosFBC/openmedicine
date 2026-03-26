import json
import os
import pytest
from open_medicine.mcp.calculators.das28 import calculate_das28, DAS28Params

_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "das28_test_cases.json")


def load_test_vectors():
    """Load published test vectors for DAS28."""
    if not os.path.exists(_DATA_PATH):
        return []
    with open(_DATA_PATH) as f:
        return json.load(f)


@pytest.mark.skipif(not os.path.exists(_DATA_PATH), reason="comparative test data not available")
@pytest.mark.parametrize("case", load_test_vectors(), ids=lambda c: c.get("description", ""))
def test_das28_vs_reference(case):
    """Cross-validate DAS28 against manually computed reference values."""
    params = DAS28Params(**case["input"])
    result = calculate_das28(params)
    assert result.value is not None, f"Expected a numeric result for: {case['description']}"
    tolerance = case.get("tolerance", 0.05)
    assert abs(result.value - case["expected"]) <= tolerance, (
        f"DAS28 mismatch for '{case['description']}': "
        f"got {result.value}, expected {case['expected']} (tolerance={tolerance})"
    )
