from typing import Dict, Any, Callable
from pydantic import BaseModel

from open_medicine.mcp.calculators.ascvd import calculate_ascvd, ASCVDParams
from open_medicine.mcp.calculators.chadsvasc import calculate_chadsvasc, CHADSVAScParams
from open_medicine.mcp.calculators.sofa import calculate_sofa, SOFAParams
from open_medicine.mcp.calculators.ckd_epi import calculate_ckd_epi, CKDEPIParams
from open_medicine.mcp.calculators.cockcroft_gault import calculate_cockcroft_gault, CockcroftGaultParams
from open_medicine.mcp.calculators.rivaroxaban_dosing import calculate_rivaroxaban_dosing, RivaroxabanDosingParams
from open_medicine.mcp.calculators.enoxaparin_dosing import calculate_enoxaparin_dosing, EnoxaparinDosingParams
from open_medicine.mcp.calculators.gcs import calculate_gcs, GCSParams
from open_medicine.mcp.calculators.hasbled import calculate_hasbled, HASBLEDParams
from open_medicine.mcp.calculators.curb65 import calculate_curb65, CURB65Params

class RegisteredTool:
    def __init__(self, description: str, pydantic_model: type[BaseModel], execute_function: Callable):
        self.description = description
        self.pydantic_model = pydantic_model
        self.execute_function = execute_function

    @property
    def schema(self) -> Dict[str, Any]:
        return self.pydantic_model.model_json_schema()

# Central mapping for the Meta-Tool runtime Execution
CALCULATOR_REGISTRY: Dict[str, RegisteredTool] = {
    "calculate_ascvd": RegisteredTool(
        description="Calculates the 10-year Atherosclerotic Cardiovascular Disease (ASCVD) risk score based on the 2013 ACC/AHA guidelines.",
        pydantic_model=ASCVDParams,
        execute_function=calculate_ascvd
    ),
    "calculate_chadsvasc": RegisteredTool(
        description="Calculates the CHA2DS2-VASc score for atrial fibrillation stroke risk.",
        pydantic_model=CHADSVAScParams,
        execute_function=calculate_chadsvasc
    ),
    "calculate_sofa": RegisteredTool(
        description="Calculates the Sequential Organ Failure Assessment (SOFA) score to determine the extent of a person's organ function or rate of failure in the ICU.",
        pydantic_model=SOFAParams,
        execute_function=calculate_sofa
    ),
    "calculate_ckd_epi": RegisteredTool(
        description="Calculates the 2021 Race-Free CKD-EPI estimated Glomerular Filtration Rate (eGFR), marking Kidney function.",
        pydantic_model=CKDEPIParams,
        execute_function=calculate_ckd_epi
    ),
    "calculate_cockcroft_gault": RegisteredTool(
        description="Calculates the estimated Creatinine Clearance (CrCl) using the Cockcroft-Gault equation for kidney-dependent medication dosage adjustments.",
        pydantic_model=CockcroftGaultParams,
        execute_function=calculate_cockcroft_gault
    ),
    "calculate_rivaroxaban_dosing": RegisteredTool(
        description="Calculates the FDA-approved Rivaroxaban (Xarelto) dosage based on kidney Creatinine Clearance (CrCl) and strict indication boundaries.",
        pydantic_model=RivaroxabanDosingParams,
        execute_function=calculate_rivaroxaban_dosing
    ),
    "calculate_enoxaparin_dosing": RegisteredTool(
        description="Calculates the FDA-approved Enoxaparin (Lovenox) anticoagulant dosage based on patient weight, Creatinine Clearance (CrCl), and clinical indication.",
        pydantic_model=EnoxaparinDosingParams,
        execute_function=calculate_enoxaparin_dosing
    ),
    "calculate_gcs": RegisteredTool(
        description="Calculates the Glasgow Coma Scale (GCS) score based on eye, verbal, and motor responses marking traumatic brain injury.",
        pydantic_model=GCSParams,
        execute_function=calculate_gcs
    ),
    "calculate_hasbled": RegisteredTool(
        description="Calculates the HAS-BLED score for 1-year risk of major bleeding in patients with atrial fibrillation on anticoagulation.",
        pydantic_model=HASBLEDParams,
        execute_function=calculate_hasbled
    ),
    "calculate_curb65": RegisteredTool(
        description="Calculates the CURB-65 score for community-acquired pneumonia severity and mortality risk stratification.",
        pydantic_model=CURB65Params,
        execute_function=calculate_curb65
    )
}
