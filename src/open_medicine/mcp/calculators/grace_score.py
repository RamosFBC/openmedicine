from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence

# Related guidelines: esc_acs_2023 (risk_stratification, antithrombotic_therapy, invasive_strategy sections)


class GRACEScoreParams(BaseModel):
    """Parameters to calculate the GRACE 2.0 Score for ACS risk stratification."""
    age: int = Field(..., description="Age in years")
    heart_rate: int = Field(..., description="Heart rate in bpm")
    systolic_bp: int = Field(..., description="Systolic blood pressure in mmHg")
    creatinine: float = Field(..., description="Serum creatinine in mg/dL")
    killip_class: int = Field(..., ge=1, le=4, description="Killip class: 1=No CHF, 2=Rales/JVD, 3=Pulmonary edema, 4=Cardiogenic shock")
    cardiac_arrest_at_admission: bool = Field(False, description="Cardiac arrest at admission")
    st_segment_deviation: bool = Field(False, description="ST-segment deviation on ECG")
    elevated_cardiac_enzymes: bool = Field(False, description="Elevated cardiac enzymes/markers")


def _age_score(age: int) -> int:
    if age < 30: return 0
    if age < 40: return 8
    if age < 50: return 25
    if age < 60: return 41
    if age < 70: return 58
    if age < 80: return 75
    if age < 90: return 91
    return 100


def _hr_score(hr: int) -> int:
    if hr < 50: return 0
    if hr < 70: return 3
    if hr < 90: return 9
    if hr < 110: return 15
    if hr < 150: return 24
    if hr < 200: return 38
    return 46


def _sbp_score(sbp: int) -> int:
    if sbp < 80: return 58
    if sbp < 100: return 53
    if sbp < 120: return 43
    if sbp < 140: return 34
    if sbp < 160: return 24
    if sbp < 200: return 10
    return 0


def _creatinine_score(cr: float) -> int:
    if cr < 0.4: return 1
    if cr < 0.8: return 4
    if cr < 1.2: return 7
    if cr < 1.6: return 10
    if cr < 2.0: return 13
    if cr < 4.0: return 21
    return 28


def _killip_score(killip: int) -> int:
    return {1: 0, 2: 20, 3: 39, 4: 59}[killip]


def calculate_grace_score(params: GRACEScoreParams) -> ClinicalResult:
    """
    Calculates the GRACE Score (simplified integer version) for ACS risk stratification.
    Reference: Fox KA et al. BMJ. 2006.
    """
    score = (
        _age_score(params.age)
        + _hr_score(params.heart_rate)
        + _sbp_score(params.systolic_bp)
        + _creatinine_score(params.creatinine)
        + _killip_score(params.killip_class)
        + (39 if params.cardiac_arrest_at_admission else 0)
        + (28 if params.st_segment_deviation else 0)
        + (14 if params.elevated_cardiac_enzymes else 0)
    )

    evidence = Evidence(
        source_doi="10.1136/bmj.38985.646481.55",
        level="Derivation & Validation Study",
        description="Prediction of risk of death and myocardial infarction in the six months after presentation with ACS (Fox KA et al., BMJ, 2006)"
    )

    if score <= 108:
        risk_level = "Low"
        mortality = "<1%"
    elif score <= 140:
        risk_level = "Intermediate"
        mortality = "1-3%"
    else:
        risk_level = "High"
        mortality = ">3%"

    interpretation = (
        f"GRACE Score is {score}. "
        f"{risk_level} risk: estimated in-hospital mortality {mortality}. "
        f"{'Consider conservative management.' if risk_level == 'Low' else 'Consider early invasive strategy.' if risk_level == 'High' else 'Clinical judgment for invasive vs conservative strategy.'}"
    )

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="96574-7",  # LOINC approximation: Acute cardiac risk assessment panel
        fhir_system="http://loinc.org",
        fhir_display="GRACE score"
    )
