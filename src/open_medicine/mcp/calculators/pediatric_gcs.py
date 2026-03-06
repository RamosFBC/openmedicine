# Related guidelines: btf_tbi_2016 (icp_monitoring_and_thresholds, surgical_and_medical_management sections)
from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence


class PediatricGCSParams(BaseModel):
    """Parameters to calculate the Pediatric Glasgow Coma Scale (pGCS) for children <= 2 years."""

    eye_response: int = Field(
        ...,
        ge=1,
        le=4,
        description=(
            "Eye Opening (E) score from 1 to 4. Scoring: "
            "4 = Eyes opening spontaneously, "
            "3 = Eye opening to speech, "
            "2 = Eye opening to pain, "
            "1 = No eye opening or response."
        ),
    )
    verbal_response: int = Field(
        ...,
        ge=1,
        le=5,
        description=(
            "Verbal Response (V) score from 1 to 5 (adapted for preverbal children <= 2 years). Scoring: "
            "5 = Smiles, oriented to sounds, follows objects, interacts, "
            "4 = Cries but consolable, inappropriate interactions, "
            "3 = Inconsistently inconsolable, moaning, "
            "2 = Inconsolable, agitated, "
            "1 = No verbal response."
        ),
    )
    motor_response: int = Field(
        ...,
        ge=1,
        le=6,
        description=(
            "Motor Response (M) score from 1 to 6 (adapted for preverbal children <= 2 years). Scoring: "
            "6 = Moves spontaneously or purposefully, "
            "5 = Withdraws from touch (localizes pain), "
            "4 = Withdraws from pain, "
            "3 = Abnormal flexion to pain (decorticate response), "
            "2 = Extension to pain (decerebrate response), "
            "1 = No motor response."
        ),
    )


def calculate_pediatric_gcs(params: PediatricGCSParams) -> ClinicalResult:
    """
    Calculates the Pediatric Glasgow Coma Scale (pGCS) for children <= 2 years.
    Assesses the level of consciousness in preverbal pediatric patients following
    brain injury, using age-appropriate verbal and motor response descriptors.
    Scale ranges from 3 (deep coma) to 15 (fully alert).
    Reference: James HE. Pediatric Annals. 1986;15(1):16-22.
    Validation: Borgialli DA et al. Acad Emerg Med. 2016;23(8):878-884.
    """
    # 1. Compute total score (sum of three components)
    total_score = params.eye_response + params.verbal_response + params.motor_response

    # 2. Build Evidence with DOI from the original James 1986 study
    evidence = Evidence(
        source_doi="10.3928/0090-4481-19860101-05",
        level="Derivation & Validation Study",
        description=(
            "Neurologic evaluation and support in the child with an acute brain insult. "
            "(James HE, Pediatr Ann 1986; validated by Borgialli DA et al, Acad Emerg Med 2016)"
        ),
    )

    # 3. Interpret result using validated severity thresholds
    #    Same thresholds as adult GCS: 13-15 mild, 9-12 moderate, 3-8 severe
    #    Per BTF TBI Guidelines, GCS <= 8 = severe TBI warranting intubation consideration
    if 13 <= total_score <= 15:
        severity = "Mild"
        meaning = (
            "Indicates minor head injury. "
            "Continue monitoring and reassess as clinically indicated."
        )
    elif 9 <= total_score <= 12:
        severity = "Moderate"
        meaning = (
            "Indicates moderate head injury. "
            "Close monitoring required; consider neuroimaging."
        )
    else:  # 3 to 8
        severity = "Severe"
        meaning = (
            "Indicates severe head injury. "
            "Intubation strongly considered for pGCS <= 8. "
            "Scores below 6 may require intracranial pressure monitoring per BTF guidelines."
        )

    interpretation = (
        f"Pediatric GCS Total Score: {total_score} "
        f"(E{params.eye_response} V{params.verbal_response} M{params.motor_response}). "
        f"Classification: {severity}. {meaning}"
    )

    # 4. Return ClinicalResult with FHIR metadata
    # LOINC 9269-2 = "Glasgow coma score total" (no pediatric-specific LOINC exists;
    # the standard GCS total code covers pediatric use with age-appropriate descriptors)
    return ClinicalResult(
        value=float(total_score),
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="9269-2",
        fhir_system="http://loinc.org",
        fhir_display="Glasgow coma score total",
    )
