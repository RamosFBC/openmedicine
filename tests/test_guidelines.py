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


class TestSearchGuidelinesHF2022:
    """Search tests for the AHA/ACC/HFSA Heart Failure 2022 guideline."""

    def test_search_heart_failure(self):
        """Searching 'heart failure' should find the AHA/ACC/HFSA HF 2022 guideline."""
        results = search_guidelines("heart failure")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aha_acc_hf_2022" in ids

    def test_search_hfref(self):
        """Searching 'HFrEF' should find the AHA/ACC/HFSA HF 2022 guideline."""
        results = search_guidelines("HFrEF")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aha_acc_hf_2022" in ids

    def test_search_sglt2_hf(self):
        """Searching 'dapagliflozin' should find the AHA/ACC/HFSA HF 2022 guideline."""
        results = search_guidelines("dapagliflozin")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aha_acc_hf_2022" in ids

    def test_search_arni(self):
        """Searching 'ARNi' should find the AHA/ACC/HFSA HF 2022 guideline."""
        results = search_guidelines("ARNi")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aha_acc_hf_2022" in ids

    def test_search_crt(self):
        """Searching 'cardiac resynchronization therapy' should find the HF 2022 guideline."""
        results = search_guidelines("cardiac resynchronization therapy")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aha_acc_hf_2022" in ids


class TestRetrieveGuidelineHF2022:
    """Retrieve tests for every section of the AHA/ACC/HFSA HF 2022 guideline."""

    def test_retrieve_hf_classification(self):
        """Retrieve the classification section of the HF 2022 guideline."""
        result = retrieve_guideline("aha_acc_hf_2022", "classification")
        assert result.value == "aha_acc_hf_2022/classification"
        assert "HFrEF" in result.interpretation
        assert result.evidence.source_doi == "10.1161/CIR.0000000000001063"

    def test_retrieve_hf_pharmacotherapy(self):
        """Retrieve the pharmacotherapy section of the HF 2022 guideline."""
        result = retrieve_guideline("aha_acc_hf_2022", "pharmacotherapy")
        assert result.value == "aha_acc_hf_2022/pharmacotherapy"
        assert "sacubitril" in result.interpretation.lower() or "ARNI" in result.interpretation or "ARNi" in result.interpretation
        assert result.evidence.source_doi == "10.1161/CIR.0000000000001063"

    def test_retrieve_hf_device_therapy(self):
        """Retrieve the device therapy section of the HF 2022 guideline."""
        result = retrieve_guideline("aha_acc_hf_2022", "device_therapy")
        assert result.value == "aha_acc_hf_2022/device_therapy"
        assert "ICD" in result.interpretation or "CRT" in result.interpretation
        assert result.evidence.source_doi == "10.1161/CIR.0000000000001063"


class TestSearchGuidelinesADADiabetes2024:
    """Search tests for the ADA Standards of Care in Diabetes 2024 guideline."""

    def test_search_diabetes(self):
        """Searching 'diabetes' should find the ADA Diabetes 2024 guideline."""
        results = search_guidelines("diabetes")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ada_diabetes_2024" in ids

    def test_search_metformin(self):
        """Searching 'metformin' should find the ADA Diabetes 2024 guideline."""
        results = search_guidelines("metformin")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ada_diabetes_2024" in ids

    def test_search_hba1c(self):
        """Searching 'HbA1c' should find the ADA Diabetes 2024 guideline."""
        results = search_guidelines("HbA1c")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ada_diabetes_2024" in ids

    def test_search_semaglutide(self):
        """Searching 'semaglutide' should find the ADA Diabetes 2024 guideline."""
        results = search_guidelines("semaglutide")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ada_diabetes_2024" in ids

    def test_search_insulin(self):
        """Searching 'basal insulin' should find the ADA Diabetes 2024 guideline."""
        results = search_guidelines("basal insulin")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ada_diabetes_2024" in ids


class TestRetrieveGuidelineADADiabetes2024:
    """Retrieve tests for every section of the ADA Diabetes 2024 guideline."""

    def test_retrieve_glycemic_targets(self):
        """Retrieve the glycemic targets section of the ADA Diabetes 2024 guideline."""
        result = retrieve_guideline("ada_diabetes_2024", "glycemic_targets")
        assert result.value == "ada_diabetes_2024/glycemic_targets"
        assert "A1C" in result.interpretation or "7%" in result.interpretation
        assert result.evidence.source_doi == "10.2337/dc24-S009"

    def test_retrieve_pharmacotherapy(self):
        """Retrieve the pharmacotherapy section of the ADA Diabetes 2024 guideline."""
        result = retrieve_guideline("ada_diabetes_2024", "pharmacotherapy")
        assert result.value == "ada_diabetes_2024/pharmacotherapy"
        assert "metformin" in result.interpretation.lower() or "Metformin" in result.interpretation
        assert result.evidence.source_doi == "10.2337/dc24-S009"

    def test_retrieve_cardiovascular_risk(self):
        """Retrieve the cardiovascular risk section of the ADA Diabetes 2024 guideline."""
        result = retrieve_guideline("ada_diabetes_2024", "cardiovascular_risk")
        assert result.value == "ada_diabetes_2024/cardiovascular_risk"
        assert "ASCVD" in result.interpretation or "statin" in result.interpretation.lower()
        assert result.evidence.source_doi == "10.2337/dc24-S009"


class TestSearchGuidelinesASHVTE2020:
    """Search tests for the ASH VTE Treatment 2020 guideline."""

    def test_search_vte(self):
        """Searching 'venous thromboembolism' should find the ASH VTE 2020 guideline."""
        results = search_guidelines("venous thromboembolism")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ash_vte_2020" in ids

    def test_search_dvt(self):
        """Searching 'DVT' should find the ASH VTE 2020 guideline."""
        results = search_guidelines("DVT")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ash_vte_2020" in ids

    def test_search_pulmonary_embolism(self):
        """Searching 'pulmonary embolism' should find the ASH VTE 2020 guideline."""
        results = search_guidelines("pulmonary embolism")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ash_vte_2020" in ids

    def test_search_doac(self):
        """Searching 'DOAC' should find the ASH VTE 2020 guideline."""
        results = search_guidelines("DOAC")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ash_vte_2020" in ids

    def test_search_apixaban(self):
        """Searching 'apixaban' should find the ASH VTE 2020 guideline."""
        results = search_guidelines("apixaban")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ash_vte_2020" in ids


class TestRetrieveGuidelineASHVTE2020:
    """Retrieve tests for every section of the ASH VTE 2020 guideline."""

    def test_retrieve_anticoagulation_therapy(self):
        """Retrieve the anticoagulation therapy section of the ASH VTE 2020 guideline."""
        result = retrieve_guideline("ash_vte_2020", "anticoagulation_therapy")
        assert result.value == "ash_vte_2020/anticoagulation_therapy"
        assert "DOAC" in result.interpretation or "apixaban" in result.interpretation.lower()
        assert result.evidence.source_doi == "10.1182/bloodadvances.2020001830"

    def test_retrieve_treatment_duration(self):
        """Retrieve the treatment duration section of the ASH VTE 2020 guideline."""
        result = retrieve_guideline("ash_vte_2020", "treatment_duration")
        assert result.value == "ash_vte_2020/treatment_duration"
        assert "3" in result.interpretation  # 3-6 months
        assert result.evidence.source_doi == "10.1182/bloodadvances.2020001830"

    def test_retrieve_advanced_management(self):
        """Retrieve the advanced management section of the ASH VTE 2020 guideline."""
        result = retrieve_guideline("ash_vte_2020", "advanced_management")
        assert result.value == "ash_vte_2020/advanced_management"
        assert "thrombol" in result.interpretation.lower() or "IVC" in result.interpretation
        assert result.evidence.source_doi == "10.1182/bloodadvances.2020001830"


class TestSearchGuidelinesACGPancreatitis2024:
    """Search tests for the ACG Acute Pancreatitis 2024 guideline."""

    def test_search_acute_pancreatitis(self):
        """Searching 'acute pancreatitis' should find the ACG guideline."""
        results = search_guidelines("acute pancreatitis")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acg_acute_pancreatitis_2024" in ids

    def test_search_bisap(self):
        """Searching 'BISAP' should find the ACG pancreatitis guideline."""
        results = search_guidelines("BISAP")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acg_acute_pancreatitis_2024" in ids

    def test_search_necrotizing_pancreatitis(self):
        """Searching 'necrotizing pancreatitis' should find the ACG guideline."""
        results = search_guidelines("necrotizing pancreatitis")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acg_acute_pancreatitis_2024" in ids

    def test_search_ercp(self):
        """Searching 'ERCP' should find the ACG pancreatitis guideline."""
        results = search_guidelines("ERCP")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acg_acute_pancreatitis_2024" in ids

    def test_search_cholecystectomy(self):
        """Searching 'cholecystectomy' should find the ACG pancreatitis guideline."""
        results = search_guidelines("cholecystectomy")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acg_acute_pancreatitis_2024" in ids

    def test_search_gallstone_pancreatitis(self):
        """Searching 'gallstone pancreatitis' should find the ACG guideline."""
        results = search_guidelines("gallstone pancreatitis")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acg_acute_pancreatitis_2024" in ids


class TestRetrieveGuidelineACGPancreatitis2024:
    """Retrieve tests for every section of the ACG Acute Pancreatitis 2024 guideline."""

    def test_retrieve_severity_assessment(self):
        """Retrieve the severity assessment section of the ACG pancreatitis guideline."""
        result = retrieve_guideline("acg_acute_pancreatitis_2024", "severity_assessment")
        assert result.value == "acg_acute_pancreatitis_2024/severity_assessment"
        assert "Revised Atlanta" in result.interpretation
        assert "BISAP" in result.interpretation
        assert "lipase" in result.interpretation.lower()
        assert result.evidence.source_doi == "10.14309/ajg.0000000000002645"

    def test_retrieve_initial_management(self):
        """Retrieve the initial management section of the ACG pancreatitis guideline."""
        result = retrieve_guideline("acg_acute_pancreatitis_2024", "initial_management")
        assert result.value == "acg_acute_pancreatitis_2024/initial_management"
        assert "lactated Ringer" in result.interpretation
        assert "1.5 mL/kg/hr" in result.interpretation
        assert "enteral" in result.interpretation.lower()
        assert result.evidence.source_doi == "10.14309/ajg.0000000000002645"

    def test_retrieve_biliary_management(self):
        """Retrieve the biliary management section of the ACG pancreatitis guideline."""
        result = retrieve_guideline("acg_acute_pancreatitis_2024", "biliary_management")
        assert result.value == "acg_acute_pancreatitis_2024/biliary_management"
        assert "ERCP" in result.interpretation
        assert "cholangitis" in result.interpretation.lower()
        assert "cholecystectomy" in result.interpretation.lower()
        assert "indomethacin" in result.interpretation.lower()
        assert result.evidence.source_doi == "10.14309/ajg.0000000000002645"

    def test_retrieve_necrotizing_pancreatitis(self):
        """Retrieve the necrotizing pancreatitis section of the ACG pancreatitis guideline."""
        result = retrieve_guideline("acg_acute_pancreatitis_2024", "necrotizing_pancreatitis")
        assert result.value == "acg_acute_pancreatitis_2024/necrotizing_pancreatitis"
        assert "step-up" in result.interpretation.lower()
        assert "4 weeks" in result.interpretation
        assert "FNA" in result.interpretation
        assert "carbapenem" in result.interpretation.lower() or "imipenem" in result.interpretation.lower()
        assert result.evidence.source_doi == "10.14309/ajg.0000000000002645"


class TestSearchGuidelinesSAH2023:
    """Search tests for the AHA/ASA SAH 2023 guideline."""

    def test_search_subarachnoid_hemorrhage(self):
        """Searching 'subarachnoid hemorrhage' should find the AHA/ASA SAH guideline."""
        results = search_guidelines("subarachnoid hemorrhage")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aha_asa_sah_2023" in ids

    def test_search_hunt_hess(self):
        """Searching 'Hunt and Hess' should find the AHA/ASA SAH guideline."""
        results = search_guidelines("Hunt and Hess")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aha_asa_sah_2023" in ids

    def test_search_fisher_grade(self):
        """Searching 'Fisher grade' should find the AHA/ASA SAH guideline."""
        results = search_guidelines("Fisher grade")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aha_asa_sah_2023" in ids

    def test_search_nimodipine(self):
        """Searching 'nimodipine' should find the AHA/ASA SAH guideline."""
        results = search_guidelines("nimodipine")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aha_asa_sah_2023" in ids

    def test_search_dci(self):
        """Searching 'delayed cerebral ischemia' should find the AHA/ASA SAH guideline."""
        results = search_guidelines("delayed cerebral ischemia")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aha_asa_sah_2023" in ids


class TestRetrieveGuidelineSAH2023:
    """Retrieve tests for every section of the AHA/ASA SAH 2023 guideline."""

    def test_retrieve_initial_assessment(self):
        """Retrieve the initial assessment section of the SAH guideline."""
        result = retrieve_guideline("aha_asa_sah_2023", "initial_assessment")
        assert result.value == "aha_asa_sah_2023/initial_assessment"
        assert "Hunt and Hess" in result.interpretation
        assert result.evidence.source_doi == "10.1161/STR.0000000000000436"

    def test_retrieve_aneurysm_treatment(self):
        """Retrieve the aneurysm treatment section of the SAH guideline."""
        result = retrieve_guideline("aha_asa_sah_2023", "aneurysm_treatment")
        assert result.value == "aha_asa_sah_2023/aneurysm_treatment"
        assert "coiling" in result.interpretation.lower() or "clipping" in result.interpretation.lower()
        assert result.evidence.source_doi == "10.1161/STR.0000000000000436"

    def test_retrieve_medical_management(self):
        """Retrieve the medical management section of the SAH guideline."""
        result = retrieve_guideline("aha_asa_sah_2023", "medical_management")
        assert result.value == "aha_asa_sah_2023/medical_management"
        assert "nimodipine" in result.interpretation.lower() or "Nimodipine" in result.interpretation
        assert result.evidence.source_doi == "10.1161/STR.0000000000000436"

    def test_retrieve_delayed_cerebral_ischemia(self):
        """Retrieve the DCI section of the SAH guideline."""
        result = retrieve_guideline("aha_asa_sah_2023", "delayed_cerebral_ischemia")
        assert result.value == "aha_asa_sah_2023/delayed_cerebral_ischemia"
        assert "DCI" in result.interpretation or "vasospasm" in result.interpretation.lower()
        assert result.evidence.source_doi == "10.1161/STR.0000000000000436"


class TestSearchGuidelinesNAFLD2023:
    """Search tests for the AASLD NAFLD 2023 guideline."""

    def test_search_nafld(self):
        """Searching 'NAFLD' should find the AASLD NAFLD guideline."""
        results = search_guidelines("NAFLD")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aasld_nafld_2023" in ids

    def test_search_fatty_liver(self):
        """Searching 'fatty liver' should find the AASLD NAFLD guideline."""
        results = search_guidelines("fatty liver")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aasld_nafld_2023" in ids

    def test_search_fib4(self):
        """Searching 'FIB-4' should find the AASLD NAFLD guideline."""
        results = search_guidelines("FIB-4")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aasld_nafld_2023" in ids

    def test_search_fibroscan(self):
        """Searching 'FibroScan' should find the AASLD NAFLD guideline."""
        results = search_guidelines("FibroScan")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aasld_nafld_2023" in ids

    def test_search_nash(self):
        """Searching 'NASH' should find the AASLD NAFLD guideline."""
        results = search_guidelines("NASH")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aasld_nafld_2023" in ids


class TestRetrieveGuidelineNAFLD2023:
    """Retrieve tests for every section of the AASLD NAFLD 2023 guideline."""

    def test_retrieve_screening_and_diagnosis(self):
        """Retrieve the screening and diagnosis section of the NAFLD guideline."""
        result = retrieve_guideline("aasld_nafld_2023", "screening_and_diagnosis")
        assert result.value == "aasld_nafld_2023/screening_and_diagnosis"
        assert "steatosis" in result.interpretation.lower()
        assert result.evidence.source_doi == "10.1097/HEP.0000000000000323"

    def test_retrieve_fibrosis_assessment(self):
        """Retrieve the fibrosis assessment section of the NAFLD guideline."""
        result = retrieve_guideline("aasld_nafld_2023", "fibrosis_assessment")
        assert result.value == "aasld_nafld_2023/fibrosis_assessment"
        assert "FIB-4" in result.interpretation
        assert result.evidence.source_doi == "10.1097/HEP.0000000000000323"

    def test_retrieve_lifestyle_and_pharmacotherapy(self):
        """Retrieve the lifestyle and pharmacotherapy section of the NAFLD guideline."""
        result = retrieve_guideline("aasld_nafld_2023", "lifestyle_and_pharmacotherapy")
        assert result.value == "aasld_nafld_2023/lifestyle_and_pharmacotherapy"
        assert "weight loss" in result.interpretation.lower() or "Weight Loss" in result.interpretation
        assert result.evidence.source_doi == "10.1097/HEP.0000000000000323"

    def test_retrieve_monitoring_and_referral(self):
        """Retrieve the monitoring and referral section of the NAFLD guideline."""
        result = retrieve_guideline("aasld_nafld_2023", "monitoring_and_referral")
        assert result.value == "aasld_nafld_2023/monitoring_and_referral"
        assert "hepatology" in result.interpretation.lower() or "referral" in result.interpretation.lower()
        assert result.evidence.source_doi == "10.1097/HEP.0000000000000323"


class TestSearchGuidelinesTIA2009:
    """Search tests for the AHA/ASA TIA 2009 guideline."""

    def test_search_tia(self):
        """Searching 'transient ischemic attack' should find the AHA/ASA TIA guideline."""
        results = search_guidelines("transient ischemic attack")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aha_asa_tia_2009" in ids

    def test_search_abcd2(self):
        """Searching 'ABCD2' should find the AHA/ASA TIA guideline."""
        results = search_guidelines("ABCD2")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aha_asa_tia_2009" in ids

    def test_search_carotid_stenosis(self):
        """Searching 'carotid stenosis' should find the AHA/ASA TIA guideline."""
        results = search_guidelines("carotid stenosis")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aha_asa_tia_2009" in ids

    def test_search_carotid_endarterectomy(self):
        """Searching 'carotid endarterectomy' should find the AHA/ASA TIA guideline."""
        results = search_guidelines("carotid endarterectomy")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aha_asa_tia_2009" in ids


class TestRetrieveGuidelineTIA2009:
    """Retrieve tests for every section of the AHA/ASA TIA 2009 guideline."""

    def test_retrieve_definition_and_risk_stratification(self):
        """Retrieve the definition and risk stratification section of the TIA guideline."""
        result = retrieve_guideline("aha_asa_tia_2009", "definition_and_risk_stratification")
        assert result.value == "aha_asa_tia_2009/definition_and_risk_stratification"
        assert "ABCD2" in result.interpretation
        assert result.evidence.source_doi == "10.1161/STROKEAHA.108.192218"

    def test_retrieve_diagnostic_evaluation(self):
        """Retrieve the diagnostic evaluation section of the TIA guideline."""
        result = retrieve_guideline("aha_asa_tia_2009", "diagnostic_evaluation")
        assert result.value == "aha_asa_tia_2009/diagnostic_evaluation"
        assert "MRI" in result.interpretation or "DWI" in result.interpretation
        assert result.evidence.source_doi == "10.1161/STROKEAHA.108.192218"

    def test_retrieve_early_management(self):
        """Retrieve the early management section of the TIA guideline."""
        result = retrieve_guideline("aha_asa_tia_2009", "early_management")
        assert result.value == "aha_asa_tia_2009/early_management"
        assert "aspirin" in result.interpretation.lower() or "Aspirin" in result.interpretation
        assert result.evidence.source_doi == "10.1161/STROKEAHA.108.192218"


class TestSearchGuidelinesSTEMI2013:
    """Search tests for the ACCF/AHA STEMI 2013 guideline."""

    def test_search_stemi(self):
        """Searching 'STEMI' should find the ACCF/AHA STEMI 2013 guideline."""
        results = search_guidelines("STEMI")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_stemi_2013" in ids

    def test_search_myocardial_infarction(self):
        """Searching 'myocardial infarction' should find the STEMI 2013 guideline."""
        results = search_guidelines("myocardial infarction")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_stemi_2013" in ids

    def test_search_primary_pci(self):
        """Searching 'primary PCI' should find the STEMI 2013 guideline."""
        results = search_guidelines("primary PCI")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_stemi_2013" in ids

    def test_search_fibrinolytic(self):
        """Searching 'fibrinolytic therapy' should find the STEMI 2013 guideline."""
        results = search_guidelines("fibrinolytic therapy")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_stemi_2013" in ids

    def test_search_tenecteplase(self):
        """Searching 'tenecteplase' should find the STEMI 2013 guideline."""
        results = search_guidelines("tenecteplase")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_stemi_2013" in ids

    def test_search_timi_stemi(self):
        """Searching 'TIMI STEMI' should find the STEMI 2013 guideline."""
        results = search_guidelines("TIMI STEMI")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_stemi_2013" in ids

    def test_search_cardiogenic_shock(self):
        """Searching 'cardiogenic shock' should find the STEMI 2013 guideline."""
        results = search_guidelines("cardiogenic shock")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_stemi_2013" in ids

    def test_search_killip_class(self):
        """Searching 'Killip class' should find the STEMI 2013 guideline."""
        results = search_guidelines("Killip class")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_stemi_2013" in ids


class TestRetrieveGuidelineSTEMI2013:
    """Retrieve tests for every section of the ACCF/AHA STEMI 2013 guideline."""

    def test_retrieve_reperfusion_therapy(self):
        """Retrieve the reperfusion therapy section of the STEMI 2013 guideline."""
        result = retrieve_guideline("acc_aha_stemi_2013", "reperfusion_therapy")
        assert result.value == "acc_aha_stemi_2013/reperfusion_therapy"
        assert "90 minutes" in result.interpretation
        assert "tenecteplase" in result.interpretation.lower() or "Tenecteplase" in result.interpretation
        assert result.evidence.source_doi == "10.1161/CIR.0b013e3182742cf6"

    def test_retrieve_antithrombotic_therapy(self):
        """Retrieve the antithrombotic therapy section of the STEMI 2013 guideline."""
        result = retrieve_guideline("acc_aha_stemi_2013", "antithrombotic_therapy")
        assert result.value == "acc_aha_stemi_2013/antithrombotic_therapy"
        assert "Aspirin" in result.interpretation
        assert "clopidogrel" in result.interpretation.lower() or "Clopidogrel" in result.interpretation
        assert result.evidence.source_doi == "10.1161/CIR.0b013e3182742cf6"

    def test_retrieve_routine_medical_therapy(self):
        """Retrieve the routine medical therapy section of the STEMI 2013 guideline."""
        result = retrieve_guideline("acc_aha_stemi_2013", "routine_medical_therapy")
        assert result.value == "acc_aha_stemi_2013/routine_medical_therapy"
        assert "beta-blocker" in result.interpretation.lower() or "Beta-Blocker" in result.interpretation or "metoprolol" in result.interpretation.lower()
        assert result.evidence.source_doi == "10.1161/CIR.0b013e3182742cf6"

    def test_retrieve_complications(self):
        """Retrieve the complications section of the STEMI 2013 guideline."""
        result = retrieve_guideline("acc_aha_stemi_2013", "complications")
        assert result.value == "acc_aha_stemi_2013/complications"
        assert "Killip" in result.interpretation
        assert "cardiogenic shock" in result.interpretation.lower() or "Cardiogenic" in result.interpretation
        assert result.evidence.source_doi == "10.1161/CIR.0b013e3182742cf6"


class TestSearchGuidelinesHypertension2017:
    """Search tests for the ACC/AHA Hypertension 2017 guideline."""

    def test_search_hypertension(self):
        """Searching 'hypertension' should find the ACC/AHA Hypertension 2017 guideline."""
        results = search_guidelines("hypertension")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_hypertension_2017" in ids

    def test_search_blood_pressure(self):
        """Searching 'blood pressure' should find the ACC/AHA Hypertension 2017 guideline."""
        results = search_guidelines("blood pressure")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_hypertension_2017" in ids

    def test_search_antihypertensive(self):
        """Searching 'antihypertensive' should find the ACC/AHA Hypertension 2017 guideline."""
        results = search_guidelines("antihypertensive")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_hypertension_2017" in ids

    def test_search_chlorthalidone(self):
        """Searching 'chlorthalidone' should find the ACC/AHA Hypertension 2017 guideline."""
        results = search_guidelines("chlorthalidone")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_hypertension_2017" in ids

    def test_search_dash_diet(self):
        """Searching 'DASH diet' should find the ACC/AHA Hypertension 2017 guideline."""
        results = search_guidelines("DASH diet")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_hypertension_2017" in ids

    def test_search_resistant_hypertension(self):
        """Searching 'resistant hypertension' should find the ACC/AHA Hypertension 2017 guideline."""
        results = search_guidelines("resistant hypertension")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_hypertension_2017" in ids

    def test_search_hypertensive_emergency(self):
        """Searching 'hypertensive emergency' should find the ACC/AHA Hypertension 2017 guideline."""
        results = search_guidelines("hypertensive emergency")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_hypertension_2017" in ids

    def test_search_abpm(self):
        """Searching 'ABPM' should find the ACC/AHA Hypertension 2017 guideline."""
        results = search_guidelines("ABPM")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_hypertension_2017" in ids


class TestRetrieveGuidelineHypertension2017:
    """Retrieve tests for every section of the ACC/AHA Hypertension 2017 guideline."""

    def test_retrieve_classification_and_measurement(self):
        """Retrieve the classification and measurement section of the Hypertension 2017 guideline."""
        result = retrieve_guideline("acc_aha_hypertension_2017", "classification_and_measurement")
        assert result.value == "acc_aha_hypertension_2017/classification_and_measurement"
        assert "Stage 1" in result.interpretation
        assert "130" in result.interpretation
        assert result.evidence.source_doi == "10.1161/HYP.0000000000000065"

    def test_retrieve_nonpharmacologic_interventions(self):
        """Retrieve the nonpharmacologic interventions section of the Hypertension 2017 guideline."""
        result = retrieve_guideline("acc_aha_hypertension_2017", "nonpharmacologic_interventions")
        assert result.value == "acc_aha_hypertension_2017/nonpharmacologic_interventions"
        assert "DASH" in result.interpretation
        assert "sodium" in result.interpretation.lower()
        assert result.evidence.source_doi == "10.1161/HYP.0000000000000065"

    def test_retrieve_pharmacotherapy(self):
        """Retrieve the pharmacotherapy section of the Hypertension 2017 guideline."""
        result = retrieve_guideline("acc_aha_hypertension_2017", "pharmacotherapy")
        assert result.value == "acc_aha_hypertension_2017/pharmacotherapy"
        assert "Chlorthalidone" in result.interpretation or "chlorthalidone" in result.interpretation.lower()
        assert "ACE" in result.interpretation
        assert result.evidence.source_doi == "10.1161/HYP.0000000000000065"

    def test_retrieve_resistant_hypertension_and_crises(self):
        """Retrieve the resistant hypertension and crises section of the Hypertension 2017 guideline."""
        result = retrieve_guideline("acc_aha_hypertension_2017", "resistant_hypertension_and_crises")
        assert result.value == "acc_aha_hypertension_2017/resistant_hypertension_and_crises"
        assert "180/120" in result.interpretation
        assert "Spironolactone" in result.interpretation or "spironolactone" in result.interpretation.lower()
        assert result.evidence.source_doi == "10.1161/HYP.0000000000000065"


class TestSearchGuidelinesCholesterol2018:
    """Search tests for the ACC/AHA Cholesterol 2018 guideline."""

    def test_search_cholesterol(self):
        """Searching 'cholesterol' should find the ACC/AHA Cholesterol 2018 guideline."""
        results = search_guidelines("cholesterol")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_cholesterol_2018" in ids

    def test_search_statin(self):
        """Searching 'statin' should find the ACC/AHA Cholesterol 2018 guideline."""
        results = search_guidelines("statin")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_cholesterol_2018" in ids

    def test_search_ldl(self):
        """Searching 'LDL-C' should find the ACC/AHA Cholesterol 2018 guideline."""
        results = search_guidelines("LDL-C")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_cholesterol_2018" in ids

    def test_search_ezetimibe(self):
        """Searching 'ezetimibe' should find the ACC/AHA Cholesterol 2018 guideline."""
        results = search_guidelines("ezetimibe")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_cholesterol_2018" in ids

    def test_search_pcsk9(self):
        """Searching 'PCSK9 inhibitor' should find the ACC/AHA Cholesterol 2018 guideline."""
        results = search_guidelines("PCSK9 inhibitor")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_cholesterol_2018" in ids

    def test_search_atorvastatin(self):
        """Searching 'atorvastatin' should find the ACC/AHA Cholesterol 2018 guideline."""
        results = search_guidelines("atorvastatin")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_cholesterol_2018" in ids

    def test_search_hyperlipidemia(self):
        """Searching 'hyperlipidemia' should find the ACC/AHA Cholesterol 2018 guideline."""
        results = search_guidelines("hyperlipidemia")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_cholesterol_2018" in ids

    def test_search_cac_score(self):
        """Searching 'CAC score' should find the ACC/AHA Cholesterol 2018 guideline."""
        results = search_guidelines("CAC score")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_cholesterol_2018" in ids

    def test_search_familial_hypercholesterolemia(self):
        """Searching 'familial hypercholesterolemia' should find the ACC/AHA Cholesterol 2018 guideline."""
        results = search_guidelines("familial hypercholesterolemia")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_cholesterol_2018" in ids


class TestRetrieveGuidelineCholesterol2018:
    """Retrieve tests for every section of the ACC/AHA Cholesterol 2018 guideline."""

    def test_retrieve_risk_assessment(self):
        """Retrieve the risk assessment section of the Cholesterol 2018 guideline."""
        result = retrieve_guideline("acc_aha_cholesterol_2018", "risk_assessment")
        assert result.value == "acc_aha_cholesterol_2018/risk_assessment"
        assert "ASCVD" in result.interpretation
        assert "7.5%" in result.interpretation or "7.5" in result.interpretation
        assert result.evidence.source_doi == "10.1016/j.jacc.2018.11.003"

    def test_retrieve_statin_therapy(self):
        """Retrieve the statin therapy section of the Cholesterol 2018 guideline."""
        result = retrieve_guideline("acc_aha_cholesterol_2018", "statin_therapy")
        assert result.value == "acc_aha_cholesterol_2018/statin_therapy"
        assert "Atorvastatin" in result.interpretation
        assert "Rosuvastatin" in result.interpretation
        assert "high-intensity" in result.interpretation.lower() or "High-Intensity" in result.interpretation
        assert result.evidence.source_doi == "10.1016/j.jacc.2018.11.003"

    def test_retrieve_secondary_prevention(self):
        """Retrieve the secondary prevention section of the Cholesterol 2018 guideline."""
        result = retrieve_guideline("acc_aha_cholesterol_2018", "secondary_prevention")
        assert result.value == "acc_aha_cholesterol_2018/secondary_prevention"
        assert "70 mg/dL" in result.interpretation
        assert "ezetimibe" in result.interpretation.lower() or "Ezetimibe" in result.interpretation
        assert result.evidence.source_doi == "10.1016/j.jacc.2018.11.003"

    def test_retrieve_nonstatin_therapy(self):
        """Retrieve the nonstatin therapy section of the Cholesterol 2018 guideline."""
        result = retrieve_guideline("acc_aha_cholesterol_2018", "nonstatin_therapy")
        assert result.value == "acc_aha_cholesterol_2018/nonstatin_therapy"
        assert "PCSK9" in result.interpretation
        assert "ezetimibe" in result.interpretation.lower() or "Ezetimibe" in result.interpretation
        assert result.evidence.source_doi == "10.1016/j.jacc.2018.11.003"


class TestSearchGuidelinesATSIDSACAP2019:
    """Search tests for the ATS/IDSA CAP 2019 guideline."""

    def test_search_cap(self):
        """Searching 'community acquired pneumonia' should find the ATS/IDSA CAP 2019 guideline."""
        results = search_guidelines("community acquired pneumonia")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ats_idsa_cap_2019" in ids

    def test_search_cap_abbreviation(self):
        """Searching 'CAP' should find the ATS/IDSA CAP 2019 guideline."""
        results = search_guidelines("CAP")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ats_idsa_cap_2019" in ids

    def test_search_psi(self):
        """Searching 'Pneumonia Severity Index' should find the ATS/IDSA CAP 2019 guideline."""
        results = search_guidelines("Pneumonia Severity Index")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ats_idsa_cap_2019" in ids

    def test_search_mrsa_pneumonia(self):
        """Searching 'MRSA' should find the ATS/IDSA CAP 2019 guideline."""
        results = search_guidelines("MRSA")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ats_idsa_cap_2019" in ids

    def test_search_pseudomonas(self):
        """Searching 'Pseudomonas aeruginosa' should find the ATS/IDSA CAP 2019 guideline."""
        results = search_guidelines("Pseudomonas aeruginosa")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ats_idsa_cap_2019" in ids

    def test_search_procalcitonin(self):
        """Searching 'procalcitonin' should find the ATS/IDSA CAP 2019 guideline."""
        results = search_guidelines("procalcitonin")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ats_idsa_cap_2019" in ids

    def test_search_levofloxacin(self):
        """Searching 'levofloxacin' should find the ATS/IDSA CAP 2019 guideline."""
        results = search_guidelines("levofloxacin")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ats_idsa_cap_2019" in ids

    def test_search_oseltamivir(self):
        """Searching 'oseltamivir' should find the ATS/IDSA CAP 2019 guideline."""
        results = search_guidelines("oseltamivir")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ats_idsa_cap_2019" in ids


class TestRetrieveGuidelineATSIDSACAP2019:
    """Retrieve tests for every section of the ATS/IDSA CAP 2019 guideline."""

    def test_retrieve_severity_assessment(self):
        """Retrieve the severity assessment section of the ATS/IDSA CAP 2019 guideline."""
        result = retrieve_guideline("ats_idsa_cap_2019", "severity_assessment")
        assert result.value == "ats_idsa_cap_2019/severity_assessment"
        assert "PSI" in result.interpretation
        assert "CURB-65" in result.interpretation
        assert "septic shock" in result.interpretation.lower() or "Septic shock" in result.interpretation
        assert result.evidence.source_doi == "10.1164/rccm.201908-1581ST"

    def test_retrieve_empiric_antibiotic_therapy(self):
        """Retrieve the empiric antibiotic therapy section of the ATS/IDSA CAP 2019 guideline."""
        result = retrieve_guideline("ats_idsa_cap_2019", "empiric_antibiotic_therapy")
        assert result.value == "ats_idsa_cap_2019/empiric_antibiotic_therapy"
        assert "Amoxicillin" in result.interpretation
        assert "ceftriaxone" in result.interpretation.lower() or "Ceftriaxone" in result.interpretation
        assert "5 days" in result.interpretation
        assert result.evidence.source_doi == "10.1164/rccm.201908-1581ST"

    def test_retrieve_microbiological_testing(self):
        """Retrieve the microbiological testing section of the ATS/IDSA CAP 2019 guideline."""
        result = retrieve_guideline("ats_idsa_cap_2019", "microbiological_testing")
        assert result.value == "ats_idsa_cap_2019/microbiological_testing"
        assert "procalcitonin" in result.interpretation.lower() or "Procalcitonin" in result.interpretation
        assert "sputum" in result.interpretation.lower()
        assert "Legionella" in result.interpretation
        assert result.evidence.source_doi == "10.1164/rccm.201908-1581ST"

    def test_retrieve_special_populations_and_follow_up(self):
        """Retrieve the special populations and follow-up section of the ATS/IDSA CAP 2019 guideline."""
        result = retrieve_guideline("ats_idsa_cap_2019", "special_populations_and_follow_up")
        assert result.value == "ats_idsa_cap_2019/special_populations_and_follow_up"
        assert "oseltamivir" in result.interpretation.lower() or "Oseltamivir" in result.interpretation
        assert "corticosteroid" in result.interpretation.lower() or "Corticosteroid" in result.interpretation
        assert result.evidence.source_doi == "10.1164/rccm.201908-1581ST"


class TestSearchGuidelinesSSCSepsis2021:
    """Search tests for the SSC Sepsis 2021 guideline."""

    def test_search_sepsis(self):
        """Searching 'sepsis' should find the SSC Sepsis 2021 guideline."""
        results = search_guidelines("sepsis")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ssc_sepsis_2021" in ids

    def test_search_septic_shock(self):
        """Searching 'septic shock' should find the SSC Sepsis 2021 guideline."""
        results = search_guidelines("septic shock")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ssc_sepsis_2021" in ids

    def test_search_surviving_sepsis_campaign(self):
        """Searching 'surviving sepsis campaign' should find the SSC Sepsis 2021 guideline."""
        results = search_guidelines("surviving sepsis campaign")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ssc_sepsis_2021" in ids

    def test_search_norepinephrine(self):
        """Searching 'norepinephrine' should find the SSC Sepsis 2021 guideline."""
        results = search_guidelines("norepinephrine")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ssc_sepsis_2021" in ids

    def test_search_vasopressor(self):
        """Searching 'vasopressor' should find the SSC Sepsis 2021 guideline."""
        results = search_guidelines("vasopressor")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ssc_sepsis_2021" in ids

    def test_search_hydrocortisone(self):
        """Searching 'hydrocortisone' should find the SSC Sepsis 2021 guideline."""
        results = search_guidelines("hydrocortisone")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ssc_sepsis_2021" in ids

    def test_search_lactate(self):
        """Searching 'lactate' should find the SSC Sepsis 2021 guideline."""
        results = search_guidelines("lactate")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ssc_sepsis_2021" in ids

    def test_search_antimicrobial_therapy(self):
        """Searching 'antimicrobial therapy' should find the SSC Sepsis 2021 guideline."""
        results = search_guidelines("antimicrobial therapy")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ssc_sepsis_2021" in ids

    def test_search_fluid_resuscitation(self):
        """Searching 'fluid resuscitation' should find the SSC Sepsis 2021 guideline."""
        results = search_guidelines("fluid resuscitation")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ssc_sepsis_2021" in ids

    def test_search_prone_positioning(self):
        """Searching 'prone positioning' should find the SSC Sepsis 2021 guideline."""
        results = search_guidelines("prone positioning")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ssc_sepsis_2021" in ids


class TestRetrieveGuidelineSSCSepsis2021:
    """Retrieve tests for every section of the SSC Sepsis 2021 guideline."""

    def test_retrieve_screening_and_early_management(self):
        """Retrieve the screening and early management section of the SSC Sepsis 2021 guideline."""
        result = retrieve_guideline("ssc_sepsis_2021", "screening_and_early_management")
        assert result.value == "ssc_sepsis_2021/screening_and_early_management"
        assert "qSOFA" in result.interpretation
        assert "30 mL/kg" in result.interpretation
        assert "lactate" in result.interpretation.lower()
        assert result.evidence.source_doi == "10.1007/s00134-021-06506-y"

    def test_retrieve_antimicrobial_therapy(self):
        """Retrieve the antimicrobial therapy section of the SSC Sepsis 2021 guideline."""
        result = retrieve_guideline("ssc_sepsis_2021", "antimicrobial_therapy")
        assert result.value == "ssc_sepsis_2021/antimicrobial_therapy"
        assert "1 hour" in result.interpretation
        assert "source control" in result.interpretation.lower()
        assert "de-escalation" in result.interpretation.lower()
        assert result.evidence.source_doi == "10.1007/s00134-021-06506-y"

    def test_retrieve_hemodynamics_and_vasopressors(self):
        """Retrieve the hemodynamics and vasopressors section of the SSC Sepsis 2021 guideline."""
        result = retrieve_guideline("ssc_sepsis_2021", "hemodynamics_and_vasopressors")
        assert result.value == "ssc_sepsis_2021/hemodynamics_and_vasopressors"
        assert "norepinephrine" in result.interpretation.lower() or "Norepinephrine" in result.interpretation
        assert "65 mmHg" in result.interpretation
        assert "vasopressin" in result.interpretation.lower() or "Vasopressin" in result.interpretation
        assert "hydrocortisone" in result.interpretation.lower() or "Hydrocortisone" in result.interpretation
        assert result.evidence.source_doi == "10.1007/s00134-021-06506-y"

    def test_retrieve_ventilation_and_supportive_care(self):
        """Retrieve the ventilation and supportive care section of the SSC Sepsis 2021 guideline."""
        result = retrieve_guideline("ssc_sepsis_2021", "ventilation_and_supportive_care")
        assert result.value == "ssc_sepsis_2021/ventilation_and_supportive_care"
        assert "6 mL/kg" in result.interpretation
        assert "prone" in result.interpretation.lower()
        assert "7.0 g/dL" in result.interpretation
        assert result.evidence.source_doi == "10.1007/s00134-021-06506-y"


class TestSearchGuidelinesKDIGOAKI2012:
    """Search tests for the KDIGO AKI 2012 guideline."""

    def test_search_acute_kidney_injury(self):
        """Searching 'acute kidney injury' should find the KDIGO AKI 2012 guideline."""
        results = search_guidelines("acute kidney injury")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "kdigo_aki_2012" in ids

    def test_search_aki(self):
        """Searching 'AKI' should find the KDIGO AKI 2012 guideline."""
        results = search_guidelines("AKI")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "kdigo_aki_2012" in ids

    def test_search_contrast_nephropathy(self):
        """Searching 'contrast nephropathy' should find the KDIGO AKI 2012 guideline."""
        results = search_guidelines("contrast nephropathy")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "kdigo_aki_2012" in ids

    def test_search_crrt(self):
        """Searching 'CRRT' should find the KDIGO AKI 2012 guideline."""
        results = search_guidelines("CRRT")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "kdigo_aki_2012" in ids

    def test_search_renal_replacement_therapy(self):
        """Searching 'renal replacement therapy' should find the KDIGO AKI 2012 guideline."""
        results = search_guidelines("renal replacement therapy")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "kdigo_aki_2012" in ids

    def test_search_oliguria(self):
        """Searching 'oliguria' should find the KDIGO AKI 2012 guideline."""
        results = search_guidelines("oliguria")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "kdigo_aki_2012" in ids

    def test_search_nephrotoxic(self):
        """Searching 'nephrotoxic' should find the KDIGO AKI 2012 guideline."""
        results = search_guidelines("nephrotoxic")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "kdigo_aki_2012" in ids

    def test_search_citrate_anticoagulation(self):
        """Searching 'citrate anticoagulation' should find the KDIGO AKI 2012 guideline."""
        results = search_guidelines("citrate anticoagulation")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "kdigo_aki_2012" in ids


class TestRetrieveGuidelineKDIGOAKI2012:
    """Retrieve tests for every section of the KDIGO AKI 2012 guideline."""

    def test_retrieve_definition_and_staging(self):
        """Retrieve the definition and staging section of the KDIGO AKI 2012 guideline."""
        result = retrieve_guideline("kdigo_aki_2012", "definition_and_staging")
        assert result.value == "kdigo_aki_2012/definition_and_staging"
        assert "0.3 mg/dL" in result.interpretation
        assert "Stage 1" in result.interpretation
        assert "Stage 2" in result.interpretation
        assert "Stage 3" in result.interpretation
        assert result.evidence.source_doi == "10.1038/kisup.2012.1"

    def test_retrieve_prevention_and_general_management(self):
        """Retrieve the prevention and general management section of the KDIGO AKI 2012 guideline."""
        result = retrieve_guideline("kdigo_aki_2012", "prevention_and_general_management")
        assert result.value == "kdigo_aki_2012/prevention_and_general_management"
        assert "isotonic crystalloid" in result.interpretation.lower() or "isotonic crystalloids" in result.interpretation
        assert "dopamine" in result.interpretation.lower() or "Dopamine" in result.interpretation
        assert "110-149 mg/dL" in result.interpretation
        assert result.evidence.source_doi == "10.1038/kisup.2012.1"

    def test_retrieve_contrast_induced_aki(self):
        """Retrieve the contrast-induced AKI section of the KDIGO AKI 2012 guideline."""
        result = retrieve_guideline("kdigo_aki_2012", "contrast_induced_aki")
        assert result.value == "kdigo_aki_2012/contrast_induced_aki"
        assert "CI-AKI" in result.interpretation
        assert "iso-osmolar" in result.interpretation.lower() or "low-osmolar" in result.interpretation.lower()
        assert "NAC" in result.interpretation
        assert result.evidence.source_doi == "10.1038/kisup.2012.1"

    def test_retrieve_renal_replacement_therapy(self):
        """Retrieve the renal replacement therapy section of the KDIGO AKI 2012 guideline."""
        result = retrieve_guideline("kdigo_aki_2012", "renal_replacement_therapy")
        assert result.value == "kdigo_aki_2012/renal_replacement_therapy"
        assert "20-25 mL/kg/h" in result.interpretation
        assert "citrate" in result.interpretation.lower()
        assert "Kt/V" in result.interpretation
        assert "3.9" in result.interpretation
        assert result.evidence.source_doi == "10.1038/kisup.2012.1"


class TestSearchGuidelinesADADKAHHS2024:
    """Search tests for the ADA DKA/HHS 2024 consensus report."""

    def test_search_diabetic_ketoacidosis(self):
        """Searching 'diabetic ketoacidosis' should find the ADA DKA/HHS 2024 guideline."""
        results = search_guidelines("diabetic ketoacidosis")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ada_dka_hhs_2024" in ids

    def test_search_dka(self):
        """Searching 'DKA' should find the ADA DKA/HHS 2024 guideline."""
        results = search_guidelines("DKA")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ada_dka_hhs_2024" in ids

    def test_search_hhs(self):
        """Searching 'hyperglycemic hyperosmolar state' should find the ADA DKA/HHS 2024 guideline."""
        results = search_guidelines("hyperglycemic hyperosmolar state")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ada_dka_hhs_2024" in ids

    def test_search_euglycemic_dka(self):
        """Searching 'euglycemic DKA' should find the ADA DKA/HHS 2024 guideline."""
        results = search_guidelines("euglycemic DKA")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ada_dka_hhs_2024" in ids

    def test_search_insulin_infusion(self):
        """Searching 'insulin infusion' should find the ADA DKA/HHS 2024 guideline."""
        results = search_guidelines("insulin infusion")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ada_dka_hhs_2024" in ids

    def test_search_beta_hydroxybutyrate(self):
        """Searching 'beta-hydroxybutyrate' should find the ADA DKA/HHS 2024 guideline."""
        results = search_guidelines("beta-hydroxybutyrate")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ada_dka_hhs_2024" in ids

    def test_search_potassium_replacement(self):
        """Searching 'potassium replacement' should find the ADA DKA/HHS 2024 guideline."""
        results = search_guidelines("potassium replacement")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ada_dka_hhs_2024" in ids

    def test_search_corrected_sodium(self):
        """Searching 'corrected sodium' should find the ADA DKA/HHS 2024 guideline."""
        results = search_guidelines("corrected sodium")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "ada_dka_hhs_2024" in ids


class TestRetrieveGuidelineADADKAHHS2024:
    """Retrieve tests for every section of the ADA DKA/HHS 2024 guideline."""

    def test_retrieve_diagnosis(self):
        """Retrieve the diagnosis section of the ADA DKA/HHS 2024 guideline."""
        result = retrieve_guideline("ada_dka_hhs_2024", "diagnosis")
        assert result.value == "ada_dka_hhs_2024/diagnosis"
        assert "beta-hydroxybutyrate" in result.interpretation.lower() or "Beta-Hydroxybutyrate" in result.interpretation
        assert "200 mg/dL" in result.interpretation
        assert "pH" in result.interpretation
        assert "osmolality" in result.interpretation.lower() or "Osmolality" in result.interpretation
        assert result.evidence.source_doi == "10.2337/dci24-0032"

    def test_retrieve_fluid_resuscitation(self):
        """Retrieve the fluid resuscitation section of the ADA DKA/HHS 2024 guideline."""
        result = retrieve_guideline("ada_dka_hhs_2024", "fluid_resuscitation")
        assert result.value == "ada_dka_hhs_2024/fluid_resuscitation"
        assert "500" in result.interpretation
        assert "1,000 mL" in result.interpretation or "1000 mL" in result.interpretation
        assert "250 mg/dL" in result.interpretation
        assert "dextrose" in result.interpretation.lower() or "Dextrose" in result.interpretation
        assert result.evidence.source_doi == "10.2337/dci24-0032"

    def test_retrieve_insulin_and_electrolytes(self):
        """Retrieve the insulin and electrolytes section of the ADA DKA/HHS 2024 guideline."""
        result = retrieve_guideline("ada_dka_hhs_2024", "insulin_and_electrolytes")
        assert result.value == "ada_dka_hhs_2024/insulin_and_electrolytes"
        assert "0.1 units/kg" in result.interpretation
        assert "potassium" in result.interpretation.lower() or "Potassium" in result.interpretation
        assert "3.5" in result.interpretation
        assert "bicarbonate" in result.interpretation.lower() or "Bicarbonate" in result.interpretation
        assert result.evidence.source_doi == "10.2337/dci24-0032"

    def test_retrieve_resolution_and_transition(self):
        """Retrieve the resolution and transition section of the ADA DKA/HHS 2024 guideline."""
        result = retrieve_guideline("ada_dka_hhs_2024", "resolution_and_transition")
        assert result.value == "ada_dka_hhs_2024/resolution_and_transition"
        assert "0.6 mmol/L" in result.interpretation
        assert "1-2 hours" in result.interpretation
        assert "0.5" in result.interpretation
        assert "sick day" in result.interpretation.lower() or "Sick" in result.interpretation
        assert result.evidence.source_doi == "10.2337/dci24-0032"


class TestSearchGuidelinesGINAAsthma2024:
    """Search tests for the GINA Asthma 2024 guideline."""

    def test_search_asthma(self):
        """Searching 'asthma' should find the GINA Asthma 2024 guideline."""
        results = search_guidelines("asthma")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "gina_asthma_2024" in ids

    def test_search_gina(self):
        """Searching 'GINA' should find the GINA Asthma 2024 guideline."""
        results = search_guidelines("GINA")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "gina_asthma_2024" in ids

    def test_search_ics_formoterol(self):
        """Searching 'ICS-formoterol' should find the GINA Asthma 2024 guideline."""
        results = search_guidelines("ICS-formoterol")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "gina_asthma_2024" in ids

    def test_search_budesonide(self):
        """Searching 'budesonide' should find the GINA Asthma 2024 guideline."""
        results = search_guidelines("budesonide")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "gina_asthma_2024" in ids

    def test_search_severe_asthma(self):
        """Searching 'severe asthma' should find the GINA Asthma 2024 guideline."""
        results = search_guidelines("severe asthma")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "gina_asthma_2024" in ids

    def test_search_omalizumab(self):
        """Searching 'omalizumab' should find the GINA Asthma 2024 guideline."""
        results = search_guidelines("omalizumab")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "gina_asthma_2024" in ids

    def test_search_tezepelumab(self):
        """Searching 'tezepelumab' should find the GINA Asthma 2024 guideline."""
        results = search_guidelines("tezepelumab")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "gina_asthma_2024" in ids

    def test_search_mart(self):
        """Searching 'maintenance and reliever therapy' should find the GINA Asthma 2024 guideline."""
        results = search_guidelines("maintenance and reliever therapy")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "gina_asthma_2024" in ids

    def test_search_exercise_induced_bronchoconstriction(self):
        """Searching 'exercise-induced bronchoconstriction' should find the GINA Asthma 2024 guideline."""
        results = search_guidelines("exercise-induced bronchoconstriction")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "gina_asthma_2024" in ids

    def test_search_wheezing(self):
        """Searching 'wheezing' should find the GINA Asthma 2024 guideline."""
        results = search_guidelines("wheezing")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "gina_asthma_2024" in ids


class TestRetrieveGuidelineGINAAsthma2024:
    """Retrieve tests for every section of the GINA Asthma 2024 guideline."""

    def test_retrieve_diagnosis_and_assessment(self):
        """Retrieve the diagnosis and assessment section of the GINA Asthma 2024 guideline."""
        result = retrieve_guideline("gina_asthma_2024", "diagnosis_and_assessment")
        assert result.value == "gina_asthma_2024/diagnosis_and_assessment"
        assert "FEV1" in result.interpretation
        assert "bronchodilator" in result.interpretation.lower()
        assert "spirometry" in result.interpretation.lower() or "Spirometry" in result.interpretation
        assert result.evidence.source_doi == "10.1183/13993003.00735-2024"

    def test_retrieve_pharmacotherapy(self):
        """Retrieve the pharmacotherapy section of the GINA Asthma 2024 guideline."""
        result = retrieve_guideline("gina_asthma_2024", "pharmacotherapy")
        assert result.value == "gina_asthma_2024/pharmacotherapy"
        assert "Track 1" in result.interpretation
        assert "ICS-formoterol" in result.interpretation or "ICS-Formoterol" in result.interpretation
        assert "MART" in result.interpretation
        assert "Step 1" in result.interpretation
        assert result.evidence.source_doi == "10.1183/13993003.00735-2024"

    def test_retrieve_acute_exacerbation_management(self):
        """Retrieve the acute exacerbation management section of the GINA Asthma 2024 guideline."""
        result = retrieve_guideline("gina_asthma_2024", "acute_exacerbation_management")
        assert result.value == "gina_asthma_2024/acute_exacerbation_management"
        assert "salbutamol" in result.interpretation.lower() or "Salbutamol" in result.interpretation
        assert "prednisolone" in result.interpretation.lower() or "Prednisolone" in result.interpretation
        assert "ipratropium" in result.interpretation.lower() or "Ipratropium" in result.interpretation
        assert "40-50 mg" in result.interpretation
        assert result.evidence.source_doi == "10.1183/13993003.00735-2024"

    def test_retrieve_severe_asthma_and_biologics(self):
        """Retrieve the severe asthma and biologics section of the GINA Asthma 2024 guideline."""
        result = retrieve_guideline("gina_asthma_2024", "severe_asthma_and_biologics")
        assert result.value == "gina_asthma_2024/severe_asthma_and_biologics"
        assert "omalizumab" in result.interpretation.lower() or "Omalizumab" in result.interpretation
        assert "mepolizumab" in result.interpretation.lower() or "Mepolizumab" in result.interpretation
        assert "dupilumab" in result.interpretation.lower() or "Dupilumab" in result.interpretation
        assert "tezepelumab" in result.interpretation.lower() or "Tezepelumab" in result.interpretation
        assert "T2" in result.interpretation
        assert result.evidence.source_doi == "10.1183/13993003.00735-2024"


class TestSearchGuidelinesICH2022:
    """Search tests for the AHA/ASA ICH 2022 guideline."""

    def test_search_intracerebral_hemorrhage(self):
        """Searching 'intracerebral hemorrhage' should find the AHA/ASA ICH 2022 guideline."""
        results = search_guidelines("intracerebral hemorrhage")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aha_asa_ich_2022" in ids

    def test_search_ich(self):
        """Searching 'ICH' should find the AHA/ASA ICH 2022 guideline."""
        results = search_guidelines("ICH")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aha_asa_ich_2022" in ids

    def test_search_hemorrhagic_stroke(self):
        """Searching 'hemorrhagic stroke' should find the AHA/ASA ICH 2022 guideline."""
        results = search_guidelines("hemorrhagic stroke")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aha_asa_ich_2022" in ids

    def test_search_hematoma_expansion(self):
        """Searching 'hematoma expansion' should find the AHA/ASA ICH 2022 guideline."""
        results = search_guidelines("hematoma expansion")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aha_asa_ich_2022" in ids

    def test_search_anticoagulant_reversal(self):
        """Searching 'anticoagulant reversal' should find the AHA/ASA ICH 2022 guideline."""
        results = search_guidelines("anticoagulant reversal")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aha_asa_ich_2022" in ids

    def test_search_idarucizumab(self):
        """Searching 'idarucizumab' should find the AHA/ASA ICH 2022 guideline."""
        results = search_guidelines("idarucizumab")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aha_asa_ich_2022" in ids

    def test_search_andexanet_alfa(self):
        """Searching 'andexanet alfa' should find the AHA/ASA ICH 2022 guideline."""
        results = search_guidelines("andexanet alfa")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aha_asa_ich_2022" in ids

    def test_search_cerebellar_hemorrhage(self):
        """Searching 'cerebellar hemorrhage' should find the AHA/ASA ICH 2022 guideline."""
        results = search_guidelines("cerebellar hemorrhage")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aha_asa_ich_2022" in ids

    def test_search_4factor_pcc(self):
        """Searching '4-factor PCC' should find the AHA/ASA ICH 2022 guideline."""
        results = search_guidelines("4-factor PCC")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aha_asa_ich_2022" in ids

    def test_search_minimally_invasive_surgery(self):
        """Searching 'minimally invasive surgery' should find the AHA/ASA ICH 2022 guideline."""
        results = search_guidelines("minimally invasive surgery")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "aha_asa_ich_2022" in ids


class TestRetrieveGuidelineICH2022:
    """Retrieve tests for every section of the AHA/ASA ICH 2022 guideline."""

    def test_retrieve_emergency_diagnosis_assessment(self):
        """Retrieve the emergency diagnosis and assessment section of the ICH 2022 guideline."""
        result = retrieve_guideline("aha_asa_ich_2022", "emergency_diagnosis_assessment")
        assert result.value == "aha_asa_ich_2022/emergency_diagnosis_assessment"
        assert "NIHSS" in result.interpretation
        assert "GCS" in result.interpretation
        assert "ICH Score" in result.interpretation
        assert "spot sign" in result.interpretation.lower() or "Spot Sign" in result.interpretation
        assert result.evidence.source_doi == "10.1161/STR.0000000000000407"

    def test_retrieve_blood_pressure_management(self):
        """Retrieve the blood pressure management section of the ICH 2022 guideline."""
        result = retrieve_guideline("aha_asa_ich_2022", "blood_pressure_management")
        assert result.value == "aha_asa_ich_2022/blood_pressure_management"
        assert "140 mmHg" in result.interpretation
        assert "150" in result.interpretation
        assert "nicardipine" in result.interpretation.lower() or "Nicardipine" in result.interpretation
        assert "labetalol" in result.interpretation.lower() or "Labetalol" in result.interpretation
        assert result.evidence.source_doi == "10.1161/STR.0000000000000407"

    def test_retrieve_hemostatic_therapy(self):
        """Retrieve the hemostatic therapy section of the ICH 2022 guideline."""
        result = retrieve_guideline("aha_asa_ich_2022", "hemostatic_therapy")
        assert result.value == "aha_asa_ich_2022/hemostatic_therapy"
        assert "4-factor PCC" in result.interpretation or "4F-PCC" in result.interpretation
        assert "idarucizumab" in result.interpretation.lower() or "Idarucizumab" in result.interpretation
        assert "andexanet alfa" in result.interpretation.lower() or "Andexanet" in result.interpretation
        assert "vitamin K" in result.interpretation.lower() or "Vitamin K" in result.interpretation
        assert result.evidence.source_doi == "10.1161/STR.0000000000000407"

    def test_retrieve_surgical_and_icu_management(self):
        """Retrieve the surgical and ICU management section of the ICH 2022 guideline."""
        result = retrieve_guideline("aha_asa_ich_2022", "surgical_and_icu_management")
        assert result.value == "aha_asa_ich_2022/surgical_and_icu_management"
        assert "15 mL" in result.interpretation
        assert "cerebellar" in result.interpretation.lower() or "Cerebellar" in result.interpretation
        assert "EVD" in result.interpretation
        assert "GCS" in result.interpretation or "minimally invasive" in result.interpretation.lower()
        assert result.evidence.source_doi == "10.1161/STR.0000000000000407"


class TestSearchGuidelinesBTFTBI2016:
    """Search tests for the BTF TBI 2016 guideline."""

    def test_search_traumatic_brain_injury(self):
        """Searching 'traumatic brain injury' should find the BTF TBI 2016 guideline."""
        results = search_guidelines("traumatic brain injury")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "btf_tbi_2016" in ids

    def test_search_icp_monitoring(self):
        """Searching 'ICP monitoring' should find the BTF TBI 2016 guideline."""
        results = search_guidelines("ICP monitoring")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "btf_tbi_2016" in ids

    def test_search_cerebral_perfusion_pressure(self):
        """Searching 'cerebral perfusion pressure' should find the BTF TBI 2016 guideline."""
        results = search_guidelines("cerebral perfusion pressure")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "btf_tbi_2016" in ids

    def test_search_decompressive_craniectomy(self):
        """Searching 'decompressive craniectomy' should find the BTF TBI 2016 guideline."""
        results = search_guidelines("decompressive craniectomy")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "btf_tbi_2016" in ids

    def test_search_mannitol(self):
        """Searching 'mannitol' should find the BTF TBI 2016 guideline."""
        results = search_guidelines("mannitol")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "btf_tbi_2016" in ids

    def test_search_pentobarbital(self):
        """Searching 'pentobarbital' should find the BTF TBI 2016 guideline."""
        results = search_guidelines("pentobarbital")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "btf_tbi_2016" in ids

    def test_search_hyperventilation(self):
        """Searching 'hyperventilation' should find the BTF TBI 2016 guideline."""
        results = search_guidelines("hyperventilation")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "btf_tbi_2016" in ids

    def test_search_neurocritical_care(self):
        """Searching 'neurocritical care' should find the BTF TBI 2016 guideline."""
        results = search_guidelines("neurocritical care")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "btf_tbi_2016" in ids

    def test_search_brain_herniation(self):
        """Searching 'brain herniation' should find the BTF TBI 2016 guideline."""
        results = search_guidelines("brain herniation")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "btf_tbi_2016" in ids

    def test_search_evd(self):
        """Searching 'external ventricular drain' should find the BTF TBI 2016 guideline."""
        results = search_guidelines("external ventricular drain")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "btf_tbi_2016" in ids


class TestRetrieveGuidelineBTFTBI2016:
    """Retrieve tests for every section of the BTF TBI 2016 guideline."""

    def test_retrieve_icp_monitoring_and_thresholds(self):
        """Retrieve the ICP monitoring and thresholds section of the BTF TBI 2016 guideline."""
        result = retrieve_guideline("btf_tbi_2016", "icp_monitoring_and_thresholds")
        assert result.value == "btf_tbi_2016/icp_monitoring_and_thresholds"
        assert "22 mmHg" in result.interpretation
        assert "GCS 3-8" in result.interpretation
        assert "60" in result.interpretation
        assert "70 mmHg" in result.interpretation
        assert result.evidence.source_doi == "10.1227/NEU.0000000000001432"

    def test_retrieve_cerebral_perfusion_and_hyperosmolar_therapy(self):
        """Retrieve the cerebral perfusion and hyperosmolar therapy section of the BTF TBI 2016 guideline."""
        result = retrieve_guideline("btf_tbi_2016", "cerebral_perfusion_and_hyperosmolar_therapy")
        assert result.value == "btf_tbi_2016/cerebral_perfusion_and_hyperosmolar_therapy"
        assert "mannitol" in result.interpretation.lower() or "Mannitol" in result.interpretation
        assert "0.25" in result.interpretation
        assert "1 g/kg" in result.interpretation
        assert "hyperventilation" in result.interpretation.lower() or "Hyperventilation" in result.interpretation
        assert result.evidence.source_doi == "10.1227/NEU.0000000000001432"

    def test_retrieve_surgical_and_medical_management(self):
        """Retrieve the surgical and medical management section of the BTF TBI 2016 guideline."""
        result = retrieve_guideline("btf_tbi_2016", "surgical_and_medical_management")
        assert result.value == "btf_tbi_2016/surgical_and_medical_management"
        assert "decompressive craniectomy" in result.interpretation.lower() or "Decompressive Craniectomy" in result.interpretation
        assert "12 x 15" in result.interpretation
        assert "phenytoin" in result.interpretation.lower() or "Phenytoin" in result.interpretation
        assert "CRASH" in result.interpretation
        assert "steroids" in result.interpretation.lower() or "Steroids" in result.interpretation
        assert result.evidence.source_doi == "10.1227/NEU.0000000000001432"

    def test_retrieve_ventilation_and_supportive_care(self):
        """Retrieve the ventilation and supportive care section of the BTF TBI 2016 guideline."""
        result = retrieve_guideline("btf_tbi_2016", "ventilation_and_supportive_care")
        assert result.value == "btf_tbi_2016/ventilation_and_supportive_care"
        assert "25 mmHg" in result.interpretation
        assert "propofol" in result.interpretation.lower() or "Propofol" in result.interpretation
        assert "barbiturate" in result.interpretation.lower() or "Barbiturate" in result.interpretation
        assert "Level I" in result.interpretation
        assert result.evidence.source_doi == "10.1227/NEU.0000000000001432"


class TestSearchGuidelinesEndocrineOsteoporosis2020:
    """Search tests for the Endocrine Society Osteoporosis 2020 guideline."""

    def test_search_osteoporosis(self):
        """Searching 'osteoporosis' should find the Endocrine Society Osteoporosis guideline."""
        results = search_guidelines("osteoporosis")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "endocrine_osteoporosis_2020" in ids

    def test_search_frax(self):
        """Searching 'FRAX' should find the Endocrine Society Osteoporosis guideline."""
        results = search_guidelines("FRAX")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "endocrine_osteoporosis_2020" in ids

    def test_search_bisphosphonate(self):
        """Searching 'bisphosphonate' should find the Endocrine Society Osteoporosis guideline."""
        results = search_guidelines("bisphosphonate")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "endocrine_osteoporosis_2020" in ids

    def test_search_denosumab(self):
        """Searching 'denosumab' should find the Endocrine Society Osteoporosis guideline."""
        results = search_guidelines("denosumab")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "endocrine_osteoporosis_2020" in ids

    def test_search_romosozumab(self):
        """Searching 'romosozumab' should find the Endocrine Society Osteoporosis guideline."""
        results = search_guidelines("romosozumab")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "endocrine_osteoporosis_2020" in ids

    def test_search_teriparatide(self):
        """Searching 'teriparatide' should find the Endocrine Society Osteoporosis guideline."""
        results = search_guidelines("teriparatide")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "endocrine_osteoporosis_2020" in ids

    def test_search_dxa(self):
        """Searching 'DXA' should find the Endocrine Society Osteoporosis guideline."""
        results = search_guidelines("DXA")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "endocrine_osteoporosis_2020" in ids

    def test_search_drug_holiday(self):
        """Searching 'drug holiday' should find the Endocrine Society Osteoporosis guideline."""
        results = search_guidelines("drug holiday")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "endocrine_osteoporosis_2020" in ids

    def test_search_hip_fracture(self):
        """Searching 'hip fracture' should find the Endocrine Society Osteoporosis guideline."""
        results = search_guidelines("hip fracture")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "endocrine_osteoporosis_2020" in ids

    def test_search_alendronate(self):
        """Searching 'alendronate' should find the Endocrine Society Osteoporosis guideline."""
        results = search_guidelines("alendronate")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "endocrine_osteoporosis_2020" in ids

    def test_search_zoledronic_acid(self):
        """Searching 'zoledronic acid' should find the Endocrine Society Osteoporosis guideline."""
        results = search_guidelines("zoledronic acid")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "endocrine_osteoporosis_2020" in ids


class TestRetrieveGuidelineEndocrineOsteoporosis2020:
    """Retrieve tests for every section of the Endocrine Society Osteoporosis 2020 guideline."""

    def test_retrieve_risk_assessment_and_diagnosis(self):
        """Retrieve the risk assessment and diagnosis section of the Osteoporosis guideline."""
        result = retrieve_guideline("endocrine_osteoporosis_2020", "risk_assessment_and_diagnosis")
        assert result.value == "endocrine_osteoporosis_2020/risk_assessment_and_diagnosis"
        assert "T-score" in result.interpretation
        assert "FRAX" in result.interpretation
        assert "-2.5" in result.interpretation
        assert "20%" in result.interpretation
        assert "3%" in result.interpretation
        assert result.evidence.source_doi == "10.1210/clinem/dgaa551"

    def test_retrieve_pharmacotherapy(self):
        """Retrieve the pharmacotherapy section of the Osteoporosis guideline."""
        result = retrieve_guideline("endocrine_osteoporosis_2020", "pharmacotherapy")
        assert result.value == "endocrine_osteoporosis_2020/pharmacotherapy"
        assert "bisphosphonate" in result.interpretation.lower() or "Bisphosphonate" in result.interpretation
        assert "alendronate" in result.interpretation.lower() or "Alendronate" in result.interpretation
        assert "denosumab" in result.interpretation.lower() or "Denosumab" in result.interpretation
        assert "60 mg" in result.interpretation
        assert result.evidence.source_doi == "10.1210/clinem/dgaa551"

    def test_retrieve_anabolic_agents_and_sequencing(self):
        """Retrieve the anabolic agents and sequencing section of the Osteoporosis guideline."""
        result = retrieve_guideline("endocrine_osteoporosis_2020", "anabolic_agents_and_sequencing")
        assert result.value == "endocrine_osteoporosis_2020/anabolic_agents_and_sequencing"
        assert "teriparatide" in result.interpretation.lower() or "Teriparatide" in result.interpretation
        assert "romosozumab" in result.interpretation.lower() or "Romosozumab" in result.interpretation
        assert "210 mg" in result.interpretation
        assert "2 years" in result.interpretation
        assert "cardiovascular" in result.interpretation.lower()
        assert result.evidence.source_doi == "10.1210/clinem/dgaa551"

    def test_retrieve_monitoring_and_drug_holidays(self):
        """Retrieve the monitoring and drug holidays section of the Osteoporosis guideline."""
        result = retrieve_guideline("endocrine_osteoporosis_2020", "monitoring_and_drug_holidays")
        assert result.value == "endocrine_osteoporosis_2020/monitoring_and_drug_holidays"
        assert "3-5 years" in result.interpretation
        assert "drug holiday" in result.interpretation.lower() or "Drug Holiday" in result.interpretation
        assert "DXA" in result.interpretation
        assert "treatment failure" in result.interpretation.lower() or "Treatment Failure" in result.interpretation
        assert result.evidence.source_doi == "10.1210/clinem/dgaa551"


class TestSearchGuidelinesACRRA2021:
    """Search tests for the ACR RA 2021 guideline."""

    def test_search_rheumatoid_arthritis(self):
        """Searching 'rheumatoid arthritis' should find the ACR RA 2021 guideline."""
        results = search_guidelines("rheumatoid arthritis")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acr_ra_2021" in ids

    def test_search_methotrexate(self):
        """Searching 'methotrexate' should find the ACR RA 2021 guideline."""
        results = search_guidelines("methotrexate")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acr_ra_2021" in ids

    def test_search_dmard(self):
        """Searching 'DMARD' should find the ACR RA 2021 guideline."""
        results = search_guidelines("DMARD")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acr_ra_2021" in ids

    def test_search_treat_to_target(self):
        """Searching 'treat-to-target' should find the ACR RA 2021 guideline."""
        results = search_guidelines("treat-to-target")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acr_ra_2021" in ids

    def test_search_tnf_inhibitor(self):
        """Searching 'TNF inhibitor' should find the ACR RA 2021 guideline."""
        results = search_guidelines("TNF inhibitor")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acr_ra_2021" in ids

    def test_search_jak_inhibitor(self):
        """Searching 'JAK inhibitor' should find the ACR RA 2021 guideline."""
        results = search_guidelines("JAK inhibitor")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acr_ra_2021" in ids

    def test_search_das28(self):
        """Searching 'DAS28' should find the ACR RA 2021 guideline."""
        results = search_guidelines("DAS28")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acr_ra_2021" in ids

    def test_search_rituximab(self):
        """Searching 'rituximab' should find the ACR RA 2021 guideline."""
        results = search_guidelines("rituximab")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acr_ra_2021" in ids

    def test_search_glucocorticoid(self):
        """Searching 'glucocorticoid' should find the ACR RA 2021 guideline."""
        results = search_guidelines("glucocorticoid")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acr_ra_2021" in ids

    def test_search_abatacept(self):
        """Searching 'abatacept' should find the ACR RA 2021 guideline."""
        results = search_guidelines("abatacept")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acr_ra_2021" in ids


class TestRetrieveGuidelineACRRA2021:
    """Retrieve tests for every section of the ACR RA 2021 guideline."""

    def test_retrieve_initial_dmard_therapy(self):
        """Retrieve the initial DMARD therapy section of the ACR RA 2021 guideline."""
        result = retrieve_guideline("acr_ra_2021", "initial_dmard_therapy")
        assert result.value == "acr_ra_2021/initial_dmard_therapy"
        assert "methotrexate" in result.interpretation.lower() or "Methotrexate" in result.interpretation
        assert "15 mg" in result.interpretation
        assert "hydroxychloroquine" in result.interpretation.lower() or "Hydroxychloroquine" in result.interpretation
        assert result.evidence.source_doi == "10.1002/acr.24596"

    def test_retrieve_biologic_targeted_dmards(self):
        """Retrieve the biologic/targeted synthetic DMARDs section of the ACR RA 2021 guideline."""
        result = retrieve_guideline("acr_ra_2021", "biologic_targeted_dmards")
        assert result.value == "acr_ra_2021/biologic_targeted_dmards"
        assert "TNF" in result.interpretation
        assert "JAK" in result.interpretation
        assert "abatacept" in result.interpretation.lower() or "Abatacept" in result.interpretation
        assert "tocilizumab" in result.interpretation.lower() or "Tocilizumab" in result.interpretation
        assert result.evidence.source_doi == "10.1002/acr.24596"

    def test_retrieve_treat_to_target(self):
        """Retrieve the treat-to-target section of the ACR RA 2021 guideline."""
        result = retrieve_guideline("acr_ra_2021", "treat_to_target")
        assert result.value == "acr_ra_2021/treat_to_target"
        assert "DAS28" in result.interpretation
        assert "CDAI" in result.interpretation
        assert "2.6" in result.interpretation
        assert "remission" in result.interpretation.lower() or "Remission" in result.interpretation
        assert result.evidence.source_doi == "10.1002/acr.24596"

    def test_retrieve_glucocorticoids_and_special_populations(self):
        """Retrieve the glucocorticoids and special populations section of the ACR RA 2021 guideline."""
        result = retrieve_guideline("acr_ra_2021", "glucocorticoids_and_special_populations")
        assert result.value == "acr_ra_2021/glucocorticoids_and_special_populations"
        assert "glucocorticoid" in result.interpretation.lower() or "Glucocorticoid" in result.interpretation
        assert "hepatitis B" in result.interpretation or "Hepatitis B" in result.interpretation
        assert "antiviral" in result.interpretation.lower() or "Antiviral" in result.interpretation
        assert result.evidence.source_doi == "10.1002/acr.24596"


class TestSearchGuidelinesAPAAUD2018:
    """Search tests for the APA Alcohol Use Disorder 2018 guideline."""

    def test_search_alcohol_use_disorder(self):
        """Searching 'alcohol use disorder' should find the APA AUD guideline."""
        results = search_guidelines("alcohol use disorder")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "apa_aud_2018" in ids

    def test_search_naltrexone(self):
        """Searching 'naltrexone' should find the APA AUD guideline."""
        results = search_guidelines("naltrexone")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "apa_aud_2018" in ids

    def test_search_acamprosate(self):
        """Searching 'acamprosate' should find the APA AUD guideline."""
        results = search_guidelines("acamprosate")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "apa_aud_2018" in ids

    def test_search_audit_c(self):
        """Searching 'AUDIT-C' should find the APA AUD guideline."""
        results = search_guidelines("AUDIT-C")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "apa_aud_2018" in ids

    def test_search_disulfiram(self):
        """Searching 'disulfiram' should find the APA AUD guideline."""
        results = search_guidelines("disulfiram")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "apa_aud_2018" in ids

    def test_search_gabapentin_aud(self):
        """Searching 'gabapentin' should find the APA AUD guideline."""
        results = search_guidelines("gabapentin")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "apa_aud_2018" in ids

    def test_search_topiramate_aud(self):
        """Searching 'topiramate' should find the APA AUD guideline."""
        results = search_guidelines("topiramate")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "apa_aud_2018" in ids

    def test_search_combine_trial(self):
        """Searching 'COMBINE trial' should find the APA AUD guideline."""
        results = search_guidelines("COMBINE trial")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "apa_aud_2018" in ids


class TestRetrieveGuidelineAPAAUD2018:
    """Retrieve tests for every section of the APA AUD 2018 guideline."""

    def test_retrieve_assessment_and_screening(self):
        """Retrieve the assessment and screening section of the APA AUD guideline."""
        result = retrieve_guideline("apa_aud_2018", "assessment_and_screening")
        assert result.value == "apa_aud_2018/assessment_and_screening"
        assert "AUDIT-C" in result.interpretation
        assert "DSM-5" in result.interpretation
        assert result.evidence.source_doi == "10.1176/appi.ajp.2017.1750101"

    def test_retrieve_fda_approved_medications(self):
        """Retrieve the FDA-approved medications section of the APA AUD guideline."""
        result = retrieve_guideline("apa_aud_2018", "fda_approved_medications")
        assert result.value == "apa_aud_2018/fda_approved_medications"
        assert "naltrexone" in result.interpretation.lower() or "Naltrexone" in result.interpretation
        assert "acamprosate" in result.interpretation.lower() or "Acamprosate" in result.interpretation
        assert "disulfiram" in result.interpretation.lower() or "Disulfiram" in result.interpretation
        assert "50 mg" in result.interpretation or "666 mg" in result.interpretation
        assert result.evidence.source_doi == "10.1176/appi.ajp.2017.1750101"

    def test_retrieve_off_label_medications(self):
        """Retrieve the off-label medications section of the APA AUD guideline."""
        result = retrieve_guideline("apa_aud_2018", "off_label_medications")
        assert result.value == "apa_aud_2018/off_label_medications"
        assert "topiramate" in result.interpretation.lower() or "Topiramate" in result.interpretation
        assert "gabapentin" in result.interpretation.lower() or "Gabapentin" in result.interpretation
        assert "2C" in result.interpretation
        assert result.evidence.source_doi == "10.1176/appi.ajp.2017.1750101"

    def test_retrieve_psychosocial_and_combined_treatment(self):
        """Retrieve the psychosocial and combined treatment section of the APA AUD guideline."""
        result = retrieve_guideline("apa_aud_2018", "psychosocial_and_combined_treatment")
        assert result.value == "apa_aud_2018/psychosocial_and_combined_treatment"
        assert "COMBINE" in result.interpretation
        assert "CBT" in result.interpretation or "Cognitive-Behavioral" in result.interpretation
        assert result.evidence.source_doi == "10.1176/appi.ajp.2017.1750101"



class TestSearchGuidelinesAPAMDD2023:

    def test_search_depression(self):
        """Searching 'depression' should find the APA MDD guideline."""
        results = search_guidelines("depression")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "apa_mdd_2023" in ids

    def test_search_mdd(self):
        """Searching 'MDD' should find the APA MDD guideline."""
        results = search_guidelines("MDD")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "apa_mdd_2023" in ids

    def test_search_cbt(self):
        """Searching 'CBT' should find the APA MDD guideline."""
        results = search_guidelines("CBT")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "apa_mdd_2023" in ids

    def test_search_ssri(self):
        """Searching 'SSRI' should find the APA MDD guideline."""
        results = search_guidelines("SSRI")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "apa_mdd_2023" in ids

    def test_search_phq9(self):
        """Searching 'PHQ-9' should find the APA MDD guideline."""
        results = search_guidelines("PHQ-9")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "apa_mdd_2023" in ids

    def test_search_adolescent_depression(self):
        """Searching 'adolescent depression' should find the APA MDD guideline."""
        results = search_guidelines("adolescent depression")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "apa_mdd_2023" in ids

    def test_search_fluoxetine(self):
        """Searching 'fluoxetine' should find the APA MDD guideline."""
        results = search_guidelines("fluoxetine")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "apa_mdd_2023" in ids

    def test_search_behavioral_activation(self):
        """Searching 'behavioral activation' should find the APA MDD guideline."""
        results = search_guidelines("behavioral activation")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "apa_mdd_2023" in ids


class TestRetrieveGuidelineAPAMDD2023:

    def test_retrieve_psychotherapy(self):
        """Retrieve the psychotherapy section of the APA MDD guideline."""
        result = retrieve_guideline("apa_mdd_2023", "psychotherapy")
        assert result.value == "apa_mdd_2023/psychotherapy"
        assert "CBT" in result.interpretation
        assert "interpersonal" in result.interpretation.lower() or "Interpersonal" in result.interpretation
        assert "behavioral activation" in result.interpretation.lower() or "Behavioral Activation" in result.interpretation
        assert result.evidence.source_doi == "10.1037/amp0001174"

    def test_retrieve_pharmacotherapy(self):
        """Retrieve the pharmacotherapy section of the APA MDD guideline."""
        result = retrieve_guideline("apa_mdd_2023", "pharmacotherapy")
        assert result.value == "apa_mdd_2023/pharmacotherapy"
        assert "SSRI" in result.interpretation
        assert "SNRI" in result.interpretation
        assert "fluoxetine" in result.interpretation.lower() or "Fluoxetine" in result.interpretation
        assert "bupropion" in result.interpretation.lower() or "Bupropion" in result.interpretation
        assert result.evidence.source_doi == "10.1037/amp0001174"

    def test_retrieve_treatment_monitoring(self):
        """Retrieve the treatment monitoring section of the APA MDD guideline."""
        result = retrieve_guideline("apa_mdd_2023", "treatment_monitoring")
        assert result.value == "apa_mdd_2023/treatment_monitoring"
        assert "PHQ-9" in result.interpretation
        assert "remission" in result.interpretation.lower() or "Remission" in result.interpretation
        assert "measurement-based care" in result.interpretation.lower() or "Measurement-Based Care" in result.interpretation
        assert result.evidence.source_doi == "10.1037/amp0001174"

    def test_retrieve_special_populations(self):
        """Retrieve the special populations section of the APA MDD guideline."""
        result = retrieve_guideline("apa_mdd_2023", "special_populations")
        assert result.value == "apa_mdd_2023/special_populations"
        assert "adolescent" in result.interpretation.lower() or "Adolescent" in result.interpretation
        assert "older adult" in result.interpretation.lower() or "Older Adult" in result.interpretation
        assert result.evidence.source_doi == "10.1037/amp0001174"


class TestSearchGuidelinesPerioperative2014:
    """Search tests for the 2014 ACC/AHA Perioperative guideline."""

    def test_search_perioperative(self):
        """Searching 'perioperative' should find the ACC/AHA perioperative guideline."""
        results = search_guidelines("perioperative")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_perioperative_2014" in ids

    def test_search_noncardiac_surgery(self):
        """Searching 'noncardiac surgery' should find the ACC/AHA perioperative guideline."""
        results = search_guidelines("noncardiac surgery")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_perioperative_2014" in ids

    def test_search_rcri(self):
        """Searching 'RCRI' should find the ACC/AHA perioperative guideline."""
        results = search_guidelines("RCRI")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_perioperative_2014" in ids

    def test_search_revised_cardiac_risk_index(self):
        """Searching 'revised cardiac risk index' should find the ACC/AHA perioperative guideline."""
        results = search_guidelines("revised cardiac risk index")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_perioperative_2014" in ids

    def test_search_lee_index(self):
        """Searching 'Lee index' should find the ACC/AHA perioperative guideline."""
        results = search_guidelines("Lee index")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_perioperative_2014" in ids

    def test_search_perioperative_beta_blocker(self):
        """Searching 'perioperative beta-blocker' should find the ACC/AHA perioperative guideline."""
        results = search_guidelines("perioperative beta-blocker")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_perioperative_2014" in ids

    def test_search_poise_trial(self):
        """Searching 'POISE trial' should find the ACC/AHA perioperative guideline."""
        results = search_guidelines("POISE trial")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_perioperative_2014" in ids

    def test_search_preoperative_cardiac_assessment(self):
        """Searching 'preoperative cardiac assessment' should find the ACC/AHA perioperative guideline."""
        results = search_guidelines("preoperative cardiac assessment")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_perioperative_2014" in ids

    def test_search_functional_capacity_mets(self):
        """Searching 'METs' should find the ACC/AHA perioperative guideline."""
        results = search_guidelines("METs")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_perioperative_2014" in ids

    def test_search_coronary_stent_surgery(self):
        """Searching 'coronary stent' should find the ACC/AHA perioperative guideline."""
        results = search_guidelines("coronary stent")
        assert len(results) >= 1
        ids = [r["guideline_id"] for r in results]
        assert "acc_aha_perioperative_2014" in ids


class TestRetrieveGuidelinePerioperative2014:
    """Retrieve tests for every section of the 2014 ACC/AHA Perioperative guideline."""

    def test_retrieve_stepwise_cardiac_assessment(self):
        """Retrieve the stepwise cardiac assessment section of the perioperative guideline."""
        result = retrieve_guideline("acc_aha_perioperative_2014", "stepwise_cardiac_assessment")
        assert result.value == "acc_aha_perioperative_2014/stepwise_cardiac_assessment"
        assert "Step 1" in result.interpretation
        assert "emergency" in result.interpretation.lower()
        assert "MACE" in result.interpretation
        assert "4 METs" in result.interpretation
        assert result.evidence.source_doi == "10.1016/j.jacc.2014.07.944"

    def test_retrieve_risk_assessment(self):
        """Retrieve the risk assessment section of the perioperative guideline."""
        result = retrieve_guideline("acc_aha_perioperative_2014", "risk_assessment")
        assert result.value == "acc_aha_perioperative_2014/risk_assessment"
        assert "RCRI" in result.interpretation
        assert "ischemic heart disease" in result.interpretation.lower() or "Ischemic Heart Disease" in result.interpretation
        assert "creatinine" in result.interpretation.lower()
        assert result.evidence.source_doi == "10.1016/j.jacc.2014.07.944"

    def test_retrieve_perioperative_beta_blocker_management(self):
        """Retrieve the beta-blocker management section of the perioperative guideline."""
        result = retrieve_guideline("acc_aha_perioperative_2014", "perioperative_beta_blocker_management")
        assert result.value == "acc_aha_perioperative_2014/perioperative_beta_blocker_management"
        assert "POISE" in result.interpretation
        assert "Class I" in result.interpretation
        assert "Class III" in result.interpretation or "Class IIb" in result.interpretation
        assert result.evidence.source_doi == "10.1016/j.jacc.2014.07.944"

    def test_retrieve_perioperative_medication_management(self):
        """Retrieve the medication management section of the perioperative guideline."""
        result = retrieve_guideline("acc_aha_perioperative_2014", "perioperative_medication_management")
        assert result.value == "acc_aha_perioperative_2014/perioperative_medication_management"
        assert "statin" in result.interpretation.lower() or "Statin" in result.interpretation
        assert "aspirin" in result.interpretation.lower() or "Aspirin" in result.interpretation
        assert "P2Y12" in result.interpretation
        assert result.evidence.source_doi == "10.1016/j.jacc.2014.07.944"
