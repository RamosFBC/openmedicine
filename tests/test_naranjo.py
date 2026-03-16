import pytest
from hypothesis import given, strategies as st, settings
from open_medicine.mcp.calculators.naranjo import (
    calculate_naranjo,
    NaranjoParams,
    NaranjoResponse,
)

# ---------------------------------------------------------------------------
# Helper to build params with all "do_not_know" as baseline
# ---------------------------------------------------------------------------
ALL_DO_NOT_KNOW = dict(
    previous_conclusive_reports=NaranjoResponse.DO_NOT_KNOW,
    event_after_drug=NaranjoResponse.DO_NOT_KNOW,
    improvement_on_discontinuation=NaranjoResponse.DO_NOT_KNOW,
    reappearance_on_rechallenge=NaranjoResponse.DO_NOT_KNOW,
    alternative_causes=NaranjoResponse.DO_NOT_KNOW,
    reaction_with_placebo=NaranjoResponse.DO_NOT_KNOW,
    drug_in_toxic_concentration=NaranjoResponse.DO_NOT_KNOW,
    severity_dose_related=NaranjoResponse.DO_NOT_KNOW,
    similar_prior_reaction=NaranjoResponse.DO_NOT_KNOW,
    confirmed_by_objective_evidence=NaranjoResponse.DO_NOT_KNOW,
)


# ---------------------------------------------------------------------------
# Tier 1: Deterministic Unit Tests
# ---------------------------------------------------------------------------


class TestNaranjoMinimumScore:
    """Test the minimum possible score (-4)."""

    def test_minimum_score(self):
        """All 'No' answers where 'No' deducts points, rest 'No' = score -4.

        Q2 No=-1, Q4 No=-1, Q5 Yes=-1, Q6 Yes=-1 gives -4.
        But all No answers: Q1=0, Q2=-1, Q3=0, Q4=-1, Q5=+2, Q6=+1, Q7=0, Q8=0, Q9=0, Q10=0 = +1
        Actually minimum is: Q2=No(-1), Q4=No(-1), Q5=Yes(-1), Q6=Yes(-1) = -4
        with all others answered to give 0.
        """
        params = NaranjoParams(
            previous_conclusive_reports=NaranjoResponse.DO_NOT_KNOW,  # 0
            event_after_drug=NaranjoResponse.NO,  # -1
            improvement_on_discontinuation=NaranjoResponse.DO_NOT_KNOW,  # 0
            reappearance_on_rechallenge=NaranjoResponse.NO,  # -1
            alternative_causes=NaranjoResponse.YES,  # -1
            reaction_with_placebo=NaranjoResponse.YES,  # -1
            drug_in_toxic_concentration=NaranjoResponse.DO_NOT_KNOW,  # 0
            severity_dose_related=NaranjoResponse.DO_NOT_KNOW,  # 0
            similar_prior_reaction=NaranjoResponse.DO_NOT_KNOW,  # 0
            confirmed_by_objective_evidence=NaranjoResponse.DO_NOT_KNOW,  # 0
        )
        result = calculate_naranjo(params)
        assert result.value == -4
        assert "Doubtful" in result.interpretation

    def test_minimum_score_all_worst(self):
        """Verify -4 is theoretical minimum by trying all 'worst' answers."""
        # Worst case: maximize negative, minimize positive
        # Q1: No=0 (best we can do negatively), Q2: No=-1, Q3: No=0,
        # Q4: No=-1, Q5: Yes=-1, Q6: Yes=-1, Q7: No=0, Q8: No=0, Q9: No=0, Q10: No=0
        params = NaranjoParams(
            previous_conclusive_reports=NaranjoResponse.NO,  # 0
            event_after_drug=NaranjoResponse.NO,  # -1
            improvement_on_discontinuation=NaranjoResponse.NO,  # 0
            reappearance_on_rechallenge=NaranjoResponse.NO,  # -1
            alternative_causes=NaranjoResponse.YES,  # -1
            reaction_with_placebo=NaranjoResponse.YES,  # -1
            drug_in_toxic_concentration=NaranjoResponse.NO,  # 0
            severity_dose_related=NaranjoResponse.NO,  # 0
            similar_prior_reaction=NaranjoResponse.NO,  # 0
            confirmed_by_objective_evidence=NaranjoResponse.NO,  # 0
        )
        result = calculate_naranjo(params)
        assert result.value == -4
        assert "Doubtful" in result.interpretation


class TestNaranjoMaximumScore:
    """Test the maximum possible score (+13)."""

    def test_maximum_score(self):
        """All answers that maximize points = +13."""
        params = NaranjoParams(
            previous_conclusive_reports=NaranjoResponse.YES,  # +1
            event_after_drug=NaranjoResponse.YES,  # +2
            improvement_on_discontinuation=NaranjoResponse.YES,  # +1
            reappearance_on_rechallenge=NaranjoResponse.YES,  # +2
            alternative_causes=NaranjoResponse.NO,  # +2
            reaction_with_placebo=NaranjoResponse.NO,  # +1
            drug_in_toxic_concentration=NaranjoResponse.YES,  # +1
            severity_dose_related=NaranjoResponse.YES,  # +1
            similar_prior_reaction=NaranjoResponse.YES,  # +1
            confirmed_by_objective_evidence=NaranjoResponse.YES,  # +1
        )
        result = calculate_naranjo(params)
        assert result.value == 13
        assert "Definite" in result.interpretation


class TestNaranjoAllDoNotKnow:
    """All 'Do not know' answers should give score 0."""

    def test_all_unknown(self):
        params = NaranjoParams(**ALL_DO_NOT_KNOW)
        result = calculate_naranjo(params)
        assert result.value == 0
        assert "Doubtful" in result.interpretation


class TestNaranjoThresholdBoundaries:
    """Test each category boundary."""

    def test_score_zero_is_doubtful(self):
        """Score 0 = Doubtful."""
        params = NaranjoParams(**ALL_DO_NOT_KNOW)
        result = calculate_naranjo(params)
        assert result.value == 0
        assert "Doubtful" in result.interpretation

    def test_score_negative_is_doubtful(self):
        """Score -1 = Doubtful."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["alternative_causes"] = NaranjoResponse.YES  # -1
        params = NaranjoParams(**kw)
        result = calculate_naranjo(params)
        assert result.value == -1
        assert "Doubtful" in result.interpretation

    def test_score_1_is_possible(self):
        """Score 1 = Possible (lower boundary)."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["previous_conclusive_reports"] = NaranjoResponse.YES  # +1
        params = NaranjoParams(**kw)
        result = calculate_naranjo(params)
        assert result.value == 1
        assert "Possible" in result.interpretation

    def test_score_4_is_possible(self):
        """Score 4 = Possible (upper boundary)."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["previous_conclusive_reports"] = NaranjoResponse.YES  # +1
        kw["improvement_on_discontinuation"] = NaranjoResponse.YES  # +1
        kw["drug_in_toxic_concentration"] = NaranjoResponse.YES  # +1
        kw["confirmed_by_objective_evidence"] = NaranjoResponse.YES  # +1
        params = NaranjoParams(**kw)
        result = calculate_naranjo(params)
        assert result.value == 4
        assert "Possible" in result.interpretation

    def test_score_5_is_probable(self):
        """Score 5 = Probable (lower boundary)."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["previous_conclusive_reports"] = NaranjoResponse.YES  # +1
        kw["improvement_on_discontinuation"] = NaranjoResponse.YES  # +1
        kw["drug_in_toxic_concentration"] = NaranjoResponse.YES  # +1
        kw["severity_dose_related"] = NaranjoResponse.YES  # +1
        kw["confirmed_by_objective_evidence"] = NaranjoResponse.YES  # +1
        params = NaranjoParams(**kw)
        result = calculate_naranjo(params)
        assert result.value == 5
        assert "Probable" in result.interpretation

    def test_score_8_is_probable(self):
        """Score 8 = Probable (upper boundary)."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["previous_conclusive_reports"] = NaranjoResponse.YES  # +1
        kw["event_after_drug"] = NaranjoResponse.YES  # +2
        kw["improvement_on_discontinuation"] = NaranjoResponse.YES  # +1
        kw["drug_in_toxic_concentration"] = NaranjoResponse.YES  # +1
        kw["severity_dose_related"] = NaranjoResponse.YES  # +1
        kw["similar_prior_reaction"] = NaranjoResponse.YES  # +1
        kw["confirmed_by_objective_evidence"] = NaranjoResponse.YES  # +1
        params = NaranjoParams(**kw)
        result = calculate_naranjo(params)
        assert result.value == 8
        assert "Probable" in result.interpretation

    def test_score_9_is_definite(self):
        """Score 9 = Definite (lower boundary)."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["previous_conclusive_reports"] = NaranjoResponse.YES  # +1
        kw["event_after_drug"] = NaranjoResponse.YES  # +2
        kw["improvement_on_discontinuation"] = NaranjoResponse.YES  # +1
        kw["reappearance_on_rechallenge"] = NaranjoResponse.YES  # +2
        kw["drug_in_toxic_concentration"] = NaranjoResponse.YES  # +1
        kw["severity_dose_related"] = NaranjoResponse.YES  # +1
        kw["confirmed_by_objective_evidence"] = NaranjoResponse.YES  # +1
        params = NaranjoParams(**kw)
        result = calculate_naranjo(params)
        assert result.value == 9
        assert "Definite" in result.interpretation


class TestNaranjoIndividualQuestionScoring:
    """Verify each question contributes the correct points."""

    def test_q1_yes(self):
        """Q1 (previous conclusive reports): Yes = +1."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["previous_conclusive_reports"] = NaranjoResponse.YES
        result = calculate_naranjo(NaranjoParams(**kw))
        assert result.value == 1

    def test_q1_no(self):
        """Q1 (previous conclusive reports): No = 0."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["previous_conclusive_reports"] = NaranjoResponse.NO
        result = calculate_naranjo(NaranjoParams(**kw))
        assert result.value == 0

    def test_q2_yes(self):
        """Q2 (event after drug): Yes = +2."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["event_after_drug"] = NaranjoResponse.YES
        result = calculate_naranjo(NaranjoParams(**kw))
        assert result.value == 2

    def test_q2_no(self):
        """Q2 (event after drug): No = -1."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["event_after_drug"] = NaranjoResponse.NO
        result = calculate_naranjo(NaranjoParams(**kw))
        assert result.value == -1

    def test_q3_yes(self):
        """Q3 (improvement on discontinuation): Yes = +1."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["improvement_on_discontinuation"] = NaranjoResponse.YES
        result = calculate_naranjo(NaranjoParams(**kw))
        assert result.value == 1

    def test_q3_no(self):
        """Q3 (improvement on discontinuation): No = 0."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["improvement_on_discontinuation"] = NaranjoResponse.NO
        result = calculate_naranjo(NaranjoParams(**kw))
        assert result.value == 0

    def test_q4_yes(self):
        """Q4 (reappearance on rechallenge): Yes = +2."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["reappearance_on_rechallenge"] = NaranjoResponse.YES
        result = calculate_naranjo(NaranjoParams(**kw))
        assert result.value == 2

    def test_q4_no(self):
        """Q4 (reappearance on rechallenge): No = -1."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["reappearance_on_rechallenge"] = NaranjoResponse.NO
        result = calculate_naranjo(NaranjoParams(**kw))
        assert result.value == -1

    def test_q5_yes(self):
        """Q5 (alternative causes): Yes = -1."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["alternative_causes"] = NaranjoResponse.YES
        result = calculate_naranjo(NaranjoParams(**kw))
        assert result.value == -1

    def test_q5_no(self):
        """Q5 (alternative causes): No = +2."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["alternative_causes"] = NaranjoResponse.NO
        result = calculate_naranjo(NaranjoParams(**kw))
        assert result.value == 2

    def test_q6_yes(self):
        """Q6 (reaction with placebo): Yes = -1."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["reaction_with_placebo"] = NaranjoResponse.YES
        result = calculate_naranjo(NaranjoParams(**kw))
        assert result.value == -1

    def test_q6_no(self):
        """Q6 (reaction with placebo): No = +1."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["reaction_with_placebo"] = NaranjoResponse.NO
        result = calculate_naranjo(NaranjoParams(**kw))
        assert result.value == 1

    def test_q7_yes(self):
        """Q7 (drug in toxic concentration): Yes = +1."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["drug_in_toxic_concentration"] = NaranjoResponse.YES
        result = calculate_naranjo(NaranjoParams(**kw))
        assert result.value == 1

    def test_q7_no(self):
        """Q7 (drug in toxic concentration): No = 0."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["drug_in_toxic_concentration"] = NaranjoResponse.NO
        result = calculate_naranjo(NaranjoParams(**kw))
        assert result.value == 0

    def test_q8_yes(self):
        """Q8 (severity dose related): Yes = +1."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["severity_dose_related"] = NaranjoResponse.YES
        result = calculate_naranjo(NaranjoParams(**kw))
        assert result.value == 1

    def test_q8_no(self):
        """Q8 (severity dose related): No = 0."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["severity_dose_related"] = NaranjoResponse.NO
        result = calculate_naranjo(NaranjoParams(**kw))
        assert result.value == 0

    def test_q9_yes(self):
        """Q9 (similar prior reaction): Yes = +1."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["similar_prior_reaction"] = NaranjoResponse.YES
        result = calculate_naranjo(NaranjoParams(**kw))
        assert result.value == 1

    def test_q9_no(self):
        """Q9 (similar prior reaction): No = 0."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["similar_prior_reaction"] = NaranjoResponse.NO
        result = calculate_naranjo(NaranjoParams(**kw))
        assert result.value == 0

    def test_q10_yes(self):
        """Q10 (confirmed by objective evidence): Yes = +1."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["confirmed_by_objective_evidence"] = NaranjoResponse.YES
        result = calculate_naranjo(NaranjoParams(**kw))
        assert result.value == 1

    def test_q10_no(self):
        """Q10 (confirmed by objective evidence): No = 0."""
        kw = dict(ALL_DO_NOT_KNOW)
        kw["confirmed_by_objective_evidence"] = NaranjoResponse.NO
        result = calculate_naranjo(NaranjoParams(**kw))
        assert result.value == 0


class TestNaranjoEvidence:
    """Verify DOI and evidence metadata."""

    def test_evidence_doi(self):
        params = NaranjoParams(**ALL_DO_NOT_KNOW)
        result = calculate_naranjo(params)
        assert result.evidence.source_doi == "10.1038/clpt.1981.154"

    def test_evidence_level(self):
        params = NaranjoParams(**ALL_DO_NOT_KNOW)
        result = calculate_naranjo(params)
        assert result.evidence.level == "Derivation & Validation Study"

    def test_evidence_description(self):
        params = NaranjoParams(**ALL_DO_NOT_KNOW)
        result = calculate_naranjo(params)
        assert "Naranjo" in result.evidence.description


class TestNaranjoFHIR:
    """Verify FHIR code metadata."""

    def test_no_loinc_code(self):
        """No LOINC code exists for Naranjo; should be None."""
        params = NaranjoParams(**ALL_DO_NOT_KNOW)
        result = calculate_naranjo(params)
        assert result.fhir_code is None
        assert result.fhir_system is None

    def test_fhir_display(self):
        params = NaranjoParams(**ALL_DO_NOT_KNOW)
        result = calculate_naranjo(params)
        assert "Naranjo" in result.fhir_display


class TestNaranjoClinicalScenarios:
    """Real-world clinical scenario tests."""

    def test_classic_definite_adr(self):
        """Patient with clear temporal relationship, positive rechallenge,
        no alternative causes, not on placebo, toxic levels found, dose-response,
        prior similar reaction, and objective evidence.
        Expected: 13 (Definite)."""
        params = NaranjoParams(
            previous_conclusive_reports=NaranjoResponse.YES,  # +1
            event_after_drug=NaranjoResponse.YES,  # +2
            improvement_on_discontinuation=NaranjoResponse.YES,  # +1
            reappearance_on_rechallenge=NaranjoResponse.YES,  # +2
            alternative_causes=NaranjoResponse.NO,  # +2
            reaction_with_placebo=NaranjoResponse.NO,  # +1
            drug_in_toxic_concentration=NaranjoResponse.YES,  # +1
            severity_dose_related=NaranjoResponse.YES,  # +1
            similar_prior_reaction=NaranjoResponse.YES,  # +1
            confirmed_by_objective_evidence=NaranjoResponse.YES,  # +1
        )
        result = calculate_naranjo(params)
        assert result.value == 13
        assert "Definite" in result.interpretation

    def test_typical_probable_adr(self):
        """Known reaction, temporal sequence, improved on withdrawal,
        no rechallenge done, alternative causes possible unknown.
        Score: 1+2+1+0+0+0+1+0+1+1 = 7 (Probable)."""
        params = NaranjoParams(
            previous_conclusive_reports=NaranjoResponse.YES,  # +1
            event_after_drug=NaranjoResponse.YES,  # +2
            improvement_on_discontinuation=NaranjoResponse.YES,  # +1
            reappearance_on_rechallenge=NaranjoResponse.DO_NOT_KNOW,  # 0
            alternative_causes=NaranjoResponse.DO_NOT_KNOW,  # 0
            reaction_with_placebo=NaranjoResponse.DO_NOT_KNOW,  # 0
            drug_in_toxic_concentration=NaranjoResponse.YES,  # +1
            severity_dose_related=NaranjoResponse.DO_NOT_KNOW,  # 0
            similar_prior_reaction=NaranjoResponse.YES,  # +1
            confirmed_by_objective_evidence=NaranjoResponse.YES,  # +1
        )
        result = calculate_naranjo(params)
        assert result.value == 7
        assert "Probable" in result.interpretation

    def test_possible_adr_limited_info(self):
        """Temporal sequence present but most data unavailable.
        Score: 0+2+0+0+0+0+0+0+0+0 = 2 (Possible)."""
        params = NaranjoParams(
            previous_conclusive_reports=NaranjoResponse.DO_NOT_KNOW,  # 0
            event_after_drug=NaranjoResponse.YES,  # +2
            improvement_on_discontinuation=NaranjoResponse.DO_NOT_KNOW,  # 0
            reappearance_on_rechallenge=NaranjoResponse.DO_NOT_KNOW,  # 0
            alternative_causes=NaranjoResponse.DO_NOT_KNOW,  # 0
            reaction_with_placebo=NaranjoResponse.DO_NOT_KNOW,  # 0
            drug_in_toxic_concentration=NaranjoResponse.DO_NOT_KNOW,  # 0
            severity_dose_related=NaranjoResponse.DO_NOT_KNOW,  # 0
            similar_prior_reaction=NaranjoResponse.DO_NOT_KNOW,  # 0
            confirmed_by_objective_evidence=NaranjoResponse.DO_NOT_KNOW,  # 0
        )
        result = calculate_naranjo(params)
        assert result.value == 2
        assert "Possible" in result.interpretation

    def test_doubtful_adr_with_alternative_causes(self):
        """Event occurred but alternative causes, prior exposure negative,
        no improvement on withdrawal.
        Score: 0+2+0+(-1)+(-1)+0+0+0+0+0 = 0 (Doubtful)."""
        params = NaranjoParams(
            previous_conclusive_reports=NaranjoResponse.DO_NOT_KNOW,  # 0
            event_after_drug=NaranjoResponse.YES,  # +2
            improvement_on_discontinuation=NaranjoResponse.DO_NOT_KNOW,  # 0
            reappearance_on_rechallenge=NaranjoResponse.NO,  # -1
            alternative_causes=NaranjoResponse.YES,  # -1
            reaction_with_placebo=NaranjoResponse.DO_NOT_KNOW,  # 0
            drug_in_toxic_concentration=NaranjoResponse.DO_NOT_KNOW,  # 0
            severity_dose_related=NaranjoResponse.DO_NOT_KNOW,  # 0
            similar_prior_reaction=NaranjoResponse.DO_NOT_KNOW,  # 0
            confirmed_by_objective_evidence=NaranjoResponse.DO_NOT_KNOW,  # 0
        )
        result = calculate_naranjo(params)
        assert result.value == 0
        assert "Doubtful" in result.interpretation


# ---------------------------------------------------------------------------
# Tier 2: Property-Based Fuzz Tests
# ---------------------------------------------------------------------------

naranjo_response_strategy = st.sampled_from(list(NaranjoResponse))


@pytest.mark.slow
@given(
    st.builds(
        NaranjoParams,
        previous_conclusive_reports=naranjo_response_strategy,
        event_after_drug=naranjo_response_strategy,
        improvement_on_discontinuation=naranjo_response_strategy,
        reappearance_on_rechallenge=naranjo_response_strategy,
        alternative_causes=naranjo_response_strategy,
        reaction_with_placebo=naranjo_response_strategy,
        drug_in_toxic_concentration=naranjo_response_strategy,
        severity_dose_related=naranjo_response_strategy,
        similar_prior_reaction=naranjo_response_strategy,
        confirmed_by_objective_evidence=naranjo_response_strategy,
    )
)
@settings(max_examples=500)
def test_naranjo_fuzz_bounds(params):
    """Property: score always in [-4, +13], interpretation never empty."""
    result = calculate_naranjo(params)
    assert result.value is not None
    assert isinstance(result.value, int)
    assert -4 <= result.value <= 13
    assert result.interpretation
    assert result.evidence.source_doi == "10.1038/clpt.1981.154"


@pytest.mark.slow
@given(
    st.builds(
        NaranjoParams,
        previous_conclusive_reports=naranjo_response_strategy,
        event_after_drug=naranjo_response_strategy,
        improvement_on_discontinuation=naranjo_response_strategy,
        reappearance_on_rechallenge=naranjo_response_strategy,
        alternative_causes=naranjo_response_strategy,
        reaction_with_placebo=naranjo_response_strategy,
        drug_in_toxic_concentration=naranjo_response_strategy,
        severity_dose_related=naranjo_response_strategy,
        similar_prior_reaction=naranjo_response_strategy,
        confirmed_by_objective_evidence=naranjo_response_strategy,
    )
)
@settings(max_examples=200)
def test_naranjo_fuzz_categories(params):
    """Property: category assignment matches score thresholds exactly."""
    result = calculate_naranjo(params)
    score = result.value
    if score >= 9:
        assert "Definite" in result.interpretation
    elif score >= 5:
        assert "Probable" in result.interpretation
    elif score >= 1:
        assert "Possible" in result.interpretation
    else:
        assert "Doubtful" in result.interpretation
