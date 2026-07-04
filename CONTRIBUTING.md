# Contributing to Open Medicine

Open Medicine is a calculator-only MCP server for deterministic medical scores and calculators. Because outputs may influence clinical reasoning, contributions must prioritize correctness, traceability, and predictable behavior.

## Development Setup

```bash
git clone https://github.com/RamosFBC/openmedicine.git
cd openmedicine
uv sync --extra test
uv run python -m pytest -v
```

## Adding a New Calculator

Use an existing calculator, such as `src/open_medicine/mcp/calculators/chadsvasc.py`, as a template.

Required steps:

1. Add `src/open_medicine/mcp/calculators/<name>.py`.
2. Define a Pydantic params model with descriptive fields.
3. Implement a deterministic function returning `ClinicalResult`.
4. Add tests in `tests/test_<name>.py` for boundary, edge, and representative cases.
5. Verify `evidence.source_doi` is present when the source has a DOI.
6. Register the calculator in `src/open_medicine/mcp/registry.py`.
7. Run:

```bash
uv run python -m pytest tests/test_<name>.py -v
uv run python -m pytest -v
```

## Pull Request Checklist

- [ ] Existing tests pass.
- [ ] New calculator has unit tests.
- [ ] DOI/source citation is present and correct.
- [ ] Registry entry is added.
- [ ] Calculator execution is deterministic and has no network calls.
- [ ] Input validation uses Pydantic.

## Out of Scope for This Release Line

Please do not add guideline retrieval, differential diagnosis, semantic embeddings, GraphRAG/Neo4j, or HTTP service APIs unless maintainers explicitly reopen those scopes.
