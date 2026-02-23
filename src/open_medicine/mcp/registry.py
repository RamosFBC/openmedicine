from typing import Dict, Any, Callable
from pydantic import BaseModel

# Original calculators
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
from open_medicine.mcp.calculators.apixaban_dosing import calculate_apixaban_dosing, ApixabanDosingParams

# Phase 1: VTE Scoring
from open_medicine.mcp.calculators.wells_dvt import calculate_wells_dvt, WellsDVTParams
from open_medicine.mcp.calculators.wells_pe import calculate_wells_pe, WellsPEParams
from open_medicine.mcp.calculators.perc import calculate_perc, PERCParams

# Phase 1: ACS Scoring
from open_medicine.mcp.calculators.heart_score import calculate_heart_score, HEARTScoreParams
from open_medicine.mcp.calculators.timi_stemi import calculate_timi_stemi, TIMISTEMIParams
from open_medicine.mcp.calculators.timi_ua_nstemi import calculate_timi_ua_nstemi, TIMIUANSTEMIParams
from open_medicine.mcp.calculators.grace_score import calculate_grace_score, GRACEScoreParams

# Phase 1: Early Warning
from open_medicine.mcp.calculators.qsofa import calculate_qsofa, QSOFAParams
from open_medicine.mcp.calculators.news2 import calculate_news2, NEWS2Params

# Phase 1: Clinical Equations
from open_medicine.mcp.calculators.corrected_qtc import calculate_corrected_qtc, CorrectedQTcParams
from open_medicine.mcp.calculators.aa_gradient import calculate_aa_gradient, AAGradientParams
from open_medicine.mcp.calculators.anion_gap import calculate_anion_gap, AnionGapParams

# Phase 1: Anticoagulant Dosing
from open_medicine.mcp.calculators.dabigatran_dosing import calculate_dabigatran_dosing, DabigatranDosingParams
from open_medicine.mcp.calculators.edoxaban_dosing import calculate_edoxaban_dosing, EdoxabanDosingParams
from open_medicine.mcp.calculators.heparin_dosing import calculate_heparin_dosing, HeparinDosingParams
from open_medicine.mcp.calculators.warfarin_initiation import calculate_warfarin_initiation, WarfarinInitiationParams


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
    # --- Original ---
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
    ),
    "calculate_apixaban_dosing": RegisteredTool(
        description="Calculates the FDA-approved Apixaban dosage for non-valvular atrial fibrillation based on patient age, weight, and serum creatinine.",
        pydantic_model=ApixabanDosingParams,
        execute_function=calculate_apixaban_dosing
    ),

    # --- Phase 1: VTE Scoring ---
    "calculate_wells_dvt": RegisteredTool(
        description="Calculates the Wells score for Deep Vein Thrombosis (DVT) pretest probability.",
        pydantic_model=WellsDVTParams,
        execute_function=calculate_wells_dvt
    ),
    "calculate_wells_pe": RegisteredTool(
        description="Calculates the Wells score for Pulmonary Embolism (PE) pretest probability.",
        pydantic_model=WellsPEParams,
        execute_function=calculate_wells_pe
    ),
    "calculate_perc": RegisteredTool(
        description="Applies the PERC (Pulmonary Embolism Rule-out Criteria) to determine if PE can be safely excluded without further testing.",
        pydantic_model=PERCParams,
        execute_function=calculate_perc
    ),

    # --- Phase 1: ACS Scoring ---
    "calculate_heart_score": RegisteredTool(
        description="Calculates the HEART score for chest pain evaluation, estimating 6-week risk of major adverse cardiac events (MACE).",
        pydantic_model=HEARTScoreParams,
        execute_function=calculate_heart_score
    ),
    "calculate_timi_stemi": RegisteredTool(
        description="Calculates the TIMI risk score for STEMI, predicting 30-day mortality in ST-elevation myocardial infarction.",
        pydantic_model=TIMISTEMIParams,
        execute_function=calculate_timi_stemi
    ),
    "calculate_timi_ua_nstemi": RegisteredTool(
        description="Calculates the TIMI risk score for UA/NSTEMI, predicting 14-day risk of death, MI, or urgent revascularization.",
        pydantic_model=TIMIUANSTEMIParams,
        execute_function=calculate_timi_ua_nstemi
    ),
    "calculate_grace_score": RegisteredTool(
        description="Calculates the GRACE (Global Registry of Acute Coronary Events) score for in-hospital mortality risk in ACS.",
        pydantic_model=GRACEScoreParams,
        execute_function=calculate_grace_score
    ),

    # --- Phase 1: Early Warning ---
    "calculate_qsofa": RegisteredTool(
        description="Calculates the qSOFA (Quick Sequential Organ Failure Assessment) score for bedside sepsis screening.",
        pydantic_model=QSOFAParams,
        execute_function=calculate_qsofa
    ),
    "calculate_news2": RegisteredTool(
        description="Calculates the NEWS2 (National Early Warning Score 2) for acute illness severity with SpO2 Scale 1/2 and ACVPU consciousness.",
        pydantic_model=NEWS2Params,
        execute_function=calculate_news2
    ),

    # --- Phase 1: Clinical Equations ---
    "calculate_corrected_qtc": RegisteredTool(
        description="Calculates the corrected QT interval (QTc) using Bazett or Fridericia formula for Torsades de Pointes risk assessment.",
        pydantic_model=CorrectedQTcParams,
        execute_function=calculate_corrected_qtc
    ),
    "calculate_aa_gradient": RegisteredTool(
        description="Calculates the Alveolar-arterial (A-a) oxygen gradient to evaluate causes of hypoxemia.",
        pydantic_model=AAGradientParams,
        execute_function=calculate_aa_gradient
    ),
    "calculate_anion_gap": RegisteredTool(
        description="Calculates the serum anion gap with optional albumin correction for metabolic acidosis evaluation.",
        pydantic_model=AnionGapParams,
        execute_function=calculate_anion_gap
    ),

    # --- Phase 1: Anticoagulant Dosing ---
    "calculate_dabigatran_dosing": RegisteredTool(
        description="Calculates the FDA-approved Dabigatran (Pradaxa) dosage for NVAF and VTE based on CrCl and P-gp inhibitor status.",
        pydantic_model=DabigatranDosingParams,
        execute_function=calculate_dabigatran_dosing
    ),
    "calculate_edoxaban_dosing": RegisteredTool(
        description="Calculates the FDA-approved Edoxaban (Savaysa) dosage for NVAF and VTE based on CrCl, weight, and P-gp inhibitor status.",
        pydantic_model=EdoxabanDosingParams,
        execute_function=calculate_edoxaban_dosing
    ),
    "calculate_heparin_dosing": RegisteredTool(
        description="Calculates weight-based IV unfractionated heparin dosing with aPTT-based adjustments (Raschke protocol).",
        pydantic_model=HeparinDosingParams,
        execute_function=calculate_heparin_dosing
    ),
    "calculate_warfarin_initiation": RegisteredTool(
        description="Provides initial Warfarin dosing guidance based on patient risk factors and indication-specific INR targets.",
        pydantic_model=WarfarinInitiationParams,
        execute_function=calculate_warfarin_initiation
    ),
}
