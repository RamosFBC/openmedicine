# Differential Diagnosis Expansion Roadmap

**Date:** 2026-03-11
**Status:** Approved
**Goal:** Expand differential diagnoses from 2 → 32, maximizing cross-links to existing 90 calculators and 44 guidelines.

## Context

The project has strong calculator and guideline coverage but only 2 differentials (chest_pain, dyspnea). Differentials provide unique value that LLMs cannot infer: ranked diagnosis lists with evidence-backed likelihoods, red flags, and cross-links to calculators.

Routing and pathways were removed in this session — routing duplicated LLM tool-composition ability, pathways duplicated guideline content with dual-maintenance risk.

## Execution

Each phase is a single `/add-differential` batch call. Subagents handle all research, JSON creation, and testing. The supervisor only runs the full test suite to confirm no conflicts.

---

## Phase 1 — High Cross-Link Density (12 differentials)

Each connects to 3+ existing calculators or guidelines.

| # | ID | Presentation | Calculator Cross-Links | Guideline Cross-Links |
|---|---|---|---|---|
| 1 | `abdominal_pain` | Acute abdominal pain | bisap, ransons, child_pugh, meld_na | acg_acute_pancreatitis_2024, aasld_cirrhosis_2023 |
| 2 | `syncope` | Syncope / presyncope | heart_score, wells_pe, perc, corrected_qtc | acc_aha_chest_pain_2021 |
| 3 | `altered_mental_status` | Altered mental status | gcs, cam_icu, sofa, serum_osmolality, corrected_sodium | sepsis3_2016, ssc_sepsis_2021 |
| 4 | `fever` | Fever / undifferentiated infection | news2, qsofa, sofa, curb65, psi_port | ssc_sepsis_2021, ats_idsa_cap_2019 |
| 5 | `headache` | Acute headache | gcs, hunt_hess, fisher_grade, nihss | aha_asa_sah_2023, aha_asa_ich_2022 |
| 6 | `lower_extremity_swelling` | Unilateral leg swelling | wells_dvt, wells_pe, perc | ash_vte_2020 |
| 7 | `acute_kidney_injury` | AKI / rising creatinine | ckd_epi, cockcroft_gault, renal_dose_adjustment, sofa | kdigo_aki_2012, kdigo_ckd_2024 |
| 8 | `liver_disease` | Acute/chronic liver disease | child_pugh, meld_na, fib4, nafld_fibrosis | aasld_cirrhosis_2023, aasld_nafld_2023 |
| 9 | `joint_pain` | Acute monoarthritis / polyarthritis | das28 | acr_gout_2020, acr_ra_2021 |
| 10 | `palpitations` | Palpitations / arrhythmia | chadsvasc, hasbled, corrected_qtc | acc_aha_af_2023 |
| 11 | `sore_throat` | Sore throat / pharyngitis | centor_mcisaac | — |
| 12 | `bleeding_disorders` | Abnormal bleeding / coagulopathy | isth_dic, 4ts_hit, hasbled | ash_vte_2020 |

**Batch command:**
```
/add-differential abdominal_pain syncope altered_mental_status fever headache lower_extremity_swelling acute_kidney_injury liver_disease joint_pain palpitations sore_throat bleeding_disorders
```

---

## Phase 2 — Medium Cross-Link (10 differentials)

Each connects to 1-2 existing tools + covers high-impact presentations.

| # | ID | Presentation | Calculator Cross-Links | Guideline Cross-Links |
|---|---|---|---|---|
| 13 | `cough` | Chronic/acute cough | curb65, psi_port, gold_copd | ats_idsa_cap_2019, gina_asthma_2024, gold_copd_2024 |
| 14 | `hyperglycemia` | Hyperglycemia / DKA / new diabetes | anion_gap, serum_osmolality, corrected_sodium | ada_diabetes_2024, ada_dka_hhs_2024 |
| 15 | `hypertension_emergency` | Hypertensive urgency/emergency | ascvd, framingham | acc_aha_hypertension_2017 |
| 16 | `urinary_symptoms` | Dysuria / UTI / urinary complaints | ipss | idsa_uti_2022 |
| 17 | `depression_anxiety` | Depression / anxiety screening | phq9, gad7, audit_c, cage, epds | apa_mdd_2023, acog_perinatal_depression_2018 |
| 18 | `gi_bleeding` | GI bleeding (upper + lower) | glasgow_blatchford, aims65, rockall | nice_ugib_2012 |
| 19 | `wheezing` | Wheezing / bronchospasm | gold_copd, news2 | gina_asthma_2024, gold_copd_2024 |
| 20 | `anemia` | Anemia workup | — | — |
| 21 | `nausea_vomiting` | Nausea / vomiting | corrected_calcium, serum_osmolality | — |
| 22 | `back_pain` | Acute low back pain | canadian_cspine | — |

**Batch command:**
```
/add-differential cough hyperglycemia hypertension_emergency urinary_symptoms depression_anxiety gi_bleeding wheezing anemia nausea_vomiting back_pain
```

---

## Phase 3 — Long-Tail (8 differentials)

Clinically important presentations with fewer existing cross-links.

| # | ID | Presentation | Calculator Cross-Links | Guideline Cross-Links |
|---|---|---|---|---|
| 23 | `dizziness` | Dizziness / vertigo | — | — |
| 24 | `fatigue` | Chronic fatigue | phq9, gad7 | apa_mdd_2023 |
| 25 | `weight_loss` | Unintentional weight loss | ecog, karnofsky | ada_diabetes_2024 |
| 26 | `rash` | Acute rash / skin eruption | — | — |
| 27 | `trauma` | Blunt/penetrating trauma triage | gcs, rts, canadian_cspine, parkland, tbsa | btf_tbi_2016, aba_burn_2016 |
| 28 | `pediatric_fever` | Pediatric fever / febrile child | pediatric_gcs, pews | — |
| 29 | `confusion_elderly` | Acute confusion in elderly | gcs, cam_icu, clinical_frailty | — |
| 30 | `burns` | Burn injury assessment | parkland, tbsa, bsa_mosteller | aba_burn_2016 |

**Batch command:**
```
/add-differential dizziness fatigue weight_loss rash trauma pediatric_fever confusion_elderly burns
```

---

## Totals

| Phase | Differentials | Calculator Cross-Links | Guideline Cross-Links |
|---|---|---|---|
| Phase 1 | 12 | ~45 | ~15 |
| Phase 2 | 10 | ~20 | ~10 |
| Phase 3 | 8 | ~12 | ~4 |
| **Total** | **30 new** | **~77** | **~29** |

Final library: **32 differentials** (2 existing + 30 new).
