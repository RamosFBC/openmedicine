# Open Medicine

**Evidence-Based Clinical Reasoning for AI Agents**

[![PyPI](https://img.shields.io/pypi/v/open-medicine)](https://pypi.org/project/open-medicine/)
[![Python](https://img.shields.io/pypi/pyversions/open-medicine)](https://pypi.org/project/open-medicine/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

*LLMs hallucinate medical math and guidelines. Open Medicine stops them.*

Open Medicine is an open-source Python library and **MCP Server** that provides **deterministic, DOI-traceable clinical reasoning** for AI agents. Every calculator, score, and guideline returns its scientific source—forcing agents to rely on verified clinical standards rather than latent knowledge.

## Why Open Medicine? 
If you ask an LLM to evaluate a clinical plan, it might casually agree with "aggressive fluid resuscitation" for a variceal bleed. This is a common, deadly hallucination. 

By plugging the `open-medicine-mcp` server into your agent (via LangChain, AutoGPT, Claude Desktop, etc.), the agent can query the actual **NICE CG141 Guidance** and correct the plan: *"Modify. Guidelines mandate a cautious, restrictive transfusion strategy (target Hgb 7-8 g/dL). Aggressive fluids will increase portal pressure."*

## Quick Start

### 1. Install the Library
Open Medicine requires Python >= 3.10. Install the library via pip. This will automatically add the `open-medicine-mcp` executable to your system PATH.
```bash
pip install open-medicine
```

### 2. Configure Your MCP Client
Add the `open-medicine-mcp` server to your MCP client's configuration file (e.g., `claude_desktop_config.json` for Claude Desktop):

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
*(This uses `uvx` to automatically manage the virtual environment and fetch the latest version.)*

### 3. Test with MCP Inspector
Alternatively, you can test the toolkit using the standard MCP testing tool:
```bash
npx @modelcontextprotocol/inspector open-medicine-mcp
```

### 4. Standalone Python Library
```bash
pip install open-medicine
```

#### Deterministic Clinical Calculators
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

#### Guideline Retrieval
```python
from open_medicine.mcp.guideline_engine import search_guidelines, retrieve_guideline

# Search by topic
matches = search_guidelines("atrial fibrillation anticoagulation")

# Retrieve specific section
result = retrieve_guideline("acc_aha_af_2023", "anticoagulation")
print(result.evidence.source_doi)  # "10.1161/CIR.0000000000001193"
```

## Available Tools (MCP)

| Tool | Purpose |
|------|---------|
| `search_clinical_calculators` | Find calculators by keyword (e.g., "GI bleed") |
| `execute_clinical_calculator` | Run a calculator with JSON schema validation |
| `search_guidelines` | Find guideline sections by topic |
| `retrieve_guideline` | Retrieve curated, DOI-backed guideline content |

## Current Coverage

**Calculators (54):** AA Gradient, ABCD2, Anion Gap, Apixaban Dosing, ASCVD, BISAP, BMI, BSA (Mosteller), Canadian C-Spine, Caprini, CHA₂DS₂-VASc, Child-Pugh, CKD-EPI, Cockcroft-Gault, Corrected Calcium, Corrected QT, Corrected Sodium, CURB-65, Dabigatran Dosing, Edoxaban Dosing, Enoxaparin Dosing, FIB-4, Fisher Grade, GCS, Glasgow-Blatchford, GOLD COPD, GRACE, HAS-BLED, HEART Score, Heparin Dosing, Hunt & Hess, Insulin Basal Dosing, MELD-Na, NAFLD Fibrosis, NEWS2, NIHSS, Osmolar Gap, Padua, Parkland, PERC, qSOFA, Ranson's, Rivaroxaban Dosing, Rockall, Revised Trauma Score (RTS), Serum Osmolality, SOFA, TIMI STEMI, TIMI UA/NSTEMI, Warfarin Initiation, Wells' DVT, Wells' PE, Winter's Formula.

**Guidelines (14):** 
- ACC/AHA AF 2023 (`acc_aha_af_2023`)
- KDIGO CKD 2024 (`kdigo_ckd_2024`)
- BTS CAP 2009 (`bts_cap_2009`)
- TIMI UA/NSTEMI 2000 (`timi_ua_nstemi_2000`)
- ACC/AHA ASCVD 2013 (`acc_aha_ascvd_2013`)
- Sepsis-3 2016 (`sepsis3_2016`)
- Wells PE 2000 (`wells_pe_2000`)
- GOLD COPD 2024 (`gold_copd_2024`)
- AHA/ACC Chest Pain 2021 (`aha_acc_chest_pain_2021`)
- AHA/ASA Ischemic Stroke 2019 (`aha_asa_stroke_2019`)
- AASLD Cirrhosis 2023 (`aasld_cirrhosis_2023`)
- ESC ACS 2023 (`esc_acs_2023`)
- NICE UGIB 2012 (`nice_ugib_2012`)
- RCP NEWS2 2017 (`rcp_news2_2017`)

## Design Principles

- **Deterministic**: Same input → same output. No LLM calls, no randomness.
- **Evidence-Backed**: Every `ClinicalResult` includes a `source_doi` and evidence level.
- **FHIR-Compatible**: Outputs include LOINC/SNOMED codes for direct integration with EHR systems.
- **Strictly Typed**: Pydantic models validate all clinical inputs at the boundary.

## License

MIT
