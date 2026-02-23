import math
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class QTcMethod(str, Enum):
    BAZETT = "bazett"
    FRIDERICIA = "fridericia"


class CorrectedQTcParams(BaseModel):
    """Parameters to calculate the corrected QT interval (QTc)."""
    qt_ms: float = Field(..., description="Measured QT interval in milliseconds")
    heart_rate: Optional[float] = Field(None, description="Heart rate in beats per minute. Used to derive RR interval (RR = 60/HR). Provide either heart_rate or rr_seconds.")
    rr_seconds: Optional[float] = Field(None, description="RR interval in seconds. Provide either heart_rate or rr_seconds.")
    method: QTcMethod = Field(QTcMethod.BAZETT, description="Correction method: 'bazett' (QT/√RR) or 'fridericia' (QT/RR^(1/3))")
    is_female: Optional[bool] = Field(None, description="Is the patient female? Used for sex-specific interpretation thresholds.")


def calculate_corrected_qtc(params: CorrectedQTcParams) -> ClinicalResult:
    """
    Calculates the corrected QT interval (QTc) using Bazett or Fridericia formula.
    Bazett: QTc = QT / √(RR). Fridericia: QTc = QT / RR^(1/3).
    Reference: Bazett HC. Heart 1920; Fridericia LS. Acta Med Scand 1920.
    """
    # Determine RR interval
    if params.rr_seconds is not None:
        rr = params.rr_seconds
    elif params.heart_rate is not None:
        if params.heart_rate <= 0:
            return ClinicalResult(
                value=None,
                interpretation="Heart rate must be greater than 0.",
                evidence=Evidence(source_doi="10.1136/hrt.7.4.353", level="Derivation Study", description="Bazett HC. An analysis of the time-relations of electrocardiograms. Heart 1920."),
                fhir_code="77867-0", fhir_system="http://loinc.org", fhir_display="QTc interval corrected"
            )
        rr = 60.0 / params.heart_rate
    else:
        return ClinicalResult(
            value=None,
            interpretation="Either heart_rate or rr_seconds must be provided.",
            evidence=Evidence(source_doi="10.1136/hrt.7.4.353", level="Derivation Study", description="Bazett HC. An analysis of the time-relations of electrocardiograms. Heart 1920."),
            fhir_code="77867-0", fhir_system="http://loinc.org", fhir_display="QTc interval corrected"
        )

    if rr <= 0:
        return ClinicalResult(
            value=None,
            interpretation="RR interval must be greater than 0.",
            evidence=Evidence(source_doi="10.1136/hrt.7.4.353", level="Derivation Study", description="Bazett HC. An analysis of the time-relations of electrocardiograms. Heart 1920."),
            fhir_code="77867-0", fhir_system="http://loinc.org", fhir_display="QTc interval corrected"
        )

    # Calculate QTc
    if params.method == QTcMethod.BAZETT:
        qtc = params.qt_ms / math.sqrt(rr)
        method_name = "Bazett"
        doi = "10.1136/hrt.7.4.353"
        description = "Bazett HC. An analysis of the time-relations of electrocardiograms. Heart 1920."
    else:
        qtc = params.qt_ms / (rr ** (1.0 / 3.0))
        method_name = "Fridericia"
        doi = "10.1111/j.0954-6820.1920.tb18266.x"
        description = "Fridericia LS. The duration of systole in an electrocardiogram in normal humans and in patients with heart disease. Acta Med Scand 1920."

    qtc_rounded = round(qtc, 1)

    # Interpretation
    method_label = f"QTc ({method_name})"
    if params.is_female is not None:
        sex_label = "female" if params.is_female else "male"
        normal_upper = 460 if params.is_female else 450
        if qtc_rounded > 500:
            interpretation = f"{method_label} is {qtc_rounded} ms ({sex_label}). Markedly prolonged (>500 ms). High risk for Torsades de Pointes. Review QT-prolonging medications and electrolytes."
        elif qtc_rounded > normal_upper:
            interpretation = f"{method_label} is {qtc_rounded} ms ({sex_label}). Prolonged (>{normal_upper} ms). Consider QT-prolonging medications, electrolyte abnormalities, and cardiac evaluation."
        else:
            interpretation = f"{method_label} is {qtc_rounded} ms ({sex_label}). Normal (≤{normal_upper} ms)."
    else:
        if qtc_rounded > 500:
            interpretation = f"{method_label} is {qtc_rounded} ms. Markedly prolonged (>500 ms). High risk for Torsades de Pointes. Review QT-prolonging medications and electrolytes."
        elif qtc_rounded > 460:
            interpretation = f"{method_label} is {qtc_rounded} ms. Possibly prolonged (>460 ms). Sex-specific thresholds: >450 ms for men, >460 ms for women."
        else:
            interpretation = f"{method_label} is {qtc_rounded} ms. Normal range."

    evidence = Evidence(source_doi=doi, level="Derivation Study", description=description)

    return ClinicalResult(
        value=qtc_rounded,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="77867-0",
        fhir_system="http://loinc.org",
        fhir_display="QTc interval corrected"
    )
