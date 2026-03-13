from open_medicine.graphrag.graph.indexes import get_index_statements, get_constraint_statements


class TestIndexStatements:
    def test_constraints_include_all_node_types(self):
        stmts = get_constraint_statements()
        text = " ".join(stmts)
        for label in ["Concept", "LogicNode", "EvidenceChunk", "Guideline", "PatientVariable"]:
            assert label in text, f"Missing constraint for {label}"

    def test_indexes_include_key_properties(self):
        stmts = get_index_statements()
        text = " ".join(stmts)
        assert "snomed_code" in text
        assert "LogicNode" in text

    def test_returns_list_of_strings(self):
        for stmt in get_constraint_statements():
            assert isinstance(stmt, str)
            assert "CREATE" in stmt or "DROP" in stmt or stmt.startswith("CREATE")
