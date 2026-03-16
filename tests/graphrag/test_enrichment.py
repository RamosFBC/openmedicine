"""Tests for GraphRAG edge property enrichment."""

from open_medicine.graphrag.enrichment import (
    PARSERS,
    parse_contraindication_properties,
    parse_dosing_properties,
    parse_interaction_properties,
    parse_monitoring_properties,
)


class TestParseDosing:
    def test_basic_dosing_text(self):
        text = (
            "Bumetanide: initial daily dose 0.5-1.0 mg once or twice daily; "
            "maximum total daily dose 10 mg"
        )
        result = parse_dosing_properties(text)
        assert result["starting_dose"] == "0.5-1.0 mg"
        assert "10 mg" in result["max_dose"]
        assert "once or twice daily" in result["frequency"]

    def test_target_dose(self):
        text = "Start at 3.125 mg twice daily, target dose of 25 mg twice daily"
        result = parse_dosing_properties(text)
        assert result["target_dose"] == "25 mg"

    def test_route_extraction(self):
        text = "Administer 40 mg IV initial dose"
        result = parse_dosing_properties(text)
        assert result["route"] == "iv"

    def test_empty_text(self):
        assert parse_dosing_properties("") == {}

    def test_no_match(self):
        result = parse_dosing_properties("Consider this medication for patients with HFrEF")
        assert result == {}

    # --- New patterns: "start X mg" (most common ACEi/ARB/BB format) ---

    def test_start_pattern(self):
        text = "Captopril: start 6.25 mg 3 times daily, titrate to target dose of 50 mg 3 times daily"
        result = parse_dosing_properties(text)
        assert result["starting_dose"] == "6.25 mg"
        assert result["target_dose"] == "50 mg"
        assert "3 times daily" in result["frequency"]

    def test_start_range(self):
        text = "Fosinopril: start 5-10 mg once daily, titrate to target dose of 40 mg once daily"
        result = parse_dosing_properties(text)
        assert result["starting_dose"] == "5-10 mg"
        assert result["target_dose"] == "40 mg"
        assert "once daily" in result["frequency"]

    def test_start_at(self):
        text = "Start at 3.125 mg twice daily, titrate to target dose of 25-50 mg twice daily"
        result = parse_dosing_properties(text)
        assert result["starting_dose"] == "3.125 mg"
        assert result["target_dose"] == "25-50 mg"

    # --- SGLT2i: "X mg once daily (starting dose equals target dose)" ---

    def test_sglt2i_equals_pattern(self):
        text = "Dapagliflozin: 10 mg once daily (starting dose equals target dose)"
        result = parse_dosing_properties(text)
        assert result["starting_dose"] == "10 mg"
        assert result["target_dose"] == "10 mg"

    def test_initial_and_target_dose(self):
        text = "Empagliflozin for HFrEF: initial and target dose 10 mg once daily (no titration required)"
        result = parse_dosing_properties(text)
        assert result["starting_dose"] == "10 mg"
        assert result["target_dose"] == "10 mg"

    # --- Infusion patterns ---

    def test_infusion_mcg_kg_min(self):
        text = "Dopamine: no bolus, infusion 5-10 mcg/kg/min for inotropic effect"
        result = parse_dosing_properties(text)
        assert result["starting_dose"] == "5-10 mcg/kg/min"
        assert result["route"] == "iv"  # infusion normalized to iv

    def test_infusion_mcg_min(self):
        text = "Norepinephrine: bolus not recommended, infusion 0.5-30 mcg/min"
        result = parse_dosing_properties(text)
        assert result["starting_dose"] == "0.5-30 mcg/min"

    # --- Max dose patterns ---

    def test_max_total_daily(self):
        text = "Furosemide: initial daily dose 20-40 mg; maximum total daily dose 600 mg"
        result = parse_dosing_properties(text)
        assert result["max_dose"] == "600 mg"

    def test_max_dose_simple(self):
        text = "maximum dose 200 mg daily"
        result = parse_dosing_properties(text)
        assert result["max_dose"] == "200 mg"

    # --- Digoxin patterns ---

    def test_digoxin_initiated(self):
        text = "Digoxin is commonly initiated and maintained at 0.125-0.25 mg daily"
        result = parse_dosing_properties(text)
        assert result["starting_dose"] == "0.125-0.25 mg"

    # --- Frequency patterns ---

    def test_frequency_3_times_daily(self):
        text = "start 6.25 mg 3 times daily"
        result = parse_dosing_properties(text)
        assert "3 times daily" in result["frequency"]

    def test_frequency_every_8_hours(self):
        text = "heparin 5000 units every 8 or 12 hours"
        result = parse_dosing_properties(text)
        assert "every 8 or 12 hours" in result["frequency"]

    def test_frequency_every_other_day(self):
        text = "Low doses 0.125 mg every other day"
        result = parse_dosing_properties(text)
        assert "every other day" in result["frequency"]


class TestParseMonitoring:
    def test_basic_monitoring(self):
        text = "Monitor potassium and renal function within 1-2 weeks of initiation"
        result = parse_monitoring_properties(text)
        assert "frequency" in result
        assert "1-2 weeks" in result["frequency"]

    def test_threshold(self):
        text = "Hold if K+ > 5.5 mEq/L"
        result = parse_monitoring_properties(text)
        assert "threshold_alert" in result
        assert "5.5" in result["threshold_alert"]

    def test_empty_text(self):
        assert parse_monitoring_properties("") == {}

    # --- New patterns ---

    def test_schedule_pattern(self):
        text = (
            "Regular checks approximately 1 week, then 4 weeks, "
            "then every 6 months after initiating MRA"
        )
        result = parse_monitoring_properties(text)
        assert "frequency" in result
        assert "1 week" in result["frequency"]

    def test_every_pattern(self):
        text = "Monitor every 3 months during stable therapy"
        result = parse_monitoring_properties(text)
        assert result["frequency"] == "every 3 months"

    def test_multiple_thresholds(self):
        text = "Hold if K+ > 5.5 mEq/L or eGFR < 30 mL/min"
        result = parse_monitoring_properties(text)
        assert "K+" in result["threshold_alert"]
        assert "eGFR" in result["threshold_alert"]

    def test_digoxin_threshold(self):
        text = "serum digoxin concentration >= 1.2 ng/mL is associated with increased mortality"
        result = parse_monitoring_properties(text)
        assert "threshold_alert" in result
        assert "1.2" in result["threshold_alert"]

    def test_nt_probnp_threshold(self):
        text = "NT-proBNP level >5314 pg/mL did not have benefit from vericiguat"
        result = parse_monitoring_properties(text)
        assert "NT-proBNP" in result["threshold_alert"]

    def test_within_7_days(self):
        text = "early follow-up within 7 days of hospital discharge"
        result = parse_monitoring_properties(text)
        assert "within 7 days" in result["frequency"]


class TestParseInteraction:
    def test_basic_interaction(self):
        text = "Allow 36-hour washout due to overlapping RAAS blockade, risk of angioedema"
        result = parse_interaction_properties(text)
        assert "mechanism" in result
        assert "clinical_effect" in result

    def test_severity_major(self):
        text = "Avoid concurrent use due to increased hypotension risk"
        result = parse_interaction_properties(text)
        assert result["severity"] == "MAJOR"

    def test_severity_moderate(self):
        text = "Use with caution when combining these medications"
        result = parse_interaction_properties(text)
        assert result["severity"] == "MODERATE"

    def test_empty_text(self):
        assert parse_interaction_properties("") == {}


class TestParseContraindication:
    def test_absolute(self):
        text = "NSAIDs should be avoided as they worsen HF symptoms"
        result = parse_contraindication_properties(text)
        assert result["severity"] == "ABSOLUTE"
        assert "reason" in result

    def test_relative(self):
        text = "Use with caution in patients with renal impairment"
        result = parse_contraindication_properties(text)
        assert result["severity"] == "RELATIVE"

    def test_empty_text(self):
        assert parse_contraindication_properties("") == {}

    # --- New patterns ---

    def test_angioedema_always_absolute(self):
        text = "ACEi should not be administered to patients with any history of angioedema"
        result = parse_contraindication_properties(text)
        assert result["severity"] == "ABSOLUTE"

    def test_angioedema_even_with_caution_word(self):
        """Angioedema overrides 'caution' keyword — must be ABSOLUTE."""
        text = "Use with caution in angioedema patients, consider ARB alternative"
        result = parse_contraindication_properties(text)
        assert result["severity"] == "ABSOLUTE"

    def test_should_not_be_used(self):
        text = "thiazolidinediones should not be used because they increase the risk of HF"
        result = parse_contraindication_properties(text)
        assert result["severity"] == "ABSOLUTE"

    def test_not_recommended(self):
        text = "nondihydropyridine CCBs are not recommended in HFrEF"
        result = parse_contraindication_properties(text)
        assert result["severity"] == "ABSOLUTE"

    def test_causes_harm(self):
        text = "In patients with HFrEF, adaptive servo-ventilation causes harm"
        result = parse_contraindication_properties(text)
        assert result["severity"] == "ABSOLUTE"

    def test_potentially_harmful(self):
        text = "long-term use of intravenous inotropes is potentially harmful"
        result = parse_contraindication_properties(text)
        assert result["severity"] == "ABSOLUTE"

    def test_increased_mortality(self):
        text = "class IC antiarrhythmic medications may increase the risk of mortality"
        result = parse_contraindication_properties(text)
        assert result["severity"] == "ABSOLUTE"

    def test_reason_worsen(self):
        text = "NSAIDs worsen HF symptoms and should be avoided"
        result = parse_contraindication_properties(text)
        assert "reason" in result

    def test_reason_associated_with(self):
        text = "Doxazosin is associated with moderate magnitude of HF induction"
        result = parse_contraindication_properties(text)
        assert "reason" in result

    def test_is_ineffective_relative(self):
        text = "routine use of nitrates is ineffective in HFpEF"
        result = parse_contraindication_properties(text)
        assert result["severity"] == "RELATIVE"


class TestParsersRegistry:
    def test_all_types_registered(self):
        assert "dosing" in PARSERS
        assert "monitoring" in PARSERS
        assert "interaction" in PARSERS
        assert "contraindication" in PARSERS

    def test_parsers_callable(self):
        for name, parser in PARSERS.items():
            result = parser("")
            assert result == {}, f"{name} parser failed on empty string"
