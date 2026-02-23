import pytest
from open_medicine.mcp.calculators.caprini import calculate_caprini, CapriniParams


def test_minimum_score():
    result = calculate_caprini(CapriniParams())
    assert result.value == 0
    assert "Lowest" in result.interpretation


def test_maximum_score():
    params = CapriniParams(
        age_41_60=True, minor_surgery=True, bmi_over_25=True, swollen_legs=True,
        varicose_veins=True, pregnancy_or_postpartum=True,
        history_unexplained_stillborn_or_recurrent_abortion=True,
        ocp_or_hrt=True, sepsis=True, serious_lung_disease=True,
        abnormal_pulmonary_function=True, acute_mi=True, chf=True,
        inflammatory_bowel_disease=True, medical_patient_at_bed_rest=True,
        age_61_74=True, arthroscopic_surgery=True, major_open_surgery=True,
        laparoscopic_surgery=True, malignancy=True, confined_to_bed=True,
        immobilizing_plaster_cast=True, central_venous_access=True,
        age_75_or_older=True, history_dvt_pe=True, family_history_thrombosis=True,
        factor_v_leiden=True, prothrombin_20210a=True, lupus_anticoagulant=True,
        anticardiolipin_antibodies=True, elevated_homocysteine=True, hit=True,
        other_thrombophilia=True,
        stroke=True, multiple_trauma=True, acute_spinal_cord_injury=True,
        major_lower_extremity_arthroplasty=True,
    )
    result = calculate_caprini(params)
    # 15*1 + 8*2 + 10*3 + 4*5 = 15+16+30+20 = 81
    assert result.value == 81
    assert "High" in result.interpretation


def test_low_risk():
    result = calculate_caprini(CapriniParams(age_41_60=True))
    assert result.value == 1
    assert "Low" in result.interpretation


def test_moderate_risk():
    result = calculate_caprini(CapriniParams(age_41_60=True, minor_surgery=True, bmi_over_25=True))
    assert result.value == 3
    assert "Moderate" in result.interpretation


def test_high_risk_boundary():
    result = calculate_caprini(CapriniParams(stroke=True))
    assert result.value == 5
    assert "High" in result.interpretation


def test_two_point_items():
    result = calculate_caprini(CapriniParams(malignancy=True))
    assert result.value == 2


def test_three_point_items():
    result = calculate_caprini(CapriniParams(history_dvt_pe=True))
    assert result.value == 3


def test_evidence_doi():
    result = calculate_caprini(CapriniParams())
    assert result.evidence.source_doi == "10.1016/j.disamonth.2005.02.002"


def test_fhir():
    result = calculate_caprini(CapriniParams())
    assert result.fhir_system == "http://loinc.org"
