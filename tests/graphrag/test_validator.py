"""Tests for post-ingestion graph validation."""

from unittest.mock import MagicMock, patch

from open_medicine.graphrag.ingestion.validator import (
    CLINICAL_LABELS,
    SEMANTIC_EDGE_TYPES,
    ValidationReport,
    validate_graph,
)


def _make_conn_with_counts(
    edge_counts: dict[str, int] | None = None,
    node_counts: dict[str, int] | None = None,
    orphans: list[dict] | None = None,
) -> MagicMock:
    """Create a mock connection that returns specified counts."""
    conn = MagicMock()

    edge_counts = edge_counts or {}
    node_counts = node_counts or {}

    def execute_read_side_effect(cypher, params=None):
        if params is None:
            params = {}
        # Edge type queries
        for edge_type in SEMANTIC_EDGE_TYPES:
            if f":{edge_type}]" in cypher:
                return [{"cnt": edge_counts.get(edge_type, 0)}]

        # Node label queries
        for label in CLINICAL_LABELS:
            if f":{label})" in cypher and "count(n)" in cypher:
                return [{"cnt": node_counts.get(label, 0)}]

        # Orphan check
        if "NOT exists" in cypher and "EvidenceChunk" in cypher:
            return orphans or []

        # Terminology check - return sample nodes
        if "LIMIT" in cypher:
            for label in CLINICAL_LABELS:
                if f":{label})" in cypher:
                    count = node_counts.get(label, 0)
                    return [{"name": f"Test{label}{i}"} for i in range(min(count, 3))]
            return []

        # Density checks (INTERACTS_WITH, MONITORED_BY specific)
        if "INTERACTS_WITH" in cypher and "count" in cypher:
            return [{"cnt": edge_counts.get("INTERACTS_WITH", 0)}]
        if "MONITORED_BY" in cypher and "count" in cypher:
            return [{"cnt": edge_counts.get("MONITORED_BY", 0)}]

        return [{"cnt": 0}]

    conn.execute_read.side_effect = execute_read_side_effect
    return conn


class TestValidatorCatchesMissingEdgeType:
    def test_missing_diagnosed_by_is_failure(self):
        """Graph missing DIAGNOSED_BY edges should report FAIL."""
        edge_counts = {et: 10 for et in SEMANTIC_EDGE_TYPES}
        edge_counts["DIAGNOSED_BY"] = 0  # Missing
        node_counts = {label: 5 for label in CLINICAL_LABELS}

        conn = _make_conn_with_counts(edge_counts, node_counts)

        with patch("open_medicine.graphrag.ingestion.linker_v2.link_entity") as mock_link:
            mock_link.return_value = MagicMock(node_id="real:123")
            report = validate_graph(conn)

        # Find the DIAGNOSED_BY check
        diag_check = next(c for c in report.checks if c.name == "edge_DIAGNOSED_BY")
        assert diag_check.status == "FAIL"
        assert report.failures > 0
        assert not report.ok


class TestValidatorPassesCompleteGraph:
    def test_complete_graph_passes(self):
        """Graph with all edge types and labels should PASS."""
        edge_counts = {et: 15 for et in SEMANTIC_EDGE_TYPES}
        node_counts = {label: 5 for label in CLINICAL_LABELS}

        conn = _make_conn_with_counts(edge_counts, node_counts)

        with patch("open_medicine.graphrag.ingestion.linker_v2.link_entity") as mock_link:
            # Return entity with coded ID (not a fallback)
            entity = MagicMock()
            entity.node_id = "rxnorm:123"
            mock_link.return_value = entity
            report = validate_graph(conn)

        assert report.failures == 0
        assert report.ok


class TestValidatorWarnings:
    def test_low_interaction_density_warns(self):
        """Low INTERACTS_WITH count should generate WARN."""
        edge_counts = {et: 15 for et in SEMANTIC_EDGE_TYPES}
        edge_counts["INTERACTS_WITH"] = 3  # Below threshold
        node_counts = {label: 5 for label in CLINICAL_LABELS}

        conn = _make_conn_with_counts(edge_counts, node_counts)

        with patch("open_medicine.graphrag.ingestion.linker_v2.link_entity") as mock_link:
            mock_link.return_value = MagicMock(node_id="rxnorm:123")
            report = validate_graph(conn)

        density_check = next(c for c in report.checks if c.name == "interaction_density")
        assert density_check.status == "WARN"

    def test_orphan_nodes_warns(self):
        """Orphan nodes should generate WARN."""
        edge_counts = {et: 15 for et in SEMANTIC_EDGE_TYPES}
        node_counts = {label: 5 for label in CLINICAL_LABELS}
        orphans = [{"label": "Drug", "cnt": 3}]

        conn = _make_conn_with_counts(edge_counts, node_counts, orphans)

        with patch("open_medicine.graphrag.ingestion.linker_v2.link_entity") as mock_link:
            mock_link.return_value = MagicMock(node_id="rxnorm:123")
            report = validate_graph(conn)

        orphan_check = next(c for c in report.checks if c.name == "orphan_nodes")
        assert orphan_check.status == "WARN"


class TestValidationReport:
    def test_report_counts(self):
        from open_medicine.graphrag.ingestion.validator import ValidationCheck

        report = ValidationReport(checks=[
            ValidationCheck("a", "PASS", "ok"),
            ValidationCheck("b", "WARN", "warning"),
            ValidationCheck("c", "FAIL", "failure"),
            ValidationCheck("d", "PASS", "ok"),
        ])
        assert report.passed == 2
        assert report.warnings == 1
        assert report.failures == 1
        assert not report.ok
