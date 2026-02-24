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
