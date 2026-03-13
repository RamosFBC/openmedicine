"""Tests for the differential diagnosis engine."""
import pytest
from open_medicine.mcp.differentials.engine import (
    search_differentials,
    get_differential,
    DifferentialParams,
)


def test_search_differentials_returns_matches():
    """Searching for 'chest pain' should return at least one differential."""
    results = search_differentials("chest pain")
    assert len(results) > 0
    assert "differential_id" in results[0]
    assert "title" in results[0]
    assert "description" in results[0]


def test_search_differentials_no_match():
    """Searching for nonsense returns empty list."""
    results = search_differentials("xyznonexistent123")
    assert results == []


def test_get_differential_returns_clinical_result():
    """Retrieving a known differential returns a ClinicalResult."""
    from open_medicine.foundation.base import ClinicalResult
    params = DifferentialParams(
        differential_id="chest_pain",
        age=55,
        sex="male",
    )
    result = get_differential(params)
    assert isinstance(result, ClinicalResult)
    assert result.evidence.source_doi != ""
    # Value should contain diagnoses list
    assert "diagnoses" in result.value


def test_get_differential_unknown_id():
    """Unknown differential_id returns an error result."""
    params = DifferentialParams(
        differential_id="nonexistent_thing",
        age=30,
        sex="female",
    )
    result = get_differential(params)
    assert "not_found" in str(result.value)


def test_differential_diagnoses_have_required_fields():
    """Each diagnosis in the differential must have required fields."""
    params = DifferentialParams(
        differential_id="chest_pain",
        age=55,
        sex="male",
    )
    result = get_differential(params)
    for dx in result.value["diagnoses"]:
        assert "name" in dx
        assert "likelihood" in dx
        assert dx["likelihood"] in ("common", "less_common", "must_not_miss")
        assert "key_features" in dx
        assert "recommended_tests" in dx


# ---- Broadening: also_consider and clinical_reasoning_prompt tests ----


def test_all_differentials_have_also_consider():
    """Every differential must have an also_consider array with at least 5 entries."""
    for diff_id in ("chest_pain", "dyspnea", "altered_mental_status", "sore_throat", "abdominal_pain"):
        params = DifferentialParams(differential_id=diff_id)
        result = get_differential(params)
        also_consider = result.value.get("also_consider", [])
        assert len(also_consider) >= 5, (
            f"{diff_id}: also_consider has {len(also_consider)} entries, need >= 5"
        )


def test_also_consider_entries_have_required_fields():
    """Every also_consider entry must have name (str) and rationale (str)."""
    for diff_id in ("chest_pain", "dyspnea", "altered_mental_status", "abdominal_pain"):
        params = DifferentialParams(differential_id=diff_id)
        result = get_differential(params)
        for entry in result.value.get("also_consider", []):
            assert "name" in entry and isinstance(entry["name"], str) and entry["name"], (
                f"{diff_id}: also_consider entry missing or empty 'name'"
            )
            assert "rationale" in entry and isinstance(entry["rationale"], str) and entry["rationale"], (
                f"{diff_id}: also_consider entry '{entry.get('name')}' missing or empty 'rationale'"
            )


def test_all_differentials_have_clinical_reasoning_prompt():
    """Every differential must have a non-empty clinical_reasoning_prompt."""
    for diff_id in ("chest_pain", "dyspnea", "altered_mental_status", "abdominal_pain"):
        params = DifferentialParams(differential_id=diff_id)
        result = get_differential(params)
        prompt = result.value.get("clinical_reasoning_prompt", "")
        assert isinstance(prompt, str) and len(prompt) > 0, (
            f"{diff_id}: clinical_reasoning_prompt is missing or empty"
        )


def test_get_differential_includes_also_consider_in_result():
    """ClinicalResult.value must contain also_consider and clinical_reasoning_prompt keys."""
    params = DifferentialParams(differential_id="chest_pain", age=55, sex="male")
    result = get_differential(params)
    assert "also_consider" in result.value, "also_consider missing from ClinicalResult.value"
    assert "clinical_reasoning_prompt" in result.value, "clinical_reasoning_prompt missing from ClinicalResult.value"


def test_interpretation_references_also_consider():
    """Interpretation text should mention also_consider count."""
    params = DifferentialParams(differential_id="chest_pain")
    result = get_differential(params)
    assert "also consider" in result.interpretation.lower() or "also_consider" in result.interpretation.lower(), (
        "Interpretation should reference the also_consider entries"
    )


# ---- Altered Mental Status differential tests ----


def test_search_altered_mental_status_by_keyword():
    """Searching 'altered mental status' should find the AMS differential."""
    results = search_differentials("altered mental status")
    assert len(results) >= 1
    ids = [r["differential_id"] for r in results]
    assert "altered_mental_status" in ids


def test_search_altered_mental_status_by_confusion():
    """Searching 'confusion' should find the AMS differential."""
    results = search_differentials("confusion")
    assert len(results) >= 1
    ids = [r["differential_id"] for r in results]
    assert "altered_mental_status" in ids


def test_search_altered_mental_status_by_delirium():
    """Searching 'delirium' should find the AMS differential."""
    results = search_differentials("delirium")
    assert len(results) >= 1
    ids = [r["differential_id"] for r in results]
    assert "altered_mental_status" in ids


def test_get_altered_mental_status_has_diagnoses():
    """Altered mental status differential should have all expected must-not-miss diagnoses."""
    params = DifferentialParams(differential_id="altered_mental_status")
    result = get_differential(params)
    names = [d["name"] for d in result.value["diagnoses"]]
    # Must-not-miss diagnoses
    assert "Stroke / Intracranial Hemorrhage" in names
    assert "Meningitis / Encephalitis" in names
    assert "Sepsis / Systemic Infection" in names
    assert "Hypoglycemia" in names
    assert "Alcohol / Benzodiazepine Withdrawal" in names


def test_altered_mental_status_evidence_doi():
    """Verify DOI matches the Kanich 2002 paper."""
    params = DifferentialParams(differential_id="altered_mental_status")
    result = get_differential(params)
    assert result.evidence.source_doi == "10.1053/ajem.2002.35464"


def test_altered_mental_status_diagnoses_required_fields():
    """Each diagnosis in the AMS differential must have required fields."""
    params = DifferentialParams(differential_id="altered_mental_status")
    result = get_differential(params)
    for dx in result.value["diagnoses"]:
        assert "name" in dx
        assert "likelihood" in dx
        assert dx["likelihood"] in ("common", "less_common", "must_not_miss")
        assert "key_features" in dx
        assert isinstance(dx["key_features"], list) and len(dx["key_features"]) > 0
        assert "recommended_tests" in dx
        assert isinstance(dx["recommended_tests"], list) and len(dx["recommended_tests"]) > 0
        assert "red_flags" in dx
        assert "related_guidelines" in dx


def test_altered_mental_status_likelihood_distribution():
    """AMS differential should have diagnoses across likelihood categories."""
    params = DifferentialParams(differential_id="altered_mental_status")
    result = get_differential(params)
    likelihoods = [d["likelihood"] for d in result.value["diagnoses"]]
    assert "must_not_miss" in likelihoods
    assert "common" in likelihoods
    assert "less_common" in likelihoods


def test_altered_mental_status_calculator_cross_references():
    """AMS differential should reference known calculators."""
    params = DifferentialParams(differential_id="altered_mental_status")
    result = get_differential(params)
    all_tests = []
    for dx in result.value["diagnoses"]:
        all_tests.extend(dx["recommended_tests"])
    # Verify calculator cross-references
    assert "calculate_gcs" in all_tests
    assert "calculate_cam_icu" in all_tests
    assert "calculate_sofa" in all_tests
    assert "calculate_serum_osmolality" in all_tests
    assert "calculate_corrected_sodium" in all_tests


def test_altered_mental_status_guideline_cross_references():
    """AMS differential should reference sepsis guidelines."""
    params = DifferentialParams(differential_id="altered_mental_status")
    result = get_differential(params)
    all_guidelines = []
    for dx in result.value["diagnoses"]:
        all_guidelines.extend(dx["related_guidelines"])
    assert "sepsis3_2016" in all_guidelines
    assert "ssc_sepsis_2021" in all_guidelines


def test_altered_mental_status_returns_clinical_result():
    """Retrieving the AMS differential returns a ClinicalResult."""
    from open_medicine.foundation.base import ClinicalResult
    params = DifferentialParams(
        differential_id="altered_mental_status",
        age=70,
        sex="male",
    )
    result = get_differential(params)
    assert isinstance(result, ClinicalResult)
    assert "diagnoses" in result.value
    assert "also_consider" in result.value
    assert "clinical_reasoning_prompt" in result.value


# ---- Abdominal Pain differential tests ----


def test_search_abdominal_pain_by_keyword():
    """Searching 'abdominal pain' should find the abdominal_pain differential."""
    results = search_differentials("abdominal pain")
    assert len(results) >= 1
    ids = [r["differential_id"] for r in results]
    assert "abdominal_pain" in ids


def test_search_abdominal_pain_by_acute_abdomen():
    """Searching 'acute abdomen' should find the abdominal_pain differential."""
    results = search_differentials("acute abdomen")
    assert len(results) >= 1
    ids = [r["differential_id"] for r in results]
    assert "abdominal_pain" in ids


def test_search_abdominal_pain_by_appendicitis():
    """Searching 'appendicitis' should find the abdominal_pain differential."""
    results = search_differentials("appendicitis")
    assert len(results) >= 1
    ids = [r["differential_id"] for r in results]
    assert "abdominal_pain" in ids


def test_get_abdominal_pain_has_diagnoses():
    """Abdominal pain differential should have all expected must-not-miss diagnoses."""
    params = DifferentialParams(differential_id="abdominal_pain")
    result = get_differential(params)
    names = [d["name"] for d in result.value["diagnoses"]]
    # Must-not-miss diagnoses
    assert "Abdominal Aortic Aneurysm (AAA) Rupture" in names
    assert "Mesenteric Ischemia" in names
    assert "Ectopic Pregnancy" in names
    assert "Perforated Viscus" in names
    # Common diagnoses
    assert "Acute Appendicitis" in names
    assert "Acute Cholecystitis" in names
    assert "Acute Pancreatitis" in names
    assert "Acute Diverticulitis" in names


def test_abdominal_pain_evidence_doi():
    """Verify DOI matches the Rogers & Kirton NEJM 2024 paper."""
    params = DifferentialParams(differential_id="abdominal_pain")
    result = get_differential(params)
    assert result.evidence.source_doi == "10.1056/NEJMra2304821"


def test_abdominal_pain_diagnoses_required_fields():
    """Each diagnosis in the abdominal pain differential must have required fields."""
    params = DifferentialParams(differential_id="abdominal_pain")
    result = get_differential(params)
    for dx in result.value["diagnoses"]:
        assert "name" in dx
        assert "likelihood" in dx
        assert dx["likelihood"] in ("common", "less_common", "must_not_miss")
        assert "key_features" in dx
        assert isinstance(dx["key_features"], list) and len(dx["key_features"]) > 0
        assert "recommended_tests" in dx
        assert isinstance(dx["recommended_tests"], list) and len(dx["recommended_tests"]) > 0
        assert "red_flags" in dx
        assert "related_guidelines" in dx


def test_abdominal_pain_likelihood_distribution():
    """Abdominal pain differential should have diagnoses across likelihood categories."""
    params = DifferentialParams(differential_id="abdominal_pain")
    result = get_differential(params)
    likelihoods = [d["likelihood"] for d in result.value["diagnoses"]]
    assert "must_not_miss" in likelihoods
    assert "common" in likelihoods
    assert "less_common" in likelihoods


def test_abdominal_pain_calculator_cross_references():
    """Abdominal pain differential should reference known calculators."""
    params = DifferentialParams(differential_id="abdominal_pain")
    result = get_differential(params)
    all_tests = []
    for dx in result.value["diagnoses"]:
        all_tests.extend(dx["recommended_tests"])
    # Verify calculator cross-references
    assert "calculate_bisap" in all_tests
    assert "calculate_ransons" in all_tests
    assert "calculate_sofa" in all_tests
    assert "calculate_anion_gap" in all_tests
    assert "calculate_glasgow_blatchford" in all_tests


def test_abdominal_pain_guideline_cross_references():
    """Abdominal pain differential should reference pancreatitis guideline."""
    params = DifferentialParams(differential_id="abdominal_pain")
    result = get_differential(params)
    all_guidelines = []
    for dx in result.value["diagnoses"]:
        all_guidelines.extend(dx["related_guidelines"])
    assert "acg_acute_pancreatitis_2024" in all_guidelines


def test_abdominal_pain_returns_clinical_result():
    """Retrieving the abdominal pain differential returns a ClinicalResult."""
    from open_medicine.foundation.base import ClinicalResult
    params = DifferentialParams(
        differential_id="abdominal_pain",
        age=45,
        sex="female",
    )
    result = get_differential(params)
    assert isinstance(result, ClinicalResult)
    assert "diagnoses" in result.value
    assert "also_consider" in result.value
    assert "clinical_reasoning_prompt" in result.value


def test_abdominal_pain_diagnosis_count():
    """Abdominal pain differential should have at least 10 diagnoses."""
    params = DifferentialParams(differential_id="abdominal_pain")
    result = get_differential(params)
    assert len(result.value["diagnoses"]) >= 10
