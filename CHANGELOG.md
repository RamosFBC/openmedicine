# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-02-22

### Added
- **10 Clinical Calculators:** ASCVD, CHA₂DS₂-VASc, SOFA, CKD-EPI (2021 race-free), Cockcroft-Gault, Rivaroxaban Dosing, Enoxaparin Dosing, GCS, HAS-BLED, CURB-65.
- **Clinical Guideline Retrieval Engine:** `search_guidelines` and `retrieve_guideline` with 3 seed guidelines (ACC/AHA AF 2023, KDIGO CKD 2024, BTS CAP 2009) and 9 curated sections.
- **Meta-Tool MCP Architecture:** `search_clinical_calculators` and `execute_clinical_calculator` for scalable tool discovery by AI agents.
- **MCP Server:** `open-medicine-mcp` CLI command.
- **Foundation:** `ClinicalResult` and `Evidence` base classes with DOI traceability and FHIR/LOINC code support.
- **57 tests:** Unit tests, comparative validation, and Hypothesis property-based bounds tests.
