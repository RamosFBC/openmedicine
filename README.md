# Open Medicine

**Evidence-Based Clinical Reasoning for AI Agents**

Open Medicine is an open-source Python library designed to provide evidence-based clinical reasoning (EBM) capabilities to AI agents. It acts as an "evidence bridge," ensuring that every clinical tool (calculators, scores, guidelines) returns not just a value, but its scientific foundation (DOI and Level of Evidence) in a deterministic and validated manner.

## Features
- **Strictly Typed Foundation**: Uses Pydantic to ensure all inputs (patient data) and outputs (clinical results) are strictly typed.
- **Model Context Protocol (MCP) Integration**: Built-in support for exposing clinical tools as external functions for AI agents via the standard MCP protocol.
- **Evidence-Backed**: Every result provides the underlying source DOI and evidence level.
- **FHIR Compliant**: Designed to integrate seamlessly with existing healthcare AI systems via Fast Healthcare Interoperability Resources (FHIR) standards, utilizing official code systems like [LOINC FHIR](https://loinc.org/fhir/).

## Project Structure
- `src/open_medicine/foundation/`: Core types and base classes (`Evidence`, `ClinicalResult`).
- `src/open_medicine/mcp/calculators/`: Clinical calculators and scores (e.g., SOFA, CHA2DS2-VASc).
- `src/open_medicine/workbench/`: Mining modules (MIMIC-IV) and synthetic data generation.

## Installation

You can use `uv` or `pip` to install the project dependencies.

```bash
# Using uv (recommended)
uv venv
source .venv/bin/activate
uv pip install -e .

# Using pip
python -m venv .venv
source .venv/bin/activate
pip install -e .
```
