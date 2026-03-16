"""Diff-based graph update support.

Snapshots guideline state before reload and diffs against the new state
to detect lost manual patches. Supports dry-run mode to preview changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from open_medicine.graphrag.graph.connection import GraphConnection


@dataclass(frozen=True)
class EdgeRecord:
    """Immutable edge representation for set comparison."""

    source_id: str
    edge_type: str
    target_id: str
    source_property: str  # '_source' property value, e.g. 'patch' or ''

    def __hash__(self) -> int:
        return hash((self.source_id, self.edge_type, self.target_id))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EdgeRecord):
            return NotImplemented
        return (
            self.source_id == other.source_id
            and self.edge_type == other.edge_type
            and self.target_id == other.target_id
        )


@dataclass
class GuidelineSnapshot:
    """Snapshot of nodes and edges associated with a guideline."""

    guideline_id: str
    recommendation_count: int = 0
    evidence_chunk_count: int = 0
    edges: set[EdgeRecord] = field(default_factory=set)
    patch_edges: set[EdgeRecord] = field(default_factory=set)


@dataclass
class GraphDiff:
    """Diff between two guideline snapshots."""

    added_edges: set[EdgeRecord] = field(default_factory=set)
    lost_edges: set[EdgeRecord] = field(default_factory=set)
    lost_patch_edges: set[EdgeRecord] = field(default_factory=set)
    recs_before: int = 0
    recs_after: int = 0
    chunks_before: int = 0
    chunks_after: int = 0


@dataclass
class DryRunReport:
    """Preview of what a load operation would do."""

    guideline_id: str
    would_delete_recs: int = 0
    would_delete_chunks: int = 0
    would_create_recs: int = 0
    would_create_chunks: int = 0
    would_create_edges: int = 0
    shared_nodes_preserved: dict[str, int] = field(default_factory=dict)
    patch_edges_at_risk: int = 0


def snapshot_guideline(conn: GraphConnection, guideline_id: str) -> GuidelineSnapshot:
    """Capture current nodes and edges scoped to a guideline."""
    # Count recommendations
    result = conn.execute_read(
        "MATCH (rec:Recommendation {guideline_id: $gid}) RETURN count(rec) AS cnt",
        {"gid": guideline_id},
    )
    rec_count = result[0]["cnt"] if result else 0

    # Count evidence chunks linked to this guideline's recommendations
    result = conn.execute_read(
        "MATCH (rec:Recommendation {guideline_id: $gid})-[:SOURCED_FROM]->(ec:EvidenceChunk) "
        "RETURN count(DISTINCT ec) AS cnt",
        {"gid": guideline_id},
    )
    chunk_count = result[0]["cnt"] if result else 0

    # Get all edges connected to this guideline's recommendations (2 hops)
    result = conn.execute_read(
        "MATCH (rec:Recommendation {guideline_id: $gid})-[*1..2]-(a)-[r]-(b) "
        "RETURN DISTINCT a.id AS src, type(r) AS rel, b.id AS tgt, "
        "coalesce(r._source, '') AS source",
        {"gid": guideline_id},
    )

    edges: set[EdgeRecord] = set()
    patch_edges: set[EdgeRecord] = set()
    for row in result:
        src = row.get("src", "")
        tgt = row.get("tgt", "")
        rel = row.get("rel", "")
        source = row.get("source", "")
        if src and tgt and rel:
            record = EdgeRecord(src, rel, tgt, source)
            edges.add(record)
            if source == "patch":
                patch_edges.add(record)

    return GuidelineSnapshot(
        guideline_id=guideline_id,
        recommendation_count=rec_count,
        evidence_chunk_count=chunk_count,
        edges=edges,
        patch_edges=patch_edges,
    )


def diff_snapshots(
    before: GuidelineSnapshot, after: GuidelineSnapshot
) -> GraphDiff:
    """Find edges lost and added between two snapshots."""
    lost = before.edges - after.edges
    added = after.edges - before.edges
    lost_patches = before.patch_edges - after.edges

    return GraphDiff(
        added_edges=added,
        lost_edges=lost,
        lost_patch_edges=lost_patches,
        recs_before=before.recommendation_count,
        recs_after=after.recommendation_count,
        chunks_before=before.evidence_chunk_count,
        chunks_after=after.evidence_chunk_count,
    )


def dry_run_report(
    conn: GraphConnection,
    guideline_id: str,
    new_extraction_count: int,
    new_chunk_count: int,
) -> DryRunReport:
    """Preview what a load operation would do without executing it."""
    snapshot = snapshot_guideline(conn, guideline_id)

    # Count shared clinical nodes that would be preserved
    result = conn.execute_read(
        "MATCH (rec:Recommendation {guideline_id: $gid})-[*1..2]-(n) "
        "WHERE n:Drug OR n:DrugClass OR n:Disease OR n:Lab OR n:Procedure "
        "RETURN labels(n)[0] AS label, count(DISTINCT n) AS cnt",
        {"gid": guideline_id},
    )
    shared = {row["label"]: row["cnt"] for row in result}

    return DryRunReport(
        guideline_id=guideline_id,
        would_delete_recs=snapshot.recommendation_count,
        would_delete_chunks=snapshot.evidence_chunk_count,
        would_create_recs=new_extraction_count,
        would_create_chunks=new_chunk_count,
        shared_nodes_preserved=shared,
        patch_edges_at_risk=len(snapshot.patch_edges),
    )


def print_dry_run_report(report: DryRunReport) -> None:
    """Pretty-print the dry-run report."""
    print(f"\n{'=' * 60}")
    print(f"Dry-Run Report for guideline: {report.guideline_id}")
    print(f"{'=' * 60}")
    print(f"  Would delete: {report.would_delete_recs} Recommendations, "
          f"{report.would_delete_chunks} EvidenceChunks")
    print(f"  Would create: {report.would_create_recs} Recommendations, "
          f"{report.would_create_chunks} EvidenceChunks")
    if report.shared_nodes_preserved:
        shared_str = ", ".join(
            f"{cnt} {label}" for label, cnt in report.shared_nodes_preserved.items()
        )
        print(f"  Would preserve: {shared_str} (shared clinical nodes)")
    if report.patch_edges_at_risk > 0:
        print(f"  WARNING: {report.patch_edges_at_risk} manually patched edges at risk")
    print(f"{'=' * 60}")


def print_diff_report(diff: GraphDiff) -> None:
    """Pretty-print the diff report after a reload."""
    print(f"\nReload complete. Diff:")
    print(f"  +{len(diff.added_edges)} new edges")
    print(f"  -{len(diff.lost_edges)} edges lost")
    if diff.lost_patch_edges:
        print(f"  WARNING: {len(diff.lost_patch_edges)} manual patches lost:")
        for edge in sorted(diff.lost_patch_edges, key=lambda e: e.source_id):
            print(f"    {edge.source_id} --{edge.edge_type}--> {edge.target_id}")
    print(f"  Recommendations: {diff.recs_before} -> {diff.recs_after}")
    print(f"  Evidence chunks: {diff.chunks_before} -> {diff.chunks_after}")
