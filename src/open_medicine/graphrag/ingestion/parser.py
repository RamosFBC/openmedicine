from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedSection:
    heading: str
    level: int
    content: str
    tables: list[list[dict[str, str]]] = field(default_factory=list)
    parent_heading: str | None = None


@dataclass
class ParsedDocument:
    guideline_id: str
    title: str
    sections: list[ParsedSection] = field(default_factory=list)


def _parse_table(lines: list[str]) -> list[dict[str, str]]:
    """Parse a markdown table into list of row dicts."""
    if len(lines) < 3:
        return []
    headers = [h.strip() for h in lines[0].strip("|").split("|")]
    rows = []
    for line in lines[2:]:  # skip header + separator
        vals = [v.strip() for v in line.strip("|").split("|")]
        rows.append(dict(zip(headers, vals)))
    return rows


def parse_markdown(path: Path, guideline_id: str) -> ParsedDocument:
    """Parse a markdown file into a structured ParsedDocument."""
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    title = ""
    sections: list[ParsedSection] = []
    heading_stack: list[tuple[int, str]] = []  # (level, heading)

    current_heading = ""
    current_level = 0
    current_lines: list[str] = []

    def _flush() -> None:
        nonlocal current_heading, current_level, current_lines
        if not current_heading:
            return
        content_text = "\n".join(current_lines).strip()
        tables: list[list[dict[str, str]]] = []
        # Extract tables from content
        table_lines: list[str] = []
        in_table = False
        for cl in current_lines:
            if "|" in cl and not in_table:
                in_table = True
                table_lines = [cl]
            elif in_table and "|" in cl:
                table_lines.append(cl)
            elif in_table:
                in_table = False
                parsed = _parse_table(table_lines)
                if parsed:
                    tables.append(parsed)
                table_lines = []
        if table_lines:
            parsed = _parse_table(table_lines)
            if parsed:
                tables.append(parsed)

        parent = None
        for lvl, hdg in reversed(heading_stack):
            if lvl < current_level:
                parent = hdg
                break

        sections.append(ParsedSection(
            heading=current_heading,
            level=current_level,
            content=content_text,
            tables=tables,
            parent_heading=parent,
        ))

    for line in lines:
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            _flush()
            current_level = len(heading_match.group(1))
            current_heading = heading_match.group(2).strip()
            current_lines = []
            if current_level == 1 and not title:
                title = current_heading
            else:
                # Update heading stack
                heading_stack = [(l, h) for l, h in heading_stack if l < current_level]
                heading_stack.append((current_level, current_heading))
        else:
            current_lines.append(line)

    _flush()

    # Remove the title section if it was the h1
    sections = [s for s in sections if s.heading != title]

    return ParsedDocument(guideline_id=guideline_id, title=title, sections=sections)
