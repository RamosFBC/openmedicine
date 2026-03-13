import pytest
from open_medicine.graphrag.graph.schema import (
    Concept, ConceptType,
    LogicNode, LogicNodeType, Condition,
    EvidenceChunk,
    Guideline,
    PatientVariable, VariableType,
)


class TestConcept:
    def test_valid_drug(self):
        c = Concept(id="apixaban", name="Apixaban", type=ConceptType.DRUG, snomed_code="703899003")
        assert c.id == "apixaban"
        assert c.type == ConceptType.DRUG

    def test_aliases_default_empty(self):
        c = Concept(id="x", name="X", type=ConceptType.DRUG)
        assert c.aliases == []

    def test_requires_id_and_name(self):
        with pytest.raises(Exception):
            Concept(type=ConceptType.DRUG)


class TestCondition:
    def test_valid_condition(self):
        c = Condition(variable="eGFR", operator="<", threshold=25, unit="mL/min")
        assert c.variable == "eGFR"
        assert c.threshold == 25

    def test_valid_operators(self):
        for op in ["<", "<=", ">", ">=", "==", "!="]:
            c = Condition(variable="x", operator=op, threshold=1)
            assert c.operator == op

    def test_invalid_operator(self):
        with pytest.raises(Exception):
            Condition(variable="x", operator="~", threshold=1)


class TestLogicNode:
    def test_valid_dosing_node(self):
        ln = LogicNode(
            id="ln_001",
            type=LogicNodeType.DOSING,
            conditions=[Condition(variable="eGFR", operator="<", threshold=25, unit="mL/min")],
            action="contraindicated",
            action_detail="Do not use if eGFR < 25",
            strength="Strong/A",
            guideline_id="acc_aha_af_2023",
            page=47,
        )
        assert ln.type == LogicNodeType.DOSING

    def test_valid_types(self):
        for t in ["dosing", "contraindication", "interaction", "monitoring", "treatment_selection", "diagnostic_criteria"]:
            assert LogicNodeType(t) == t

    def test_conditions_list_required(self):
        with pytest.raises(Exception):
            LogicNode(
                id="ln_001", type=LogicNodeType.DOSING,
                action="contraindicated", action_detail="x",
                strength="Strong/A", guideline_id="g", page=1,
            )


class TestEvidenceChunk:
    def test_valid_chunk(self):
        ec = EvidenceChunk(
            id="chunk_001", text="Apixaban should not be used...",
            guideline_id="acc_aha_af_2023", section="anticoagulation",
            page_start=47, page_end=47,
        )
        assert ec.guideline_id == "acc_aha_af_2023"

    def test_parent_chunk_optional(self):
        ec = EvidenceChunk(
            id="c1", text="t", guideline_id="g", section="s",
            page_start=1, page_end=1,
        )
        assert ec.parent_chunk_id is None


class TestGuideline:
    def test_valid_guideline(self):
        g = Guideline(
            id="acc_aha_af_2023",
            title="2023 ACC/AHA AF Guideline",
            doi="10.1161/CIR.0000000000001193",
            year=2023,
            organization="ACC/AHA",
            total_pages=287,
        )
        assert g.year == 2023


class TestPatientVariable:
    def test_valid_continuous(self):
        pv = PatientVariable(
            id="eGFR", name="Estimated GFR",
            unit="mL/min/1.73m²", type=VariableType.CONTINUOUS,
        )
        assert pv.type == VariableType.CONTINUOUS

    def test_valid_types(self):
        for t in ["continuous", "categorical", "boolean"]:
            assert VariableType(t) == t
