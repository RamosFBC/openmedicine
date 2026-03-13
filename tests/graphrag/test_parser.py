import pytest
from pathlib import Path
from open_medicine.graphrag.ingestion.parser import (
    ParsedSection, ParsedDocument, parse_markdown,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestParseMarkdown:
    def test_extracts_top_level_title(self):
        doc = parse_markdown(FIXTURES / "sample_guideline.md", guideline_id="test_htn_2024")
        assert doc.title == "Test Guideline for Hypertension 2024"
        assert doc.guideline_id == "test_htn_2024"

    def test_extracts_sections_with_hierarchy(self):
        doc = parse_markdown(FIXTURES / "sample_guideline.md", guideline_id="test_htn_2024")
        headings = [s.heading for s in doc.sections]
        assert "1. Pharmacotherapy" in headings
        assert "1.1 First-Line Agents" in headings
        assert "1.2 Renal Dosing Adjustments" in headings

    def test_section_levels(self):
        doc = parse_markdown(FIXTURES / "sample_guideline.md", guideline_id="test_htn_2024")
        section_map = {s.heading: s for s in doc.sections}
        assert section_map["1. Pharmacotherapy"].level == 2
        assert section_map["1.1 First-Line Agents"].level == 3

    def test_parent_heading_assigned(self):
        doc = parse_markdown(FIXTURES / "sample_guideline.md", guideline_id="test_htn_2024")
        section_map = {s.heading: s for s in doc.sections}
        assert section_map["1.1 First-Line Agents"].parent_heading == "1. Pharmacotherapy"

    def test_table_detected(self):
        doc = parse_markdown(FIXTURES / "sample_guideline.md", guideline_id="test_htn_2024")
        section_map = {s.heading: s for s in doc.sections}
        renal = section_map["1.2 Renal Dosing Adjustments"]
        assert len(renal.tables) > 0
        assert "Lisinopril" in str(renal.tables[0])

    def test_leaf_sections_have_content(self):
        doc = parse_markdown(FIXTURES / "sample_guideline.md", guideline_id="test_htn_2024")
        leaf_sections = [s for s in doc.sections if s.level == 3]
        for s in leaf_sections:
            assert len(s.content) > 0, f"Leaf section '{s.heading}' has no content"
