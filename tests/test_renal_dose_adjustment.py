from open_medicine.mcp.calculators.renal_dose_adjustment import (
    calculate_renal_dose_adjustment,
    RenalDoseAdjustmentParams,
    RenalMetric,
)


def test_vancomycin_normal_renal_function():
    params = RenalDoseAdjustmentParams(
        drug_name="vancomycin",
        renal_value=80.0,
        renal_metric=RenalMetric.CRCL,
    )
    result = calculate_renal_dose_adjustment(params)
    assert result.value["adjustment_type"] == "no_adjustment"
    assert result.value["drug_name"] == "vancomycin"
    assert result.value["metric_match"] is True
    assert result.evidence.source_doi != ""
