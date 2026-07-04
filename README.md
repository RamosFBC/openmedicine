# Open Medicine

**MCP server for deterministic medical calculators and clinical scores.**

[![PyPI](https://img.shields.io/pypi/v/open-medicine)](https://pypi.org/project/open-medicine/)
[![Python](https://img.shields.io/pypi/pyversions/open-medicine)](https://pypi.org/project/open-medicine/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

Open Medicine provides a lightweight MCP server focused only on medical calculators. It exposes deterministic, typed calculator execution for AI agents, with DOI-traceable evidence returned in each `ClinicalResult`.

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

- `search_clinical_calculators` — search the calculator registry by keyword and return calculator IDs plus JSON Schemas.
- `execute_clinical_calculator` — execute a calculator by ID with validated JSON parameters.

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

The calculator registry includes 92 clinical calculators and scores across cardiovascular risk, anticoagulant dosing, renal function, ICU severity, neurology, trauma, GI bleeding, hepatology, pulmonary/VTE risk, psychiatry screening, pediatrics, obstetrics, oncology, toxicology, and fluid/electrolyte calculations.

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
- **Evidence-backed:** calculator outputs include DOI-backed evidence metadata when available.

## License

MIT
