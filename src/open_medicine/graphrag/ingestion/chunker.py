from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass
from open_medicine.graphrag.ingestion.parser import ParsedDocument


@dataclass
class Chunk:
    id: str
    text: str
    guideline_id: str
    section: str
    parent_chunk_id: str | None = None


def _hash_id(guideline_id: str, section: str, index: int, is_parent: bool) -> str:
    key = f"{guideline_id}:{section}:{index}:{'parent' if is_parent else 'child'}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _estimate_tokens(text: str) -> int:
    return len(text.split())


def _split_text(text: str, max_tokens: int, overlap: int = 50) -> list[str]:
    words = text.split()
    if len(words) <= max_tokens:
        return [text]
    chunks = []
    start = 0
    while start < len(words):
        end = start + max_tokens
        chunks.append(" ".join(words[start:end]))
        start = end - overlap
    return chunks


def chunk_document(doc: ParsedDocument, max_tokens: int = 400, overlap: int = 50) -> list[Chunk]:
    chunks: list[Chunk] = []

    for sec_idx, section in enumerate(doc.sections):
        parent_id = _hash_id(doc.guideline_id, section.heading, sec_idx, is_parent=True)

        # Parent chunk = full section content
        parent_text = section.content
        chunks.append(Chunk(
            id=parent_id,
            text=parent_text,
            guideline_id=doc.guideline_id,
            section=section.heading,
            parent_chunk_id=None,
        ))

        # Child chunks from text
        text_parts = _split_text(section.content, max_tokens, overlap)
        child_idx = 0
        for part in text_parts:
            child_id = _hash_id(doc.guideline_id, section.heading, child_idx, is_parent=False)
            chunks.append(Chunk(
                id=child_id,
                text=part,
                guideline_id=doc.guideline_id,
                section=section.heading,
                parent_chunk_id=parent_id,
            ))
            child_idx += 1

        # Table chunks (atomic)
        for table in section.tables:
            table_text = json.dumps(table, indent=2)
            child_id = _hash_id(doc.guideline_id, section.heading, child_idx, is_parent=False)
            chunks.append(Chunk(
                id=child_id,
                text=table_text,
                guideline_id=doc.guideline_id,
                section=section.heading,
                parent_chunk_id=parent_id,
            ))
            child_idx += 1

    return chunks
