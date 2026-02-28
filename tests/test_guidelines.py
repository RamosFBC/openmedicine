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
