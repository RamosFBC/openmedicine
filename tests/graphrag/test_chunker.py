import pytest
from open_medicine.graphrag.ingestion.parser import ParsedSection, ParsedDocument
from open_medicine.graphrag.ingestion.chunker import chunk_document, Chunk


def _make_doc(sections: list[ParsedSection]) -> ParsedDocument:
    return ParsedDocument(guideline_id="test_001", title="Test", sections=sections)


class TestChunker:
    def test_short_section_becomes_single_child(self):
        doc = _make_doc([
            ParsedSection(heading="Section A", level=2, content="Short text.", parent_heading=None),
        ])
        chunks = chunk_document(doc)
        children = [c for c in chunks if c.parent_chunk_id is not None]
        parents = [c for c in chunks if c.parent_chunk_id is None]
        assert len(parents) == 1
        assert len(children) == 1

    def test_long_section_splits_into_children(self):
        long_text = "This is a sentence. " * 200  # ~800 tokens
        doc = _make_doc([
            ParsedSection(heading="Long Section", level=2, content=long_text, parent_heading=None),
        ])
        chunks = chunk_document(doc, max_tokens=200)
        children = [c for c in chunks if c.parent_chunk_id is not None]
        assert len(children) > 1

    def test_table_kept_atomic(self):
        doc = _make_doc([
            ParsedSection(
                heading="Table Section", level=2, content="Intro text.",
                tables=[[{"Drug": "A", "Dose": "10mg"}, {"Drug": "B", "Dose": "20mg"}]],
                parent_heading=None,
            ),
        ])
        chunks = chunk_document(doc)
        table_chunks = [c for c in chunks if "Drug" in c.text and "Dose" in c.text]
        assert len(table_chunks) >= 1

    def test_chunk_ids_deterministic(self):
        doc = _make_doc([
            ParsedSection(heading="S", level=2, content="Content here.", parent_heading=None),
        ])
        chunks1 = chunk_document(doc)
        chunks2 = chunk_document(doc)
        assert [c.id for c in chunks1] == [c.id for c in chunks2]

    def test_chunk_has_guideline_and_section(self):
        doc = _make_doc([
            ParsedSection(heading="My Section", level=2, content="Text.", parent_heading=None),
        ])
        chunks = chunk_document(doc)
        for c in chunks:
            assert c.guideline_id == "test_001"
            assert c.section == "My Section"
