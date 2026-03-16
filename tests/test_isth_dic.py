import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.isth_dic import calculate_isth_dic, ISTHDICParams


# ---------------------------------------------------------------------------
# Tier 1: Deterministic Unit Tests
# ---------------------------------------------------------------------------


class TestMinimumScore:
    """All parameters normal -- score should be 0."""

    def test_all_normal(self):
        params = ISTHDICParams(
            platelet_count=200,
            fibrin_marker_increase=0,
            pt_prolongation_seconds=0.0,
            fibrinogen_level=3.0,
        )
        result = calculate_isth_dic(params)
        assert result.value == 0
        assert "Not compatible with overt DIC" in result.interpretation

    def test_borderline_normal(self):
        """All values right at the normal boundaries (no points)."""
        params = ISTHDICParams(
            platelet_count=100,  # >= 100 -> 0 pts
            fibrin_marker_increase=0,  # no increase -> 0 pts
            pt_prolongation_seconds=2.9,  # < 3 -> 0 pts
            fibrinogen_level=1.0,  # >= 1 -> 0 pts
        )
        result = calculate_isth_dic(params)
        assert result.value == 0


class TestMaximumScore:
    """All parameters at their worst -- score should be 8."""

    def test_all_maximal(self):
        params = ISTHDICParams(
            platelet_count=10,  # < 50 -> 2 pts
            fibrin_marker_increase=2,  # strong increase -> 3 pts
            pt_prolongation_seconds=10.0,  # >= 6 -> 2 pts
            fibrinogen_level=0.5,  # < 1 -> 1 pt
        )
        result = calculate_isth_dic(params)
        assert result.value == 8
        assert "Compatible with overt DIC" in result.interpretation


class TestPlateletScoring:
    """Platelet count thresholds: >=100 = 0, 50-99 = 1, <50 = 2."""

    def test_platelets_high_normal(self):
        params = ISTHDICParams(
            platelet_count=350,
            fibrin_marker_increase=0,
            pt_prolongation_seconds=0.0,
            fibrinogen_level=3.0,
        )
        result = calculate_isth_dic(params)
        assert result.value == 0

    def test_platelets_at_100(self):
        """Exactly 100 is the lower bound of the normal category = 0 pts."""
        params = ISTHDICParams(
            platelet_count=100,
            fibrin_marker_increase=0,
            pt_prolongation_seconds=0.0,
            fibrinogen_level=3.0,
        )
        result = calculate_isth_dic(params)
        assert result.value == 0

    def test_platelets_99(self):
        """99 is in the 50-99 range = 1 pt."""
        params = ISTHDICParams(
            platelet_count=99,
            fibrin_marker_increase=0,
            pt_prolongation_seconds=0.0,
            fibrinogen_level=3.0,
        )
        result = calculate_isth_dic(params)
        assert result.value == 1

    def test_platelets_at_50(self):
        """Exactly 50 is in the 50-99 range = 1 pt."""
        params = ISTHDICParams(
            platelet_count=50,
            fibrin_marker_increase=0,
            pt_prolongation_seconds=0.0,
            fibrinogen_level=3.0,
        )
        result = calculate_isth_dic(params)
        assert result.value == 1

    def test_platelets_49(self):
        """49 is < 50 = 2 pts."""
        params = ISTHDICParams(
            platelet_count=49,
            fibrin_marker_increase=0,
            pt_prolongation_seconds=0.0,
            fibrinogen_level=3.0,
        )
        result = calculate_isth_dic(params)
        assert result.value == 2

    def test_platelets_zero(self):
        """Zero platelets = 2 pts."""
        params = ISTHDICParams(
            platelet_count=0,
            fibrin_marker_increase=0,
            pt_prolongation_seconds=0.0,
            fibrinogen_level=3.0,
        )
        result = calculate_isth_dic(params)
        assert result.value == 2


class TestFibrinMarkerScoring:
    """Fibrin marker: no increase = 0, moderate = 2, strong = 3."""

    def test_no_increase(self):
        params = ISTHDICParams(
            platelet_count=200,
            fibrin_marker_increase=0,
            pt_prolongation_seconds=0.0,
            fibrinogen_level=3.0,
        )
        result = calculate_isth_dic(params)
        assert result.value == 0

    def test_moderate_increase(self):
        params = ISTHDICParams(
            platelet_count=200,
            fibrin_marker_increase=1,
            pt_prolongation_seconds=0.0,
            fibrinogen_level=3.0,
        )
        result = calculate_isth_dic(params)
        assert result.value == 2

    def test_strong_increase(self):
        params = ISTHDICParams(
            platelet_count=200,
            fibrin_marker_increase=2,
            pt_prolongation_seconds=0.0,
            fibrinogen_level=3.0,
        )
        result = calculate_isth_dic(params)
        assert result.value == 3


class TestPTProlongationScoring:
    """PT prolongation: <3 s = 0, 3-<6 s = 1, >=6 s = 2."""

    def test_no_prolongation(self):
        params = ISTHDICParams(
            platelet_count=200,
            fibrin_marker_increase=0,
            pt_prolongation_seconds=0.0,
            fibrinogen_level=3.0,
        )
        result = calculate_isth_dic(params)
        assert result.value == 0

    def test_just_below_3(self):
        params = ISTHDICParams(
            platelet_count=200,
            fibrin_marker_increase=0,
            pt_prolongation_seconds=2.9,
            fibrinogen_level=3.0,
        )
        result = calculate_isth_dic(params)
        assert result.value == 0

    def test_exactly_3(self):
        """3 seconds is the lower boundary of the 1-point tier."""
        params = ISTHDICParams(
            platelet_count=200,
            fibrin_marker_increase=0,
            pt_prolongation_seconds=3.0,
            fibrinogen_level=3.0,
        )
        result = calculate_isth_dic(params)
        assert result.value == 1

    def test_5_9_seconds(self):
        """5.9 s is still in the 3-<6 range = 1 pt."""
        params = ISTHDICParams(
            platelet_count=200,
            fibrin_marker_increase=0,
            pt_prolongation_seconds=5.9,
            fibrinogen_level=3.0,
        )
        result = calculate_isth_dic(params)
        assert result.value == 1

    def test_exactly_6(self):
        """6 seconds hits the >= 6 threshold = 2 pts."""
        params = ISTHDICParams(
            platelet_count=200,
            fibrin_marker_increase=0,
            pt_prolongation_seconds=6.0,
            fibrinogen_level=3.0,
        )
        result = calculate_isth_dic(params)
        assert result.value == 2

    def test_large_prolongation(self):
        params = ISTHDICParams(
            platelet_count=200,
            fibrin_marker_increase=0,
            pt_prolongation_seconds=15.0,
            fibrinogen_level=3.0,
        )
        result = calculate_isth_dic(params)
        assert result.value == 2


class TestFibrinogenScoring:
    """Fibrinogen: >= 1 g/L = 0, < 1 g/L = 1."""

    def test_normal_fibrinogen(self):
        params = ISTHDICParams(
            platelet_count=200,
            fibrin_marker_increase=0,
            pt_prolongation_seconds=0.0,
            fibrinogen_level=3.0,
        )
        result = calculate_isth_dic(params)
        assert result.value == 0

    def test_at_1_gl(self):
        """Exactly 1 g/L is normal = 0 pts."""
        params = ISTHDICParams(
            platelet_count=200,
            fibrin_marker_increase=0,
            pt_prolongation_seconds=0.0,
            fibrinogen_level=1.0,
        )
        result = calculate_isth_dic(params)
        assert result.value == 0

    def test_below_1_gl(self):
        """0.99 g/L = 1 pt."""
        params = ISTHDICParams(
            platelet_count=200,
            fibrin_marker_increase=0,
            pt_prolongation_seconds=0.0,
            fibrinogen_level=0.99,
        )
        result = calculate_isth_dic(params)
        assert result.value == 1

    def test_very_low_fibrinogen(self):
        params = ISTHDICParams(
            platelet_count=200,
            fibrin_marker_increase=0,
            pt_prolongation_seconds=0.0,
            fibrinogen_level=0.0,
        )
        result = calculate_isth_dic(params)
        assert result.value == 1


class TestInterpretationThreshold:
    """Score >= 5 = compatible with overt DIC; < 5 = not overt."""

    def test_score_4_not_overt(self):
        """Score of 4 should not be classified as overt DIC."""
        params = ISTHDICParams(
            platelet_count=49,  # 2 pts
            fibrin_marker_increase=1,  # 2 pts
            pt_prolongation_seconds=0.0,  # 0 pts
            fibrinogen_level=3.0,  # 0 pts
        )
        result = calculate_isth_dic(params)
        assert result.value == 4
        assert "Not compatible with overt DIC" in result.interpretation

    def test_score_5_overt(self):
        """Score of 5 is the threshold for overt DIC."""
        params = ISTHDICParams(
            platelet_count=49,  # 2 pts
            fibrin_marker_increase=1,  # 2 pts
            pt_prolongation_seconds=3.0,  # 1 pt
            fibrinogen_level=3.0,  # 0 pts
        )
        result = calculate_isth_dic(params)
        assert result.value == 5
        assert "Compatible with overt DIC" in result.interpretation

    def test_score_6_overt(self):
        params = ISTHDICParams(
            platelet_count=49,  # 2 pts
            fibrin_marker_increase=1,  # 2 pts
            pt_prolongation_seconds=6.0,  # 2 pts
            fibrinogen_level=3.0,  # 0 pts
        )
        result = calculate_isth_dic(params)
        assert result.value == 6
        assert "Compatible with overt DIC" in result.interpretation

    def test_score_7_overt(self):
        params = ISTHDICParams(
            platelet_count=49,  # 2 pts
            fibrin_marker_increase=2,  # 3 pts
            pt_prolongation_seconds=6.0,  # 2 pts
            fibrinogen_level=3.0,  # 0 pts
        )
        result = calculate_isth_dic(params)
        assert result.value == 7
        assert "Compatible with overt DIC" in result.interpretation


class TestClinicalScenarios:
    """Combined scoring scenarios resembling real clinical presentations."""

    def test_sepsis_with_overt_dic(self):
        """Sepsis patient with full-blown DIC: low platelets, high D-dimer,
        prolonged PT, low fibrinogen."""
        params = ISTHDICParams(
            platelet_count=30,  # 2 pts
            fibrin_marker_increase=2,  # 3 pts (strong increase)
            pt_prolongation_seconds=7.0,  # 2 pts
            fibrinogen_level=0.8,  # 1 pt
        )
        result = calculate_isth_dic(params)
        assert result.value == 8  # maximum
        assert "Compatible with overt DIC" in result.interpretation

    def test_mild_coagulopathy_not_dic(self):
        """Mild thrombocytopenia with mildly elevated D-dimer -- not DIC."""
        params = ISTHDICParams(
            platelet_count=80,  # 1 pt
            fibrin_marker_increase=1,  # 2 pts (moderate increase)
            pt_prolongation_seconds=1.0,  # 0 pts
            fibrinogen_level=2.5,  # 0 pts
        )
        result = calculate_isth_dic(params)
        assert result.value == 3
        assert "Not compatible with overt DIC" in result.interpretation

    def test_borderline_dic(self):
        """Borderline case just at the overt threshold."""
        params = ISTHDICParams(
            platelet_count=60,  # 1 pt
            fibrin_marker_increase=1,  # 2 pts
            pt_prolongation_seconds=6.0,  # 2 pts
            fibrinogen_level=1.0,  # 0 pts
        )
        result = calculate_isth_dic(params)
        assert result.value == 5
        assert "Compatible with overt DIC" in result.interpretation

    def test_isolated_strong_fibrin_marker(self):
        """Strong D-dimer alone with otherwise normal labs."""
        params = ISTHDICParams(
            platelet_count=250,  # 0 pts
            fibrin_marker_increase=2,  # 3 pts
            pt_prolongation_seconds=0.0,  # 0 pts
            fibrinogen_level=4.0,  # 0 pts
        )
        result = calculate_isth_dic(params)
        assert result.value == 3
        assert "Not compatible with overt DIC" in result.interpretation


class TestEvidenceAndFHIR:
    """Verify DOI, evidence level, and FHIR code."""

    def test_evidence_doi(self):
        params = ISTHDICParams(
            platelet_count=200,
            fibrin_marker_increase=0,
            pt_prolongation_seconds=0.0,
            fibrinogen_level=3.0,
        )
        result = calculate_isth_dic(params)
        assert result.evidence.source_doi == "10.1055/s-0037-1616068"

    def test_evidence_level(self):
        params = ISTHDICParams(
            platelet_count=200,
            fibrin_marker_increase=0,
            pt_prolongation_seconds=0.0,
            fibrinogen_level=3.0,
        )
        result = calculate_isth_dic(params)
        assert result.evidence.level == "Guideline"

    def test_fhir_code(self):
        params = ISTHDICParams(
            platelet_count=200,
            fibrin_marker_increase=0,
            pt_prolongation_seconds=0.0,
            fibrinogen_level=3.0,
        )
        result = calculate_isth_dic(params)
        assert result.fhir_code == "98125-8"
        assert result.fhir_system == "http://loinc.org"
        assert result.fhir_display == "Intravascular coagulation and fibrinolysis panel"

    def test_interpretation_includes_score(self):
        """Interpretation string must contain the numeric score."""
        params = ISTHDICParams(
            platelet_count=80,
            fibrin_marker_increase=1,
            pt_prolongation_seconds=4.0,
            fibrinogen_level=0.8,
        )
        result = calculate_isth_dic(params)
        assert str(result.value) in result.interpretation


class TestInputValidation:
    """Pydantic constraints enforce valid ranges."""

    def test_negative_platelet_rejected(self):
        with pytest.raises(Exception):
            ISTHDICParams(
                platelet_count=-1,
                fibrin_marker_increase=0,
                pt_prolongation_seconds=0.0,
                fibrinogen_level=3.0,
            )

    def test_fibrin_marker_out_of_range(self):
        with pytest.raises(Exception):
            ISTHDICParams(
                platelet_count=200,
                fibrin_marker_increase=3,
                pt_prolongation_seconds=0.0,
                fibrinogen_level=3.0,
            )

    def test_negative_pt_prolongation_rejected(self):
        with pytest.raises(Exception):
            ISTHDICParams(
                platelet_count=200,
                fibrin_marker_increase=0,
                pt_prolongation_seconds=-1.0,
                fibrinogen_level=3.0,
            )

    def test_negative_fibrinogen_rejected(self):
        with pytest.raises(Exception):
            ISTHDICParams(
                platelet_count=200,
                fibrin_marker_increase=0,
                pt_prolongation_seconds=0.0,
                fibrinogen_level=-0.5,
            )


# ---------------------------------------------------------------------------
# Tier 2: Property-Based Fuzz Tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
@given(
    platelet_count=st.integers(min_value=0, max_value=800),
    fibrin_marker_increase=st.integers(min_value=0, max_value=2),
    pt_prolongation_seconds=st.floats(min_value=0.0, max_value=60.0),
    fibrinogen_level=st.floats(min_value=0.0, max_value=15.0),
)
@settings(max_examples=500)
def test_isth_dic_fuzz_valid_range(
    platelet_count, fibrin_marker_increase, pt_prolongation_seconds, fibrinogen_level
):
    """Output is always within 0-8 for any valid input combination."""
    params = ISTHDICParams(
        platelet_count=platelet_count,
        fibrin_marker_increase=fibrin_marker_increase,
        pt_prolongation_seconds=pt_prolongation_seconds,
        fibrinogen_level=fibrinogen_level,
    )
    result = calculate_isth_dic(params)
    assert result.value is not None
    assert isinstance(result.value, int)
    assert 0 <= result.value <= 8
    assert result.interpretation
    assert result.evidence.source_doi


@pytest.mark.slow
@given(
    platelet_count=st.integers(min_value=0, max_value=800),
    fibrin_marker_increase=st.integers(min_value=0, max_value=2),
    pt_prolongation_seconds=st.floats(min_value=0.0, max_value=60.0),
    fibrinogen_level=st.floats(min_value=0.0, max_value=15.0),
)
@settings(max_examples=500)
def test_isth_dic_fuzz_interpretation_consistency(
    platelet_count, fibrin_marker_increase, pt_prolongation_seconds, fibrinogen_level
):
    """If score >= 5, interpretation says compatible; if < 5, not compatible."""
    params = ISTHDICParams(
        platelet_count=platelet_count,
        fibrin_marker_increase=fibrin_marker_increase,
        pt_prolongation_seconds=pt_prolongation_seconds,
        fibrinogen_level=fibrinogen_level,
    )
    result = calculate_isth_dic(params)
    if result.value >= 5:
        assert "Compatible with overt DIC" in result.interpretation
    else:
        assert "Not compatible with overt DIC" in result.interpretation
