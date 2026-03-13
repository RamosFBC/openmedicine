from __future__ import annotations
from open_medicine.graphrag.graph.connection import GraphConnection
from open_medicine.graphrag.graph.queries import ReasoningQueries
from open_medicine.graphrag.ingestion.embeddings import embed_query
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
    def __init__(self, conn: GraphConnection, voyage_api_key: str = "") -> None:
        self._conn = conn
        self._voyage_api_key = voyage_api_key

    def _embed_query(self, text: str) -> list[float]:
        return embed_query(text, api_key=self._voyage_api_key)

    def _synthesize(self, question: str, sources: str) -> str:
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
        query_vector = self._embed_query(query_text)

        cypher, params = ReasoningQueries.vector_search(query_vector)
        rows = self._conn.execute_read(cypher, params)

        if not rows:
            return GraphRAGResult(
                source="llm_synthesis", matches=[],
                synthesis=None, evidence=[],
                confidence="low", missing_variables=[],
            )

        # Graph-enhanced: get parent context for each chunk
        enhanced_sources: list[str] = []
        evidence: list[EvidenceCitation] = []
        for r in rows:
            ctx_cypher, ctx_params = ReasoningQueries.graph_enhanced_context(r["ec_id"])
            ctx_rows = self._conn.execute_read(ctx_cypher, ctx_params)

            chunk_text = r["ec_text"]
            parent_text = ""
            if ctx_rows and ctx_rows[0].get("parent_text"):
                parent_text = ctx_rows[0]["parent_text"]

            source_block = f"[{r['g_title']}, {r['ec_section']}]\n"
            if parent_text:
                source_block += f"Context: {parent_text[:200]}...\n"
            source_block += chunk_text
            enhanced_sources.append(source_block)

            evidence.append(EvidenceCitation(
                chunk_id=r["ec_id"], text=r["ec_text"],
                guideline_title=r["g_title"], doi=r["g_doi"],
                section=r["ec_section"], page=0,
            ))

        sources_text = "\n\n---\n\n".join(enhanced_sources)
        question = f"{q.intent}: {', '.join(q.concepts)}"
        if q.patient_vars:
            question += f" (patient: {q.patient_vars})"

        synthesis = self._synthesize(question, sources_text)

        return GraphRAGResult(
            source="llm_synthesis", matches=[],
            synthesis=synthesis, evidence=evidence,
            confidence="medium", missing_variables=[],
        )
