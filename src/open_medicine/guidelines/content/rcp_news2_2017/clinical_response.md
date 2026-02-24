# Clinical Response to NEWS2 Triggers — RCP 2017

## NEWS2 Thresholds and Clinical Response Framework

The RCP NEWS2 report defines **graduated clinical response triggers** based on the aggregate NEWS2 score and individual parameter scores. The response framework ensures that the urgency and competency of the clinical response matches the severity of the patient's acute illness.

## Response Algorithm

### NEWS2 Score 0 — Routine Monitoring

- **Clinical Risk:** Low
- **Monitoring:** Continue routine NEWS2 monitoring at a **minimum of every 12 hours**.
- **Clinical Response:** Routine care. No escalation required.

### NEWS2 Score 1–4 — Ward-Based Assessment

- **Clinical Risk:** Low
- **Monitoring:** Increase to **minimum every 4–6 hours**.
- **Clinical Response:**
  - A **registered nurse** must assess the patient.
  - Decide whether increased monitoring frequency is required.
  - Decide whether escalation of clinical care is needed.

### Score of 3 in Any Single Parameter — Urgent Ward-Based Response

- **Clinical Risk:** Low–Medium (a score of 3 in a single parameter indicates marked physiological derangement)
- **Monitoring:** Increase to **minimum every 1 hour**.
- **Clinical Response:**
  - The registered nurse must **immediately inform the medical team** caring for the patient.
  - A **clinician competent in acute illness assessment** must review the patient.
  - Decide if escalation to a higher level of care is needed.
  - Determine the frequency of subsequent monitoring.

### NEWS2 Score 5–6 — Urgent Response (Key Threshold)

- **Clinical Risk:** Medium
- **Monitoring:** **Minimum hourly**, or every 30 minutes if clinical concern.
- **Clinical Response:**
  - This is the **key threshold for urgent clinical review and action**.
  - **Urgent assessment within 60 minutes** by a clinician or team with competencies in the assessment and treatment of acutely ill patients (ward-based doctor or acute team nurse).
  - The assessing team must decide whether escalation to a **critical care outreach team** or equivalent is required.
  - **Consider sepsis** if infection is suspected: initiate Sepsis-3 screening (see Sepsis-3 guideline).
  - Initiate appropriate clinical interventions as needed.

### NEWS2 Score ≥ 7 — Emergency Response

- **Clinical Risk:** High
- **Monitoring:** **Continuous vital sign monitoring** or minimum every 30 minutes.
- **Clinical Response:**
  - **Emergency assessment within 30 minutes** by a team with critical care competencies, including airway management skills.
  - **If no improvement:** Senior clinician review within 60 minutes.
  - The medical team, including senior doctors/consultants, must be **immediately informed**.
  - **Consider transfer** to a higher-dependency care area (HDU) or intensive care unit (ICU).
  - Initiate emergency clinical interventions.

> **OpenMedicine Calculator:** `calculate_news2` — available via MCP for automated NEWS2 scoring.

## Response Decision Tree

```
NEWS2 score calculated
  → Score = 0?
      → Routine monitoring (every 12 hours)
  → Score 1–4?
      → Ward-based nursing assessment (every 4–6 hours)
      → Any single parameter = 3?
          → YES → Urgent ward-based response
                   → Inform medical team immediately
                   → Hourly monitoring
          → NO → Continue ward-based monitoring
  → Score 5–6?
      → URGENT response within 60 minutes
      → Clinician with acute illness competencies must assess
      → Hourly monitoring (consider half-hourly)
      → Consider sepsis screening if infection suspected
      → Decide: escalate to critical care outreach?
  → Score ≥ 7?
      → EMERGENCY response within 30 minutes
      → Critical care team assessment
      → Continuous monitoring
      → Consider HDU/ICU transfer
      → Senior clinician review within 60 minutes if no improvement
```

## Special Considerations

### Sepsis
- NEWS2 ≥ 5 should prompt consideration of **sepsis** if there are clinical features of infection.
- NEWS2 is endorsed by NHS England as part of the sepsis identification pathway.
- If sepsis is suspected, initiate the Sepsis-3 pathway and the 1-hour bundle.

### Oxygen Therapy Escalation
- NEWS2 can help guide decisions about oxygen escalation:
  - If SpO₂ score is contributing significantly to a high total score, assess for the underlying cause of hypoxemia.
  - Do NOT simply increase supplemental O₂ to normalize the score — treat the underlying condition.

### Post-Surgical and Post-Procedure Patients
- Normal post-operative physiology (mild tachycardia, mild hypotension) may trigger NEWS2 alerts.
- Clinical teams should have **agreed post-operative observation parameters** and modify response protocols accordingly while still using NEWS2 for early detection of unexpected deterioration.

## Limitations

- NEWS2 is a **screening tool**, not a diagnostic tool. It identifies patients who may be deteriorating but does not diagnose the cause.
- Response times (30 minutes, 60 minutes) represent the **maximum acceptable delay** — not the target. Earlier response is always preferred.
- The framework assumes an appropriately staffed clinical environment. In understaffed settings, the response framework may not be achievable.
- NEWS2 does not account for the trajectory of change: a rapidly rising score (e.g., from 2 to 5 over 2 hours) may be more concerning than a stable score of 5.
