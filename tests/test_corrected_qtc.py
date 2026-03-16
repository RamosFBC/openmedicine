import math
import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.corrected_qtc import calculate_corrected_qtc, CorrectedQTcParams, QTcMethod


# --- Bazett tests ---

def test_bazett_with_hr_normal():
    """QT=400ms, HR=60 → RR=1.0s → QTc=400/√1=400ms. Normal."""
    result = calculate_corrected_qtc(CorrectedQTcParams(qt_ms=400, heart_rate=60, method=QTcMethod.BAZETT, is_female=False))
    assert result.value == 400.0
    assert "Normal" in result.interpretation

def test_bazett_with_rr():
    """QT=400ms, RR=1.0s → QTc=400ms."""
    result = calculate_corrected_qtc(CorrectedQTcParams(qt_ms=400, rr_seconds=1.0, method=QTcMethod.BAZETT))
    assert result.value == 400.0

def test_bazett_prolonged_male():
    """QT=450ms, HR=75 → RR=0.8 → QTc=450/√0.8≈503.1ms. Markedly prolonged."""
    result = calculate_corrected_qtc(CorrectedQTcParams(qt_ms=450, heart_rate=75, method=QTcMethod.BAZETT, is_female=False))
    expected = round(450 / math.sqrt(0.8), 1)
    assert result.value == expected
    assert "Markedly prolonged" in result.interpretation

def test_bazett_prolonged_female():
    """QT=420ms, HR=80 → RR=0.75 → QTc≈485.0ms. Prolonged for female (>460)."""
    result = calculate_corrected_qtc(CorrectedQTcParams(qt_ms=420, heart_rate=80, method=QTcMethod.BAZETT, is_female=True))
    expected = round(420 / math.sqrt(0.75), 1)
    assert result.value == expected
    assert "Prolonged" in result.interpretation

def test_bazett_normal_female():
    """QT=360ms, HR=75 → RR=0.8 → QTc≈402.5ms. Normal for female."""
    result = calculate_corrected_qtc(CorrectedQTcParams(qt_ms=360, heart_rate=75, method=QTcMethod.BAZETT, is_female=True))
    assert result.value <= 460
    assert "Normal" in result.interpretation


# --- Fridericia tests ---

def test_fridericia_with_hr():
    """QT=400ms, HR=60 → RR=1.0 → QTc=400/(1.0)^(1/3)=400ms."""
    result = calculate_corrected_qtc(CorrectedQTcParams(qt_ms=400, heart_rate=60, method=QTcMethod.FRIDERICIA))
    assert result.value == 400.0

def test_fridericia_high_hr():
    """QT=350ms, HR=100 → RR=0.6 → QTc=350/0.6^(1/3)."""
    result = calculate_corrected_qtc(CorrectedQTcParams(qt_ms=350, heart_rate=100, method=QTcMethod.FRIDERICIA, is_female=False))
    expected = round(350 / (0.6 ** (1/3)), 1)
    assert result.value == expected

def test_fridericia_different_from_bazett():
    """At non-unity RR, Bazett and Fridericia give different results."""
    params_b = CorrectedQTcParams(qt_ms=400, heart_rate=80, method=QTcMethod.BAZETT)
    params_f = CorrectedQTcParams(qt_ms=400, heart_rate=80, method=QTcMethod.FRIDERICIA)
    rb = calculate_corrected_qtc(params_b)
    rf = calculate_corrected_qtc(params_f)
    assert rb.value != rf.value


# --- Edge cases ---

def test_no_hr_or_rr():
    result = calculate_corrected_qtc(CorrectedQTcParams(qt_ms=400))
    assert result.value is None
    assert "must be provided" in result.interpretation

def test_zero_hr():
    result = calculate_corrected_qtc(CorrectedQTcParams(qt_ms=400, heart_rate=0))
    assert result.value is None

def test_negative_rr():
    result = calculate_corrected_qtc(CorrectedQTcParams(qt_ms=400, rr_seconds=-1))
    assert result.value is None

def test_rr_takes_precedence_over_hr():
    """When both provided, rr_seconds is used."""
    result = calculate_corrected_qtc(CorrectedQTcParams(qt_ms=400, heart_rate=999, rr_seconds=1.0))
    assert result.value == 400.0


# --- Evidence ---

def test_evidence_bazett():
    result = calculate_corrected_qtc(CorrectedQTcParams(qt_ms=400, heart_rate=60, method=QTcMethod.BAZETT))
    assert result.evidence.source_doi == "10.1136/hrt.7.4.353"

def test_evidence_fridericia():
    result = calculate_corrected_qtc(CorrectedQTcParams(qt_ms=400, heart_rate=60, method=QTcMethod.FRIDERICIA))
    assert "Fridericia" in result.evidence.description

def test_fhir_code():
    result = calculate_corrected_qtc(CorrectedQTcParams(qt_ms=400, heart_rate=60))
    assert result.fhir_code == "77867-0"
    assert result.fhir_system == "http://loinc.org"


# --- Fuzz tests ---

@pytest.mark.slow
@given(
    qt_ms=st.floats(min_value=100, max_value=700),
    heart_rate=st.floats(min_value=20, max_value=250),
)
@settings(max_examples=500)
def test_qtc_fuzz_bazett(qt_ms, heart_rate):
    result = calculate_corrected_qtc(CorrectedQTcParams(qt_ms=qt_ms, heart_rate=heart_rate, method=QTcMethod.BAZETT))
    assert result.value is not None
    assert result.value > 0
    assert result.interpretation

@pytest.mark.slow
@given(
    qt_ms=st.floats(min_value=100, max_value=700),
    heart_rate=st.floats(min_value=20, max_value=250),
)
@settings(max_examples=500)
def test_qtc_fuzz_fridericia(qt_ms, heart_rate):
    result = calculate_corrected_qtc(CorrectedQTcParams(qt_ms=qt_ms, heart_rate=heart_rate, method=QTcMethod.FRIDERICIA))
    assert result.value is not None
    assert result.value > 0
    assert result.interpretation
