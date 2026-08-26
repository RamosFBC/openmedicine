# Open Medicine

**MCP server for deterministic medical calculators and clinical scores.**

[![PyPI](https://img.shields.io/pypi/v/open-medicine)](https://pypi.org/project/open-medicine/)
[![Python](https://img.shields.io/pypi/pyversions/open-medicine)](https://pypi.org/project/open-medicine/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

Open Medicine provides a lightweight MCP server focused only on medical calculators. It exposes deterministic, typed calculator execution for AI agents, with source-traceable evidence returned in each `ClinicalResult`. DOI metadata is preserved when a source has a DOI; regulatory labels and other authoritative documents can instead carry document-level provenance.

This release removes guideline retrieval, differential diagnosis, semantic embeddings, HTTP service APIs, and GraphRAG/Neo4j functionality. The package is now intentionally narrow: discover a calculator, validate parameters, execute it, and return a structured clinical result.

## Quick Start

### Install

```bash
pip install open-medicine
```

### Configure your MCP client

```json
{
  "mcpServers": {
    "open-medicine": {
      "command": "uvx",
      "args": ["--from", "open-medicine", "open-medicine-mcp"]
    }
  }
}
```

### Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector open-medicine-mcp
```

## MCP Tools

Open Medicine exposes exactly two MCP tools:

- `search_clinical_calculators` — search the calculator registry by keyword and return calculator IDs, package version, JSON Schemas, and deterministic schema hashes.
- `execute_clinical_calculator` — execute a calculator by ID with validated JSON parameters and stable machine-readable error codes.

## Result Contract

Successful and non-successful calculator outcomes share a typed result envelope:

```json
{
  "status": "success",
  "errors": [],
  "value": 2,
  "component_breakdown": {},
  "interpretation": "...",
  "evidence": {"source_doi": null, "level": "...", "description": "..."}
}
```

`status` is one of `success`, `insufficient_data`, or `error`. Structured errors
contain a stable `code`, a human-readable `message`, and optional safe `details`.
Unknown calculators, invalid parameters, and execution failures returned by the
MCP server use the same stable error shape. Successful results require a value
and no errors; non-successful results require no value and at least one error.
Every clinical result requires an evidence object. Successful clinical rules use
a DOI or authoritative document provenance when available; error outcomes explicitly
may say no evidence available.

## Safety Changes in v0.14

- **CHA₂DS₂-VASc:** all clinical factors must be explicit. Use JSON `null` for
  unknown data; the calculator returns `insufficient_data` and no score.
- **GCS:** provide either each component score or a corresponding
  `*_non_testable_reason`. If any component is non-testable, no total is reported.
- **Renal dose adjustment:** CrCl/eGFR mismatches fail closed by default and
  return no dose. `strict_metric=false` preserves the legacy warning-only mode
  for deliberate compatibility testing.
- **Cockcroft–Gault:** required `weight_type` is explicit and currently limited to
  `"actual"`; the interpretation states the steady-state and body-size limits.
- **CKD-EPI:** required `renal_function_stable` records the steady-state context.

These calculators return calculations and bounded interpretations, not autonomous
treatment decisions. Clinical action remains the responsibility of qualified humans.

## Python Usage

```python
from open_medicine.mcp.calculators.chadsvasc import calculate_chadsvasc, CHADSVAScParams

result = calculate_chadsvasc(CHADSVAScParams(
    age=72,
    hypertension=True,
    diabetes=False,
    congestive_heart_failure=False,
    stroke_tia_thromboembolism=True,
    vascular_disease=False,
    female_sex=False,
))

print(result.value)
print(result.interpretation)
print(result.evidence.source_doi)
```

## Current Coverage

The calculator registry includes 93 clinical calculators and scores across cardiovascular risk, anticoagulant dosing, renal function, ICU severity, neurology, trauma, GI bleeding, hepatology, pulmonary/VTE risk, psychiatry screening, pediatrics, obstetrics, oncology, toxicology, and fluid/electrolyte calculations.

Examples include CHA₂DS₂-VASc, HAS-BLED, Wells DVT/PE, PERC, HEART, TIMI, GRACE, qSOFA, NEWS2, SOFA, APACHE II, GCS, NIHSS, MELD-Na, Child-Pugh, FIB-4, CKD-EPI, Cockcroft-Gault, renal dose adjustment, BMI, BSA, corrected sodium/calcium/QTc, anion gap, osmolar gap, Winter's formula, CURB-65, PSI/PORT, AIMS65, Glasgow-Blatchford, RCRI, Charlson, PHQ-9, GAD-7, CAGE, AUDIT-C, CIWA-Ar, COWS, Apgar, Pediatric GCS, PEWS, TBSA, and more.

## Development

```bash
uv sync --extra test
uv run python -m pytest -v
uv run open-medicine-mcp
uv build
```

## Design Principles

- **Calculator-only MCP surface:** no guideline, differential, embedding, GraphRAG, Neo4j, or HTTP service dependencies.
- **Deterministic:** same input produces the same output.
- **Typed:** Pydantic models validate all calculator inputs.
- **Evidence-backed:** calculator outputs include DOI or document-level provenance metadata when available.
- **Fail closed:** unknown clinical inputs and incompatible renal metrics do not silently become normal values or dosing outputs.

## License

MIT
