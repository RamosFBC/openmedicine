from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class FailedExtraction:
    guideline_id: str
    chunk_id: str
    chunk_text: str
    error: str
    timestamp: str

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, raw: str) -> FailedExtraction:
        return cls(**json.loads(raw))


class DeadLetterQueue:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, failure: FailedExtraction) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(failure.to_json() + "\n")

    def load(self) -> list[FailedExtraction]:
        if not self.path.exists():
            return []
        items: list[FailedExtraction] = []
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    items.append(FailedExtraction.from_json(line))
        return items

    def count(self) -> int:
        if not self.path.exists():
            return 0
        with open(self.path, encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
