# Risk Assessment and Diagnosis of Osteoporosis in Postmenopausal Women — Endocrine Society 2020

## WHO Diagnostic Criteria

Osteoporosis in postmenopausal women is diagnosed using dual-energy X-ray absorptiometry (DXA) based on the WHO classification of bone mineral density (BMD):

| Category | T-score |
|---|---|
| **Normal** | T-score >= -1.0 |
| **Osteopenia (low bone mass)** | T-score between -1.0 and -2.5 |
| **Osteoporosis** | T-score <= -2.5 |
| **Severe (established) osteoporosis** | T-score <= -2.5 with one or more fragility fractures |

- T-score is measured at the **femoral neck**, **total hip**, or **lumbar spine** (L1-L4).
- The femoral neck T-score is the reference standard for the WHO classification.

## Indications for Pharmacological Treatment

In the United States, the Endocrine Society recommends pharmacological therapy for postmenopausal women meeting any of the following criteria:

1. **Prior hip or vertebral fracture** (clinical or morphometric) (Strong Recommendation, High-Quality Evidence, 1|++++).
2. **T-score <= -2.5** at the femoral neck, total hip, or lumbar spine by DXA.
3. **T-score between -1.0 and -2.5 (osteopenia)** AND a 10-year probability based on the US-adapted FRAX tool of:
   - **>= 20%** for major osteoporotic fracture (MOF: clinical vertebral, hip, forearm, or proximal humerus), OR
   - **>= 3%** for hip fracture.

> **OpenMedicine Calculator:** `calculate_frax` -- available via MCP for automated FRAX 10-year fracture risk estimation.

## FRAX Risk Assessment

The FRAX tool integrates the following clinical risk factors to estimate 10-year fracture probability:

| Risk Factor | Description |
|---|---|
| **Age** | Validated for ages 40-90 years |
| **Sex** | Female (this guideline applies to postmenopausal women) |
| **BMI** | Body mass index (kg/m^2) |
| **Prior fragility fracture** | Including morphometric vertebral fracture |
| **Parental hip fracture** | History of hip fracture in mother or father |
| **Current smoking** | Active tobacco use |
| **Glucocorticoid use** | Current or >= 3 months at >= 5 mg/day prednisolone equivalent |
| **Rheumatoid arthritis** | Confirmed diagnosis |
| **Secondary osteoporosis** | Type I diabetes, osteogenesis imperfecta, untreated hyperthyroidism, hypogonadism, premature menopause (< 45 years), chronic malnutrition/malabsorption, chronic liver disease |
| **Alcohol >= 3 units/day** | 3 or more alcoholic drinks daily |
| **Femoral neck BMD T-score** | Optional; calculation can be done with or without BMD |

### FRAX Interpretation for Treatment Decisions

- If FRAX **hip fracture probability >= 3%** OR **major osteoporotic fracture probability >= 20%** --> pharmacological treatment is recommended.
- If both thresholds are below these values --> lifestyle modifications, calcium and vitamin D supplementation, weight-bearing exercise, and fall prevention.
- FRAX should be used in conjunction with DXA when T-score is in the osteopenic range (-1.0 to -2.5).

## Risk Stratification: High vs. Very High Risk

The guideline distinguishes between high-risk and very high-risk categories to guide treatment intensity:

### High Risk of Fracture

- T-score <= -2.5 at the femoral neck, total hip, or lumbar spine
- T-score between -1.0 and -2.5 with FRAX >= 20% MOF or >= 3% hip fracture
- Prior low-trauma fracture

### Very High Risk of Fracture

- T-score <= -2.5 **with** one or more fragility fractures (severe/established osteoporosis)
- Multiple vertebral fractures
- Fracture within the past 12 months (imminent fracture risk)
- Fractures while on approved osteoporosis therapy
- T-score <= -3.0 even without fracture history (very low BMD)
- High fall risk combined with low BMD
- Very high FRAX probability (e.g., > 30% MOF or > 4.5% hip)

The distinction between high and very high risk determines whether initial therapy should be antiresorptive (bisphosphonates, denosumab) or anabolic (teriparatide, abaloparatide, romosozumab).

## Screening Recommendations

- DXA screening is recommended for all women aged **>= 65 years**.
- DXA screening is recommended for postmenopausal women **< 65 years** with clinical risk factors for osteoporosis (e.g., low body weight, prior fracture, high-risk medication use, disease or condition associated with bone loss).
- Vertebral fracture assessment (VFA) by DXA or lateral spine X-ray should be considered in women aged >= 70 years or with historical height loss >= 1.5 inches (4 cm).

## Limitations

- FRAX underestimates fracture risk in patients with multiple risk factors, recent fracture, multiple vertebral fractures, high-dose glucocorticoid use, or type 2 diabetes.
- DXA T-score at a single site may not capture the full extent of skeletal fragility.
- The treatment thresholds (>= 20% MOF, >= 3% hip) are derived from cost-effectiveness analyses in the US population and may not be applicable to other countries without country-specific calibration.
- FRAX does not account for dose-response relationships (e.g., number of prior fractures, glucocorticoid dose, alcohol intake beyond 3 units).
