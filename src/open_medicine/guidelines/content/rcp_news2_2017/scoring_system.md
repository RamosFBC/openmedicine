# NEWS2 Scoring System — RCP 2017

## Overview

The National Early Warning Score 2 (NEWS2) is a standardised scoring system developed by the Royal College of Physicians (RCP) for the assessment of acute-illness severity. It is endorsed by NHS England and NHS Improvement as the early warning system for identifying acutely ill patients — including those with sepsis — in hospitals.

## Physiological Parameters and Scoring

NEWS2 uses **6 physiological parameters** plus a supplemental oxygen adjustment. Each parameter is scored based on how far it deviates from normal.

### Scoring Table — Scale 1 (Standard)

| Parameter | 3 | 2 | 1 | 0 | 1 | 2 | 3 |
|---|---|---|---|---|---|---|---|
| **Respiration Rate** (breaths/min) | ≤ 8 | | 9–11 | 12–20 | | 21–24 | ≥ 25 |
| **SpO₂ Scale 1** (%) | ≤ 91 | 92–93 | 94–95 | ≥ 96 | | | |
| **Systolic BP** (mmHg) | ≤ 90 | 91–100 | 101–110 | 111–219 | | | ≥ 220 |
| **Pulse** (bpm) | ≤ 40 | | 41–50 | 51–90 | 91–110 | 111–130 | ≥ 131 |
| **Consciousness** (ACVPU) | | | | Alert | | | Confusion, V, P, or U |
| **Temperature** (°C) | ≤ 35.0 | | 35.1–36.0 | 36.1–38.0 | 38.1–39.0 | ≥ 39.1 | |

### Supplemental Oxygen
- **On supplemental oxygen:** Add **2 points** to the total score.

### SpO₂ Scale 2 — For Confirmed Hypercapnic Respiratory Failure

Scale 2 should ONLY be used for patients with **confirmed hypercapnic respiratory failure** (e.g., COPD with documented type 2 respiratory failure) who have a prescribed target SpO₂ range of 88–92%.

| SpO₂ Scale 2 | 3 | 2 | 1 | 0 (on air) | 0 (on O₂) | 1 (on O₂) | 2 (on O₂) | 3 (on O₂) |
|---|---|---|---|---|---|---|---|---|
| **SpO₂ (%)** | ≤ 83 | 84–85 | 86–87 | 88–92 | 93–94 | 95–96 | ≥ 97 | ≥ 97 |

> For Scale 2 patients: SpO₂ of 88–92% on air scores 0. SpO₂ of 93–94% **on supplemental O₂** scores 1 (because oxygen is being administered to a patient whose target range is 88–92%, suggesting the patient is receiving more oxygen than their target).

### Consciousness Level — ACVPU Scale

| Level | Description | NEWS2 Score |
|---|---|---|
| **A** | Alert | 0 |
| **C** | New Confusion* | 3 |
| **V** | Responds to Voice | 3 |
| **P** | Responds to Pain | 3 |
| **U** | Unresponsive | 3 |

*New-onset confusion, disorientation, and/or agitation where previously the mental state was normal. This may be subtle — the patient may respond to questions coherently but with some confusion. This corresponds to GCS verbal response of 3 or 4 (rather than normal 5).

> **OpenMedicine Calculator:** `calculate_news2` — available via MCP for automated NEWS2 scoring across all parameters.

## Score Interpretation

| NEWS2 Score | Clinical Risk | Frequency of Monitoring |
|---|---|---|
| **0** | Low | Minimum every 12 hours |
| **1–4** (total) | Low | Minimum every 4–6 hours |
| **3** in any single parameter | Low–Medium | Minimum every 1 hour |
| **5–6** (total) | Medium | Minimum every 1 hour |
| **≥ 7** | High | Continuous or minimum every 30 minutes |

## Limitations

- NEWS2 was designed and validated for use in **adult hospital patients** (≥ 16 years). It is NOT validated for obstetric patients, children, or patients with spinal cord injury affecting autonomic function.
- Scale 2 should only be used with a confirmed diagnosis of hypercapnic respiratory failure and a documented target SpO₂ of 88–92%. Using Scale 2 inappropriately may mask genuine hypoxia.
- A single normal NEWS2 score does not exclude clinical deterioration — serial assessment with trending is essential.
- NEWS2 does not replace clinical judgment. An experienced clinician may identify clinical concern not captured by the score.
