from __future__ import annotations
from dataclasses import dataclass


@dataclass
class LinkedEntity:
    canonical_name: str
    entity_type: str
    snomed_code: str | None = None
    loinc_code: str | None = None
    fhir_code: str | None = None


_DRUG_MAP: dict[str, LinkedEntity] = {
    "apixaban": LinkedEntity("Apixaban", "drug", snomed_code="703899003"),
    "eliquis": LinkedEntity("Apixaban", "drug", snomed_code="703899003"),
    "rivaroxaban": LinkedEntity("Rivaroxaban", "drug", snomed_code="703901006"),
    "xarelto": LinkedEntity("Rivaroxaban", "drug", snomed_code="703901006"),
    "warfarin": LinkedEntity("Warfarin", "drug", snomed_code="372756006"),
    "dabigatran": LinkedEntity("Dabigatran", "drug", snomed_code="700029008"),
    "edoxaban": LinkedEntity("Edoxaban", "drug", snomed_code="712519002"),
    "lisinopril": LinkedEntity("Lisinopril", "drug", snomed_code="386873009"),
    "enalapril": LinkedEntity("Enalapril", "drug", snomed_code="372658000"),
    "metoprolol": LinkedEntity("Metoprolol", "drug", snomed_code="372826007"),
    "amiodarone": LinkedEntity("Amiodarone", "drug", snomed_code="372821002"),
    "digoxin": LinkedEntity("Digoxin", "drug", snomed_code="387461009"),
    "atorvastatin": LinkedEntity("Atorvastatin", "drug", snomed_code="373444002"),
    "rosuvastatin": LinkedEntity("Rosuvastatin", "drug", snomed_code="412295007"),
    "heparin": LinkedEntity("Heparin", "drug", snomed_code="372877000"),
    "amoxicillin": LinkedEntity("Amoxicillin", "drug", snomed_code="372687004"),
    "azithromycin": LinkedEntity("Azithromycin", "drug", snomed_code="387531004"),
    "ceftriaxone": LinkedEntity("Ceftriaxone", "drug", snomed_code="372670001"),
    "furosemide": LinkedEntity("Furosemide", "drug", snomed_code="387475002"),
    "spironolactone": LinkedEntity("Spironolactone", "drug", snomed_code="387078006"),
    "sacubitril/valsartan": LinkedEntity("Sacubitril/Valsartan", "drug", snomed_code="716083005"),
    "entresto": LinkedEntity("Sacubitril/Valsartan", "drug", snomed_code="716083005"),
    "dapagliflozin": LinkedEntity("Dapagliflozin", "drug", snomed_code="703674005"),
    "empagliflozin": LinkedEntity("Empagliflozin", "drug", snomed_code="703894007"),
}

_LAB_MAP: dict[str, LinkedEntity] = {
    "egfr": LinkedEntity("eGFR", "lab", loinc_code="77147-7"),
    "creatinine": LinkedEntity("Creatinine", "lab", loinc_code="2160-0"),
    "potassium": LinkedEntity("Potassium", "lab", loinc_code="2823-3"),
    "sodium": LinkedEntity("Sodium", "lab", loinc_code="2951-2"),
    "bnp": LinkedEntity("BNP", "lab", loinc_code="42637-9"),
    "nt-probnp": LinkedEntity("NT-proBNP", "lab", loinc_code="33762-6"),
    "troponin": LinkedEntity("Troponin", "lab", loinc_code="6598-7"),
    "inr": LinkedEntity("INR", "lab", loinc_code="6301-6"),
    "ldl": LinkedEntity("LDL Cholesterol", "lab", loinc_code="13457-7"),
    "hdl": LinkedEntity("HDL Cholesterol", "lab", loinc_code="2085-9"),
    "total cholesterol": LinkedEntity("Total Cholesterol", "lab", loinc_code="2093-3"),
    "alt": LinkedEntity("ALT", "lab", loinc_code="1742-6"),
    "ast": LinkedEntity("AST", "lab", loinc_code="1920-8"),
    "hemoglobin": LinkedEntity("Hemoglobin", "lab", loinc_code="718-7"),
    "hba1c": LinkedEntity("HbA1c", "lab", loinc_code="4548-4"),
    "albumin": LinkedEntity("Albumin", "lab", loinc_code="1751-7"),
    "qtc": LinkedEntity("QTc Interval", "lab", loinc_code="8897-1"),
    "crcl": LinkedEntity("Creatinine Clearance", "lab", loinc_code="2164-2"),
}

_TYPE_MAPS = {
    "drug": _DRUG_MAP,
    "lab": _LAB_MAP,
}


def link_entity(name: str, entity_type: str) -> LinkedEntity | None:
    """Resolve a clinical entity name to its canonical form with codes."""
    mapping = _TYPE_MAPS.get(entity_type)
    if not mapping:
        return None
    return mapping.get(name.lower())
