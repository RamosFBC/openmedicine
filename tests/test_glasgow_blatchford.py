import pytest
from open_medicine.mcp.calculators.glasgow_blatchford import calculate_glasgow_blatchford, GlasgowBlatchfordParams


def _make(**kwargs):
    defaults = dict(bun=10.0, hemoglobin=15.0, systolic_bp=120, pulse=70, is_male=True,
                    melena=False, syncope=False, hepatic_disease=False, cardiac_failure=False)
    defaults.update(kwargs)
    return GlasgowBlatchfordParams(**defaults)


def test_minimum_score():
    result = calculate_glasgow_blatchford(_make())
    assert result.value == 0
    assert "Very low risk" in result.interpretation


def test_maximum_score_male():
    params = GlasgowBlatchfordParams(
        bun=80.0, hemoglobin=8.0, systolic_bp=80, pulse=110, is_male=True,
        melena=True, syncope=True, hepatic_disease=True, cardiac_failure=True
    )
    result = calculate_glasgow_blatchford(params)
    # BUN>=70→6, Hb<10 male→6, SBP<90→3, pulse>=100→1, melena→1, syncope→1, hepatic→1, cardiac→1 = 20
    assert result.value == 20


def test_maximum_score_female():
    params = GlasgowBlatchfordParams(
        bun=80.0, hemoglobin=8.0, systolic_bp=80, pulse=110, is_male=False,
        melena=True, syncope=True, hepatic_disease=True, cardiac_failure=True
    )
    result = calculate_glasgow_blatchford(params)
    # BUN>=70→6, Hb<10 female→6, SBP<90→3, pulse>=100→1, + 4 binary = 20
    assert result.value == 20


def test_bun_thresholds():
    assert calculate_glasgow_blatchford(_make(bun=18.1)).value == 0
    assert calculate_glasgow_blatchford(_make(bun=18.2)).value == 2
    assert calculate_glasgow_blatchford(_make(bun=22.4)).value == 3
    assert calculate_glasgow_blatchford(_make(bun=28.0)).value == 4
    assert calculate_glasgow_blatchford(_make(bun=70.0)).value == 6


def test_hemoglobin_male():
    assert calculate_glasgow_blatchford(_make(hemoglobin=13.0)).value == 0
    assert calculate_glasgow_blatchford(_make(hemoglobin=12.9)).value == 1
    assert calculate_glasgow_blatchford(_make(hemoglobin=12.0)).value == 1
    assert calculate_glasgow_blatchford(_make(hemoglobin=11.9)).value == 3
    assert calculate_glasgow_blatchford(_make(hemoglobin=9.9)).value == 6


def test_hemoglobin_female():
    assert calculate_glasgow_blatchford(_make(hemoglobin=12.0, is_male=False)).value == 0
    assert calculate_glasgow_blatchford(_make(hemoglobin=11.9, is_male=False)).value == 1
    assert calculate_glasgow_blatchford(_make(hemoglobin=9.9, is_male=False)).value == 6


def test_systolic_bp_thresholds():
    assert calculate_glasgow_blatchford(_make(systolic_bp=110)).value == 0
    assert calculate_glasgow_blatchford(_make(systolic_bp=109)).value == 1
    assert calculate_glasgow_blatchford(_make(systolic_bp=99)).value == 2
    assert calculate_glasgow_blatchford(_make(systolic_bp=89)).value == 3


def test_low_risk_boundary():
    result = calculate_glasgow_blatchford(_make(pulse=100))  # score=1
    assert result.value == 1
    assert "Low risk" in result.interpretation


def test_moderate_risk():
    result = calculate_glasgow_blatchford(_make(bun=18.2))  # score=2
    assert result.value == 2
    assert "Moderate risk" in result.interpretation


def test_high_risk():
    result = calculate_glasgow_blatchford(_make(bun=28.0, melena=True, syncope=True, hepatic_disease=True))
    assert result.value >= 7
    assert "High risk" in result.interpretation


def test_evidence_doi():
    result = calculate_glasgow_blatchford(_make())
    assert result.evidence.source_doi == "10.1016/S0140-6736(00)02816-6"


def test_fhir_code():
    result = calculate_glasgow_blatchford(_make())
    assert result.fhir_system == "http://loinc.org"
