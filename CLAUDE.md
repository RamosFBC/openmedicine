# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Project

Open Medicine is a Python package and stdio MCP server for deterministic, DOI-traceable medical calculators and clinical scores.

The current architecture is intentionally calculator-only. Do not add guideline retrieval, differential diagnosis, semantic embeddings, GraphRAG/Neo4j, or HTTP service functionality to this release line unless the project direction changes explicitly.

## Commands

```bash
uv sync --extra test
uv run python -m pytest -v
uv run python -m pytest tests/test_chadsvasc.py -v
uv run python -m pytest tests/test_chadsvasc.py::test_chadsvasc_max_score -v
uv run python -m pytest -k "chadsvasc" -v
uv run open-medicine-mcp
uv build
```

Always use `uv run python -m pytest` rather than relying on `pytest` being on PATH.

## Architecture

1. **Foundation** (`src/open_medicine/foundation/base.py`)
   - Core models: `Evidence` and `ClinicalResult`.
   - Calculator outputs should return `ClinicalResult` with evidence metadata.

2. **Calculators** (`src/open_medicine/mcp/calculators/`)
   - One module per calculator.
   - Pydantic params model plus a pure calculation function.

3. **Registry** (`src/open_medicine/mcp/registry.py`)
   - Imports calculator modules and exposes `CALCULATOR_REGISTRY`.
   - Every MCP-discoverable calculator must be registered here.

4. **MCP Server** (`src/open_medicine/mcp/server.py`)
   - Exposes only two stdio MCP tools:
     - `search_clinical_calculators`
     - `execute_clinical_calculator`

## Adding a Calculator

1. Create `src/open_medicine/mcp/calculators/<name>.py`.
2. Define a Pydantic params model with clear `Field(...)` descriptions.
3. Implement a deterministic pure function returning `ClinicalResult`.
4. Add unit tests in `tests/test_<name>.py` covering min/max/edge cases and DOI evidence.
5. Register the calculator in `src/open_medicine/mcp/registry.py`.
6. Run focused and full tests:

```bash
uv run python -m pytest tests/test_<name>.py -v
uv run python -m pytest -v
```

## Clinical Accuracy Rules

- Prefer primary-source formulas and validation papers.
- Include a DOI whenever the source has one.
- Keep calculations deterministic and side-effect free.
- Validate all public inputs through Pydantic.
- Do not introduce network calls into calculator execution.
