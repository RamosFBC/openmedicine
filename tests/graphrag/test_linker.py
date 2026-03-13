from open_medicine.graphrag.ingestion.linker import link_entity, LinkedEntity


class TestLinker:
    def test_known_drug(self):
        result = link_entity("apixaban", "drug")
        assert result is not None
        assert result.snomed_code is not None
        assert result.canonical_name == "Apixaban"

    def test_known_lab(self):
        result = link_entity("eGFR", "lab")
        assert result is not None
        assert result.loinc_code is not None

    def test_unknown_entity_returns_none(self):
        result = link_entity("xyznonexistent", "drug")
        assert result is None

    def test_case_insensitive(self):
        r1 = link_entity("Apixaban", "drug")
        r2 = link_entity("apixaban", "drug")
        assert r1 is not None and r2 is not None
        assert r1.snomed_code == r2.snomed_code

    def test_alias_resolution(self):
        result = link_entity("Eliquis", "drug")
        assert result is not None
        assert result.canonical_name == "Apixaban"


from open_medicine.graphrag.ingestion.linker import link_variable, LinkedVariable


class TestVariableLinker:
    def test_known_variable(self):
        result = link_variable("eGFR")
        assert result is not None
        assert result.canonical_name == "eGFR"
        assert result.loinc_code == "77147-7"
        assert result.unit == "mL/min/1.73m²"
        assert result.var_type == "continuous"

    def test_case_insensitive(self):
        r1 = link_variable("EGFR")
        r2 = link_variable("egfr")
        assert r1 is not None and r2 is not None
        assert r1.loinc_code == r2.loinc_code

    def test_unknown_variable(self):
        result = link_variable("nonexistent_var")
        assert result is None

    def test_boolean_variable(self):
        result = link_variable("pregnancy")
        assert result is not None
        assert result.var_type == "boolean"

    def test_age_variable(self):
        result = link_variable("age")
        assert result is not None
        assert result.var_type == "continuous"
