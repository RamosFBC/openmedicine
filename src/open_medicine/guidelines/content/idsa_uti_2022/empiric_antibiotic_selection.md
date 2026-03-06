# Empiric Antibiotic Selection for Complicated UTI — IDSA 2022

## Four-Step Empiric Selection Framework

The IDSA recommends a **four-step process** applied at the point of care to guide the initial empiric antibiotic choice for each patient with complicated UTI.

### Step 1: Assess Severity of Illness

Determine whether the patient has **sepsis** (life-threatening organ dysfunction due to infection, SOFA score >=2) or **no sepsis**. This distinction guides the initial prioritization of empiric antibiotics.

> **OpenMedicine Calculator:** `calculate_sofa` — available via MCP for automated SOFA scoring. `calculate_qsofa` — available via MCP for bedside qSOFA screening.

### Step 2: Evaluate Patient-Specific Risk Factors for Resistance

- Review prior urine and blood culture results for resistant isolates
- **Avoid fluoroquinolones** if the patient has received a fluoroquinolone within the **past 12 months** (increased risk of fluoroquinolone-resistant uropathogens)
- Assess recent antibiotic exposure, healthcare facility exposure, and prior MDR infection

### Step 3: Account for Patient-Specific Considerations

- Drug allergies and hypersensitivity (especially beta-lactam allergy)
- Contraindications (e.g., fluoroquinolone-associated tendinopathy, aortic aneurysm risk)
- Drug-drug interactions
- Renal function and dosing adjustments
- Route of administration feasibility (IV vs oral)

### Step 4: Consult a Local Antibiogram (Sepsis Cases)

For patients with **sepsis**, consult a recent, relevant local antibiogram to guide empiric selection:

| Severity | Antibiogram Susceptibility Threshold |
|---|---|
| **Septic shock** | Select an antibiotic for which >=90% of the most relevant organisms are susceptible |
| **Sepsis without shock** | Select an antibiotic for which >=80% of the most relevant organisms are susceptible |

For patients **without sepsis**, no specific recommendation is made regarding antibiogram use for further tailoring empiric antibiotic choice.

## Empiric Antibiotic Recommendations by Severity

### Sepsis Due to Complicated UTI

For patients with **sepsis** due to cUTI, the IDSA suggests initially selecting among the following (Conditional, Very Low to Moderate Certainty):

| Antibiotic Class | Specific Agents |
|---|---|
| **Third/fourth-generation cephalosporins** | Ceftriaxone, ceftazidime, cefotaxime, cefepime |
| **Carbapenems** | Meropenem, imipenem-cilastatin, ertapenem, doripenem |
| **Piperacillin-tazobactam** | Piperacillin-tazobactam |
| **Fluoroquinolones** | Levofloxacin, ciprofloxacin |

### Non-Sepsis Complicated UTI

For patients with suspected cUTI **without sepsis** (including acute pyelonephritis), the IDSA suggests initially selecting among the following, **rather than carbapenems and newer agents** (Conditional, Very Low to Moderate Certainty):

| Antibiotic Class | Specific Agents |
|---|---|
| **Third/fourth-generation cephalosporins** | Ceftriaxone, ceftazidime, cefotaxime, cefepime |
| **Piperacillin-tazobactam** | Piperacillin-tazobactam |
| **Fluoroquinolones** | Levofloxacin, ciprofloxacin |

- **Carbapenems** should be reserved for sepsis or confirmed/suspected ESBL-producing organisms in non-sepsis cases.

### Alternative/Reserve Agents

The following agents are reserved for confirmed resistant organisms or when preferred agents cannot be used:

- **Novel beta-lactam/beta-lactamase inhibitor combinations:** Ceftazidime-avibactam, ceftolozane-tazobactam
- **Cefiderocol**
- **Plazomicin**
- **Aminoglycosides** (gentamicin, tobramycin, amikacin)

## IV Antibiotic Dosing for Complicated UTI

| Agent | IV Dose | Frequency | Notes |
|---|---|---|---|
| **Ceftriaxone** | 1-2 g | Every 24 hours | Preferred cephalosporin; once-daily dosing |
| **Cefepime** | 2 g | Every 8 hours | Fourth-generation; covers Pseudomonas |
| **Ceftazidime** | 2 g | Every 8 hours | Third-generation; covers Pseudomonas |
| **Meropenem** | 1 g | Every 8 hours | Reserve for sepsis or resistant organisms |
| **Ertapenem** | 1 g | Every 24 hours | No Pseudomonas coverage |
| **Imipenem-cilastatin** | 500 mg | Every 6 hours | Lower seizure threshold |
| **Piperacillin-tazobactam** | 4.5 g | Every 6-8 hours | Broad gram-negative coverage |
| **Levofloxacin** | 750 mg | Every 24 hours | IV or oral; high bioavailability |
| **Ciprofloxacin** | 400 mg | Every 12 hours | IV formulation |

## Outpatient Empiric Therapy (Non-Sepsis)

For patients with non-sepsis cUTI who can be managed as outpatients:

- **Fluoroquinolones** (levofloxacin 750 mg PO daily, ciprofloxacin 500 mg PO BID or 750 mg PO BID)
- **TMP-SMX** (1 DS tablet [160/800 mg] PO BID) — if susceptibility is known or local resistance is low
- **Amoxicillin-clavulanate** (875/125 mg PO TID) — less well studied; may be appropriate in select settings

## Clinical Decision Algorithm

```
Patient presents with suspected complicated UTI
  |
  +--> Step 1: Assess for sepsis (SOFA >=2)
  |     |
  |     +--> SEPSIS PRESENT
  |     |     |
  |     |     +--> Step 2: Any fluoroquinolone use in past 12 months?
  |     |     |     YES --> Avoid fluoroquinolones; prefer cephalosporin or carbapenem
  |     |     |     NO --> Fluoroquinolone remains an option
  |     |     |
  |     |     +--> Step 3: Allergies? Renal function? Drug interactions?
  |     |     |     Adjust agent selection accordingly
  |     |     |
  |     |     +--> Step 4: Consult local antibiogram
  |     |           Septic shock: select agent with >=90% susceptibility
  |     |           Sepsis without shock: select agent with >=80% susceptibility
  |     |           --> Choose from: cephalosporin, carbapenem, pip-tazo, or FQ
  |     |
  |     +--> NO SEPSIS
  |           |
  |           +--> Step 2: Any fluoroquinolone use in past 12 months?
  |           |     YES --> Avoid fluoroquinolones
  |           |     NO --> Fluoroquinolone remains an option
  |           |
  |           +--> Step 3: Allergies? Renal function? Oral feasibility?
  |           |     Can take oral? --> Consider outpatient fluoroquinolone or TMP-SMX
  |           |     Requires IV? --> Cephalosporin or pip-tazo (avoid carbapenems)
  |           |
  |           +--> Obtain urine culture before or at initiation of therapy
  |                Reassess at 48-72 hours with culture results
```

## Key Principles

- **Obtain urine culture** before starting antibiotics whenever feasible
- **De-escalate** to narrowest-spectrum effective agent once culture and susceptibility data are available
- The empiric selection framework prioritizes avoiding unnecessary use of **carbapenems** and **novel agents** in non-sepsis cases to preserve antimicrobial stewardship
- Reassess within **48-72 hours** if the patient is not improving; consider imaging (CT abdomen/pelvis) or escalation of therapy

## Limitations

- These recommendations are based primarily on studies of community-acquired uropathogens. Patients with healthcare-associated or multidrug-resistant infections may require broader empiric coverage.
- Evidence for the four-step framework comes from expert consensus and observational data rather than randomized trials comparing this approach to other selection strategies.
- Local antibiogram data may not reflect individual patient risk, particularly for patients with prior resistant isolates.
