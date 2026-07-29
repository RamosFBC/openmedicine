from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


class HASBLEDParams(BaseModel):
    """Parameters to calculate the HAS-BLED bleeding risk score for patients with atrial fibrillation."""
    hypertension: bool = Field(False, description="Uncontrolled hypertension (systolic BP > 160 mmHg)")
    abnormal_renal_function: bool = Field(False, description="Abnormal renal function (dialysis, transplant, or serum creatinine > 2.26 mg/dL)")
    abnormal_liver_function: bool = Field(False, description="Abnormal liver function (cirrhosis, bilirubin > 2x upper limit of normal, or AST/ALT/ALP > 3x upper limit of normal)")
    stroke: bool = Field(False, description="Prior stroke history")
    bleeding: bool = Field(False, description="Prior major bleeding or predisposition to bleeding")
    labile_inr: bool = Field(False, description="Labile INR (unstable/high INRs, time in therapeutic range < 60%)")
    elderly: bool = Field(False, description="Age > 65 years")
    drugs: bool = Field(False, description="Concomitant use of antiplatelet agents or NSAIDs")
    alcohol: bool = Field(False, description="Alcohol use (>= 8 drinks per week)")


def calculate_hasbled(params: HASBLEDParams) -> ClinicalResult:
    """
    Calculates the HAS-BLED score for 1-year risk of major bleeding
    in patients with atrial fibrillation on anticoagulation.

    Reference: Pisters R et al. Chest. 2010;138(5):1093-1100.
    """
    score = sum([
        params.hypertension,
        params.abnormal_renal_function,
        params.abnormal_liver_function,
        params.stroke,
        params.bleeding,
        params.labile_inr,
        params.elderly,
        params.drugs,
        params.alcohol
    ])

    evidence = Evidence(
        source_doi="10.1378/chest.10-0134",
        level="Validation Study",
        description="A novel user-friendly score (HAS-BLED) to assess 1-year risk of major bleeding in patients with atrial fibrillation: the Euro Heart Survey."
    )

    if score == 0:
        interpretation = f"HAS-BLED score is {score}. Low bleeding risk."
    elif score <= 2:
        interpretation = f"HAS-BLED score is {score}. Moderate bleeding risk. Anticoagulation can generally be continued with routine monitoring."
    else:
        interpretation = f"HAS-BLED score is {score}. High bleeding risk (>= 3). Does not contraindicate anticoagulation, but modifiable risk factors should be addressed and closer follow-up is warranted."

    return ClinicalResult(
        value=score,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="LP419518-4",
        fhir_system="http://loinc.org",
        fhir_display="HAS-BLED score"
    )
