"""Post-ingestion graph validation.

Checks structural integrity and coverage of the loaded graph to catch
gaps (like missing edge types) before they cause silent clinical query failures.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from open_medicine.graphrag.graph.connection import GraphConnection

logger = logging.getLogger(__name__)

# Semantic edge types that should have at least 1 edge after ingestion
SEMANTIC_EDGE_TYPES = [
    "INDICATED_FOR",
    "CONTRAINDICATED_IN",
    "DOSED_FOR",
    "MONITORED_BY",
    "INTERACTS_WITH",
    "DIAGNOSED_BY",
    "MEMBER_OF",
    "PRESENTS_WITH",
    "STAGE_OF",
]

# Clinical node labels that should have at least 1 node
CLINICAL_LABELS = [
    "Drug",
    "DrugClass",
    "Disease",
    "Lab",
]

# Minimum edge counts for density warnings
MIN_INTERACTION_EDGES = 10
MIN_MONITORING_EDGES = 10


@dataclass
class ValidationCheck:
    """Result of a single validation check."""

    name: str
    status: str  # PASS, WARN, FAIL
    message: str
    details: dict = field(default_factory=dict)


@dataclass
class ValidationReport:
    """Complete validation report."""

    checks: list[ValidationCheck] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.status == "PASS")

    @property
    def warnings(self) -> int:
        return sum(1 for c in self.checks if c.status == "WARN")

    @property
    def failures(self) -> int:
        return sum(1 for c in self.checks if c.status == "FAIL")

    @property
    def ok(self) -> bool:
        return self.failures == 0


def validate_graph(conn: GraphConnection) -> ValidationReport:
    """Run post-ingestion validation checks on the graph.

    Checks:
    1. Edge type coverage — every semantic edge type has at least 1 edge
    2. Node label coverage — every clinical label has at least 1 node
    3. Orphan check — no nodes with zero edges (except EvidenceChunk)
    4. Terminology match — sample drug/disease nodes resolve via link_entity
    5. Interaction density — warn if INTERACTS_WITH < 10
    6. Monitoring density — warn if MONITORED_BY < 10
    """
    report = ValidationReport()

    # 1. Edge type coverage
    for edge_type in SEMANTIC_EDGE_TYPES:
        result = conn.execute_read(
            f"MATCH ()-[r:{edge_type}]->() RETURN count(r) AS cnt", {}
        )
        count = result[0]["cnt"] if result else 0
        if count == 0:
            report.checks.append(ValidationCheck(
                name=f"edge_{edge_type}",
                status="FAIL",
                message=f"No {edge_type} edges found in graph",
                details={"count": count},
            ))
        else:
            report.checks.append(ValidationCheck(
                name=f"edge_{edge_type}",
                status="PASS",
                message=f"{edge_type}: {count} edges",
                details={"count": count},
            ))

    # 2. Node label coverage
    for label in CLINICAL_LABELS:
        result = conn.execute_read(
            f"MATCH (n:{label}) RETURN count(n) AS cnt", {}
        )
        count = result[0]["cnt"] if result else 0
        if count == 0:
            report.checks.append(ValidationCheck(
                name=f"node_{label}",
                status="FAIL",
                message=f"No {label} nodes found in graph",
                details={"count": count},
            ))
        else:
            report.checks.append(ValidationCheck(
                name=f"node_{label}",
                status="PASS",
                message=f"{label}: {count} nodes",
                details={"count": count},
            ))

    # 3. Orphan check (nodes with zero edges, excluding EvidenceChunk)
    result = conn.execute_read(
        "MATCH (n) WHERE NOT exists { (n)--() } "
        "AND NOT n:EvidenceChunk "
        "RETURN labels(n)[0] AS label, count(n) AS cnt", {}
    )
    orphan_total = sum(r["cnt"] for r in result)
    if orphan_total > 0:
        orphan_details = {r["label"]: r["cnt"] for r in result}
        report.checks.append(ValidationCheck(
            name="orphan_nodes",
            status="WARN",
            message=f"{orphan_total} orphan nodes (no relationships)",
            details=orphan_details,
        ))
    else:
        report.checks.append(ValidationCheck(
            name="orphan_nodes",
            status="PASS",
            message="No orphan nodes",
        ))

    # 4. Terminology match — sample drug/disease nodes
    _check_terminology_match(conn, report, "Drug", "drug", 10)
    _check_terminology_match(conn, report, "Disease", "disease", 10)

    # 5. Interaction density
    result = conn.execute_read(
        "MATCH ()-[r:INTERACTS_WITH]->() RETURN count(r) AS cnt", {}
    )
    interaction_count = result[0]["cnt"] if result else 0
    if interaction_count < MIN_INTERACTION_EDGES:
        report.checks.append(ValidationCheck(
            name="interaction_density",
            status="WARN",
            message=f"Only {interaction_count} INTERACTS_WITH edges (min recommended: {MIN_INTERACTION_EDGES})",
            details={"count": interaction_count},
        ))
    else:
        report.checks.append(ValidationCheck(
            name="interaction_density",
            status="PASS",
            message=f"INTERACTS_WITH: {interaction_count} edges",
            details={"count": interaction_count},
        ))

    # 6. Monitoring density
    result = conn.execute_read(
        "MATCH ()-[r:MONITORED_BY]->() RETURN count(r) AS cnt", {}
    )
    monitoring_count = result[0]["cnt"] if result else 0
    if monitoring_count < MIN_MONITORING_EDGES:
        report.checks.append(ValidationCheck(
            name="monitoring_density",
            status="WARN",
            message=f"Only {monitoring_count} MONITORED_BY edges (min recommended: {MIN_MONITORING_EDGES})",
            details={"count": monitoring_count},
        ))
    else:
        report.checks.append(ValidationCheck(
            name="monitoring_density",
            status="PASS",
            message=f"MONITORED_BY: {monitoring_count} edges",
            details={"count": monitoring_count},
        ))

    return report


def _check_terminology_match(
    conn: GraphConnection,
    report: ValidationReport,
    label: str,
    entity_type: str,
    sample_size: int,
) -> None:
    """Sample nodes of a given label and verify they resolve via link_entity."""
    from open_medicine.graphrag.ingestion.linker_v2 import link_entity

    result = conn.execute_read(
        f"MATCH (n:{label}) RETURN n.name AS name LIMIT $limit",
        {"limit": sample_size},
    )

    if not result:
        return  # No nodes to check — covered by label coverage check

    resolved = 0
    unresolved: list[str] = []
    for row in result:
        name = row.get("name", "")
        if not name:
            continue
        entity = link_entity(name, entity_type)
        if entity and entity.node_id and not entity.node_id.startswith(f"{entity_type}:"):
            # Has a real coded ID (not a generated fallback)
            resolved += 1
        else:
            unresolved.append(name)

    total = len(result)
    if unresolved:
        report.checks.append(ValidationCheck(
            name=f"terminology_{label.lower()}",
            status="WARN",
            message=f"{resolved}/{total} {label} nodes resolve in terminology "
                    f"({len(unresolved)} unresolved)",
            details={"unresolved": unresolved[:5]},
        ))
    else:
        report.checks.append(ValidationCheck(
            name=f"terminology_{label.lower()}",
            status="PASS",
            message=f"All {total} sampled {label} nodes resolve in terminology",
        ))


def print_validation_report(report: ValidationReport) -> None:
    """Pretty-print the validation report."""
    print("\n" + "=" * 60)
    print("Post-Ingestion Validation Report")
    print("=" * 60)

    for check in report.checks:
        icon = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗"}.get(check.status, "?")
        print(f"  [{icon} {check.status:4s}] {check.message}")
        if check.details and check.status != "PASS":
            for key, val in check.details.items():
                print(f"          {key}: {val}")

    print()
    print(
        f"Summary: {report.passed} PASS, {report.warnings} WARN, "
        f"{report.failures} FAIL"
    )
    if report.ok:
        print("Status: VALIDATION PASSED")
    else:
        print("Status: VALIDATION FAILED — review failures above")
    print("=" * 60)
