import pytest
from open_medicine.mcp.calculators.renal_dose_adjustment import (
    calculate_renal_dose_adjustment,
    RenalDoseAdjustmentParams,
    RenalMetric,
    _DRUG_DB,
)

# --- Happy path: one test per seed drug ---


def test_vancomycin_normal_renal_function():
    params = RenalDoseAdjustmentParams(drug_name="vancomycin", renal_value=80.0, renal_metric=RenalMetric.CRCL)
    result = calculate_renal_dose_adjustment(params)
    assert result.value["adjustment_type"] == "no_adjustment"
    assert result.value["drug_name"] == "vancomycin"
    assert result.value["metric_match"] is True
    assert result.evidence.source_doi != ""


def test_vancomycin_severe_impairment():
    params = RenalDoseAdjustmentParams(drug_name="vancomycin", renal_value=20.0, renal_metric=RenalMetric.CRCL)
    result = calculate_renal_dose_adjustment(params)
    assert result.value["adjustment_type"] in ("interval_extension", "dose_reduction", "use_with_caution")
    assert result.value["adjusted_dose"] != result.value["normal_dose"]


def test_gabapentin_moderate_impairment():
    params = RenalDoseAdjustmentParams(drug_name="gabapentin", renal_value=45.0, renal_metric=RenalMetric.CRCL)
    result = calculate_renal_dose_adjustment(params)
    assert result.value["adjustment_type"] in ("dose_reduction", "interval_extension")


def test_metformin_contraindicated():
    params = RenalDoseAdjustmentParams(drug_name="metformin", renal_value=20.0, renal_metric=RenalMetric.EGFR)
    result = calculate_renal_dose_adjustment(params)
    assert result.value["adjustment_type"] == "contraindicated"


# --- Tier boundary tests ---


def test_boundary_exact_min():
    """Value exactly at tier min should match that tier."""
    params = RenalDoseAdjustmentParams(drug_name="vancomycin", renal_value=30.0, renal_metric=RenalMetric.CRCL)
    result = calculate_renal_dose_adjustment(params)
    assert result.value["adjustment_type"] != "no_adjustment"  # 30 is in the reduced tier


def test_boundary_exact_max():
    """Value exactly at tier max should match that tier."""
    params = RenalDoseAdjustmentParams(drug_name="vancomycin", renal_value=49.0, renal_metric=RenalMetric.CRCL)
    result = calculate_renal_dose_adjustment(params)
    assert result.value["adjustment_type"] != "no_adjustment"


def test_boundary_just_above():
    """Value just above a tier boundary should be in the higher tier."""
    params = RenalDoseAdjustmentParams(drug_name="vancomycin", renal_value=50.0, renal_metric=RenalMetric.CRCL)
    result = calculate_renal_dose_adjustment(params)
    assert result.value["adjustment_type"] == "no_adjustment"


# --- Metric mismatch ---


def test_metric_mismatch_egfr_for_crcl_drug():
    """Providing eGFR for a drug whose label uses CrCl should flag mismatch."""
    params = RenalDoseAdjustmentParams(drug_name="vancomycin", renal_value=80.0, renal_metric=RenalMetric.EGFR)
    result = calculate_renal_dose_adjustment(params)
    assert result.value["metric_match"] is False
    assert result.value["metric_mismatch_warning"] is not None
    assert "CrCl" in result.value["metric_mismatch_warning"]


def test_metric_match_egfr_for_egfr_drug():
    """Providing eGFR for a drug whose label uses eGFR should match."""
    params = RenalDoseAdjustmentParams(drug_name="metformin", renal_value=60.0, renal_metric=RenalMetric.EGFR)
    result = calculate_renal_dose_adjustment(params)
    assert result.value["metric_match"] is True
    assert result.value["metric_mismatch_warning"] is None


# --- Drug not found ---


def test_drug_not_found():
    params = RenalDoseAdjustmentParams(drug_name="nonexistent_drug", renal_value=80.0, renal_metric=RenalMetric.CRCL)
    result = calculate_renal_dose_adjustment(params)
    assert result.value["adjustment_type"] == "drug_not_found"
    assert "available_drugs" in result.value


# --- Case insensitivity ---


@pytest.mark.parametrize("name", ["Vancomycin", "VANCOMYCIN", "vancomycin", " vancomycin "])
def test_case_insensitive_lookup(name):
    params = RenalDoseAdjustmentParams(drug_name=name, renal_value=80.0, renal_metric=RenalMetric.CRCL)
    result = calculate_renal_dose_adjustment(params)
    assert result.value["drug_name"] == "vancomycin"


# --- DOI present for every drug ---


@pytest.mark.parametrize("drug_name", list(_DRUG_DB.keys()))
def test_doi_present(drug_name):
    params = RenalDoseAdjustmentParams(drug_name=drug_name, renal_value=50.0, renal_metric=RenalMetric.CRCL)
    result = calculate_renal_dose_adjustment(params)
    assert result.evidence.source_doi != ""
    assert result.evidence.source_doi != "N/A"


# --- JSON schema validation ---

VALID_ADJUSTMENT_TYPES = {"no_adjustment", "dose_reduction", "interval_extension", "contraindicated", "use_with_caution"}
REQUIRED_DRUG_FIELDS = {"drug_name", "brand_names", "drug_class", "route", "label_renal_metric", "normal_dose", "requires_tdm", "hepatic_interaction_flag", "source_doi", "source_description", "evidence_level", "tiers"}
REQUIRED_TIER_FIELDS = {"min", "max", "dose", "adjustment_type"}


def test_json_schema_all_drugs_have_required_fields():
    for drug_key, drug in _DRUG_DB.items():
        missing = REQUIRED_DRUG_FIELDS - set(drug.keys())
        assert not missing, f"{drug_key} missing fields: {missing}"


def test_json_schema_all_tiers_have_required_fields():
    for drug_key, drug in _DRUG_DB.items():
        assert len(drug["tiers"]) >= 1, f"{drug_key} has no tiers"
        for i, tier in enumerate(drug["tiers"]):
            missing = REQUIRED_TIER_FIELDS - set(tier.keys())
            assert not missing, f"{drug_key} tier {i} missing fields: {missing}"


def test_json_schema_adjustment_types_valid():
    for drug_key, drug in _DRUG_DB.items():
        for i, tier in enumerate(drug["tiers"]):
            assert tier["adjustment_type"] in VALID_ADJUSTMENT_TYPES, \
                f"{drug_key} tier {i} has invalid adjustment_type: {tier['adjustment_type']}"


def test_json_schema_tiers_cover_zero_to_infinity():
    for drug_key, drug in _DRUG_DB.items():
        tiers = drug["tiers"]
        mins = [t["min"] for t in tiers]
        assert 0 in mins, f"{drug_key} tiers don't start at 0"
        has_infinity = any(t["max"] is None for t in tiers)
        assert has_infinity, f"{drug_key} tiers don't cover infinity"


def test_json_schema_no_overlapping_tiers():
    for drug_key, drug in _DRUG_DB.items():
        tiers = sorted(drug["tiers"], key=lambda t: t["min"])
        for i in range(len(tiers) - 1):
            current_max = tiers[i]["max"] if tiers[i]["max"] is not None else float("inf")
            next_min = tiers[i + 1]["min"]
            assert current_max < next_min or current_max == next_min - 1 or (current_max + 1 == next_min), \
                f"{drug_key}: tier {i} (max={current_max}) overlaps with tier {i+1} (min={next_min})"


def test_json_schema_doi_nonempty():
    for drug_key, drug in _DRUG_DB.items():
        assert drug["source_doi"].strip() != "", f"{drug_key} has empty DOI"


# --- Per-drug parametrized tests for all drugs ---


@pytest.mark.parametrize("drug_name", list(_DRUG_DB.keys()))
def test_every_drug_normal_renal(drug_name):
    """Every drug should return no_adjustment at normal renal function."""
    drug = _DRUG_DB[drug_name]
    metric = RenalMetric.EGFR if drug["label_renal_metric"] == "egfr" else RenalMetric.CRCL
    params = RenalDoseAdjustmentParams(drug_name=drug_name, renal_value=90.0, renal_metric=metric)
    result = calculate_renal_dose_adjustment(params)
    assert result.value["adjustment_type"] == "no_adjustment"
    assert result.value["adjusted_dose"] == drug["normal_dose"]


@pytest.mark.parametrize("drug_name", list(_DRUG_DB.keys()))
def test_every_drug_low_renal(drug_name):
    """Every drug should return a non-normal result at very low renal function."""
    drug = _DRUG_DB[drug_name]
    metric = RenalMetric.EGFR if drug["label_renal_metric"] == "egfr" else RenalMetric.CRCL
    params = RenalDoseAdjustmentParams(drug_name=drug_name, renal_value=5.0, renal_metric=metric)
    result = calculate_renal_dose_adjustment(params)
    assert result.value["adjustment_type"] != "no_adjustment"
