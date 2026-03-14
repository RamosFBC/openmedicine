from open_medicine.graphrag.terminology import load_terminology, lookup


class TestLoadTerminology:
    def test_load_drugs(self):
        data = load_terminology("drugs")
        assert "Apixaban" in data
        assert data["Apixaban"]["snomed_code"] == "703899003"

    def test_load_diseases(self):
        data = load_terminology("diseases")
        assert "Heart Failure" in data
        assert data["Heart Failure"]["icd10_code"] == "I50"

    def test_load_labs(self):
        data = load_terminology("labs")
        assert "eGFR" in data
        assert data["eGFR"]["loinc_code"] == "77147-7"

    def test_load_drug_classes(self):
        data = load_terminology("drug_classes")
        assert "Beta Blocker" in data
        assert "Carvedilol" in data["Beta Blocker"]["member_drugs"]

    def test_load_procedures(self):
        data = load_terminology("procedures")
        assert "Echocardiography" in data

    def test_load_devices(self):
        data = load_terminology("devices")
        assert "ICD" in data

    def test_load_symptoms(self):
        data = load_terminology("symptoms")
        assert "Dyspnea" in data

    def test_load_variables(self):
        data = load_terminology("variables")
        assert "LVEF" in data
        assert data["LVEF"]["linked_lab"] == "LVEF"

    def test_nonexistent_file_returns_empty(self):
        data = load_terminology("nonexistent_file")
        assert data == {}


class TestLookup:
    def test_canonical_name_match(self):
        result = lookup("drugs", "Apixaban")
        assert result is not None
        assert result["snomed_code"] == "703899003"

    def test_case_insensitive(self):
        result = lookup("drugs", "apixaban")
        assert result is not None

    def test_alias_match(self):
        result = lookup("drugs", "Eliquis")
        assert result is not None
        assert result["snomed_code"] == "703899003"

    def test_alias_case_insensitive(self):
        result = lookup("drugs", "entresto")
        assert result is not None
        assert result["snomed_code"] == "716083005"

    def test_not_found(self):
        result = lookup("drugs", "NonexistentDrug")
        assert result is None

    def test_disease_lookup(self):
        result = lookup("diseases", "HFrEF")
        assert result is not None
        assert result["snomed_code"] == "703272007"

    def test_lab_lookup(self):
        result = lookup("labs", "eGFR")
        assert result is not None
        assert result["loinc_code"] == "77147-7"

    def test_variable_lookup(self):
        result = lookup("variables", "LVEF")
        assert result is not None
        assert result["var_type"] == "continuous"

    def test_symptom_alias(self):
        result = lookup("symptoms", "SOB")
        assert result is not None
        assert result["snomed_code"] == "267036007"
