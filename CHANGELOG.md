# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.2] - 2026-02-24

### Fixed
- Corrected DOI references across 16 calculators to cite original derivation papers instead of secondary sources, validation studies, or guidelines that merely reference them.
  - **Wrong DOIs (secondary sources):** CHA₂DS₂-VASc, Apixaban Dosing, Wells DVT, Canadian C-Spine, ASCVD, Parkland, Serum Osmolality, Osmolar Gap, NEWS2.
  - **Invalid DOI formats:** Fisher Grade, Hunt-Hess, BMI (were citation strings), Enoxaparin Dosing, Rivaroxaban Dosing, GOLD COPD (were free text).
  - **Incorrect DOI (wrong paper):** Ranson's Criteria (DOI resolved to unrelated Annals of Surgery paper; original 1974 paper has no DOI, now uses PMID:4834279).
- Updated 7 test files to match corrected DOI values.

## [0.2.1] - 2026-02-24

### Fixed
- Fixed MCP server registry mapping to correctly load and serve all 14 curated guidelines.

### Changed
- Expanded README coverage to accurately list all 54 available calculators and 14 guidelines, and added a Reddit-ready project hook.

## [0.2.0] - 2026-02-23

### Added
- **31 New Clinical Calculators (Phases 1-3):** 
  - **Cardiology:** Wells DVT/PE, PERC, HEART Score, TIMI STEMI/NSTEMI, GRACE, QTc.
  - **Critical Care/Pulmonology:** qSOFA, NEWS2, A-a gradient, Anion Gap, Winter's Formula, Osmolality, Osmolar Gap, Corrected Na/Ca.
  - **Anticoagulation:** Apixaban, Dabigatran, Edoxaban, Heparin, Warfarin dosing.
  - **Hepatology/GI:** MELD-Na, Child-Pugh, FIB-4, NAFLD Fibrosis Score.
  - **Other:** BMI, GOLD COPD, Caprini, Padua, BSA, Insulin Basal, plus neurology and trauma calculators from Phase 3.
- **14 New Clinical Guideline Modules:**
  - **Apixaban Dosing Guidelines**
  - **Wells' Criteria for PE (2000)** — pre-test probability, diagnostic algorithm.
  - **Sepsis-3 (2016)** — sepsis definition, SOFA criteria.
  - **ACC/AHA ASCVD Risk (2013)** — interpretation and management.
  - **TIMI UA/NSTEMI (2000)** — risk assessment.
  - **GOLD COPD 2024** — spirometric grading, ABE assessment, initial pharmacotherapy.
  - **AHA/ACC Chest Pain 2021** — HEART score risk stratification, acute management.
  - **AHA/ASA Acute Ischemic Stroke 2019** — initial assessment, thrombolysis, thrombectomy.
  - **AASLD Cirrhosis 2023** — Child-Pugh/MELD-Na staging, complications management.
  - **ESC ACS 2023** — GRACE score risk stratification, antithrombotic therapy, invasive strategy.
  - **NICE Upper GI Bleeding CG141** — risk assessment, resuscitation, endoscopic management.
  - **RCP NEWS2 2017** — scoring system, clinical response.
- **Calculator cross-references** — added `# Related guidelines:` comments to numerous calculators routing to their respective guidelines.
- **Hundreds of new tests** covering the new calculators and guidelines.

### Changed
- Enhanced multiple existing guideline content files (e.g. KDIGO CKD, BTS CAP, ACC/AHA AFib) with more actionable drug information and executable decision algorithms following the "UpToDate for Agents" standard.


## [0.1.0] - 2026-02-22

### Added
- **10 Clinical Calculators:** ASCVD, CHA₂DS₂-VASc, SOFA, CKD-EPI (2021 race-free), Cockcroft-Gault, Rivaroxaban Dosing, Enoxaparin Dosing, GCS, HAS-BLED, CURB-65.
- **Clinical Guideline Retrieval Engine:** `search_guidelines` and `retrieve_guideline` with 3 seed guidelines (ACC/AHA AF 2023, KDIGO CKD 2024, BTS CAP 2009) and 9 curated sections.
- **Meta-Tool MCP Architecture:** `search_clinical_calculators` and `execute_clinical_calculator` for scalable tool discovery by AI agents.
- **MCP Server:** `open-medicine-mcp` CLI command.
- **Foundation:** `ClinicalResult` and `Evidence` base classes with DOI traceability and FHIR/LOINC code support.
- **57 tests:** Unit tests, comparative validation, and Hypothesis property-based bounds tests.
