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
5. Add source provenance. Use `evidence.source_doi` when the source has a DOI;
   otherwise record the authoritative document metadata available to the calculator.
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
- [ ] Missing clinical inputs are represented explicitly and never default silently to normal/false.
- [ ] Error and insufficient-data paths have stable codes and regression tests.
- [ ] Treatment recommendations are not embedded in a calculation unless the calculator's scoped contract explicitly requires them.
- [ ] Registry entry is added.
- [ ] Calculator execution is deterministic and has no network calls.
- [ ] Input validation uses Pydantic.

## Result and Evidence Contracts

- Successful results require a non-null value and an empty `errors` list.
- Unsafe or impossible calculations should return `error` or `insufficient_data`
  with `value=None`, a stable error code, and actionable safe details.
- Every `ClinicalResult` requires an `Evidence` object. Successful clinical
  rules use a DOI or authoritative document provenance when available; error outcomes
  explicitly may say no evidence available.
- Do not use sentinel citations such as `"N/A"`. DOI absence is represented by
  `source_doi=None`; use authority, URL/document ID, version/section, retrieval
  date, and content hash when those fields apply.
- Never expose raw exception text through MCP error responses.

## Out of Scope for This Release Line

Please do not add guideline retrieval, differential diagnosis, semantic embeddings, GraphRAG/Neo4j, or HTTP service APIs unless maintainers explicitly reopen those scopes.
