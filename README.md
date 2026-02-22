# Open Medicine

**Evidence-Based Clinical Reasoning for AI Agents**

[![PyPI](https://img.shields.io/pypi/v/open-medicine)](https://pypi.org/project/open-medicine/)
[![Python](https://img.shields.io/pypi/pyversions/open-medicine)](https://pypi.org/project/open-medicine/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

Open Medicine is an open-source Python library that provides **deterministic, DOI-traceable clinical reasoning** for AI agents. Every calculator, score, and guideline returns its scientific source — eliminating hallucinated clinical advice.

## Install

```bash
pip install open-medicine
```

## Quick Start

### Clinical Calculators

```python
from open_medicine.mcp.calculators.chadsvasc import calculate_chadsvasc, CHADSVAScParams

result = calculate_chadsvasc(CHADSVAScParams(
    age=72,
    hypertension=True,
    diabetes=False,
    congestive_heart_failure=False,
    stroke_tia_thromboembolism=True,
    vascular_disease=False,
    female_sex=False
))

print(result.value)             # 4
print(result.interpretation)    # "CHA2DS2-VASc score is 4. High risk..."
print(result.evidence.source_doi)  # "10.1161/CIR.0000000000001193"
```

### Guideline Retrieval

```python
from open_medicine.mcp.guideline_engine import search_guidelines, retrieve_guideline

# Search by topic
matches = search_guidelines("atrial fibrillation anticoagulation")
# → [{"guideline_id": "acc_aha_af_2023", "title": "...", "doi": "...", ...}]

# Retrieve specific section
result = retrieve_guideline("acc_aha_af_2023", "anticoagulation")
print(result.interpretation)     # Full curated guideline text
print(result.evidence.source_doi)  # "10.1161/CIR.0000000000001193"
```

### MCP Server (for AI Agents)

```bash
open-medicine-mcp
```

Exposes 4 meta-tools via the [Model Context Protocol](https://modelcontextprotocol.io):

| Tool | Purpose |
|------|---------|
| `search_clinical_calculators` | Find calculators by keyword |
| `execute_clinical_calculator` | Run a calculator with validated parameters |
| `search_guidelines` | Find guideline sections by topic |
| `retrieve_guideline` | Retrieve curated guideline content |

## Available Calculators

| Calculator | Clinical Use | Evidence |
|------------|-------------|----------|
| **CHA₂DS₂-VASc** | AF stroke risk | ACC/AHA 2023 |
| **HAS-BLED** | AF bleeding risk | Pisters 2010 |
| **ASCVD** | 10-year CV risk | ACC/AHA 2013 |
| **SOFA** | Organ failure (ICU) | Vincent 1996 |
| **CURB-65** | Pneumonia severity | Lim 2003 |
| **GCS** | Brain injury severity | Teasdale 1974 |
| **CKD-EPI** | Kidney function (eGFR) | NEJM 2021 |
| **Cockcroft-Gault** | Creatinine clearance | Cockcroft 1976 |
| **Rivaroxaban Dosing** | Renal dose adjustment | FDA Label |
| **Enoxaparin Dosing** | Renal dose adjustment | FDA Label |

## Available Guidelines

| Guideline | Sections | DOI |
|-----------|----------|-----|
| ACC/AHA AF 2023 | anticoagulation, rate_control, rhythm_control | `10.1161/CIR.0000000000001193` |
| KDIGO CKD 2024 | evaluation, staging, referral | `10.1016/j.kint.2023.10.018` |
| BTS CAP 2009 | severity_assessment, antibiotic_therapy, discharge | `10.1136/thx.2009.121434` |

## Design Principles

- **Deterministic**: Same input → same output. No LLM calls, no randomness.
- **Evidence-Backed**: Every `ClinicalResult` includes a `source_doi` and evidence level.
- **FHIR-Compatible**: Outputs include LOINC codes for direct integration with EHR systems.
- **Strictly Typed**: Pydantic models validate all clinical inputs at the boundary.

## License

MIT
