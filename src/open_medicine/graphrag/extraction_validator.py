"""Post-extraction validation gate for typed extractors.

Validates that each extraction meets the minimum quality bar for its rec_type.
Rejects individual rules that are missing required structured properties,
have empty relationships, or violate type-specific invariants.

Used in Phase 2.3 of the /ingest-guideline pipeline.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Required structured_properties per rec_type
# ---------------------------------------------------------------------------

REQUIRED_PROPERTIES: dict[str, list[str]] = {
    "dosing": ["starting_dose", "target_dose", "max_dose"],  # at least ONE required
    "monitoring": ["frequency"],
    "contraindication": ["severity"],
    "interaction": ["severity"],
    "treatment_selection": [],  # no strict property requirements
    "diagnostic_criteria": ["threshold_variable", "staging_system", "classification"],  # at least ONE
    "safety_warning": ["warning_type"],
}

# Properties where at least ONE must be present (not all)
AT_LEAST_ONE: dict[str, list[str]] = {
    "dosing": ["starting_dose", "target_dose", "max_dose"],
    "diagnostic_criteria": ["threshold_variable", "staging_system", "classification"],
}


@dataclass
class ValidationIssue:
    """A single validation failure."""

    rec_id: str
    rec_type: str
    issue_type: str  # missing_property, empty_relationships, misclassified, etc.
    message: str
    severity: str = "error"  # error = reject, warning = flag but keep


@dataclass
class ValidationResult:
    """Result of validating a set of extractions."""

    total_rules: int = 0
    accepted: int = 0
    rejected: int = 0
    warnings: int = 0
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if self.total_rules == 0:
            return 1.0
        return self.accepted / self.total_rules

    def summary(self) -> str:
        lines = [
            f"Validation: {self.accepted}/{self.total_rules} accepted "
            f"({self.pass_rate:.0%}), {self.rejected} rejected, "
            f"{self.warnings} warnings",
        ]
        for issue in self.issues:
            prefix = "REJECT" if issue.severity == "error" else "WARN"
            lines.append(f"  [{prefix}] {issue.rec_id}: {issue.message}")
        return "\n".join(lines)


def validate_rule(rule: dict[str, Any]) -> list[ValidationIssue]:
    """Validate a single extraction rule. Returns list of issues (empty = valid)."""
    issues: list[ValidationIssue] = []
    rec_id = rule.get("rec_id", "unknown")
    rec_type = rule.get("rec_type", "")

    # --- Check relationships are non-empty ---
    relationships = rule.get("relationships", [])
    if not relationships:
        issues.append(
            ValidationIssue(
                rec_id=rec_id,
                rec_type=rec_type,
                issue_type="empty_relationships",
                message="relationships array is empty — typed extractor must derive at least one",
            )
        )

    # --- Check structured_properties exist (only for types that require them) ---
    props = rule.get("structured_properties", {})
    required_fields = REQUIRED_PROPERTIES.get(rec_type, [])
    if not props and required_fields:
        issues.append(
            ValidationIssue(
                rec_id=rec_id,
                rec_type=rec_type,
                issue_type="missing_structured_properties",
                message=f"structured_properties is empty for {rec_type} rule",
            )
        )

    # --- Type-specific property checks ---
    if rec_type in AT_LEAST_ONE:
        required_set = AT_LEAST_ONE[rec_type]
        if props and not any(props.get(k) for k in required_set):
            issues.append(
                ValidationIssue(
                    rec_id=rec_id,
                    rec_type=rec_type,
                    issue_type="missing_property",
                    message=(
                        f"dosing rule has no dose values — need at least one of: "
                        f"{', '.join(required_set)}"
                    ),
                )
            )

    if rec_type == "monitoring":
        if props and not props.get("frequency"):
            issues.append(
                ValidationIssue(
                    rec_id=rec_id,
                    rec_type=rec_type,
                    issue_type="missing_property",
                    message="monitoring rule has no frequency",
                )
            )

    if rec_type == "contraindication":
        if props and not props.get("severity"):
            issues.append(
                ValidationIssue(
                    rec_id=rec_id,
                    rec_type=rec_type,
                    issue_type="missing_property",
                    message="contraindication rule has no severity (ABSOLUTE/RELATIVE)",
                )
            )
        # Check for misclassification signals
        action = rule.get("action", "").lower()
        misclass_signals = ["withdraw", "abrupt", "exclude", "caution", "other than"]
        if any(w in action for w in misclass_signals):
            issues.append(
                ValidationIssue(
                    rec_id=rec_id,
                    rec_type=rec_type,
                    issue_type="misclassified",
                    message=(
                        f"likely safety_warning, not contraindication — "
                        f"action contains: {action[:80]}"
                    ),
                    severity="warning",
                )
            )

    if rec_type == "interaction":
        if props and not props.get("severity"):
            issues.append(
                ValidationIssue(
                    rec_id=rec_id,
                    rec_type=rec_type,
                    issue_type="missing_property",
                    message="interaction rule has no severity (MAJOR/MODERATE/MINOR)",
                )
            )

    if rec_type == "safety_warning":
        if props and not props.get("warning_type"):
            issues.append(
                ValidationIssue(
                    rec_id=rec_id,
                    rec_type=rec_type,
                    issue_type="missing_property",
                    message="safety_warning rule has no warning_type",
                )
            )

    # --- Check concepts exist ---
    concepts = rule.get("concepts", [])
    if not concepts:
        issues.append(
            ValidationIssue(
                rec_id=rec_id,
                rec_type=rec_type,
                issue_type="no_concepts",
                message="rule has no concepts",
            )
        )

    # --- Check concept roles ---
    has_subject = any(c.get("role") == "subject" for c in concepts)
    if not has_subject and concepts:
        issues.append(
            ValidationIssue(
                rec_id=rec_id,
                rec_type=rec_type,
                issue_type="no_subject",
                message="no concept has role 'subject'",
                severity="warning",
            )
        )

    if rec_type == "monitoring":
        has_monitor = any(c.get("role") == "monitor" for c in concepts)
        if not has_monitor and concepts:
            issues.append(
                ValidationIssue(
                    rec_id=rec_id,
                    rec_type=rec_type,
                    issue_type="wrong_role",
                    message="monitoring rule has no concept with role 'monitor' — labs should use monitor role",
                    severity="warning",
                )
            )

    # --- Check strength and evidence_quality ---
    valid_strengths = {
        "strong_for", "moderate_for", "weak_for", "strong_against", "no_benefit",
    }
    strength = rule.get("strength", "")
    if strength and strength not in valid_strengths:
        issues.append(
            ValidationIssue(
                rec_id=rec_id,
                rec_type=rec_type,
                issue_type="invalid_strength",
                message=f"invalid strength '{strength}' — use old-format separator '/' detected",
                severity="warning",
            )
        )

    valid_qualities = {"high", "moderate", "low", "very_low", "expert"}
    quality = rule.get("evidence_quality", "")
    if quality and quality not in valid_qualities:
        issues.append(
            ValidationIssue(
                rec_id=rec_id,
                rec_type=rec_type,
                issue_type="invalid_evidence_quality",
                message=f"invalid evidence_quality '{quality}'",
                severity="warning",
            )
        )

    # --- Pregnancy contraindication target check ---
    if rec_type == "contraindication":
        action = rule.get("action", "").lower()
        if "pregnan" in action:
            targets = [c for c in concepts if c.get("role") == "target"]
            if targets and not any(t["name"] == "Pregnancy" for t in targets):
                issues.append(
                    ValidationIssue(
                        rec_id=rec_id,
                        rec_type=rec_type,
                        issue_type="pregnancy_target",
                        message=(
                            f"pregnancy contraindication targets "
                            f"{[t['name'] for t in targets]} instead of Pregnancy"
                        ),
                    )
                )

    return issues


def validate_file(
    filepath: Path,
    *,
    terminology_dir: Path | None = None,
) -> ValidationResult:
    """Validate all rules in a JSONL extraction file."""
    result = ValidationResult()
    valid_names: set[str] | None = None

    if terminology_dir and terminology_dir.exists():
        valid_names = _load_terminology_names(terminology_dir)

    if not filepath.exists():
        return result

    for line in filepath.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rule = json.loads(line)
        except json.JSONDecodeError:
            continue

        result.total_rules += 1
        issues = validate_rule(rule)

        # Check terminology membership if available
        if valid_names is not None:
            for concept in rule.get("concepts", []):
                name = concept.get("name", "")
                if name.lower() not in valid_names:
                    issues.append(
                        ValidationIssue(
                            rec_id=rule.get("rec_id", "unknown"),
                            rec_type=rule.get("rec_type", ""),
                            issue_type="not_in_terminology",
                            message=f"concept '{name}' not found in terminology files",
                            severity="warning",
                        )
                    )

        errors = [i for i in issues if i.severity == "error"]
        warns = [i for i in issues if i.severity == "warning"]

        if errors:
            result.rejected += 1
        else:
            result.accepted += 1

        result.warnings += len(warns)
        result.issues.extend(issues)

    return result


def validate_directory(
    extraction_dir: Path,
    *,
    terminology_dir: Path | None = None,
) -> ValidationResult:
    """Validate all JSONL files in an extraction directory."""
    combined = ValidationResult()

    for filepath in sorted(extraction_dir.glob("*.jsonl")):
        file_result = validate_file(
            filepath, terminology_dir=terminology_dir
        )
        combined.total_rules += file_result.total_rules
        combined.accepted += file_result.accepted
        combined.rejected += file_result.rejected
        combined.warnings += file_result.warnings
        combined.issues.extend(file_result.issues)

    return combined


def _load_terminology_names(terminology_dir: Path) -> set[str]:
    """Load all valid concept names (canonical + aliases) from terminology files."""
    valid_names: set[str] = set()
    filenames = [
        "drugs.json", "drug_classes.json", "diseases.json", "labs.json",
        "procedures.json", "devices.json", "symptoms.json",
    ]
    for fname in filenames:
        fpath = terminology_dir / fname
        if not fpath.exists():
            continue
        data = json.loads(fpath.read_text())
        for canonical, entry in data.items():
            valid_names.add(canonical.lower())
            if isinstance(entry, dict):
                for alias in entry.get("aliases", []):
                    valid_names.add(alias.lower())
    return valid_names
