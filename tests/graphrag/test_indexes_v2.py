from open_medicine.graphrag.graph.indexes_v2 import (
    get_constraint_statements,
    get_index_statements,
)


class TestConstraints:
    def test_returns_list_of_strings(self):
        stmts = get_constraint_statements()
        assert isinstance(stmts, list)
        assert all(isinstance(s, str) for s in stmts)

    def test_all_node_types_have_constraints(self):
        stmts = get_constraint_statements()
        text = " ".join(stmts)
        expected_labels = [
            "Drug", "DrugClass", "Disease", "Symptom", "Lab", "Procedure", "Device",
            "Guideline", "Recommendation", "EvidenceChunk", "Publication",
            "Population", "PatientVariable", "TemporalConstraint",
            "Organization", "CareSetting", "CareTeamRole",
        ]
        for label in expected_labels:
            assert label in text, f"Missing constraint for {label}"

    def test_all_use_if_not_exists(self):
        for stmt in get_constraint_statements():
            assert "IF NOT EXISTS" in stmt

    def test_count(self):
        assert len(get_constraint_statements()) == 17


class TestIndexes:
    def test_returns_list_of_strings(self):
        stmts = get_index_statements()
        assert isinstance(stmts, list)
        assert all(isinstance(s, str) for s in stmts)

    def test_has_vector_index(self):
        stmts = get_index_statements()
        vector_stmts = [s for s in stmts if "VECTOR" in s]
        assert len(vector_stmts) == 1
        assert "evidence_embedding" in vector_stmts[0]
        assert "1024" in vector_stmts[0]

    def test_has_fulltext_index(self):
        stmts = get_index_statements()
        ft_stmts = [s for s in stmts if "FULLTEXT" in s]
        assert len(ft_stmts) == 1
        assert "clinical_entity_search" in ft_stmts[0]

    def test_all_use_if_not_exists(self):
        for stmt in get_index_statements():
            assert "IF NOT EXISTS" in stmt

    def test_drug_indexes(self):
        stmts = get_index_statements()
        text = " ".join(stmts)
        assert "drug_name" in text
        assert "drug_rxnorm" in text

    def test_disease_indexes(self):
        stmts = get_index_statements()
        text = " ".join(stmts)
        assert "disease_name" in text
        assert "disease_snomed" in text

    def test_recommendation_indexes(self):
        stmts = get_index_statements()
        text = " ".join(stmts)
        assert "recommendation_type" in text
        assert "recommendation_guideline" in text
