import pytest
from open_medicine.mcp.guideline_engine import search_guidelines, retrieve_guideline


class TestSearchGuidelines:
    def test_search_atrial_fibrillation(self):
        """Searching 'atrial fibrillation' should find the ACC/AHA AF guideline."""
        results = search_guidelines("atrial fibrillation")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_af_2023" in ids
        # Verify structure
        match = [r for r in results if r["guideline_id"] == "acc_aha_af_2023"][0]
        assert "doi" in match
        assert "available_sections" in match
        assert "anticoagulation" in match["available_sections"]

    def test_search_kidney(self):
        """Searching 'kidney' should find the KDIGO CKD guideline."""
        results = search_guidelines("kidney")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "kdigo_ckd_2024" in ids

    def test_search_pneumonia(self):
        """Searching 'pneumonia' should find the BTS CAP guideline."""
        results = search_guidelines("pneumonia")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "bts_cap_2009" in ids

    def test_search_no_results(self):
        """Searching for a non-existent topic returns empty list."""
        results = search_guidelines("xyznonexistent")
        assert results == []

    def test_search_timi_nstemi(self):
        """Searching 'NSTEMI' should find the TIMI UA/NSTEMI guideline."""
        results = search_guidelines("NSTEMI")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "timi_ua_nstemi_2000" in ids

    def test_search_case_insensitive(self):
        """Search should be case-insensitive."""
        results_lower = search_guidelines("ckd")
        results_upper = search_guidelines("CKD")
        assert len(results_lower) == len(results_upper)

    def test_search_ascvd(self):
        """Searching 'ascvd' should find the ACC/AHA ASCVD guideline."""
        results = search_guidelines("ascvd")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_ascvd_2013" in ids

    def test_search_sepsis3(self):
        """Searching 'sepsis-3' should find the Sepsis-3 guideline."""
        results = search_guidelines("sepsis-3")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "sepsis3_2016" in ids

    def test_search_wells_pe(self):
        """Searching 'wells score' should find the Wells PE guideline."""
        results = search_guidelines("wells score")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "wells_pe_2000" in ids

    def test_search_gold_copd(self):
        """Searching 'copd' should find the GOLD COPD guideline."""
        results = search_guidelines("copd")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "gold_copd_2024" in ids

class TestRetrieveGuideline:
    def test_retrieve_anticoagulation(self):
        """Retrieve the anticoagulation section of the AF guideline."""
        result = retrieve_guideline("acc_aha_af_2023", "anticoagulation")
        assert result.value == "acc_aha_af_2023/anticoagulation"
        assert "CHA2DS2-VASc" in result.interpretation
        assert "DOI" not in result.interpretation  # Content, not metadata
        assert result.evidence.source_doi == "10.1161/CIR.0000000000001193"

    def test_retrieve_severity_assessment(self):
        """Retrieve the severity assessment section of the BTS guideline."""
        result = retrieve_guideline("bts_cap_2009", "severity_assessment")
        assert "CURB-65" in result.interpretation
        assert result.evidence.source_doi == "10.1136/thx.2009.121434"

    def test_retrieve_staging(self):
        """Retrieve the CKD staging section."""
        result = retrieve_guideline("kdigo_ckd_2024", "staging")
        assert "GFR" in result.interpretation
        assert result.evidence.source_doi == "10.1016/j.kint.2023.10.018"

    def test_retrieve_invalid_guideline(self):
        """Requesting a non-existent guideline should raise ValueError."""
        with pytest.raises(ValueError, match="not found"):
            retrieve_guideline("nonexistent_guideline", "section")

    def test_retrieve_invalid_section(self):
        """Requesting a non-existent section should raise ValueError."""
        with pytest.raises(ValueError, match="not found"):
            retrieve_guideline("acc_aha_af_2023", "nonexistent_section")

    def test_retrieve_timi_nstemi_risk_assessment(self):
        """Retrieve the risk assessment section of the TIMI UA/NSTEMI guideline."""
        result = retrieve_guideline("timi_ua_nstemi_2000", "risk_assessment")
        assert result.value == "timi_ua_nstemi_2000/risk_assessment"
        assert "TIMI" in result.interpretation
        assert result.evidence.source_doi == "10.1001/jama.284.7.835"

    def test_retrieve_ascvd_risk_assessment(self):
        """Retrieve the risk assessment section of the ASCVD guideline."""
        result = retrieve_guideline("acc_aha_ascvd_2013", "risk_assessment")
        assert result.value == "acc_aha_ascvd_2013/risk_assessment"
        assert "Pooled Cohort Equations" in result.interpretation
        assert result.evidence.source_doi == "10.1161/01.cir.0000437741.48606.98"

    def test_retrieve_ascvd_interpretation(self):
        """Retrieve the interpretation section of the ASCVD guideline."""
        result = retrieve_guideline("acc_aha_ascvd_2013", "interpretation")
        assert result.value == "acc_aha_ascvd_2013/interpretation"
        assert "7.5%" in result.interpretation
        assert result.evidence.source_doi == "10.1161/01.cir.0000437741.48606.98"

    def test_retrieve_sepsis3_definition(self):
        """Retrieve the sepsis definition section of the Sepsis-3 guideline."""
        result = retrieve_guideline("sepsis3_2016", "sepsis_definition")
        assert result.value == "sepsis3_2016/sepsis_definition"
        assert "SOFA" in result.interpretation
        assert result.evidence.source_doi == "10.1001/jama.2016.0287"

    def test_retrieve_sepsis3_qsofa_screening(self):
        """Retrieve the qSOFA screening section of the Sepsis-3 guideline."""
        result = retrieve_guideline("sepsis3_2016", "qsofa_screening")
        assert result.value == "sepsis3_2016/qsofa_screening"
        assert "Glasgow Coma Scale" in result.interpretation
        assert result.evidence.source_doi == "10.1001/jama.2016.0287"

    def test_retrieve_wells_pe_probability(self):
        """Retrieve the pre-test probability section of the Wells PE guideline."""
        result = retrieve_guideline("wells_pe_2000", "pre_test_probability")
        assert result.value == "wells_pe_2000/pre_test_probability"
        assert "3.0 points" in result.interpretation
        assert result.evidence.source_doi == "10.1055/s-0037-1613870"

    def test_retrieve_wells_pe_algorithm(self):
        """Retrieve the diagnostic algorithm section of the Wells PE guideline."""
        result = retrieve_guideline("wells_pe_2000", "diagnostic_algorithm")
        assert result.value == "wells_pe_2000/diagnostic_algorithm"
        assert "CTPA" in result.interpretation
        assert result.evidence.source_doi == "10.1055/s-0037-1613870"

    def test_retrieve_gold_copd_spirometric(self):
        """Retrieve the spirometric grading section of the GOLD COPD guideline."""
        result = retrieve_guideline("gold_copd_2024", "spirometric_grading")
        assert result.value == "gold_copd_2024/spirometric_grading"
        assert "FEV1" in result.interpretation
        assert result.evidence.source_doi == "10.1016/S2213-2600(23)00461-7"

    def test_retrieve_gold_copd_abe(self):
        """Retrieve the ABE assessment section of the GOLD COPD guideline."""
        result = retrieve_guideline("gold_copd_2024", "abe_assessment")
        assert result.value == "gold_copd_2024/abe_assessment"
        assert "mMRC" in result.interpretation
        assert result.evidence.source_doi == "10.1016/S2213-2600(23)00461-7"

    def test_retrieve_gold_copd_pharmacotherapy(self):
        """Retrieve the initial pharmacotherapy section of the GOLD COPD guideline."""
        result = retrieve_guideline("gold_copd_2024", "initial_pharmacotherapy")
        assert result.value == "gold_copd_2024/initial_pharmacotherapy"
        assert "LAMA" in result.interpretation
        assert result.evidence.source_doi == "10.1016/S2213-2600(23)00461-7"

    def test_retrieve_chest_pain_risk_stratification(self):
        """Retrieve the risk stratification section of the AHA/ACC Chest Pain guideline."""
        result = retrieve_guideline("aha_acc_chest_pain_2021", "risk_stratification")
        assert result.value == "aha_acc_chest_pain_2021/risk_stratification"
        assert "HEART" in result.interpretation
        assert result.evidence.source_doi == "10.1161/CIR.0000000000001029"

    def test_retrieve_chest_pain_acute_management(self):
        """Retrieve the acute management section of the AHA/ACC Chest Pain guideline."""
        result = retrieve_guideline("aha_acc_chest_pain_2021", "acute_management")
        assert result.value == "aha_acc_chest_pain_2021/acute_management"
        assert "Aspirin" in result.interpretation
        assert result.evidence.source_doi == "10.1161/CIR.0000000000001029"

    def test_retrieve_stroke_initial_assessment(self):
        """Retrieve the initial assessment section of the AHA/ASA Stroke guideline."""
        result = retrieve_guideline("aha_asa_stroke_2019", "initial_assessment")
        assert result.value == "aha_asa_stroke_2019/initial_assessment"
        assert "NIHSS" in result.interpretation
        assert result.evidence.source_doi == "10.1161/STR.0000000000000211"

    def test_retrieve_stroke_thrombolysis(self):
        """Retrieve the thrombolysis section of the AHA/ASA Stroke guideline."""
        result = retrieve_guideline("aha_asa_stroke_2019", "thrombolysis")
        assert result.value == "aha_asa_stroke_2019/thrombolysis"
        assert "alteplase" in result.interpretation.lower()
        assert result.evidence.source_doi == "10.1161/STR.0000000000000211"

    def test_retrieve_stroke_thrombectomy(self):
        """Retrieve the thrombectomy section of the AHA/ASA Stroke guideline."""
        result = retrieve_guideline("aha_asa_stroke_2019", "thrombectomy")
        assert result.value == "aha_asa_stroke_2019/thrombectomy"
        assert "DAWN" in result.interpretation
        assert result.evidence.source_doi == "10.1161/STR.0000000000000211"

    def test_retrieve_cirrhosis_staging(self):
        """Retrieve the staging section of the AASLD Cirrhosis guideline."""
        result = retrieve_guideline("aasld_cirrhosis_2023", "staging")
        assert result.value == "aasld_cirrhosis_2023/staging"
        assert "Child-Pugh" in result.interpretation
        assert result.evidence.source_doi == "10.1097/HEP.0000000000000562"

    def test_retrieve_cirrhosis_complications(self):
        """Retrieve the complications section of the AASLD Cirrhosis guideline."""
        result = retrieve_guideline("aasld_cirrhosis_2023", "complications")
        assert result.value == "aasld_cirrhosis_2023/complications"
        assert "Lactulose" in result.interpretation
        assert result.evidence.source_doi == "10.1097/HEP.0000000000000562"


class TestSearchGuidelinesNewBatch:
    """Search tests for the new batch of guidelines: ESC ACS, NICE UGIB, RCP NEWS2."""

    # --- ESC ACS 2023 ---

    def test_search_grace_score(self):
        """Searching 'GRACE score' should find the ESC ACS 2023 guideline."""
        results = search_guidelines("GRACE score")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "esc_acs_2023" in ids

    def test_search_nstemi_esc(self):
        """Searching 'NSTEMI' should find the ESC ACS 2023 guideline."""
        results = search_guidelines("NSTEMI")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "esc_acs_2023" in ids

    def test_search_ticagrelor(self):
        """Searching 'ticagrelor' should find the ESC ACS 2023 guideline."""
        results = search_guidelines("ticagrelor")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "esc_acs_2023" in ids

    # --- NICE UGIB 2012 ---

    def test_search_gi_bleeding(self):
        """Searching 'upper gastrointestinal bleeding' should find the NICE UGIB guideline."""
        results = search_guidelines("upper gastrointestinal bleeding")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "nice_ugib_2012" in ids

    def test_search_blatchford(self):
        """Searching 'Blatchford score' should find the NICE UGIB guideline."""
        results = search_guidelines("Blatchford score")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "nice_ugib_2012" in ids

    def test_search_hematemesis(self):
        """Searching 'hematemesis' should find the NICE UGIB guideline."""
        results = search_guidelines("hematemesis")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "nice_ugib_2012" in ids

    # --- RCP NEWS2 2017 ---

    def test_search_news2(self):
        """Searching 'NEWS2' should find the RCP NEWS2 guideline."""
        results = search_guidelines("NEWS2")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "rcp_news2_2017" in ids

    def test_search_early_warning(self):
        """Searching 'early warning score' should find the RCP NEWS2 guideline."""
        results = search_guidelines("early warning score")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "rcp_news2_2017" in ids

    def test_search_clinical_deterioration(self):
        """Searching 'clinical deterioration' should find the RCP NEWS2 guideline."""
        results = search_guidelines("clinical deterioration")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "rcp_news2_2017" in ids


class TestRetrieveGuidelineNewBatch:
    """Retrieve tests for every section of the new guidelines."""

    # --- ESC ACS 2023 ---

    def test_retrieve_esc_acs_risk_stratification(self):
        """Retrieve the risk stratification section of the ESC ACS 2023 guideline."""
        result = retrieve_guideline("esc_acs_2023", "risk_stratification")
        assert result.value == "esc_acs_2023/risk_stratification"
        assert "GRACE" in result.interpretation
        assert result.evidence.source_doi == "10.1093/eurheartj/ehad191"

    def test_retrieve_esc_acs_antithrombotic(self):
        """Retrieve the antithrombotic therapy section of the ESC ACS 2023 guideline."""
        result = retrieve_guideline("esc_acs_2023", "antithrombotic_therapy")
        assert result.value == "esc_acs_2023/antithrombotic_therapy"
        assert "Aspirin" in result.interpretation
        assert result.evidence.source_doi == "10.1093/eurheartj/ehad191"

    def test_retrieve_esc_acs_invasive_strategy(self):
        """Retrieve the invasive strategy section of the ESC ACS 2023 guideline."""
        result = retrieve_guideline("esc_acs_2023", "invasive_strategy")
        assert result.value == "esc_acs_2023/invasive_strategy"
        assert "24" in result.interpretation
        assert result.evidence.source_doi == "10.1093/eurheartj/ehad191"

    # --- NICE UGIB 2012 ---

    def test_retrieve_nice_ugib_risk_assessment(self):
        """Retrieve the risk assessment section of the NICE UGIB guideline."""
        result = retrieve_guideline("nice_ugib_2012", "risk_assessment")
        assert result.value == "nice_ugib_2012/risk_assessment"
        assert "Blatchford" in result.interpretation
        assert result.evidence.source_doi == "10.1136/gut.2011.241976"

    def test_retrieve_nice_ugib_resuscitation(self):
        """Retrieve the resuscitation section of the NICE UGIB guideline."""
        result = retrieve_guideline("nice_ugib_2012", "resuscitation")
        assert result.value == "nice_ugib_2012/resuscitation"
        assert "transfusion" in result.interpretation.lower()
        assert result.evidence.source_doi == "10.1136/gut.2011.241976"

    def test_retrieve_nice_ugib_endoscopic(self):
        """Retrieve the endoscopic management section of the NICE UGIB guideline."""
        result = retrieve_guideline("nice_ugib_2012", "endoscopic_management")
        assert result.value == "nice_ugib_2012/endoscopic_management"
        assert "endoscopy" in result.interpretation.lower()
        assert result.evidence.source_doi == "10.1136/gut.2011.241976"

    # --- RCP NEWS2 2017 ---

    def test_retrieve_rcp_news2_scoring(self):
        """Retrieve the scoring system section of the RCP NEWS2 guideline."""
        result = retrieve_guideline("rcp_news2_2017", "scoring_system")
        assert result.value == "rcp_news2_2017/scoring_system"
        assert "NEWS2" in result.interpretation
        assert result.evidence.source_doi == "10.7861/clinmedicine.17-6-s68"

    def test_retrieve_rcp_news2_response(self):
        """Retrieve the clinical response section of the RCP NEWS2 guideline."""
        result = retrieve_guideline("rcp_news2_2017", "clinical_response")
        assert result.value == "rcp_news2_2017/clinical_response"
        assert "response" in result.interpretation.lower() or "escalation" in result.interpretation.lower()
        assert result.evidence.source_doi == "10.7861/clinmedicine.17-6-s68"
