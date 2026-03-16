"""Tests for the typed extraction validator."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from open_medicine.graphrag.extraction_validator import (
    ValidationResult,
    validate_file,
    validate_rule,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_rule(
    rec_type: str = "treatment_selection",
    *,
    rec_id: str = "rec_test_001",
    action: str = "Test action",
    concepts: list | None = None,
    relationships: list | None = None,
    structured_properties: dict | None = None,
    strength: str = "strong_for",
    evidence_quality: str = "high",
    **overrides: object,
) -> dict:
    default_concepts = [
        {"name": "Bisoprolol", "type": "drug", "role": "subject"},
        {"name": "HFrEF", "type": "disease", "role": "target"},
    ]
    default_relationships = [
        {
            "rel_type": "INDICATED_FOR",
            "source_name": "Bisoprolol",
            "source_type": "drug",
            "target_name": "HFrEF",
            "target_type": "disease",
            "properties": {},
        }
    ]
    rule = {
        "rec_id": rec_id,
        "rec_type": rec_type,
        "action": action,
        "action_detail": "Detail text",
        "strength": strength,
        "evidence_quality": evidence_quality,
        "concepts": default_concepts if concepts is None else concepts,
        "relationships": default_relationships if relationships is None else relationships,
        "structured_properties": structured_properties if structured_properties is not None else {},
        "source_text": "Test source",
        "guideline_id": "test",
    }
    rule.update(overrides)
    return rule


# ---------------------------------------------------------------------------
# Tests: validate_rule
# ---------------------------------------------------------------------------


class TestValidateRule:
    def test_valid_treatment_selection(self) -> None:
        rule = _make_rule("treatment_selection")
        issues = validate_rule(rule)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_empty_relationships_rejected(self) -> None:
        rule = _make_rule("treatment_selection", relationships=[])
        issues = validate_rule(rule)
        errors = [i for i in issues if i.severity == "error"]
        assert any(i.issue_type == "empty_relationships" for i in errors)

    def test_dosing_without_any_dose_rejected(self) -> None:
        rule = _make_rule(
            "dosing",
            structured_properties={"frequency": "once daily"},
            relationships=[{"rel_type": "DOSED_FOR", "source_name": "X", "source_type": "drug", "target_name": "Y", "target_type": "disease", "properties": {}}],
        )
        issues = validate_rule(rule)
        errors = [i for i in issues if i.severity == "error"]
        assert any(i.issue_type == "missing_property" for i in errors)

    def test_dosing_with_starting_dose_accepted(self) -> None:
        rule = _make_rule(
            "dosing",
            structured_properties={"starting_dose": "1.25 mg", "frequency": "once daily"},
            relationships=[{"rel_type": "DOSED_FOR", "source_name": "X", "source_type": "drug", "target_name": "Y", "target_type": "disease", "properties": {}}],
        )
        issues = validate_rule(rule)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_dosing_with_target_dose_accepted(self) -> None:
        rule = _make_rule(
            "dosing",
            structured_properties={"target_dose": "10 mg"},
            relationships=[{"rel_type": "DOSED_FOR", "source_name": "X", "source_type": "drug", "target_name": "Y", "target_type": "disease", "properties": {}}],
        )
        issues = validate_rule(rule)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_dosing_empty_properties_rejected(self) -> None:
        rule = _make_rule(
            "dosing",
            structured_properties={},
            relationships=[{"rel_type": "DOSED_FOR", "source_name": "X", "source_type": "drug", "target_name": "Y", "target_type": "disease", "properties": {}}],
        )
        issues = validate_rule(rule)
        errors = [i for i in issues if i.severity == "error"]
        assert any(i.issue_type == "missing_structured_properties" for i in errors)

    def test_monitoring_without_frequency_rejected(self) -> None:
        rule = _make_rule(
            "monitoring",
            structured_properties={"threshold_alert": "K+ > 5.0"},
            concepts=[
                {"name": "ACE Inhibitor", "type": "drug_class", "role": "subject"},
                {"name": "Potassium", "type": "lab", "role": "monitor"},
            ],
            relationships=[{"rel_type": "MONITORED_BY", "source_name": "ACE Inhibitor", "source_type": "drug_class", "target_name": "Potassium", "target_type": "lab", "properties": {}}],
        )
        issues = validate_rule(rule)
        errors = [i for i in issues if i.severity == "error"]
        assert any(i.issue_type == "missing_property" for i in errors)

    def test_monitoring_with_frequency_accepted(self) -> None:
        rule = _make_rule(
            "monitoring",
            structured_properties={"frequency": "within 1-2 weeks"},
            concepts=[
                {"name": "ACE Inhibitor", "type": "drug_class", "role": "subject"},
                {"name": "Potassium", "type": "lab", "role": "monitor"},
            ],
            relationships=[{"rel_type": "MONITORED_BY", "source_name": "ACE Inhibitor", "source_type": "drug_class", "target_name": "Potassium", "target_type": "lab", "properties": {}}],
        )
        issues = validate_rule(rule)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_monitoring_without_monitor_role_warns(self) -> None:
        rule = _make_rule(
            "monitoring",
            structured_properties={"frequency": "weekly"},
            concepts=[
                {"name": "ACE Inhibitor", "type": "drug_class", "role": "subject"},
                {"name": "Potassium", "type": "lab", "role": "subject"},  # wrong role
            ],
            relationships=[{"rel_type": "MONITORED_BY", "source_name": "ACE Inhibitor", "source_type": "drug_class", "target_name": "Potassium", "target_type": "lab", "properties": {}}],
        )
        issues = validate_rule(rule)
        warnings = [i for i in issues if i.severity == "warning"]
        assert any(i.issue_type == "wrong_role" for i in warnings)

    def test_contraindication_without_severity_rejected(self) -> None:
        rule = _make_rule(
            "contraindication",
            action="Do not use NSAIDs in HF",
            structured_properties={"reason": "worsens HF"},
            relationships=[{"rel_type": "CONTRAINDICATED_IN", "source_name": "NSAID", "source_type": "drug_class", "target_name": "HFrEF", "target_type": "disease", "properties": {}}],
        )
        issues = validate_rule(rule)
        errors = [i for i in issues if i.severity == "error"]
        assert any(i.issue_type == "missing_property" for i in errors)

    def test_contraindication_with_severity_accepted(self) -> None:
        rule = _make_rule(
            "contraindication",
            action="Do not use NSAIDs in HF",
            structured_properties={"severity": "ABSOLUTE", "reason": "worsens HF"},
            relationships=[{"rel_type": "CONTRAINDICATED_IN", "source_name": "NSAID", "source_type": "drug_class", "target_name": "HFrEF", "target_type": "disease", "properties": {}}],
        )
        issues = validate_rule(rule)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_contraindication_misclassified_warns(self) -> None:
        rule = _make_rule(
            "contraindication",
            action="Avoid abrupt withdrawal of beta blockers",
            structured_properties={"severity": "RELATIVE"},
            relationships=[{"rel_type": "CONTRAINDICATED_IN", "source_name": "Beta Blocker", "source_type": "drug_class", "target_name": "HFrEF", "target_type": "disease", "properties": {}}],
        )
        issues = validate_rule(rule)
        warnings = [i for i in issues if i.severity == "warning"]
        assert any(i.issue_type == "misclassified" for i in warnings)

    def test_interaction_without_severity_rejected(self) -> None:
        rule = _make_rule(
            "interaction",
            structured_properties={"mechanism": "dual RAAS blockade"},
            relationships=[{"rel_type": "INTERACTS_WITH", "source_name": "ACEi", "source_type": "drug_class", "target_name": "ARNi", "target_type": "drug_class", "properties": {}}],
        )
        issues = validate_rule(rule)
        errors = [i for i in issues if i.severity == "error"]
        assert any(i.issue_type == "missing_property" for i in errors)

    def test_interaction_with_severity_accepted(self) -> None:
        rule = _make_rule(
            "interaction",
            structured_properties={"severity": "MAJOR", "mechanism": "dual RAAS blockade"},
            relationships=[{"rel_type": "INTERACTS_WITH", "source_name": "ACEi", "source_type": "drug_class", "target_name": "ARNi", "target_type": "drug_class", "properties": {}}],
        )
        issues = validate_rule(rule)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_no_concepts_rejected(self) -> None:
        rule = _make_rule("treatment_selection", concepts=[])
        issues = validate_rule(rule)
        errors = [i for i in issues if i.severity == "error"]
        assert any(i.issue_type == "no_concepts" for i in errors)

    def test_no_subject_role_warns(self) -> None:
        rule = _make_rule(
            "treatment_selection",
            concepts=[{"name": "HFrEF", "type": "disease", "role": "target"}],
        )
        issues = validate_rule(rule)
        warnings = [i for i in issues if i.severity == "warning"]
        assert any(i.issue_type == "no_subject" for i in warnings)

    def test_invalid_strength_warns(self) -> None:
        rule = _make_rule("treatment_selection", strength="Strong/A")
        issues = validate_rule(rule)
        warnings = [i for i in issues if i.severity == "warning"]
        assert any(i.issue_type == "invalid_strength" for i in warnings)

    def test_pregnancy_contraindication_wrong_target(self) -> None:
        rule = _make_rule(
            "contraindication",
            action="Do not administer ACEi in pregnant women with HF",
            structured_properties={"severity": "ABSOLUTE"},
            concepts=[
                {"name": "ACE Inhibitor", "type": "drug_class", "role": "subject"},
                {"name": "Heart Failure", "type": "disease", "role": "target"},
            ],
            relationships=[{"rel_type": "CONTRAINDICATED_IN", "source_name": "ACE Inhibitor", "source_type": "drug_class", "target_name": "Heart Failure", "target_type": "disease", "properties": {}}],
        )
        issues = validate_rule(rule)
        errors = [i for i in issues if i.severity == "error"]
        assert any(i.issue_type == "pregnancy_target" for i in errors)

    def test_pregnancy_contraindication_correct_target(self) -> None:
        rule = _make_rule(
            "contraindication",
            action="Do not administer ACEi in pregnant women",
            structured_properties={"severity": "ABSOLUTE"},
            concepts=[
                {"name": "ACE Inhibitor", "type": "drug_class", "role": "subject"},
                {"name": "Pregnancy", "type": "disease", "role": "target"},
            ],
            relationships=[{"rel_type": "CONTRAINDICATED_IN", "source_name": "ACE Inhibitor", "source_type": "drug_class", "target_name": "Pregnancy", "target_type": "disease", "properties": {}}],
        )
        issues = validate_rule(rule)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    # --- diagnostic_criteria ---

    def test_diagnostic_criteria_with_threshold_accepted(self) -> None:
        rule = _make_rule(
            "diagnostic_criteria",
            action="Define HFrEF as LVEF ≤40%",
            structured_properties={"threshold_variable": "LVEF", "threshold_operator": "<=", "threshold_value": "40", "threshold_unit": "%"},
            concepts=[
                {"name": "HFrEF", "type": "disease", "role": "target"},
                {"name": "LVEF", "type": "lab", "role": "subject"},
            ],
            relationships=[{"rel_type": "DIAGNOSED_BY", "source_name": "HFrEF", "source_type": "disease", "target_name": "LVEF", "target_type": "lab", "properties": {}}],
        )
        issues = validate_rule(rule)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_diagnostic_criteria_with_staging_accepted(self) -> None:
        rule = _make_rule(
            "diagnostic_criteria",
            action="Stage C HF classification",
            structured_properties={"staging_system": "ACC/AHA", "classification": "Stage C"},
            concepts=[
                {"name": "Heart Failure", "type": "disease", "role": "target"},
            ],
            relationships=[{"rel_type": "DIAGNOSED_BY", "source_name": "Heart Failure", "source_type": "disease", "target_name": "Echocardiography", "target_type": "procedure", "properties": {}}],
        )
        issues = validate_rule(rule)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_diagnostic_criteria_empty_properties_rejected(self) -> None:
        rule = _make_rule(
            "diagnostic_criteria",
            structured_properties={},
            relationships=[{"rel_type": "DIAGNOSED_BY", "source_name": "X", "source_type": "disease", "target_name": "Y", "target_type": "lab", "properties": {}}],
        )
        issues = validate_rule(rule)
        errors = [i for i in issues if i.severity == "error"]
        assert any(i.issue_type == "missing_structured_properties" for i in errors)

    def test_diagnostic_criteria_no_threshold_or_staging_rejected(self) -> None:
        rule = _make_rule(
            "diagnostic_criteria",
            structured_properties={"some_other_field": "value"},
            relationships=[{"rel_type": "DIAGNOSED_BY", "source_name": "X", "source_type": "disease", "target_name": "Y", "target_type": "lab", "properties": {}}],
        )
        issues = validate_rule(rule)
        errors = [i for i in issues if i.severity == "error"]
        assert any(i.issue_type == "missing_property" for i in errors)

    # --- safety_warning ---

    def test_safety_warning_with_warning_type_accepted(self) -> None:
        rule = _make_rule(
            "safety_warning",
            action="Avoid abrupt withdrawal of beta blockers",
            structured_properties={"warning_type": "withdrawal", "affected_drug": "Beta Blocker"},
            concepts=[
                {"name": "Beta Blocker", "type": "drug_class", "role": "subject"},
                {"name": "HFrEF", "type": "disease", "role": "target"},
            ],
            relationships=[{"rel_type": "RECOMMENDS", "source_name": "rec_001", "source_type": "recommendation", "target_name": "Beta Blocker", "target_type": "drug_class", "properties": {}}],
        )
        issues = validate_rule(rule)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_safety_warning_empty_properties_rejected(self) -> None:
        rule = _make_rule(
            "safety_warning",
            structured_properties={},
            relationships=[{"rel_type": "RECOMMENDS", "source_name": "rec_001", "source_type": "recommendation", "target_name": "Beta Blocker", "target_type": "drug_class", "properties": {}}],
        )
        issues = validate_rule(rule)
        errors = [i for i in issues if i.severity == "error"]
        assert any(i.issue_type == "missing_structured_properties" for i in errors)

    def test_safety_warning_without_warning_type_rejected(self) -> None:
        rule = _make_rule(
            "safety_warning",
            structured_properties={"affected_drug": "Beta Blocker"},
            relationships=[{"rel_type": "RECOMMENDS", "source_name": "rec_001", "source_type": "recommendation", "target_name": "Beta Blocker", "target_type": "drug_class", "properties": {}}],
        )
        issues = validate_rule(rule)
        errors = [i for i in issues if i.severity == "error"]
        assert any(i.issue_type == "missing_property" for i in errors)


# ---------------------------------------------------------------------------
# Tests: validate_file
# ---------------------------------------------------------------------------


class TestValidateFile:
    def test_valid_file(self, tmp_path: Path) -> None:
        rules = [
            _make_rule("treatment_selection", rec_id="rec_001"),
            _make_rule("treatment_selection", rec_id="rec_002"),
        ]
        filepath = tmp_path / "test.jsonl"
        filepath.write_text("\n".join(json.dumps(r) for r in rules))

        result = validate_file(filepath)
        assert result.total_rules == 2
        assert result.accepted == 2
        assert result.rejected == 0

    def test_mixed_valid_and_invalid(self, tmp_path: Path) -> None:
        rules = [
            _make_rule("treatment_selection", rec_id="rec_001"),
            _make_rule("dosing", rec_id="rec_002", structured_properties={}, relationships=[]),
        ]
        filepath = tmp_path / "test.jsonl"
        filepath.write_text("\n".join(json.dumps(r) for r in rules))

        result = validate_file(filepath)
        assert result.total_rules == 2
        assert result.accepted == 1
        assert result.rejected == 1

    def test_empty_file(self, tmp_path: Path) -> None:
        filepath = tmp_path / "empty.jsonl"
        filepath.write_text("")

        result = validate_file(filepath)
        assert result.total_rules == 0
        assert result.pass_rate == 1.0

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        result = validate_file(tmp_path / "nope.jsonl")
        assert result.total_rules == 0

    def test_summary_output(self, tmp_path: Path) -> None:
        rules = [
            _make_rule("dosing", rec_id="rec_001", structured_properties={}, relationships=[]),
        ]
        filepath = tmp_path / "test.jsonl"
        filepath.write_text(json.dumps(rules[0]))

        result = validate_file(filepath)
        summary = result.summary()
        assert "REJECT" in summary
        assert "rec_001" in summary

    def test_pass_rate_calculation(self) -> None:
        result = ValidationResult(total_rules=10, accepted=8, rejected=2)
        assert result.pass_rate == 0.8
