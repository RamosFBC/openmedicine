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
