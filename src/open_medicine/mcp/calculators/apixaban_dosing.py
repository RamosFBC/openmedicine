from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence

class ApixabanDosingParams(BaseModel):
    """Parameters to calculate Apixaban dosing in non-valvular atrial fibrillation."""
    age: int = Field(..., description="Age in years")
    weight_kg: float = Field(..., description="Body weight in kilograms")
    serum_creatinine: float = Field(..., description="Serum creatinine in mg/dL")

def calculate_apixaban_dosing(params: ApixabanDosingParams) -> ClinicalResult:
    """
    Determines the appropriate FDA-approved Apixaban dosage for non-valvular 
    atrial fibrillation based on age, weight, and serum creatinine.
    
    The recommended dose is 5 mg twice daily.
    The dose is reduced to 2.5 mg twice daily if the patient has at least two of:
      - Age >= 80 years
      - Body weight <= 60 kg
      - Serum creatinine >= 1.5 mg/dL
    """
    age = params.age
    weight = params.weight_kg
    scr = params.serum_creatinine
    
    criteria_met = 0
    if age >= 80:
        criteria_met += 1
    if weight <= 60.0:
        criteria_met += 1
    if scr >= 1.5:
        criteria_met += 1
        
    dose_str = "5 mg twice daily"
    if criteria_met >= 2:
        dose_str = "2.5 mg twice daily"

    interpretation = (
        f"Based on Age={age}, Weight={weight}kg, and SCr={scr}mg/dL, "
        f"the patient meets {criteria_met} of the 3 criteria for dose reduction. "
        f"The recommended Apixaban dose is: {dose_str}."
    )

    evidence = Evidence(
        source_doi="10.1056/NEJMoa1107039",
        level="Randomized Controlled Trial",
        description="Granger CB et al. Apixaban versus warfarin in patients with atrial fibrillation (ARISTOTLE). N Engl J Med. 2011;365(11):981-992."
    )

    return ClinicalResult(
        value=criteria_met,
        interpretation=interpretation,
        evidence=evidence,
        fhir_code="30525-0", # Age
        fhir_system="http://loinc.org",
        fhir_display="Age"
    )
