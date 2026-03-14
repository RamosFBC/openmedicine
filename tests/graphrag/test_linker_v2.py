from open_medicine.graphrag.ingestion.linker_v2 import (
    LinkedEntity,
    LinkedVariable,
    get_drug_class_members,
    link_entity,
    link_variable,
)


class TestLinkEntity:
    def test_known_drug(self):
        result = link_entity("Apixaban", "drug")
        assert result is not None
        assert result.canonical_name == "Apixaban"
        assert result.entity_type == "drug"
        assert result.node_label == "Drug"
        assert result.snomed_code == "703899003"
        assert result.node_id.startswith("rxnorm:")

    def test_drug_alias(self):
        result = link_entity("Entresto", "drug")
        assert result is not None
        assert result.canonical_name == "Sacubitril/Valsartan"
        assert result.snomed_code == "716083005"

    def test_case_insensitive(self):
        result = link_entity("apixaban", "drug")
        assert result is not None
        assert result.canonical_name == "Apixaban"

    def test_known_disease(self):
        result = link_entity("Heart Failure", "disease")
        assert result is not None
        assert result.node_label == "Disease"
        assert result.snomed_code == "84114007"
        assert result.icd10_code == "I50"

    def test_known_lab(self):
        result = link_entity("eGFR", "lab")
        assert result is not None
        assert result.node_label == "Lab"
        assert result.loinc_code == "77147-7"
        assert result.unit == "mL/min/1.73m²"

    def test_known_drug_class(self):
        result = link_entity("Beta Blocker", "drug_class")
        assert result is not None
        assert result.node_label == "DrugClass"
        assert result.atc_code == "C07"

    def test_known_procedure(self):
        result = link_entity("Echocardiography", "procedure")
        assert result is not None
        assert result.node_label == "Procedure"
        assert result.snomed_code == "40701008"

    def test_known_device(self):
        result = link_entity("ICD", "device")
        assert result is not None
        assert result.node_label == "Device"
        assert result.snomed_code == "72506001"

    def test_known_symptom(self):
        result = link_entity("Dyspnea", "symptom")
        assert result is not None
        assert result.node_label == "Symptom"
        assert result.snomed_code == "267036007"

    def test_unknown_drug_returns_minimal(self):
        result = link_entity("Sotagliflozin", "drug")
        assert result is not None
        assert result.canonical_name == "Sotagliflozin"
        assert result.node_label == "Drug"
        assert result.node_id == "drug:sotagliflozin"
        assert result.snomed_code is None

    def test_unknown_entity_type(self):
        result = link_entity("Something", "unknown_type")
        assert result is None

    def test_all_types_return_correct_labels(self):
        type_label_pairs = [
            ("drug", "Drug"),
            ("drug_class", "DrugClass"),
            ("disease", "Disease"),
            ("symptom", "Symptom"),
            ("lab", "Lab"),
            ("procedure", "Procedure"),
            ("device", "Device"),
        ]
        for entity_type, expected_label in type_label_pairs:
            result = link_entity("TestEntity", entity_type)
            assert result is not None
            assert result.node_label == expected_label, (
                f"Expected {expected_label} for type {entity_type}"
            )


class TestLinkVariable:
    def test_known_variable(self):
        result = link_variable("LVEF")
        assert result is not None
        assert result.canonical_name == "LVEF"
        assert result.loinc_code == "10230-1"
        assert result.unit == "%"
        assert result.var_type == "continuous"
        assert result.linked_lab == "LVEF"

    def test_case_insensitive(self):
        result = link_variable("lvef")
        assert result is not None
        assert result.canonical_name == "LVEF"

    def test_boolean_variable(self):
        result = link_variable("Pregnancy")
        assert result is not None
        assert result.var_type == "boolean"
        assert result.linked_lab is None

    def test_unknown_variable(self):
        result = link_variable("unknown_var")
        assert result is None

    def test_linked_lab_field(self):
        result = link_variable("Potassium")
        assert result is not None
        assert result.linked_lab == "Potassium"


class TestGetDrugClassMembers:
    def test_beta_blocker_members(self):
        members = get_drug_class_members("Beta Blocker")
        assert "Carvedilol" in members
        assert "Metoprolol Succinate" in members
        assert "Bisoprolol" in members

    def test_acei_members(self):
        members = get_drug_class_members("ACE Inhibitor")
        assert "Lisinopril" in members
        assert "Enalapril" in members

    def test_unknown_class(self):
        members = get_drug_class_members("Unknown Class")
        assert members == []
