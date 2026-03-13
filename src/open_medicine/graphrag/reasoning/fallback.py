from __future__ import annotations
from open_medicine.graphrag.graph.connection import GraphConnection
from open_medicine.graphrag.reasoning.types import (
    ClinicalQuery, GraphRAGResult, EvidenceCitation,
)

SYNTHESIS_PROMPT = """You are a clinical guideline assistant. Answer ONLY based on the provided source texts.
If the sources do not contain enough information, say so explicitly.

Sources:
{sources}

Question: {question}

Requirements:
- Cite the specific guideline, section, and page for every claim
- Do not extrapolate beyond what the sources state
- Flag any uncertainty"""


class FallbackEngine:
    def __init__(self, conn: GraphConnection) -> None:
        self._conn = conn

    def _vector_search(self, query_text: str, top_k: int = 10) -> list[dict]:
        """Search EvidenceChunks by full-text index (vector index when available)."""
        cypher = (
            "CALL db.index.fulltext.queryNodes('evidence_text', $query) "
            "YIELD node, score "
            "MATCH (node)-[:BELONGS_TO]->(g:Guideline) "
            "OPTIONAL MATCH (ln:LogicNode)-[:SOURCED_FROM]->(node) "
            "RETURN node.id AS ec_id, node.text AS ec_text, node.section AS ec_section, "
            "score, g.title AS g_title, g.doi AS g_doi, "
            "COALESCE(ln.page, 0) AS ln_page "
            "LIMIT $limit"
        )
        return self._conn.execute_read(cypher, {"query": query_text, "limit": top_k})

    def _synthesize(self, question: str, sources: str) -> str:
        """Call LLM for synthesis."""
        import anthropic
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[{"role": "user", "content": SYNTHESIS_PROMPT.format(sources=sources, question=question)}],
        )
        return response.content[0].text

    def query(self, q: ClinicalQuery) -> GraphRAGResult:
        query_text = f"{q.intent} {' '.join(q.concepts)}"
        rows = self._vector_search(query_text)

        if not rows:
            return GraphRAGResult(
                source="llm_synthesis",
                matches=[],
                synthesis=None,
                evidence=[],
                confidence="low",
                missing_variables=[],
            )

        evidence = [
            EvidenceCitation(
                chunk_id=r["ec_id"], text=r["ec_text"],
                guideline_title=r["g_title"], doi=r["g_doi"],
                section=r["ec_section"], page=r["ln_page"],
            )
            for r in rows
        ]

        sources_text = "\n\n---\n\n".join(
            f"[{e.guideline_title}, {e.section}, p.{e.page}]\n{e.text}"
            for e in evidence
        )
        question = f"{q.intent}: {', '.join(q.concepts)}"
        if q.patient_vars:
            question += f" (patient: {q.patient_vars})"

        synthesis = self._synthesize(question, sources_text)

        return GraphRAGResult(
            source="llm_synthesis",
            matches=[],
            synthesis=synthesis,
            evidence=evidence,
            confidence="medium",
            missing_variables=[],
        )
