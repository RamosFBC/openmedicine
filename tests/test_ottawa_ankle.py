import pytest
from open_medicine.mcp.calculators.ottawa_ankle import calculate_ottawa_ankle, OttawaAnkleParams


# ============================================================
# Tier 1: Deterministic Unit Tests
# ============================================================


def test_ottawa_ankle_no_imaging_all_criteria_absent():
    """All criteria absent -> no imaging needed (value=0)."""
    params = OttawaAnkleParams()
    result = calculate_ottawa_ankle(params)
    assert result.value == 0
    assert "Ankle X-ray NOT indicated" in result.interpretation
    assert "Foot X-ray NOT indicated" in result.interpretation


def test_ottawa_ankle_no_imaging_malleolar_pain_only_no_tenderness():
    """Malleolar zone pain present but no tenderness and can bear weight -> no ankle X-ray."""
    params = OttawaAnkleParams(malleolar_zone_pain=True)
    result = calculate_ottawa_ankle(params)
    assert result.value == 0
    assert "Ankle X-ray NOT indicated" in result.interpretation
    assert "malleolar zone pain present but no" in result.interpretation


def test_ottawa_ankle_no_imaging_midfoot_pain_only_no_tenderness():
    """Midfoot zone pain present but no tenderness and can bear weight -> no foot X-ray."""
    params = OttawaAnkleParams(midfoot_zone_pain=True)
    result = calculate_ottawa_ankle(params)
    assert result.value == 0
    assert "Foot X-ray NOT indicated" in result.interpretation
    assert "midfoot zone pain present but no" in result.interpretation


def test_ottawa_ankle_ankle_xray_lateral_tenderness():
    """Malleolar pain + lateral malleolar tenderness -> ankle X-ray indicated (value=1)."""
    params = OttawaAnkleParams(
        malleolar_zone_pain=True,
        tenderness_posterior_edge_or_tip_lateral_malleolus=True,
    )
    result = calculate_ottawa_ankle(params)
    assert result.value == 1
    assert "Ankle X-ray INDICATED" in result.interpretation
    assert "lateral malleolar tenderness" in result.interpretation
    assert "Foot X-ray NOT indicated" in result.interpretation


def test_ottawa_ankle_ankle_xray_medial_tenderness():
    """Malleolar pain + medial malleolar tenderness -> ankle X-ray indicated (value=1)."""
    params = OttawaAnkleParams(
        malleolar_zone_pain=True,
        tenderness_posterior_edge_or_tip_medial_malleolus=True,
    )
    result = calculate_ottawa_ankle(params)
    assert result.value == 1
    assert "Ankle X-ray INDICATED" in result.interpretation
    assert "medial malleolar tenderness" in result.interpretation


def test_ottawa_ankle_ankle_xray_inability_bear_weight():
    """Malleolar pain + inability to bear weight -> ankle X-ray indicated (value=1)."""
    params = OttawaAnkleParams(
        malleolar_zone_pain=True,
        inability_to_bear_weight=True,
    )
    result = calculate_ottawa_ankle(params)
    assert result.value == 1
    assert "Ankle X-ray INDICATED" in result.interpretation
    assert "inability to bear weight" in result.interpretation


def test_ottawa_ankle_foot_xray_fifth_metatarsal():
    """Midfoot pain + 5th metatarsal tenderness -> foot X-ray indicated (value=2)."""
    params = OttawaAnkleParams(
        midfoot_zone_pain=True,
        tenderness_base_fifth_metatarsal=True,
    )
    result = calculate_ottawa_ankle(params)
    assert result.value == 2
    assert "Foot X-ray INDICATED" in result.interpretation
    assert "base of 5th metatarsal tenderness" in result.interpretation
    assert "Ankle X-ray NOT indicated" in result.interpretation


def test_ottawa_ankle_foot_xray_navicular():
    """Midfoot pain + navicular tenderness -> foot X-ray indicated (value=2)."""
    params = OttawaAnkleParams(
        midfoot_zone_pain=True,
        tenderness_navicular=True,
    )
    result = calculate_ottawa_ankle(params)
    assert result.value == 2
    assert "Foot X-ray INDICATED" in result.interpretation
    assert "navicular tenderness" in result.interpretation


def test_ottawa_ankle_foot_xray_inability_bear_weight():
    """Midfoot pain + inability to bear weight -> foot X-ray indicated (value=2)."""
    params = OttawaAnkleParams(
        midfoot_zone_pain=True,
        inability_to_bear_weight=True,
    )
    result = calculate_ottawa_ankle(params)
    assert result.value == 2
    assert "Foot X-ray INDICATED" in result.interpretation
    assert "inability to bear weight" in result.interpretation


def test_ottawa_ankle_both_series_needed():
    """Both malleolar and midfoot criteria met -> both X-rays indicated (value=3)."""
    params = OttawaAnkleParams(
        malleolar_zone_pain=True,
        tenderness_posterior_edge_or_tip_lateral_malleolus=True,
        midfoot_zone_pain=True,
        tenderness_navicular=True,
    )
    result = calculate_ottawa_ankle(params)
    assert result.value == 3
    assert "Ankle X-ray INDICATED" in result.interpretation
    assert "Foot X-ray INDICATED" in result.interpretation


def test_ottawa_ankle_both_series_via_inability_to_bear_weight():
    """Both zone pain + inability to bear weight triggers both X-ray series (value=3)."""
    params = OttawaAnkleParams(
        malleolar_zone_pain=True,
        midfoot_zone_pain=True,
        inability_to_bear_weight=True,
    )
    result = calculate_ottawa_ankle(params)
    assert result.value == 3
    assert "Ankle X-ray INDICATED" in result.interpretation
    assert "Foot X-ray INDICATED" in result.interpretation


def test_ottawa_ankle_all_positive():
    """All criteria positive -> both X-ray series indicated (value=3)."""
    params = OttawaAnkleParams(
        malleolar_zone_pain=True,
        tenderness_posterior_edge_or_tip_lateral_malleolus=True,
        tenderness_posterior_edge_or_tip_medial_malleolus=True,
        midfoot_zone_pain=True,
        tenderness_base_fifth_metatarsal=True,
        tenderness_navicular=True,
        inability_to_bear_weight=True,
    )
    result = calculate_ottawa_ankle(params)
    assert result.value == 3
    assert "Ankle X-ray INDICATED" in result.interpretation
    assert "Foot X-ray INDICATED" in result.interpretation


def test_ottawa_ankle_tenderness_without_zone_pain_no_imaging():
    """Tenderness criteria present but NO zone pain -> no imaging (rule requires zone pain first)."""
    params = OttawaAnkleParams(
        malleolar_zone_pain=False,
        tenderness_posterior_edge_or_tip_lateral_malleolus=True,
        tenderness_posterior_edge_or_tip_medial_malleolus=True,
        midfoot_zone_pain=False,
        tenderness_base_fifth_metatarsal=True,
        tenderness_navicular=True,
    )
    result = calculate_ottawa_ankle(params)
    assert result.value == 0
    assert "Ankle X-ray NOT indicated" in result.interpretation
    assert "Foot X-ray NOT indicated" in result.interpretation


def test_ottawa_ankle_inability_bear_weight_without_zone_pain():
    """Inability to bear weight present but no zone pain -> no imaging."""
    params = OttawaAnkleParams(
        inability_to_bear_weight=True,
    )
    result = calculate_ottawa_ankle(params)
    assert result.value == 0
    assert "Ankle X-ray NOT indicated" in result.interpretation
    assert "Foot X-ray NOT indicated" in result.interpretation


def test_ottawa_ankle_multiple_ankle_reasons():
    """Multiple positive ankle criteria should all appear in the interpretation."""
    params = OttawaAnkleParams(
        malleolar_zone_pain=True,
        tenderness_posterior_edge_or_tip_lateral_malleolus=True,
        tenderness_posterior_edge_or_tip_medial_malleolus=True,
        inability_to_bear_weight=True,
    )
    result = calculate_ottawa_ankle(params)
    assert result.value == 1
    assert "lateral malleolar tenderness" in result.interpretation
    assert "medial malleolar tenderness" in result.interpretation
    assert "inability to bear weight" in result.interpretation


def test_ottawa_ankle_multiple_foot_reasons():
    """Multiple positive foot criteria should all appear in the interpretation."""
    params = OttawaAnkleParams(
        midfoot_zone_pain=True,
        tenderness_base_fifth_metatarsal=True,
        tenderness_navicular=True,
        inability_to_bear_weight=True,
    )
    result = calculate_ottawa_ankle(params)
    assert result.value == 2
    assert "base of 5th metatarsal tenderness" in result.interpretation
    assert "navicular tenderness" in result.interpretation
    assert "inability to bear weight" in result.interpretation


# ============================================================
# Evidence and FHIR verification
# ============================================================


def test_ottawa_ankle_evidence_doi():
    """Verify the DOI matches the 1992 Stiell original derivation study."""
    params = OttawaAnkleParams()
    result = calculate_ottawa_ankle(params)
    assert result.evidence.source_doi == "10.1016/s0196-0644(05)82656-3"


def test_ottawa_ankle_evidence_level():
    """Verify evidence level is Derivation Study."""
    params = OttawaAnkleParams()
    result = calculate_ottawa_ankle(params)
    assert result.evidence.level == "Derivation Study"


def test_ottawa_ankle_fhir_code():
    """Verify FHIR code represents a clinical decision assessment, not an imaging procedure."""
    params = OttawaAnkleParams()
    result = calculate_ottawa_ankle(params)
    assert result.fhir_code == "71482-4"
    assert result.fhir_system == "http://loinc.org"


def test_ottawa_ankle_interpretation_never_empty():
    """Interpretation string is never empty for any combination of inputs."""
    # No criteria
    result1 = calculate_ottawa_ankle(OttawaAnkleParams())
    assert len(result1.interpretation) > 0
    assert result1.interpretation.startswith("Ottawa Ankle Rules:")

    # All criteria
    result2 = calculate_ottawa_ankle(OttawaAnkleParams(
        malleolar_zone_pain=True,
        tenderness_posterior_edge_or_tip_lateral_malleolus=True,
        midfoot_zone_pain=True,
        tenderness_navicular=True,
        inability_to_bear_weight=True,
    ))
    assert len(result2.interpretation) > 0
    assert result2.interpretation.startswith("Ottawa Ankle Rules:")


# ============================================================
# Value encoding tests
# ============================================================


def test_ottawa_ankle_value_encoding():
    """Verify value encoding: 0=none, 1=ankle, 2=foot, 3=both."""
    # 0 = no imaging
    assert calculate_ottawa_ankle(OttawaAnkleParams()).value == 0

    # 1 = ankle only
    assert calculate_ottawa_ankle(OttawaAnkleParams(
        malleolar_zone_pain=True,
        tenderness_posterior_edge_or_tip_lateral_malleolus=True,
    )).value == 1

    # 2 = foot only
    assert calculate_ottawa_ankle(OttawaAnkleParams(
        midfoot_zone_pain=True,
        tenderness_base_fifth_metatarsal=True,
    )).value == 2

    # 3 = both
    assert calculate_ottawa_ankle(OttawaAnkleParams(
        malleolar_zone_pain=True,
        tenderness_posterior_edge_or_tip_lateral_malleolus=True,
        midfoot_zone_pain=True,
        tenderness_base_fifth_metatarsal=True,
    )).value == 3
