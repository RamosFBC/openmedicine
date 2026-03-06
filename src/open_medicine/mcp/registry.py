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
from open_medicine.mcp.calculators.mews import calculate_mews, MEWSParams

# Phase 1: Clinical Equations
from open_medicine.mcp.calculators.corrected_qtc import calculate_corrected_qtc, CorrectedQTcParams
from open_medicine.mcp.calculators.aa_gradient import calculate_aa_gradient, AaGradientParams
from open_medicine.mcp.calculators.anion_gap import calculate_anion_gap, AnionGapParams

# Phase 1: Anticoagulant Dosing
from open_medicine.mcp.calculators.dabigatran_dosing import calculate_dabigatran_dosing, DabigatranDosingParams
from open_medicine.mcp.calculators.edoxaban_dosing import calculate_edoxaban_dosing, EdoxabanDosingParams
from open_medicine.mcp.calculators.heparin_dosing import calculate_heparin_dosing, HeparinDosingParams
from open_medicine.mcp.calculators.warfarin_initiation import calculate_warfarin_initiation, WarfarinInitiationParams

# Phase 2: Hepatology
from open_medicine.mcp.calculators.meld_na import calculate_meld_na, MELDNaParams
from open_medicine.mcp.calculators.child_pugh import calculate_child_pugh, ChildPughParams
from open_medicine.mcp.calculators.fib4 import calculate_fib4, FIB4Params
from open_medicine.mcp.calculators.nafld_fibrosis import calculate_nafld_fibrosis, NAFLDFibrosisParams

# Phase 2: Lab Corrections
from open_medicine.mcp.calculators.serum_osmolality import calculate_serum_osmolality, SerumOsmolalityParams
from open_medicine.mcp.calculators.osmolar_gap import calculate_osmolar_gap, OsmolarGapParams
from open_medicine.mcp.calculators.winters_formula import calculate_winters_formula, WintersFormulaParams
from open_medicine.mcp.calculators.corrected_sodium import calculate_corrected_sodium, CorrectedSodiumParams
from open_medicine.mcp.calculators.corrected_calcium import calculate_corrected_calcium, CorrectedCalciumParams
from open_medicine.mcp.calculators.bmi import calculate_bmi, BMIParams

# Phase 2: Pulmonary + VTE Risk
from open_medicine.mcp.calculators.gold_copd import calculate_gold_copd, GOLDCOPDParams
from open_medicine.mcp.calculators.caprini import calculate_caprini, CapriniParams
from open_medicine.mcp.calculators.padua import calculate_padua, PaduaParams

# Phase 2: Anthropometrics + Dosing
from open_medicine.mcp.calculators.bsa_mosteller import calculate_bsa_mosteller, BSAMostellerParams
from open_medicine.mcp.calculators.insulin_basal_dosing import calculate_insulin_basal_dosing, InsulinBasalDosingParams
# Phase 3: Neurology, Trauma & GI
from open_medicine.mcp.calculators.abcd2 import calculate_abcd2, ABCD2Params
from open_medicine.mcp.calculators.bisap import calculate_bisap, BISAPParams
from open_medicine.mcp.calculators.canadian_cspine import calculate_canadian_cspine, CanadianCSpineParams
from open_medicine.mcp.calculators.fisher_grade import calculate_fisher_grade, FisherGradeParams
from open_medicine.mcp.calculators.glasgow_blatchford import calculate_glasgow_blatchford, GlasgowBlatchfordParams
from open_medicine.mcp.calculators.hunt_hess import calculate_hunt_hess, HuntHessParams
from open_medicine.mcp.calculators.nihss import calculate_nihss, NIHSSParams
from open_medicine.mcp.calculators.parkland import calculate_parkland, ParklandParams
from open_medicine.mcp.calculators.ransons import calculate_ransons, RansonsParams
from open_medicine.mcp.calculators.rockall import calculate_rockall, RockallParams
from open_medicine.mcp.calculators.rts import calculate_rts, RTSParams
from open_medicine.mcp.calculators.centor_mcisaac import calculate_centor_mcisaac, CentorMcIsaacParams
from open_medicine.mcp.calculators.ottawa_ankle import calculate_ottawa_ankle, OttawaAnkleParams

# Psychiatry / Mental Health Screening
from open_medicine.mcp.calculators.gad7 import calculate_gad7, GAD7Params
from open_medicine.mcp.calculators.phq9 import calculate_phq9, PHQ9Params
from open_medicine.mcp.calculators.audit_c import calculate_audit_c, AUDITCParams
from open_medicine.mcp.calculators.cage import calculate_cage, CAGEParams
from open_medicine.mcp.calculators.epds import calculate_epds, EPDSParams

# ICU Severity Scoring
from open_medicine.mcp.calculators.apache2 import calculate_apache2, APACHE2Params

# Hematology / Coagulation
from open_medicine.mcp.calculators.isth_dic import calculate_isth_dic, ISTHDICParams
from open_medicine.mcp.calculators.four_ts_hit import calculate_4ts_hit, FourTsHITParams

# Cardiovascular Risk
from open_medicine.mcp.calculators.framingham import calculate_framingham, FraminghamParams

# Fluid Management
from open_medicine.mcp.calculators.maintenance_iv_fluids import calculate_maintenance_iv_fluids, MaintenanceIVFluidsParams

# Obstetrics
from open_medicine.mcp.calculators.bishop import calculate_bishop, BishopParams

# Bone / Osteoporosis
from open_medicine.mcp.calculators.frax import calculate_frax, FRAXParams

# Rheumatology
from open_medicine.mcp.calculators.das28 import calculate_das28, DAS28Params

# Perioperative Cardiac Risk
from open_medicine.mcp.calculators.rcri import calculate_rcri, RCRIParams

# Comorbidity
from open_medicine.mcp.calculators.charlson import calculate_charlson, CharlsonParams

# Oncology
from open_medicine.mcp.calculators.ecog import calculate_ecog, ECOGParams
from open_medicine.mcp.calculators.karnofsky import calculate_karnofsky, KarnofskyParams

# Geriatrics / Frailty
from open_medicine.mcp.calculators.clinical_frailty import calculate_clinical_frailty, ClinicalFrailtyParams

# Neonatal
from open_medicine.mcp.calculators.apgar import calculate_apgar, ApgarParams

# Burn Assessment
from open_medicine.mcp.calculators.tbsa import calculate_tbsa, TBSAParams

# Pneumonia Severity
from open_medicine.mcp.calculators.psi_port import calculate_psi_port, PSIPortParams
from open_medicine.mcp.calculators.crb65 import calculate_crb65, CRB65Params

# Toxicology
from open_medicine.mcp.calculators.rumack_matthew import calculate_rumack_matthew, RumackMatthewParams

# Urology
from open_medicine.mcp.calculators.ipss import calculate_ipss, IPSSParams

# Infectious Disease
from open_medicine.mcp.calculators.duke_criteria import calculate_duke_criteria, DukeCriteriaParams

# Oncology: Febrile Neutropenia
from open_medicine.mcp.calculators.mascc import calculate_mascc, MASCCParams

# Pharmacovigilance / Drug Safety
from open_medicine.mcp.calculators.naranjo import calculate_naranjo, NaranjoParams

# Alcohol Withdrawal
from open_medicine.mcp.calculators.ciwa_ar import calculate_ciwa_ar, CIWAArParams

# Opioid Withdrawal
from open_medicine.mcp.calculators.cows import calculate_cows, COWSParams

# GI Bleeding Risk
from open_medicine.mcp.calculators.aims65 import calculate_aims65, AIMS65Params

# Sleep Medicine / Perioperative OSA Screening
from open_medicine.mcp.calculators.stop_bang import calculate_stop_bang, STOPBangParams

# Soft Tissue Infection
from open_medicine.mcp.calculators.lrinec import calculate_lrinec, LRINECParams

# ICU Sedation Assessment
from open_medicine.mcp.calculators.rass import calculate_rass, RASSParams

# Pediatric Neurology
from open_medicine.mcp.calculators.pediatric_gcs import calculate_pediatric_gcs, PediatricGCSParams

# ICU Delirium Assessment
from open_medicine.mcp.calculators.cam_icu import calculate_cam_icu, CAMICUParams

# Pediatric Early Warning
from open_medicine.mcp.calculators.pews import calculate_pews, PEWSParams


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
    "calculate_mews": RegisteredTool(
        description="Calculates the Modified Early Warning Score (MEWS) for identifying medical patients at risk of clinical deterioration based on vital signs and AVPU consciousness level.",
        pydantic_model=MEWSParams,
        execute_function=calculate_mews
    ),

    # --- Phase 1: Clinical Equations ---
    "calculate_corrected_qtc": RegisteredTool(
        description="Calculates the corrected QT interval (QTc) using Bazett or Fridericia formula for Torsades de Pointes risk assessment.",
        pydantic_model=CorrectedQTcParams,
        execute_function=calculate_corrected_qtc
    ),
    "calculate_aa_gradient": RegisteredTool(
        description="Calculates the Alveolar-arterial (A-a) oxygen gradient to evaluate causes of hypoxemia.",
        pydantic_model=AaGradientParams,
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

    # --- Phase 2: Hepatology ---
    "calculate_meld_na": RegisteredTool(
        description="Calculates the MELD-Na score for end-stage liver disease severity and transplant prioritization.",
        pydantic_model=MELDNaParams,
        execute_function=calculate_meld_na
    ),
    "calculate_child_pugh": RegisteredTool(
        description="Calculates the Child-Pugh score for hepatic function classification (Class A/B/C) in cirrhosis.",
        pydantic_model=ChildPughParams,
        execute_function=calculate_child_pugh
    ),
    "calculate_fib4": RegisteredTool(
        description="Calculates the FIB-4 index for non-invasive liver fibrosis staging.",
        pydantic_model=FIB4Params,
        execute_function=calculate_fib4
    ),
    "calculate_nafld_fibrosis": RegisteredTool(
        description="Calculates the NAFLD Fibrosis Score (NFS) for advanced fibrosis probability in non-alcoholic fatty liver disease.",
        pydantic_model=NAFLDFibrosisParams,
        execute_function=calculate_nafld_fibrosis
    ),

    # --- Phase 2: Lab Corrections ---
    "calculate_serum_osmolality": RegisteredTool(
        description="Calculates the estimated serum osmolality from sodium, glucose, and BUN.",
        pydantic_model=SerumOsmolalityParams,
        execute_function=calculate_serum_osmolality
    ),
    "calculate_osmolar_gap": RegisteredTool(
        description="Calculates the osmolar gap (measured minus calculated osmolality) to screen for toxic alcohol ingestion.",
        pydantic_model=OsmolarGapParams,
        execute_function=calculate_osmolar_gap
    ),
    "calculate_winters_formula": RegisteredTool(
        description="Calculates expected pCO2 in metabolic acidosis using Winter's formula to detect mixed acid-base disorders.",
        pydantic_model=WintersFormulaParams,
        execute_function=calculate_winters_formula
    ),
    "calculate_corrected_sodium": RegisteredTool(
        description="Calculates corrected sodium for hyperglycemia using Katz (and Hillier for glucose >400) formulas.",
        pydantic_model=CorrectedSodiumParams,
        execute_function=calculate_corrected_sodium
    ),
    "calculate_corrected_calcium": RegisteredTool(
        description="Calculates albumin-corrected serum calcium level.",
        pydantic_model=CorrectedCalciumParams,
        execute_function=calculate_corrected_calcium
    ),
    "calculate_bmi": RegisteredTool(
        description="Calculates Body Mass Index (BMI) with WHO classification (underweight through obesity class III).",
        pydantic_model=BMIParams,
        execute_function=calculate_bmi
    ),

    # --- Phase 2: Pulmonary + VTE Risk ---
    "calculate_gold_copd": RegisteredTool(
        description="Classifies COPD severity by GOLD 2024 spirometric grade and ABE group assignment.",
        pydantic_model=GOLDCOPDParams,
        execute_function=calculate_gold_copd
    ),
    "calculate_caprini": RegisteredTool(
        description="Calculates the Caprini VTE risk assessment score for surgical patients to guide thromboprophylaxis.",
        pydantic_model=CapriniParams,
        execute_function=calculate_caprini
    ),
    "calculate_padua": RegisteredTool(
        description="Calculates the Padua Prediction Score for VTE risk in medical inpatients.",
        pydantic_model=PaduaParams,
        execute_function=calculate_padua
    ),

    # --- Phase 2: Anthropometrics + Dosing ---
    "calculate_bsa_mosteller": RegisteredTool(
        description="Calculates Body Surface Area (BSA) using the Mosteller formula for drug dosing and physiologic calculations.",
        pydantic_model=BSAMostellerParams,
        execute_function=calculate_bsa_mosteller
    ),
    "calculate_insulin_basal_dosing": RegisteredTool(
        description="Calculates basal insulin initiation dose and fasting glucose-based titration per ADA 2024 Standards of Care.",
        pydantic_model=InsulinBasalDosingParams,
        execute_function=calculate_insulin_basal_dosing
    ),
    # --- Phase 3: Neurology, Trauma & GI ---
    "calculate_abcd2": RegisteredTool(
        description="Calculates the ABCD2 Score for risk of stroke after TIA.",
        pydantic_model=ABCD2Params,
        execute_function=calculate_abcd2
    ),
    "calculate_bisap": RegisteredTool(
        description="Calculates the BISAP (Bedside Index for Severity in Acute Pancreatitis) score.",
        pydantic_model=BISAPParams,
        execute_function=calculate_bisap
    ),
    "calculate_canadian_cspine": RegisteredTool(
        description="Evaluates the Canadian C-Spine Rule for cervical spine clearance in alert, stable trauma patients.",
        pydantic_model=CanadianCSpineParams,
        execute_function=calculate_canadian_cspine
    ),
    "calculate_fisher_grade": RegisteredTool(
        description="Calculates the Fisher Grade for CT classification of SAH and vasospasm risk.",
        pydantic_model=FisherGradeParams,
        execute_function=calculate_fisher_grade
    ),
    "calculate_glasgow_blatchford": RegisteredTool(
        description="Calculates the Glasgow-Blatchford Bleeding Score (GBS) for risk stratification",
        pydantic_model=GlasgowBlatchfordParams,
        execute_function=calculate_glasgow_blatchford
    ),
    "calculate_hunt_hess": RegisteredTool(
        description="Calculates the Hunt-Hess Scale for grading subarachnoid hemorrhage severity.",
        pydantic_model=HuntHessParams,
        execute_function=calculate_hunt_hess
    ),
    "calculate_nihss": RegisteredTool(
        description="Calculates the NIH Stroke Scale (NIHSS) for quantifying neurological deficit in acute stroke.",
        pydantic_model=NIHSSParams,
        execute_function=calculate_nihss
    ),
    "calculate_parkland": RegisteredTool(
        description="Calculates the Parkland Formula for fluid resuscitation in burn patients.",
        pydantic_model=ParklandParams,
        execute_function=calculate_parkland
    ),
    "calculate_ransons": RegisteredTool(
        description="Calculates Ranson's Criteria for acute pancreatitis severity.",
        pydantic_model=RansonsParams,
        execute_function=calculate_ransons
    ),
    "calculate_rockall": RegisteredTool(
        description="Calculates the Rockall Score for rebleeding and mortality risk after upper GI bleeding.",
        pydantic_model=RockallParams,
        execute_function=calculate_rockall
    ),
    "calculate_rts": RegisteredTool(
        description="Calculates the Revised Trauma Score (RTS) for triage and outcome prediction in trauma.",
        pydantic_model=RTSParams,
        execute_function=calculate_rts
    ),

    # --- Emergency / Trauma Decision Rules ---
    "calculate_ottawa_ankle": RegisteredTool(
        description="Evaluates the Ottawa Ankle Rules to determine the need for ankle and/or midfoot radiography after an acute ankle or midfoot injury.",
        pydantic_model=OttawaAnkleParams,
        execute_function=calculate_ottawa_ankle
    ),

    # --- Infectious Disease ---
    "calculate_centor_mcisaac": RegisteredTool(
        description="Calculates the Modified Centor (McIsaac) Score to estimate the probability of group A streptococcal (GAS) pharyngitis and guide testing/treatment decisions.",
        pydantic_model=CentorMcIsaacParams,
        execute_function=calculate_centor_mcisaac
    ),

    # --- Psychiatry / Mental Health Screening ---
    "calculate_gad7": RegisteredTool(
        description="Calculates the GAD-7 (Generalized Anxiety Disorder 7-item) score for anxiety screening and severity assessment.",
        pydantic_model=GAD7Params,
        execute_function=calculate_gad7
    ),
    "calculate_phq9": RegisteredTool(
        description="Calculates the PHQ-9 (Patient Health Questionnaire-9) score for depression screening and severity assessment.",
        pydantic_model=PHQ9Params,
        execute_function=calculate_phq9
    ),
    "calculate_audit_c": RegisteredTool(
        description="Calculates the AUDIT-C (Alcohol Use Disorders Identification Test - Consumption) score for alcohol screening with sex-specific thresholds.",
        pydantic_model=AUDITCParams,
        execute_function=calculate_audit_c
    ),
    "calculate_cage": RegisteredTool(
        description="Calculates the CAGE Questionnaire score (0-4) for alcohol use screening based on four yes/no questions (Cut down, Annoyed, Guilty, Eye-opener).",
        pydantic_model=CAGEParams,
        execute_function=calculate_cage
    ),
    "calculate_epds": RegisteredTool(
        description="Calculates the Edinburgh Postnatal Depression Scale (EPDS) score for screening postnatal depression in the perinatal period.",
        pydantic_model=EPDSParams,
        execute_function=calculate_epds
    ),

    # --- ICU Severity Scoring ---
    "calculate_apache2": RegisteredTool(
        description="Calculates the APACHE II (Acute Physiology and Chronic Health Evaluation II) score for ICU mortality risk estimation based on 12 physiologic variables, age, and chronic health status.",
        pydantic_model=APACHE2Params,
        execute_function=calculate_apache2
    ),

    # --- Hematology / Coagulation ---
    "calculate_isth_dic": RegisteredTool(
        description="Calculates the ISTH Overt DIC Score for diagnosis of disseminated intravascular coagulation based on platelet count, fibrin-related markers, PT prolongation, and fibrinogen level.",
        pydantic_model=ISTHDICParams,
        execute_function=calculate_isth_dic
    ),
    "calculate_4ts_hit": RegisteredTool(
        description="Calculates the 4Ts score for pretest probability of Heparin-Induced Thrombocytopenia (HIT) based on Thrombocytopenia, Timing, Thrombosis, and oTher causes.",
        pydantic_model=FourTsHITParams,
        execute_function=calculate_4ts_hit
    ),

    # --- Cardiovascular Risk ---
    "calculate_framingham": RegisteredTool(
        description="Calculates the Framingham Risk Score for 10-year general cardiovascular disease (CVD) risk using the 2008 D'Agostino et al. model.",
        pydantic_model=FraminghamParams,
        execute_function=calculate_framingham
    ),

    # --- Fluid Management ---
    "calculate_maintenance_iv_fluids": RegisteredTool(
        description="Calculates maintenance IV fluid rate using the Holliday-Segar method (4-2-1 rule) based on patient weight, providing hourly and daily fluid requirements.",
        pydantic_model=MaintenanceIVFluidsParams,
        execute_function=calculate_maintenance_iv_fluids
    ),

    # --- Obstetrics ---
    "calculate_bishop": RegisteredTool(
        description="Calculates the Bishop Score for pre-induction cervical favorability assessment based on dilation, effacement, station, consistency, and position.",
        pydantic_model=BishopParams,
        execute_function=calculate_bishop
    ),

    # --- Bone / Osteoporosis ---
    "calculate_frax": RegisteredTool(
        description="Calculates the estimated FRAX 10-year probability of major osteoporotic fracture and hip fracture for US Caucasian population based on clinical risk factors with optional femoral neck BMD T-score.",
        pydantic_model=FRAXParams,
        execute_function=calculate_frax
    ),

    # --- Rheumatology ---
    "calculate_das28": RegisteredTool(
        description="Calculates the DAS28 (Disease Activity Score 28) for rheumatoid arthritis disease activity assessment, supporting both ESR and CRP variants.",
        pydantic_model=DAS28Params,
        execute_function=calculate_das28
    ),

    # --- Perioperative Cardiac Risk ---
    "calculate_rcri": RegisteredTool(
        description="Calculates the Revised Cardiac Risk Index (RCRI / Lee Index) for estimating risk of major cardiac complications after noncardiac surgery based on 6 clinical predictors.",
        pydantic_model=RCRIParams,
        execute_function=calculate_rcri
    ),

    # --- Comorbidity ---
    "calculate_charlson": RegisteredTool(
        description="Calculates the Charlson Comorbidity Index (CCI) for predicting 10-year mortality based on 19 weighted comorbid conditions with optional age adjustment.",
        pydantic_model=CharlsonParams,
        execute_function=calculate_charlson
    ),

    # --- Oncology ---
    "calculate_ecog": RegisteredTool(
        description="Records and interprets the ECOG (Eastern Cooperative Oncology Group) Performance Status for oncology functional assessment, treatment decisions, and clinical trial eligibility.",
        pydantic_model=ECOGParams,
        execute_function=calculate_ecog
    ),
    "calculate_karnofsky": RegisteredTool(
        description="Records and interprets the Karnofsky Performance Status (KPS) score for oncology functional assessment, chemotherapy tolerance, and prognosis estimation.",
        pydantic_model=KarnofskyParams,
        execute_function=calculate_karnofsky
    ),

    # --- Neonatal ---
    "calculate_apgar": RegisteredTool(
        description="Calculates the Apgar Score for rapid assessment of newborn condition at birth based on five criteria: Appearance, Pulse, Grimace, Activity, and Respiration.",
        pydantic_model=ApgarParams,
        execute_function=calculate_apgar
    ),

    # --- Burn Assessment ---
    "calculate_tbsa": RegisteredTool(
        description="Calculates the estimated Total Body Surface Area (TBSA) burned using the Wallace Rule of Nines for adult burn assessment and fluid resuscitation guidance.",
        pydantic_model=TBSAParams,
        execute_function=calculate_tbsa
    ),

    # --- Pneumonia Severity ---
    "calculate_psi_port": RegisteredTool(
        description="Calculates the PSI/PORT (Pneumonia Severity Index) score for community-acquired pneumonia risk stratification, predicting 30-day mortality and guiding the initial site-of-care decision.",
        pydantic_model=PSIPortParams,
        execute_function=calculate_psi_port
    ),
    "calculate_crb65": RegisteredTool(
        description="Calculates the CRB-65 score for community-acquired pneumonia severity assessment without laboratory tests, predicting 30-day mortality and guiding site-of-care decisions in primary care and pre-hospital settings.",
        pydantic_model=CRB65Params,
        execute_function=calculate_crb65
    ),

    # --- Geriatrics / Frailty ---
    "calculate_clinical_frailty": RegisteredTool(
        description="Calculates the Clinical Frailty Scale (CFS) by Rockwood et al. for classifying frailty in older adults from very fit (1) to terminally ill (9), guiding goals-of-care and intervention decisions.",
        pydantic_model=ClinicalFrailtyParams,
        execute_function=calculate_clinical_frailty
    ),

    # --- Infectious Disease: Endocarditis ---
    "calculate_duke_criteria": RegisteredTool(
        description="Evaluates the Modified Duke Criteria for the diagnosis of Infective Endocarditis, classifying patients as Definite, Possible, or Rejected based on pathological, major, and minor clinical criteria.",
        pydantic_model=DukeCriteriaParams,
        execute_function=calculate_duke_criteria
    ),

    # --- Oncology: Febrile Neutropenia ---
    "calculate_mascc": RegisteredTool(
        description="Calculates the MASCC (Multinational Association for Supportive Care in Cancer) Risk Index for identifying low-risk febrile neutropenic cancer patients who may be candidates for outpatient oral antibiotic therapy.",
        pydantic_model=MASCCParams,
        execute_function=calculate_mascc
    ),

    # --- Urology ---
    "calculate_ipss": RegisteredTool(
        description="Calculates the International Prostate Symptom Score (IPSS) for assessing lower urinary tract symptom severity in benign prostatic hyperplasia (BPH), with optional Quality of Life (QoL) assessment.",
        pydantic_model=IPSSParams,
        execute_function=calculate_ipss
    ),

    # --- Pharmacovigilance / Drug Safety ---
    "calculate_naranjo": RegisteredTool(
        description="Calculates the Naranjo Adverse Drug Reaction (ADR) Probability Scale to estimate the likelihood that an adverse event was caused by a drug, classifying causality as Definite, Probable, Possible, or Doubtful.",
        pydantic_model=NaranjoParams,
        execute_function=calculate_naranjo
    ),

    # --- Alcohol Withdrawal ---
    "calculate_ciwa_ar": RegisteredTool(
        description="Calculates the CIWA-Ar (Clinical Institute Withdrawal Assessment for Alcohol, Revised) score (0-67) to quantify the severity of alcohol withdrawal and guide symptom-triggered benzodiazepine therapy.",
        pydantic_model=CIWAArParams,
        execute_function=calculate_ciwa_ar
    ),

    # --- Toxicology ---
    "calculate_rumack_matthew": RegisteredTool(
        description="Evaluates acetaminophen (paracetamol) toxicity risk using the Rumack-Matthew Nomogram, plotting serum concentration against time since ingestion to determine need for N-acetylcysteine (NAC) treatment.",
        pydantic_model=RumackMatthewParams,
        execute_function=calculate_rumack_matthew
    ),

    # --- Opioid Withdrawal ---
    "calculate_cows": RegisteredTool(
        description="Calculates the Clinical Opiate Withdrawal Scale (COWS) total score (0-48) to quantify opioid withdrawal severity and guide buprenorphine induction timing.",
        pydantic_model=COWSParams,
        execute_function=calculate_cows
    ),

    # --- GI Bleeding Risk ---
    "calculate_aims65": RegisteredTool(
        description="Calculates the AIMS65 Score (0-5) for predicting in-hospital mortality in acute upper gastrointestinal bleeding based on Albumin, INR, Mental status, Systolic BP, and age >= 65.",
        pydantic_model=AIMS65Params,
        execute_function=calculate_aims65
    ),

    # --- Sleep Medicine / Perioperative OSA Screening ---
    "calculate_stop_bang": RegisteredTool(
        description="Calculates the STOP-Bang score (0-8) for obstructive sleep apnea screening based on Snoring, Tiredness, Observed apnea, high blood Pressure, BMI, Age, Neck circumference, and Gender.",
        pydantic_model=STOPBangParams,
        execute_function=calculate_stop_bang
    ),

    # --- Soft Tissue Infection ---
    "calculate_lrinec": RegisteredTool(
        description="Calculates the LRINEC (Laboratory Risk Indicator for Necrotizing Fasciitis) score (0-13) to distinguish necrotizing fasciitis from other soft tissue infections using six routine laboratory values (CRP, WBC, hemoglobin, sodium, creatinine, glucose).",
        pydantic_model=LRINECParams,
        execute_function=calculate_lrinec
    ),

    # --- ICU Sedation Assessment ---
    "calculate_rass": RegisteredTool(
        description="Records and interprets the Richmond Agitation-Sedation Scale (RASS) score (-5 to +4) for assessing agitation and sedation levels in adult ICU patients, guiding sedative titration and agitation management.",
        pydantic_model=RASSParams,
        execute_function=calculate_rass
    ),

    # --- Pediatric Neurology ---
    "calculate_pediatric_gcs": RegisteredTool(
        description="Calculates the Pediatric Glasgow Coma Scale (pGCS) score for children <= 2 years using age-appropriate eye, verbal, and motor response criteria to assess consciousness level after brain injury.",
        pydantic_model=PediatricGCSParams,
        execute_function=calculate_pediatric_gcs
    ),

    # --- Pediatric Early Warning ---
    "calculate_pews": RegisteredTool(
        description="Calculates the Bedside Paediatric Early Warning System (PEWS) score (0-26) for hospitalized children using seven age-specific vital sign and clinical observation components to identify risk of clinical deterioration.",
        pydantic_model=PEWSParams,
        execute_function=calculate_pews
    ),

    # --- ICU Delirium Assessment ---
    "calculate_cam_icu": RegisteredTool(
        description="Calculates the CAM-ICU (Confusion Assessment Method for the ICU) for delirium assessment in critically ill patients, evaluating acute onset, inattention, altered consciousness, and disorganized thinking.",
        pydantic_model=CAMICUParams,
        execute_function=calculate_cam_icu
    ),
}
