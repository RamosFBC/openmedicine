from pydantic import BaseModel, Field
from open_medicine.foundation.base import ClinicalResult, Evidence

class GCSParams(BaseModel):
    """Parameters to calculate the Glasgow Coma Scale (GCS)."""
    eye_response: int = Field(..., description="Eye Opening (E) score from 1 to 4. Scoring: 4 = Spontaneous, 3 = To verbal command/speech, 2 = To pain, 1 = No response.", ge=1, le=4)
    verbal_response: int = Field(..., description="Verbal Response (V) score from 1 to 5. Scoring: 5 = Oriented and converses, 4 = Confused conversation, 3 = Inappropriate words, 2 = Incomprehensible sounds, 1 = No response.", ge=1, le=5)
    motor_response: int = Field(..., description="Motor Response (M) score from 1 to 6. Scoring: 6 = Obeys commands, 5 = Localizes to pain, 4 = Withdraws from pain, 3 = Abnormal flexion (decorticate posturing), 2 = Extension (decerebrate posturing), 1 = No response.", ge=1, le=6)

def calculate_gcs(params: GCSParams) -> ClinicalResult:
    """
    Calculates the Glasgow Coma Scale (GCS) based on the three neurological responses.
    This assesses the level of consciousness following brain injury.
    Scale ranges from 3 (deep coma) to 15 (fully awake).
    """
    total_score = params.eye_response + params.verbal_response + params.motor_response
    
    # Stratification logic for brain injury severity
    if 13 <= total_score <= 15:
        severity = "Mild"
        meaning = "Indicates mild brain injury or concussion. Patient is generally alert."
    elif 9 <= total_score <= 12:
        severity = "Moderate"
        meaning = "Indicates moderate brain injury."
    else: # 3 to 8
        severity = "Severe"
        meaning = "Indicates severe brain injury, often consistent with coma status. Intubation strongly considered for GCS ≤ 8."

    interpretation = (
        f"GCS Total Score: {total_score} (E{params.eye_response} V{params.verbal_response} M{params.motor_response}). "
        f"Classification: {severity}. {meaning}"
    )

    evidence = Evidence(
        source_doi="10.1016/s0140-6736(74)91639-0",
        level="Validation Study",
        description="Assessment of coma and impaired consciousness. A practical scale. (Teasdale G, Jennett B, Lancet 1974)"
    )

    return ClinicalResult(
        value=float(total_score),
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="9269-2",
        fhir_system="http://loinc.org",
        fhir_display="Glasgow coma score total"
    )
