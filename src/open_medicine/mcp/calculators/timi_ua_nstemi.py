from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class TIMIUANSTEMIParams(BaseModel):
    """Parameters to calculate the TIMI Risk Score for UA/NSTEMI."""
    age_gte_65: bool = Field(False, description="Age ≥ 65 years")
    three_or_more_cad_risk_factors: bool = Field(False, description="≥3 CAD risk factors (family hx, HTN, hypercholesterolemia, DM, smoking)")
    known_cad_gte_50_stenosis: bool = Field(False, description="Known CAD with ≥50% coronary stenosis")
    aspirin_use_past_7_days: bool = Field(False, description="ASA/aspirin use in the past 7 days")
    two_or_more_anginal_events_24h: bool = Field(False, description="≥2 anginal events in the past 24 hours")
    st_deviation_gte_0_5mm: bool = Field(False, description="ST deviation ≥ 0.5mm on presenting ECG")
    elevated_cardiac_markers: bool = Field(False, description="Elevated cardiac markers (troponin or CK-MB)")


def calculate_timi_ua_nstemi(params: TIMIUANSTEMIParams) -> ClinicalResult:
    """
    Calculates the TIMI Risk Score for Unstable Angina/NSTEMI.
    Reference: Antman EM et al. JAMA. 2000.
    """
    score = sum([
        params.age_gte_65,
        params.three_or_more_cad_risk_factors,
        params.known_cad_gte_50_stenosis,
        params.aspirin_use_past_7_days,
        params.two_or_more_anginal_events_24h,
        params.st_deviation_gte_0_5mm,
        params.elevated_cardiac_markers,
    ])

    evidence = Evidence(
        source_doi="10.1001/jama.284.7.835",
        level="Derivation & Validation Study",
        description="The TIMI risk score for unstable angina/non-ST elevation MI (Antman EM et al., JAMA, 2000)"
    )

    if score <= 2:
        risk_level = "Low"
        event_rate = "≤8.3%"
        recommendation = "Consider non-invasive evaluation and conservative management."
    elif score <= 4:
        risk_level = "Intermediate"
        event_rate = "13.2-19.9%"
        recommendation = "Consider early invasive strategy."
    else:
        risk_level = "High"
        event_rate = "26.2-40.9%"
        recommendation = "Early invasive strategy strongly recommended."

    interpretation = (
        f"TIMI UA/NSTEMI Risk Score is {score}/7. "
        f"{risk_level} risk: {event_rate} risk of all-cause mortality, MI, or urgent revascularization at 14 days. "
        f"{recommendation}"
    )

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="96574-7",  # LOINC approximation: Acute cardiac risk assessment panel
        fhir_system="http://loinc.org",
        fhir_display="TIMI risk score for UA/NSTEMI"
    )
