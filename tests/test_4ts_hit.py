import pytest
from pydantic import ValidationError
from open_medicine.mcp.calculators.four_ts_hit import calculate_4ts_hit, FourTsHITParams


# ---------------------------------------------------------------------------
# Tier 1: Deterministic Unit Tests
# ---------------------------------------------------------------------------


class TestMinimumScore:
    """Test lowest possible score (0) with all categories at minimum."""

    def test_minimum_score_value(self):
        params = FourTsHITParams(
            thrombocytopenia=0,
            timing=0,
            thrombosis=0,
            other_causes=0,
        )
        result = calculate_4ts_hit(params)
        assert result.value == 0

    def test_minimum_score_is_low_probability(self):
        params = FourTsHITParams(
            thrombocytopenia=0,
            timing=0,
            thrombosis=0,
            other_causes=0,
        )
        result = calculate_4ts_hit(params)
        assert "Low pretest probability" in result.interpretation
        assert "HIT is unlikely" in result.interpretation


class TestMaximumScore:
    """Test highest possible score (8) with all categories at maximum."""

    def test_maximum_score_value(self):
        params = FourTsHITParams(
            thrombocytopenia=2,
            timing=2,
            thrombosis=2,
            other_causes=2,
        )
        result = calculate_4ts_hit(params)
        assert result.value == 8

    def test_maximum_score_is_high_probability(self):
        params = FourTsHITParams(
            thrombocytopenia=2,
            timing=2,
            thrombosis=2,
            other_causes=2,
        )
        result = calculate_4ts_hit(params)
        assert "High pretest probability" in result.interpretation
        assert "HIT is likely" in result.interpretation
        assert "Discontinue all heparin" in result.interpretation


class TestLowProbabilityBoundary:
    """Test upper boundary of low probability (score = 3)."""

    def test_score_3_is_low(self):
        """Score of 3 is the upper boundary of low probability."""
        params = FourTsHITParams(
            thrombocytopenia=1,
            timing=1,
            thrombosis=1,
            other_causes=0,
        )
        result = calculate_4ts_hit(params)
        assert result.value == 3
        assert "Low pretest probability" in result.interpretation

    def test_score_3_with_different_combination(self):
        """Another combination that yields score 3."""
        params = FourTsHITParams(
            thrombocytopenia=2,
            timing=1,
            thrombosis=0,
            other_causes=0,
        )
        result = calculate_4ts_hit(params)
        assert result.value == 3
        assert "Low pretest probability" in result.interpretation


class TestIntermediateProbabilityBoundary:
    """Test intermediate probability boundaries (score 4-5)."""

    def test_score_4_is_intermediate(self):
        """Score of 4 is the lower boundary of intermediate probability."""
        params = FourTsHITParams(
            thrombocytopenia=1,
            timing=1,
            thrombosis=1,
            other_causes=1,
        )
        result = calculate_4ts_hit(params)
        assert result.value == 4
        assert "Intermediate pretest probability" in result.interpretation
        assert "HIT is possible" in result.interpretation

    def test_score_5_is_intermediate(self):
        """Score of 5 is the upper boundary of intermediate probability."""
        params = FourTsHITParams(
            thrombocytopenia=2,
            timing=1,
            thrombosis=1,
            other_causes=1,
        )
        result = calculate_4ts_hit(params)
        assert result.value == 5
        assert "Intermediate pretest probability" in result.interpretation

    def test_score_4_recommends_testing(self):
        """Intermediate probability should recommend HIT antibody testing."""
        params = FourTsHITParams(
            thrombocytopenia=2,
            timing=2,
            thrombosis=0,
            other_causes=0,
        )
        result = calculate_4ts_hit(params)
        assert result.value == 4
        assert "HIT antibody testing" in result.interpretation


class TestHighProbabilityBoundary:
    """Test high probability boundaries (score 6-8)."""

    def test_score_6_is_high(self):
        """Score of 6 is the lower boundary of high probability."""
        params = FourTsHITParams(
            thrombocytopenia=2,
            timing=2,
            thrombosis=1,
            other_causes=1,
        )
        result = calculate_4ts_hit(params)
        assert result.value == 6
        assert "High pretest probability" in result.interpretation
        assert "HIT is likely" in result.interpretation

    def test_score_7_is_high(self):
        """Score of 7 is high probability."""
        params = FourTsHITParams(
            thrombocytopenia=2,
            timing=2,
            thrombosis=2,
            other_causes=1,
        )
        result = calculate_4ts_hit(params)
        assert result.value == 7
        assert "High pretest probability" in result.interpretation

    def test_high_probability_recommends_heparin_cessation(self):
        """High probability should recommend discontinuing heparin."""
        params = FourTsHITParams(
            thrombocytopenia=2,
            timing=2,
            thrombosis=1,
            other_causes=1,
        )
        result = calculate_4ts_hit(params)
        assert "Discontinue all heparin" in result.interpretation
        assert "non-heparin anticoagulation" in result.interpretation


class TestEvidenceDOI:
    """Verify the evidence DOI is the Lo et al. 2006 validation study."""

    def test_evidence_doi(self):
        params = FourTsHITParams(
            thrombocytopenia=0,
            timing=0,
            thrombosis=0,
            other_causes=0,
        )
        result = calculate_4ts_hit(params)
        assert result.evidence.source_doi == "10.1111/j.1538-7836.2006.01787.x"

    def test_evidence_level(self):
        params = FourTsHITParams(
            thrombocytopenia=0,
            timing=0,
            thrombosis=0,
            other_causes=0,
        )
        result = calculate_4ts_hit(params)
        assert result.evidence.level == "Derivation & Validation Study"

    def test_evidence_description_contains_author(self):
        params = FourTsHITParams(
            thrombocytopenia=0,
            timing=0,
            thrombosis=0,
            other_causes=0,
        )
        result = calculate_4ts_hit(params)
        assert "Lo GK" in result.evidence.description
        assert "Warkentin TE" in result.evidence.description


class TestFHIRCode:
    """Verify FHIR code is correctly set."""

    def test_fhir_code(self):
        params = FourTsHITParams(
            thrombocytopenia=1,
            timing=1,
            thrombosis=1,
            other_causes=1,
        )
        result = calculate_4ts_hit(params)
        assert result.fhir_code == "LP419518-4"
        assert result.fhir_system == "http://loinc.org"
        assert "4Ts" in result.fhir_display


class TestInputValidation:
    """Test that invalid inputs are rejected by Pydantic validation."""

    def test_thrombocytopenia_too_high(self):
        with pytest.raises(ValidationError):
            FourTsHITParams(
                thrombocytopenia=3,
                timing=0,
                thrombosis=0,
                other_causes=0,
            )

    def test_timing_too_low(self):
        with pytest.raises(ValidationError):
            FourTsHITParams(
                thrombocytopenia=0,
                timing=-1,
                thrombosis=0,
                other_causes=0,
            )

    def test_thrombosis_too_high(self):
        with pytest.raises(ValidationError):
            FourTsHITParams(
                thrombocytopenia=0,
                timing=0,
                thrombosis=5,
                other_causes=0,
            )

    def test_other_causes_too_high(self):
        with pytest.raises(ValidationError):
            FourTsHITParams(
                thrombocytopenia=0,
                timing=0,
                thrombosis=0,
                other_causes=3,
            )

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            FourTsHITParams(
                thrombocytopenia=0,
                timing=0,
                thrombosis=0,
                # other_causes missing
            )


class TestAllPossibleScores:
    """Verify every integer score from 0 to 8 falls into the correct risk stratum."""

    @pytest.mark.parametrize(
        "t, ti, th, oc, expected_score, expected_stratum",
        [
            (0, 0, 0, 0, 0, "Low"),
            (1, 0, 0, 0, 1, "Low"),
            (1, 1, 0, 0, 2, "Low"),
            (1, 1, 1, 0, 3, "Low"),
            (1, 1, 1, 1, 4, "Intermediate"),
            (2, 1, 1, 1, 5, "Intermediate"),
            (2, 2, 1, 1, 6, "High"),
            (2, 2, 2, 1, 7, "High"),
            (2, 2, 2, 2, 8, "High"),
        ],
    )
    def test_score_stratum(self, t, ti, th, oc, expected_score, expected_stratum):
        params = FourTsHITParams(
            thrombocytopenia=t,
            timing=ti,
            thrombosis=th,
            other_causes=oc,
        )
        result = calculate_4ts_hit(params)
        assert result.value == expected_score
        assert expected_stratum.lower() in result.interpretation.lower()


class TestInterpretationContent:
    """Verify interpretation strings contain the score value and clinical actions."""

    def test_low_score_mentions_no_testing(self):
        params = FourTsHITParams(
            thrombocytopenia=0,
            timing=1,
            thrombosis=0,
            other_causes=1,
        )
        result = calculate_4ts_hit(params)
        assert "not recommended" in result.interpretation.lower()

    def test_intermediate_mentions_ppv(self):
        params = FourTsHITParams(
            thrombocytopenia=2,
            timing=1,
            thrombosis=0,
            other_causes=1,
        )
        result = calculate_4ts_hit(params)
        assert "PPV" in result.interpretation

    def test_high_mentions_ppv(self):
        params = FourTsHITParams(
            thrombocytopenia=2,
            timing=2,
            thrombosis=2,
            other_causes=0,
        )
        result = calculate_4ts_hit(params)
        assert "PPV" in result.interpretation

    def test_score_value_in_interpretation(self):
        """The numeric score should always appear in the interpretation."""
        for total in range(9):
            # Use minimum combination to reach each score
            t = min(total, 2)
            remainder = total - t
            ti = min(remainder, 2)
            remainder -= ti
            th = min(remainder, 2)
            oc = remainder - th
            params = FourTsHITParams(
                thrombocytopenia=t,
                timing=ti,
                thrombosis=th,
                other_causes=oc,
            )
            result = calculate_4ts_hit(params)
            assert str(total) in result.interpretation


class TestClinicalScenarios:
    """Cross-validation against known clinical scenarios from literature."""

    def test_typical_hit_case(self):
        """Classic HIT: platelet drop >50% on day 7, new DVT, no other cause.
        Expected: high probability (score 8)."""
        params = FourTsHITParams(
            thrombocytopenia=2,  # >50% drop, nadir >=20
            timing=2,            # clear onset day 5-10
            thrombosis=2,        # new confirmed thrombosis
            other_causes=2,      # no other apparent cause
        )
        result = calculate_4ts_hit(params)
        assert result.value == 8
        assert "High pretest probability" in result.interpretation

    def test_post_surgical_thrombocytopenia(self):
        """Post-surgical patient: platelet drop with clear other cause.
        Expected: low probability."""
        params = FourTsHITParams(
            thrombocytopenia=1,  # fall >50% but due to surgery
            timing=1,            # timing consistent but unclear
            thrombosis=0,        # no thrombosis
            other_causes=0,      # definite other cause (surgery)
        )
        result = calculate_4ts_hit(params)
        assert result.value == 2
        assert "Low pretest probability" in result.interpretation

    def test_septic_patient_on_heparin(self):
        """Septic patient with moderate platelet drop and possible other causes.
        Expected: intermediate probability."""
        params = FourTsHITParams(
            thrombocytopenia=1,  # 30-50% fall
            timing=2,            # clear day 5-10 onset
            thrombosis=0,        # no thrombosis
            other_causes=1,      # possible other cause (sepsis)
        )
        result = calculate_4ts_hit(params)
        assert result.value == 4
        assert "Intermediate pretest probability" in result.interpretation

    def test_reexposure_rapid_onset(self):
        """Patient with prior heparin exposure within 30 days, rapid onset.
        Expected: high probability if other features supportive."""
        params = FourTsHITParams(
            thrombocytopenia=2,  # >50% fall, nadir >=20
            timing=2,            # <=1 day, prior exposure within 30 days
            thrombosis=1,        # suspected thrombosis
            other_causes=2,      # no other cause
        )
        result = calculate_4ts_hit(params)
        assert result.value == 7
        assert "High pretest probability" in result.interpretation
