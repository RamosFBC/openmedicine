"""Tests for the tokenized search with clinical synonym expansion."""
import pytest
from open_medicine.mcp.search_utils import score_match, tokenized_search, _expand_query_tokens


class TestExpandQueryTokens:
    """Test synonym expansion logic."""

    def test_single_word_direct(self):
        tokens = _expand_query_tokens("kidney")
        assert "kidney" in tokens
        assert "renal" in tokens
        assert "nephro" in tokens

    def test_synonym_bidirectional(self):
        """If 'renal' expands to include 'kidney', 'kidney' should expand to include 'renal'."""
        tokens_kidney = _expand_query_tokens("kidney")
        tokens_renal = _expand_query_tokens("renal")
        assert "kidney" in tokens_renal
        assert "renal" in tokens_kidney

    def test_multi_word_synonym(self):
        """Multi-word terms like 'heart attack' should expand to MI synonyms."""
        tokens = _expand_query_tokens("heart attack")
        assert "myocardial" in tokens
        assert "infarction" in tokens
        assert "stemi" in tokens

    def test_abbreviation_expansion(self):
        tokens = _expand_query_tokens("afib")
        assert "atrial" in tokens
        assert "fibrillation" in tokens

    def test_no_synonym_for_unknown(self):
        tokens = _expand_query_tokens("xyznotaword")
        assert tokens == {"xyznotaword"}

    def test_copd_synonyms(self):
        tokens = _expand_query_tokens("copd")
        assert "chronic" in tokens
        assert "obstructive" in tokens
        assert "emphysema" in tokens

    def test_pe_dvt_synonyms(self):
        tokens = _expand_query_tokens("pe")
        assert "pulmonary" in tokens
        assert "embolism" in tokens
        assert "vte" in tokens


class TestScoreMatch:
    """Test scoring function."""

    def test_exact_phrase_scores_high(self):
        score = score_match("kidney function", "Calculates estimated Glomerular Filtration Rate (eGFR), marking Kidney function.")
        assert score > 0.5

    def test_no_match_scores_zero(self):
        score = score_match("xyz nothing", "Calculates the CHA2DS2-VASc score for atrial fibrillation.")
        assert score == 0.0

    def test_synonym_match_scores_positive(self):
        """'renal function' should match text containing 'kidney function'."""
        score = score_match("renal function", "Calculates the 2021 Race-Free CKD-EPI estimated Glomerular Filtration Rate (eGFR), marking Kidney function.")
        assert score > 0.0

    def test_direct_match_scores_higher_than_synonym(self):
        text = "Kidney function calculator"
        direct_score = score_match("kidney", text)
        synonym_score = score_match("renal", text)
        assert direct_score > synonym_score

    def test_multi_token_query(self):
        """Both tokens matching should score higher than one token matching."""
        text = "Calculates the CHA2DS2-VASc score for atrial fibrillation stroke risk."
        score_both = score_match("stroke fibrillation", text)
        score_one = score_match("stroke xyznonexistent", text)
        assert score_both > score_one


class TestTokenizedSearch:
    """Test the main search function."""

    def test_basic_search(self):
        items = [
            {"name": "A", "searchable_text": "kidney function calculator"},
            {"name": "B", "searchable_text": "heart failure assessment"},
            {"name": "C", "searchable_text": "liver cirrhosis scoring"},
        ]
        results = tokenized_search("kidney", items)
        assert len(results) >= 1
        assert results[0]["name"] == "A"

    def test_synonym_search(self):
        """Searching 'renal' should find items about 'kidney'."""
        items = [
            {"name": "CKD-EPI", "searchable_text": "calculate_ckd_epi Calculates estimated Glomerular Filtration Rate marking Kidney function."},
            {"name": "SOFA", "searchable_text": "calculate_sofa Sequential Organ Failure Assessment ICU."},
        ]
        results = tokenized_search("renal", items)
        assert len(results) >= 1
        assert results[0]["name"] == "CKD-EPI"

    def test_multi_word_search(self):
        """Multi-word queries should match items with any of the words."""
        items = [
            {"name": "HEART", "searchable_text": "calculate_heart_score HEART score chest pain cardiac events"},
            {"name": "GCS", "searchable_text": "calculate_gcs Glasgow Coma Scale brain injury"},
            {"name": "CHA2DS2", "searchable_text": "calculate_chadsvasc CHA2DS2-VASc atrial fibrillation stroke risk"},
        ]
        results = tokenized_search("stroke risk atrial fibrillation", items)
        # CHA2DS2 should rank highest (matches stroke, risk, atrial, fibrillation)
        assert results[0]["name"] == "CHA2DS2"

    def test_empty_query_returns_empty(self):
        items = [{"name": "A", "searchable_text": "something"}]
        results = tokenized_search("", items)
        assert results == []

    def test_no_matches_returns_empty(self):
        items = [{"name": "A", "searchable_text": "kidney function"}]
        results = tokenized_search("xyznotaword", items)
        assert results == []

    def test_results_sorted_by_score(self):
        items = [
            {"name": "weak", "searchable_text": "general health assessment"},
            {"name": "strong", "searchable_text": "kidney function renal assessment nephrology"},
        ]
        results = tokenized_search("kidney renal", items)
        assert len(results) >= 1
        assert results[0]["name"] == "strong"

    def test_score_not_in_output_when_stripped(self):
        """The _score field should be present in raw output for internal use."""
        items = [{"name": "A", "searchable_text": "kidney function"}]
        results = tokenized_search("kidney", items)
        assert "_score" in results[0]  # raw output includes score


class TestSearchIntegration:
    """Integration tests against the actual registries."""

    def test_calculator_search_renal(self):
        """'renal' should find kidney-related calculators."""
        from open_medicine.mcp.registry import CALCULATOR_REGISTRY
        items = [
            {
                "calculator_id": calc_id,
                "description": tool_def.description,
                "searchable_text": f"{calc_id} {tool_def.description}",
            }
            for calc_id, tool_def in CALCULATOR_REGISTRY.items()
        ]
        results = tokenized_search("renal", items)
        calc_ids = [r["calculator_id"] for r in results]
        assert "calculate_ckd_epi" in calc_ids
        assert "calculate_cockcroft_gault" in calc_ids

    def test_calculator_search_afib(self):
        """'afib' should find atrial fibrillation calculators."""
        from open_medicine.mcp.registry import CALCULATOR_REGISTRY
        items = [
            {
                "calculator_id": calc_id,
                "description": tool_def.description,
                "searchable_text": f"{calc_id} {tool_def.description}",
            }
            for calc_id, tool_def in CALCULATOR_REGISTRY.items()
        ]
        results = tokenized_search("afib", items)
        calc_ids = [r["calculator_id"] for r in results]
        assert "calculate_chadsvasc" in calc_ids

    def test_calculator_search_stroke_risk(self):
        """'stroke risk' with separate words should find CHA2DS2-VASc."""
        from open_medicine.mcp.registry import CALCULATOR_REGISTRY
        items = [
            {
                "calculator_id": calc_id,
                "description": tool_def.description,
                "searchable_text": f"{calc_id} {tool_def.description}",
            }
            for calc_id, tool_def in CALCULATOR_REGISTRY.items()
        ]
        results = tokenized_search("stroke risk", items)
        calc_ids = [r["calculator_id"] for r in results]
        assert "calculate_chadsvasc" in calc_ids

    def test_calculator_search_blood_thinner(self):
        """'blood thinner dosing' should find anticoagulant calculators."""
        from open_medicine.mcp.registry import CALCULATOR_REGISTRY
        items = [
            {
                "calculator_id": calc_id,
                "description": tool_def.description,
                "searchable_text": f"{calc_id} {tool_def.description}",
            }
            for calc_id, tool_def in CALCULATOR_REGISTRY.items()
        ]
        results = tokenized_search("blood thinner dosing", items)
        calc_ids = [r["calculator_id"] for r in results]
        # Should find at least some anticoagulant dosing calculators
        anticoag_ids = {"calculate_rivaroxaban_dosing", "calculate_apixaban_dosing",
                        "calculate_dabigatran_dosing", "calculate_enoxaparin_dosing",
                        "calculate_heparin_dosing", "calculate_warfarin_initiation",
                        "calculate_edoxaban_dosing"}
        assert len(set(calc_ids) & anticoag_ids) >= 1

    def test_guideline_search_works(self):
        """Guideline search should return results for common queries."""
        from open_medicine.mcp.guideline_engine import search_guidelines
        results = search_guidelines("atrial fibrillation")
        assert len(results) >= 1

    def test_differential_search_works(self):
        """Differential search should return results for common queries."""
        from open_medicine.mcp.differentials.engine import search_differentials
        results = search_differentials("chest pain")
        assert len(results) >= 1

