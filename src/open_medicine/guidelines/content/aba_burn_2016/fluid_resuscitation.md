# Fluid Resuscitation in Burns — ABA 2016

## Indications for Fluid Resuscitation

Formal IV fluid resuscitation is indicated for:

- **Adults:** Burns exceeding **20% TBSA** (partial-thickness or full-thickness)
- **Children:** Burns exceeding **10-15% TBSA**
- **Oral resuscitation only:** May be appropriate for burns **< 30% TBSA** if the patient is alert, has no nausea/vomiting, and can tolerate oral intake

> **Key Rule:** Fluid resuscitation is most effective when initiated within the first 2 hours of injury. The resuscitation clock starts from the **time of burn injury**, not the time of hospital arrival.

## Parkland (Baxter) Formula

The Parkland formula is the most widely used crystalloid resuscitation formula:

**Total 24-hour fluid = 4 mL x body weight (kg) x % TBSA burned**

| Parameter | Value |
|---|---|
| **Fluid type** | Lactated Ringer's (LR) solution |
| **First 8 hours** | 50% of total calculated volume |
| **Next 16 hours** | Remaining 50% of total calculated volume |
| **Time zero** | Time of burn injury (not hospital arrival) |

### Worked Example

A 70 kg patient with 30% TBSA burn:
- Total 24h volume = 4 x 70 x 30 = **8,400 mL LR**
- First 8 hours: 4,200 mL (525 mL/hr)
- Next 16 hours: 4,200 mL (262.5 mL/hr)

> **OpenMedicine Calculator:** `calculate_parkland` -- available via MCP for automated Parkland formula calculation.

## Modified Brooke Formula

An alternative crystalloid resuscitation formula using lower initial volumes:

**Total 24-hour fluid = 2 mL x body weight (kg) x % TBSA burned**

| Parameter | Value |
|---|---|
| **Fluid type** | Lactated Ringer's (LR) solution |
| **First 8 hours** | 50% of total calculated volume |
| **Next 16 hours** | Remaining 50% of total calculated volume |

The Modified Brooke formula was developed to reduce the risk of over-resuscitation (fluid creep) while maintaining adequate end-organ perfusion.

## ABA Consensus Range

The ABA Advanced Burn Life Support (ABLS) programme recommends an initial crystalloid resuscitation rate of **2-4 mL/kg/% TBSA** over 24 hours, titrated to clinical endpoints. This range encompasses both the Modified Brooke (2 mL) and Parkland (4 mL) formulas.

### Fluid Selection

- **Lactated Ringer's (LR)** is the recommended initial resuscitation fluid across all age groups
- LR is preferred over normal saline (NS) due to its more physiological electrolyte composition and lower risk of hyperchloremic metabolic acidosis
- **Avoid hypotonic fluids** as they exacerbate edema formation

## Monitoring and Titration

Fluid resuscitation must be continuously titrated to clinical endpoints, **not administered as a fixed rate**.

### Adult Monitoring Targets

| Parameter | Target |
|---|---|
| **Urine output** | 0.5-1.0 mL/kg/hr (30-50 mL/hr for average adult) |
| **Systolic blood pressure** | > 90 mmHg |
| **Heart rate** | Trending toward normal |
| **Base deficit** | < 2 mEq/L |
| **Mental status** | Alert and oriented |
| **Peripheral pulses** | Palpable |

### Pediatric Monitoring Targets

| Parameter | Target |
|---|---|
| **Urine output (< 30 kg)** | 1 mL/kg/hr |
| **Urine output (> 30 kg)** | 0.5 mL/kg/hr |
| **Lactate** | Trending toward normal |

### Titration Algorithm

```
Begin LR at calculated rate (Parkland or Modified Brooke)
  -> Assess urine output hourly
      -> Urine output < 0.5 mL/kg/hr?
          -> Increase rate by 25-33%
          -> Reassess in 1 hour
      -> Urine output 0.5-1.0 mL/kg/hr?
          -> Maintain current rate
      -> Urine output > 1.0 mL/kg/hr?
          -> Decrease rate by 25-33%
          -> Reassess in 1 hour
  -> Assess for signs of over-resuscitation every 2-4 hours
      -> Pulmonary edema, abdominal distension, extremity tightness?
          -> Reduce rate, consider colloid rescue
```

## Pediatric Considerations

Children have higher fluid requirements relative to body weight due to:
- Greater body surface area-to-mass ratio
- Higher metabolic rate
- Limited glycogen stores (may require **dextrose supplementation** in maintenance fluids)

### Pediatric Formulas

| Formula | Calculation |
|---|---|
| **Parkland (pediatric)** | 3 mL/kg/% TBSA + maintenance fluids |
| **Cincinnati** | 4 mL/kg/% TBSA + 1,500 mL/m² BSA (maintenance) |
| **Galveston** | 5,000 mL/m² BSA burned + 2,000 mL/m² total BSA |

Maintenance fluids with dextrose (D5LR or D5 1/2NS) should be added to resuscitation fluids in children to prevent hypoglycemia.

## Colloid Administration

Albumin may be used as an adjunct to crystalloid resuscitation:

- **Indication:** Consider when crystalloid requirements are **exceeding predicted volumes** (> 6 mL/kg/% TBSA) and resuscitation goals are not being met
- **Typical formulation:** 5% albumin in LR
- **Timing:** May be started after the first 8-12 hours of resuscitation, or earlier as a rescue intervention
- **Rationale:** Reduces overall fluid volume requirements and may decrease edema

### When to Consider Colloid Rescue

```
Patient on crystalloid resuscitation
  -> At 8 hours, total fluid administered > calculated Parkland volume?
      -> Yes -> Consider 5% albumin infusion
      -> Urine output still < 0.5 mL/kg/hr despite increased crystalloid?
          -> Start 5% albumin at 0.5-1.0 mL/kg/hr
          -> Reassess in 2-4 hours
```

## Over-Resuscitation (Fluid Creep)

Excessive fluid administration is a significant iatrogenic complication. "More is not better" -- the risk of fluid overload can be as life-threatening as the burn injury itself.

### Complications of Over-Resuscitation

| Complication | Diagnostic Threshold |
|---|---|
| **Abdominal compartment syndrome** | Intra-abdominal pressure > 20 mmHg with end-organ dysfunction |
| **Extremity compartment syndrome** | Compartment pressure > 30 mmHg with circulatory impairment |
| **Pulmonary edema** | Clinical signs: dyspnea, hypoxemia, bilateral infiltrates |
| **Cerebral edema** | Altered mental status, papilledema |

### Prevention Strategies

- Titrate fluids to **urine output targets**, not formula predictions
- Avoid reflexive rate increases; allow 1 hour to assess response to rate changes
- Consider colloid administration early if crystalloid volumes are exceeding predictions
- Monitor intra-abdominal pressure in patients with large burns (> 40% TBSA) or when total resuscitation exceeds 250 mL/kg

## Special Populations

### Patients with Inhalation Injury

- Inhalation injury increases fluid requirements by approximately **30-40%** above predicted volumes
- Monitor closely for pulmonary edema, as these patients are at higher risk
- Earlier consideration of colloid rescue may be warranted

### Patients with Rhabdomyolysis

- Target urine output of **1 mL/kg/hr** (higher than standard targets)
- Monitor for myoglobinuria (dark/tea-colored urine)
- Consider sodium bicarbonate to alkalinize urine if myoglobinuria is present

### Electrical Burns

- TBSA may significantly underestimate the extent of deep tissue injury
- Fluid requirements are often **higher than predicted** by surface area calculations
- Monitor for rhabdomyolysis and cardiac arrhythmias

## Limitations

- All resuscitation formulas are **starting points**, not definitive prescriptions; they require continuous titration to clinical endpoints.
- The optimal balance between crystalloid and colloid resuscitation remains an area of active investigation.
- Urine output is an imperfect surrogate for end-organ perfusion; patients with diabetes insipidus, glycosuria, or receiving diuretics require alternative monitoring parameters.
- No single monitoring parameter is sufficient; clinical assessment must integrate multiple data points.
