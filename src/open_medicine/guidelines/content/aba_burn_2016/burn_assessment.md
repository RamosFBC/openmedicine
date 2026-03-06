# Burn Assessment and Severity Classification — ABA 2016

## Burn Depth Classification

Burns are classified by depth of tissue injury. Only partial-thickness and full-thickness burns are included in TBSA calculations for fluid resuscitation purposes. Superficial (first-degree) burns are **excluded** from TBSA.

| Depth | Layers Involved | Appearance | Sensation | Healing |
|---|---|---|---|---|
| **Superficial (1st degree)** | Epidermis only | Pink to red, dry, no blisters, blanches with pressure | Painful | 5-10 days, no scarring |
| **Superficial partial-thickness (2nd degree)** | Epidermis + papillary dermis | Red/pink, moist, blisters, blanches with pressure | Very painful | 2-3 weeks, minimal scarring |
| **Deep partial-thickness (2nd degree)** | Epidermis + reticular dermis | Mottled, drier, sluggish blanching | Minimal pain | >3 weeks, unavoidable scarring |
| **Full-thickness (3rd degree)** | Epidermis + dermis + subcutaneous fat | White, brown, or charred; leathery, firm, dry; no blanching | No pain (insensate) | Requires surgical intervention; >8 weeks |

### Clinical Decision Logic

```
Assess burn wound
  -> Dry, red, no blisters, painful? -> Superficial -> Exclude from TBSA
  -> Moist, blistered, very painful, blanches? -> Superficial partial-thickness -> Include in TBSA
  -> Mottled, drier, minimal pain, sluggish blanching? -> Deep partial-thickness -> Include in TBSA
  -> White/leathery/charred, insensate, no blanching? -> Full-thickness -> Include in TBSA
```

## TBSA Assessment

### Rule of Nines (Adults)

The Wallace Rule of Nines provides a rapid estimation of TBSA burned in adults:

| Body Region | TBSA (%) |
|---|---|
| **Head and neck** | 9% |
| **Each upper extremity** | 9% (total 18%) |
| **Anterior trunk** (chest + abdomen) | 18% |
| **Posterior trunk** (upper + lower back) | 18% |
| **Each lower extremity** | 18% (total 36%) |
| **Perineum/genitalia** | 1% |
| **Total** | 100% |

> **OpenMedicine Calculator:** `calculate_tbsa` -- available via MCP for automated TBSA estimation using the Rule of Nines.

### Pediatric Modifications (Lund and Browder)

Children have proportionally larger heads and smaller legs than adults. The Lund and Browder chart is more accurate for pediatric patients:

| Body Region | Infant | 5 years | 10 years | 15 years |
|---|---|---|---|---|
| **Head** | 18% | 14% | 11% | 9% |
| **Each leg** | 13.5% | 16% | 17% | 18% |
| **Each arm** | 10% | 10% | 10% | 10% |
| **Anterior trunk** | 13% | 13% | 13% | 13% |
| **Posterior trunk** | 13% | 13% | 13% | 13% |

### Palmar Surface Method

For scattered or irregular burns, the patient's **palm alone** (excluding fingers) approximates **0.5% TBSA**; the **whole hand** (palm + fingers) approximates **1% TBSA**.

## Burn Severity Classification (ABA)

The American Burn Association classifies burn severity into three categories:

| Severity | Partial-Thickness TBSA | Full-Thickness TBSA | Special Criteria |
|---|---|---|---|
| **Minor** | <10% adults; <5% children/elderly | <2% | No high-risk areas, no inhalation injury |
| **Moderate** | 10-20% adults; 5-10% children/elderly | 2-5% | High-voltage injury, suspected inhalation, circumferential burns, immunocompromised patients |
| **Major** | >20% adults; >10% children/elderly | >5% | Known inhalation injury; burns of face, eyes, ears, genitalia, joints; significant associated injuries |

### Severity-Based Management Algorithm

```
Minor burn (<10% TBSA partial-thickness in adults)
  -> Outpatient management if no high-risk areas involved
  -> Evaluate for burn center referral if face, hands, feet, genitalia, perineum, major joints

Moderate burn (10-20% TBSA partial-thickness in adults)
  -> Hospital admission for IV fluid resuscitation
  -> Consider burn center referral per ABA criteria

Major burn (>20% TBSA partial-thickness in adults)
  -> Immediate burn center transfer
  -> IV fluid resuscitation per Parkland formula
  -> Assess for inhalation injury, associated trauma
```

## Burn Center Referral Criteria (ABA)

The following burn injuries should be referred to a verified burn center:

1. **Partial-thickness burns > 10% TBSA**
2. **Any full-thickness (3rd degree) burns**
3. **Burns involving face, hands, feet, genitalia, perineum, or major joints**
4. **Chemical burns**
5. **Electrical burns** (including lightning injury)
6. **Inhalation injury**
7. **Burns with pre-existing medical conditions** that could complicate management, prolong recovery, or affect mortality
8. **Burns with concomitant trauma** (e.g., fractures) where the burn injury poses the greatest risk of morbidity or mortality
9. **Burns in children** at hospitals without qualified personnel or equipment for pediatric care
10. **Burns requiring special social, emotional, or rehabilitative intervention** (including suspected child abuse)

### Referral Decision Logic

```
Any burn patient
  -> Full-thickness burn of any size? -> Refer to burn center
  -> Partial-thickness > 10% TBSA? -> Refer to burn center
  -> Face, hands, feet, genitalia, perineum, major joints involved? -> Refer to burn center
  -> Chemical or electrical injury? -> Refer to burn center
  -> Suspected inhalation injury? -> Refer to burn center
  -> Significant comorbidities? -> Refer to burn center
  -> Associated traumatic injuries? -> Refer to burn center
  -> Pediatric patient without specialized pediatric care? -> Refer to burn center
  -> None of the above? -> Manage locally with appropriate follow-up
```

### Pre-Transfer Considerations

- Initiate IV fluid resuscitation **before transfer** using the Parkland formula
- **Do not perform extensive debridement** or apply extensive topical antibiotics before transfer
- Cover burns with **clean, dry dressings** for transport
- Ensure **airway is secured** if inhalation injury is suspected
- Document **time of injury** (critical for fluid resuscitation timing)

> **OpenMedicine Calculator:** `calculate_parkland` -- available via MCP for automated Parkland formula calculation for fluid resuscitation.

## Limitations

- The Rule of Nines is an approximation and may be inaccurate in obese patients, patients with large body habitus, and pediatric patients (use Lund and Browder chart for children).
- Burn depth assessment is clinical and can be difficult to determine accurately in the first 24-48 hours; deep partial-thickness and full-thickness burns may appear similar initially.
- The ABA severity classification does not account for all variables that influence outcomes (e.g., patient age, comorbidities, time to treatment).
- Burn center referral criteria are guidelines, not absolute rules; clinical judgment should be applied in individual cases.
