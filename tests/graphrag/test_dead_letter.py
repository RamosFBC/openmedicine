import json
import pytest
from pathlib import Path
from open_medicine.graphrag.ingestion.dead_letter import DeadLetterQueue, FailedExtraction


class TestFailedExtraction:
    def test_serializable(self):
        f = FailedExtraction(
            guideline_id="g1", chunk_id="c1",
            chunk_text="Some text", error="LLM timeout",
            timestamp="2026-03-13T10:00:00",
        )
        data = json.loads(f.to_json())
        assert data["guideline_id"] == "g1"
        assert data["error"] == "LLM timeout"

    def test_from_json(self):
        f = FailedExtraction(
            guideline_id="g1", chunk_id="c1",
            chunk_text="Text", error="err",
            timestamp="2026-03-13T10:00:00",
        )
        restored = FailedExtraction.from_json(f.to_json())
        assert restored.guideline_id == f.guideline_id
        assert restored.chunk_id == f.chunk_id


class TestDeadLetterQueue:
    def test_append_creates_file(self, tmp_path):
        dlq = DeadLetterQueue(tmp_path / "failed.jsonl")
        dlq.append(FailedExtraction(
            guideline_id="g1", chunk_id="c1",
            chunk_text="Text", error="err",
            timestamp="2026-03-13T10:00:00",
        ))
        assert dlq.path.exists()

    def test_append_and_load(self, tmp_path):
        dlq = DeadLetterQueue(tmp_path / "failed.jsonl")
        dlq.append(FailedExtraction("g1", "c1", "Text1", "err1", "2026-03-13T10:00:00"))
        dlq.append(FailedExtraction("g1", "c2", "Text2", "err2", "2026-03-13T10:01:00"))
        items = dlq.load()
        assert len(items) == 2
        assert items[0].chunk_id == "c1"
        assert items[1].chunk_id == "c2"

    def test_load_empty_file(self, tmp_path):
        dlq = DeadLetterQueue(tmp_path / "nonexistent.jsonl")
        items = dlq.load()
        assert items == []

    def test_count(self, tmp_path):
        dlq = DeadLetterQueue(tmp_path / "failed.jsonl")
        assert dlq.count() == 0
        dlq.append(FailedExtraction("g1", "c1", "T", "e", "2026-03-13T10:00:00"))
        assert dlq.count() == 1
