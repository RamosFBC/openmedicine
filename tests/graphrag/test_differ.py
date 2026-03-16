"""Tests for diff-based graph update support."""

from unittest.mock import MagicMock

from open_medicine.graphrag.ingestion.differ import (
    DryRunReport,
    EdgeRecord,
    GraphDiff,
    GuidelineSnapshot,
    diff_snapshots,
    dry_run_report,
    snapshot_guideline,
)


class TestEdgeRecordEquality:
    def test_same_triple_different_source_are_equal(self):
        """EdgeRecord equality ignores source_property — only triple matters."""
        a = EdgeRecord("drug:1", "INTERACTS_WITH", "drug:2", "")
        b = EdgeRecord("drug:1", "INTERACTS_WITH", "drug:2", "patch")
        assert a == b

    def test_different_triple_not_equal(self):
        a = EdgeRecord("drug:1", "INTERACTS_WITH", "drug:2", "")
        b = EdgeRecord("drug:1", "MONITORED_BY", "lab:1", "")
        assert a != b

    def test_hash_matches_equality(self):
        """Two equal EdgeRecords must hash the same for set operations."""
        a = EdgeRecord("drug:1", "INTERACTS_WITH", "drug:2", "")
        b = EdgeRecord("drug:1", "INTERACTS_WITH", "drug:2", "patch")
        assert hash(a) == hash(b)
        assert len({a, b}) == 1  # Set deduplication


class TestDiffSnapshots:
    def test_diff_detects_lost_edges(self):
        """Edges present before but absent after are reported as lost."""
        edge_kept = EdgeRecord("drug:1", "INDICATED_FOR", "disease:1", "")
        edge_lost = EdgeRecord("drug:2", "MONITORED_BY", "lab:1", "")

        before = GuidelineSnapshot(
            guideline_id="hf",
            recommendation_count=5,
            evidence_chunk_count=10,
            edges={edge_kept, edge_lost},
        )
        after = GuidelineSnapshot(
            guideline_id="hf",
            recommendation_count=4,
            evidence_chunk_count=8,
            edges={edge_kept},
        )

        diff = diff_snapshots(before, after)
        assert edge_lost in diff.lost_edges
        assert edge_kept not in diff.lost_edges
        assert diff.recs_before == 5
        assert diff.recs_after == 4

    def test_diff_detects_added_edges(self):
        """Edges present after but absent before are reported as added."""
        existing = EdgeRecord("drug:1", "INDICATED_FOR", "disease:1", "")
        new_edge = EdgeRecord("drug:3", "DOSED_FOR", "disease:2", "")

        before = GuidelineSnapshot(guideline_id="hf", edges={existing})
        after = GuidelineSnapshot(guideline_id="hf", edges={existing, new_edge})

        diff = diff_snapshots(before, after)
        assert new_edge in diff.added_edges
        assert len(diff.lost_edges) == 0

    def test_diff_detects_lost_patch_edges(self):
        """Manually patched edges lost during reload are flagged separately."""
        patch_edge = EdgeRecord("drug:1", "INTERACTS_WITH", "drug:2", "patch")
        regular_edge = EdgeRecord("drug:1", "INDICATED_FOR", "disease:1", "")

        before = GuidelineSnapshot(
            guideline_id="hf",
            edges={patch_edge, regular_edge},
            patch_edges={patch_edge},
        )
        # After reload, the patch edge is gone
        after = GuidelineSnapshot(
            guideline_id="hf",
            edges={regular_edge},
        )

        diff = diff_snapshots(before, after)
        assert patch_edge in diff.lost_patch_edges
        assert len(diff.lost_patch_edges) == 1

    def test_no_changes_produces_empty_diff(self):
        edge = EdgeRecord("drug:1", "INDICATED_FOR", "disease:1", "")
        snapshot = GuidelineSnapshot(
            guideline_id="hf",
            recommendation_count=3,
            evidence_chunk_count=6,
            edges={edge},
        )
        diff = diff_snapshots(snapshot, snapshot)
        assert len(diff.added_edges) == 0
        assert len(diff.lost_edges) == 0
        assert len(diff.lost_patch_edges) == 0


class TestSnapshotGuideline:
    def test_snapshot_captures_counts_and_edges(self):
        """snapshot_guideline reads rec count, chunk count, and edges from graph."""
        conn = MagicMock()

        call_count = 0

        def execute_read_side_effect(cypher, params=None):
            nonlocal call_count
            call_count += 1
            if "count(rec)" in cypher:
                return [{"cnt": 5}]
            if "count(DISTINCT ec)" in cypher:
                return [{"cnt": 12}]
            if "DISTINCT a.id AS src" in cypher:
                return [
                    {"src": "drug:1", "rel": "INDICATED_FOR", "tgt": "disease:1", "source": ""},
                    {"src": "drug:2", "rel": "MONITORED_BY", "tgt": "lab:1", "source": "patch"},
                ]
            return []

        conn.execute_read.side_effect = execute_read_side_effect

        snap = snapshot_guideline(conn, "heart_failure")
        assert snap.guideline_id == "heart_failure"
        assert snap.recommendation_count == 5
        assert snap.evidence_chunk_count == 12
        assert len(snap.edges) == 2
        assert len(snap.patch_edges) == 1

    def test_snapshot_empty_guideline(self):
        """Snapshot of a guideline with no data returns zeros."""
        conn = MagicMock()
        conn.execute_read.return_value = []

        snap = snapshot_guideline(conn, "nonexistent")
        assert snap.recommendation_count == 0
        assert snap.evidence_chunk_count == 0
        assert len(snap.edges) == 0


class TestDryRunReport:
    def test_dry_run_shows_preview(self):
        """dry_run_report returns correct counts without modifying graph."""
        conn = MagicMock()

        def execute_read_side_effect(cypher, params=None):
            if "count(rec)" in cypher:
                return [{"cnt": 3}]
            if "count(DISTINCT ec)" in cypher:
                return [{"cnt": 8}]
            if "DISTINCT a.id AS src" in cypher:
                return [
                    {"src": "drug:1", "rel": "MONITORED_BY", "tgt": "lab:1", "source": "patch"},
                ]
            if "labels(n)[0]" in cypher:
                return [{"label": "Drug", "cnt": 5}, {"label": "Lab", "cnt": 2}]
            return []

        conn.execute_read.side_effect = execute_read_side_effect

        report = dry_run_report(conn, "heart_failure", new_extraction_count=10, new_chunk_count=20)

        assert report.guideline_id == "heart_failure"
        assert report.would_delete_recs == 3
        assert report.would_delete_chunks == 8
        assert report.would_create_recs == 10
        assert report.would_create_chunks == 20
        assert report.shared_nodes_preserved == {"Drug": 5, "Lab": 2}
        assert report.patch_edges_at_risk == 1
        # Verify no write calls were made
        conn.execute_write.assert_not_called()
