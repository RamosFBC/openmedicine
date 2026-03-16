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

    def test_severity_minor(self):
        text = "Minor interaction with minimal clinical significance"
        result = parse_interaction_properties(text)
        assert result["severity"] == "MINOR"

    def test_no_severity_keywords(self):
        """When no severity keywords match, severity should be omitted."""
        text = "These two drugs interact in some way"
        result = parse_interaction_properties(text)
        assert "severity" not in result

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

    def test_no_severity_keywords(self):
        """When no severity keywords match, severity should be omitted."""
        text = "This drug is restricted in certain populations"
        result = parse_contraindication_properties(text)
        assert "severity" not in result

    def test_empty_text(self):
        assert parse_contraindication_properties("") == {}


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
