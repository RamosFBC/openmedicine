# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-03-06

### Added
- **28 New Clinical Calculators (Phases 5-7):**
  - **Cross-Domain Essentials (Phase 5):** RCRI (Revised Cardiac Risk Index), Charlson Comorbidity Index, ECOG Performance Status, Karnofsky Performance Status, Apgar Score, PSI/PORT (Pneumonia Severity Index), Clinical Frailty Scale, TBSA Rule of Nines, Edinburgh Postnatal Depression Scale (EPDS), CAGE Questionnaire.
  - **Infectious Disease & Toxicology (Phase 6):** MASCC Score (Febrile Neutropenia), Modified Duke Criteria (Endocarditis), CIWA-Ar (Alcohol Withdrawal), COWS (Clinical Opiate Withdrawal Scale), Rumack-Matthew Nomogram (Acetaminophen Toxicity), Naranjo ADR Probability Scale, IPSS (International Prostate Symptom Score), MEWS (Modified Early Warning Score).
  - **ICU/Delirium & Pediatrics (Phase 7):** CAM-ICU (Confusion Assessment Method), RASS (Richmond Agitation-Sedation Scale), STOP-BANG (OSA Screening), AIMS65 (Upper GI Bleed Mortality), Pediatric GCS, PEWS (Pediatric Early Warning Score), LRINEC (Necrotizing Fasciitis), CRB-65 (Community Pneumonia).
- **7 New Clinical Guideline Modules:**
  - **ABA Burn Care 2016** — initial assessment, fluid resuscitation (Parkland formula), wound management, inhalation injury.
  - **ACOG Perinatal Depression 2018** — screening recommendations (EPDS), treatment during pregnancy, postpartum management.
  - **AHA/AAP NRP 2020** — neonatal resuscitation algorithm, Apgar scoring, initial steps, positive pressure ventilation.
  - **AHA Infective Endocarditis 2015** — Duke criteria, empiric/targeted antimicrobial therapy, surgical indications.
  - **IDSA Bacterial Meningitis 2017** — empiric antibiotics, dexamethasone adjunctive therapy, pathogen-specific treatment.
  - **IDSA Complicated UTI 2022** — diagnosis, empiric and targeted antimicrobial therapy, catheter-associated UTI.
  - **ACR Gout 2020** — urate-lowering therapy, acute flare management, treat-to-target strategy.
- **Property-based bounds tests** (Hypothesis) for all 28 new calculators.
- **Comparative validation tests** for Rumack-Matthew nomogram.
- **Cross-reference links** between new calculators and guidelines (Duke Criteria ↔ Endocarditis, CIWA-Ar ↔ AUD, PSI/PORT ↔ CAP, EPDS ↔ Perinatal Depression, TBSA ↔ Burn Care, Apgar ↔ NRP, CAGE ↔ AUD, CRB-65 ↔ CAP).
- **Project totals:** 92 calculators, 43 guideline modules, 2335 tests.

### Fixed
- Duke Criteria fuzz test corrected to match intentional design (no LOINC code exists for Duke classification).
- Minor fixes to GCS, Parkland, and PHQ-9 calculators.

## [0.4.0] - 2026-03-02

### Added
- **15 New Clinical Calculators (Phases 3-4):**
  - **Primary Care/ED:** Ottawa Ankle Rules, Centor/McIsaac Score.
  - **Psychiatry/Screening:** PHQ-9 (Depression), GAD-7 (Anxiety), AUDIT-C (Alcohol).
  - **Critical Care:** APACHE II.
  - **Hematology:** 4Ts HIT Score, ISTH DIC Score.
  - **Cardiology:** Framingham Risk Score.
  - **Fluids:** Maintenance IV Fluids (4-2-1 rule).
  - **Obstetrics:** Bishop Score.
  - **Rheumatology:** DAS28 (ESR/CRP variants).
  - **Endocrinology:** FRAX Fracture Risk Assessment.
- **13 New Clinical Guideline Modules:**
  - **ACC/AHA Cholesterol 2018** — statin therapy, nonstatin therapy, risk assessment, secondary prevention.
  - **SSC Sepsis 2021** — screening/early management, antimicrobial therapy, hemodynamics/vasopressors, ventilation/supportive care.
  - **ADA DKA/HHS 2024** — diagnosis, fluid resuscitation, insulin/electrolytes, resolution/transition.
  - **KDIGO AKI 2012** — definition/staging, prevention/management, RRT, contrast-induced AKI.
  - **GINA Asthma 2024** — diagnosis/assessment, pharmacotherapy, exacerbation management, severe asthma/biologics.
  - **AHA/ASA ICH 2022** — emergency diagnosis, BP management, hemostatic therapy, surgical/ICU management.
  - **BTF TBI 2016** — ICP monitoring, cerebral perfusion/hyperosmolar therapy, surgical/medical management, ventilation/supportive care.
  - **ATS/IDSA CAP 2019** — severity assessment, empiric antibiotics, microbiological testing, special populations.
  - **ACR RA 2021** — initial DMARD therapy, biologic/targeted DMARDs, treat-to-target, glucocorticoids/special populations.
  - **Endocrine Osteoporosis 2020** — risk assessment/diagnosis, pharmacotherapy, anabolic agents/sequencing, monitoring/drug holidays.
  - **APA MDD 2023** — pharmacotherapy, psychotherapy, treatment monitoring, special populations.
  - **APA AUD 2018** — assessment/screening, FDA-approved medications, off-label medications, psychosocial/combined treatment.
  - **ACC/AHA Perioperative 2014** — stepwise cardiac assessment, risk assessment, beta-blocker management, medication management.
- **Guideline cross-references** added to 9 existing calculators (anion_gap, ascvd, ckd_epi, cockcroft_gault, corrected_sodium, curb65, gcs, qsofa, sofa).
- **Property-based bounds tests** (Hypothesis) for all new Phase 3-4 calculators.
- **Comparative validation tests** for DAS28 and Maintenance IV Fluids.
- **Project totals:** 67 calculators, 36 guideline modules, 1189 tests.

### Fixed
- DAS28-ESR calculator now floors score at 0 (negative values from sub-physiologic ESR inputs are not clinically meaningful).
- Corrected DAS28-CRP comparative test vector (4.95 → 4.83 per formula).

## [0.3.1] - 2026-03-01

### Added
- **ACC/AHA Hypertension 2017 Clinical Guideline** — BP classification, initial pharmacotherapy, compelling indications, resistant hypertension, and special populations.

## [0.3.0] - 2026-02-28

### Added
- **8 New Clinical Guideline Modules:**
  - **AHA/ACC/HFSA Heart Failure 2022** — classification, pharmacotherapy (GDMT including SGLT2i, ARNI), device therapy (ICD, CRT).
  - **ADA Standards of Care in Diabetes 2024** — glycemic targets, pharmacotherapy (metformin, GLP-1 RA, SGLT2i), cardiovascular risk management.
  - **ASH VTE 2020** — anticoagulation therapy (DOACs, LMWH, warfarin), treatment duration, advanced management. Links 11 calculators.
  - **ACG Acute Pancreatitis 2024** — severity assessment (BISAP, Ranson's), initial management, biliary management, necrotizing pancreatitis.
  - **AHA/ASA Subarachnoid Hemorrhage 2023** — initial assessment (Hunt-Hess, Fisher), aneurysm treatment, medical management, delayed cerebral ischemia.
  - **AASLD NAFLD/MASLD 2023** — screening and diagnosis, fibrosis assessment (FIB-4, NAFLD Fibrosis Score), lifestyle and pharmacotherapy, monitoring and referral.
  - **AHA/ASA TIA 2009** — definition and risk stratification (ABCD2), diagnostic evaluation, early management.
  - **ACCF/AHA STEMI 2013** — reperfusion therapy (PCI vs fibrinolysis), antithrombotic therapy, routine medical therapy, complications (Killip classification, cardiogenic shock).
- **Calculator cross-references** — linked `timi_stemi` calculator to the new STEMI guideline.
- **72 new guideline tests** covering search and retrieval for all 8 new guidelines.

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
