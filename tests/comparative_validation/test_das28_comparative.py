import json
import os
import pytest
from open_medicine.mcp.calculators.das28 import calculate_das28, DAS28Params


def load_test_vectors():
    """Load published test vectors for DAS28."""
    data_path = os.path.join(
        os.path.dirname(__file__),
        "data",
        "das28_test_cases.json"
    )
    with open(data_path) as f:
        return json.load(f)


@pytest.mark.parametrize("case", load_test_vectors(), ids=lambda c: c["description"])
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
