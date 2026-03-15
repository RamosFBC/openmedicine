from open_medicine.graphrag.terminology import fuzzy_match


class TestFuzzyMatch:
    def test_exact_match(self):
        results = fuzzy_match("Carvedilol")
        assert any(r[0] == "Carvedilol" for r in results)

    def test_prefix_match(self):
        results = fuzzy_match("Carve")
        assert any("Carvedilol" in r[0] for r in results)

    def test_substring_match(self):
        results = fuzzy_match("valsartan")
        # Should find Sacubitril/Valsartan or Valsartan
        assert len(results) > 0

    def test_case_insensitive(self):
        results = fuzzy_match("hfref")
        assert any("HFrEF" in r[0] for r in results)

    def test_no_match(self):
        results = fuzzy_match("xyznonexistent123")
        assert results == []

    def test_returns_tuples_of_name_and_type(self):
        results = fuzzy_match("Carvedilol")
        assert len(results) > 0
        name, entity_type = results[0]
        assert isinstance(name, str)
        assert entity_type in ("drug", "drug_class", "disease", "lab", "procedure", "device", "symptom")

    def test_max_results(self):
        results = fuzzy_match("heart", max_results=3)
        assert len(results) <= 3
