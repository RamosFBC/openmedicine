import pytest

from open_medicine.graphrag.graph.schema_v2 import (
    CLINICAL_LABELS,
    EVIDENCE_EDGE_TYPES,
    NODE_LABEL_MAP,
    SEMANTIC_EDGE_TYPES,
    CareSetting,
    CareTeamRole,
    ContraindicatedInProps,
    ContraindicationSeverity,
    CausesSideEffectProps,
    DefinesProps,
    Device,
    DiagnosedByProps,
    Disease,
    DosedForProps,
    Drug,
    DrugClass,
    EvidenceChunk,
    EvidenceQuality,
    Guideline,
    IndicatedForProps,
    InteractsWithProps,
    InteractionSeverity,
    Lab,
    Likelihood,
    MonitoredByProps,
    Organization,
    PatientVariable,
    Population,
    PopulationCriterion,
    Procedure,
    Publication,
    Recommendation,
    RecommendationStrength,
    RecommendationType,
    Symptom,
    TemporalConstraint,
    TemporalType,
    VariableType,
)


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestRecommendationType:
    def test_all_values(self):
        expected = {
            "treatment_selection", "dosing", "contraindication", "interaction",
            "monitoring", "diagnostic_criteria", "prevention", "referral",
            "device_therapy", "lifestyle", "discharge", "follow_up",
        }
        assert {v.value for v in RecommendationType} == expected

    def test_string_coercion(self):
        assert RecommendationType("dosing") == RecommendationType.DOSING


class TestEvidenceQuality:
    def test_all_values(self):
        assert {v.value for v in EvidenceQuality} == {
            "high", "moderate", "low", "very_low", "expert",
        }


class TestRecommendationStrength:
    def test_all_values(self):
        assert {v.value for v in RecommendationStrength} == {
            "strong_for", "moderate_for", "weak_for", "strong_against", "no_benefit",
        }


class TestTemporalType:
    def test_all_values(self):
        assert {v.value for v in TemporalType} == {
            "duration", "frequency", "relative", "sequence", "washout", "reassessment",
        }


class TestInteractionSeverity:
    def test_all_values(self):
        assert {v.value for v in InteractionSeverity} == {"major", "moderate", "minor"}


class TestContraindicationSeverity:
    def test_all_values(self):
        assert {v.value for v in ContraindicationSeverity} == {"absolute", "relative"}


class TestLikelihood:
    def test_all_values(self):
        assert {v.value for v in Likelihood} == {"common", "uncommon", "rare"}


# ---------------------------------------------------------------------------
# Clinical Core Node tests
# ---------------------------------------------------------------------------


class TestDrug:
    def test_valid_drug(self):
        d = Drug(
            id="rxnorm:1656354",
            name="Sacubitril/Valsartan",
            rxnorm_code="1656354",
            snomed_code="716083005",
            atc_code="C09DX04",
            aliases=["Entresto", "ARNi"],
        )
        assert d.id == "rxnorm:1656354"
        assert d.name == "Sacubitril/Valsartan"
        assert len(d.aliases) == 2

    def test_minimal_drug(self):
        d = Drug(id="rxnorm:123", name="TestDrug")
        assert d.rxnorm_code is None
        assert d.aliases == []

    def test_requires_id_and_name(self):
        with pytest.raises(Exception):
            Drug(name="No ID")


class TestDrugClass:
    def test_valid_drug_class(self):
        dc = DrugClass(
            id="atc:C07",
            name="Beta Blocker",
            atc_code="C07",
            fda_epc="Beta-Adrenergic Blocker",
            aliases=["BB", "beta-blocker"],
        )
        assert dc.atc_code == "C07"

    def test_minimal(self):
        dc = DrugClass(id="atc:X", name="Test")
        assert dc.fda_epc is None


class TestDisease:
    def test_valid_disease(self):
        d = Disease(
            id="snomed:84114007",
            name="Heart Failure",
            snomed_code="84114007",
            icd10_code="I50",
            mondo_id="MONDO:0005252",
            aliases=["HF", "CHF"],
        )
        assert d.icd10_code == "I50"

    def test_minimal(self):
        d = Disease(id="snomed:123", name="Test Disease")
        assert d.mondo_id is None


class TestSymptom:
    def test_valid_symptom(self):
        s = Symptom(
            id="snomed:267036007",
            name="Dyspnea",
            snomed_code="267036007",
            aliases=["SOB", "shortness of breath"],
        )
        assert s.snomed_code == "267036007"


class TestLab:
    def test_valid_lab(self):
        lab = Lab(
            id="loinc:77147-7",
            name="eGFR",
            loinc_code="77147-7",
            unit="mL/min/1.73m²",
            reference_range=">60",
        )
        assert lab.unit == "mL/min/1.73m²"

    def test_minimal(self):
        lab = Lab(id="loinc:X", name="Test Lab")
        assert lab.reference_range is None


class TestProcedure:
    def test_valid_procedure(self):
        p = Procedure(
            id="snomed:40701008",
            name="Echocardiography",
            snomed_code="40701008",
            cpt_code="93306",
        )
        assert p.cpt_code == "93306"


class TestDevice:
    def test_valid_device(self):
        d = Device(
            id="snomed:72506001",
            name="ICD",
            snomed_code="72506001",
            gmdn_code="37017",
            aliases=["implantable cardioverter-defibrillator"],
        )
        assert d.gmdn_code == "37017"


# ---------------------------------------------------------------------------
# Evidence & Recommendation Node tests
# ---------------------------------------------------------------------------


class TestGuideline:
    def test_valid_guideline(self):
        g = Guideline(
            id="acc_aha_hf_2022",
            title="2022 AHA/ACC/HFSA Heart Failure Guideline",
            doi="10.1161/CIR.0000000000001063",
            year=2022,
            organization="AHA/ACC/HFSA",
            version="1.0",
        )
        assert g.year == 2022
        assert g.version == "1.0"

    def test_version_optional(self):
        g = Guideline(id="g1", title="T", doi="10.x/y", year=2024, organization="O")
        assert g.version is None


class TestRecommendation:
    def test_valid_recommendation(self):
        rec = Recommendation(
            id="rec_001",
            type=RecommendationType.TREATMENT_SELECTION,
            action="Prescribe ARNi",
            action_detail="In patients with HFrEF, ARNi is recommended",
            strength=RecommendationStrength.STRONG_FOR,
            evidence_quality=EvidenceQuality.HIGH,
            guideline_id="acc_aha_hf_2022",
            section="Pharmacologic Treatment",
            page=42,
        )
        assert rec.strength == RecommendationStrength.STRONG_FOR
        assert rec.evidence_quality == EvidenceQuality.HIGH

    def test_conditions_json_optional(self):
        rec = Recommendation(
            id="rec_002",
            type=RecommendationType.DOSING,
            action="Start low dose",
            action_detail="Titrate to target",
            strength=RecommendationStrength.STRONG_FOR,
            evidence_quality=EvidenceQuality.MODERATE,
            guideline_id="g1",
        )
        assert rec.conditions_json is None
        assert rec.section is None
        assert rec.page is None


class TestEvidenceChunk:
    def test_valid_chunk(self):
        ec = EvidenceChunk(
            id="chunk_001",
            text="In patients with HFrEF...",
            section="Treatment",
            page_start=42,
            page_end=43,
        )
        assert ec.page_start == 42

    def test_minimal_chunk(self):
        ec = EvidenceChunk(id="c1", text="Some text")
        assert ec.section is None
        assert ec.embedding is None


class TestPublication:
    def test_valid_publication(self):
        pub = Publication(
            doi="10.1056/NEJMoa1409077",
            title="PARADIGM-HF Trial",
            year=2014,
            study_type="RCT",
        )
        assert pub.doi == "10.1056/NEJMoa1409077"

    def test_minimal(self):
        pub = Publication(doi="10.x/y")
        assert pub.title is None


# ---------------------------------------------------------------------------
# Patient Context tests
# ---------------------------------------------------------------------------


class TestPopulationCriterion:
    def test_valid_criterion(self):
        pc = PopulationCriterion(
            variable="LVEF", operator="<=", threshold=40, unit="%"
        )
        assert pc.threshold == 40

    def test_valid_operators(self):
        for op in ["<", "<=", ">", ">=", "==", "!="]:
            pc = PopulationCriterion(variable="x", operator=op, threshold=1)
            assert pc.operator == op

    def test_invalid_operator(self):
        with pytest.raises(Exception):
            PopulationCriterion(variable="x", operator="~", threshold=1)

    def test_string_threshold(self):
        pc = PopulationCriterion(variable="HF_type", operator="==", threshold="HFrEF")
        assert pc.threshold == "HFrEF"


class TestPopulation:
    def test_valid_population(self):
        pop = Population(
            id="pop_001",
            description="HFrEF, LVEF <=40%, NYHA II-IV",
            inclusion=[
                PopulationCriterion(variable="LVEF", operator="<=", threshold=40, unit="%"),
                PopulationCriterion(variable="NYHA_class", operator=">=", threshold=2),
            ],
            exclusion=[
                PopulationCriterion(variable="Pregnancy", operator="==", threshold="true"),
            ],
        )
        assert len(pop.inclusion) == 2
        assert len(pop.exclusion) == 1

    def test_defaults_empty(self):
        pop = Population(id="p1", description="Test")
        assert pop.inclusion == []
        assert pop.exclusion == []


class TestPatientVariable:
    def test_valid_variable(self):
        pv = PatientVariable(
            id="pv:lvef",
            name="LVEF",
            loinc_code="10230-1",
            unit="%",
            var_type=VariableType.CONTINUOUS,
        )
        assert pv.var_type == VariableType.CONTINUOUS

    def test_boolean_variable(self):
        pv = PatientVariable(
            id="pv:pregnancy",
            name="Pregnancy",
            var_type=VariableType.BOOLEAN,
        )
        assert pv.loinc_code is None


# ---------------------------------------------------------------------------
# Temporal tests
# ---------------------------------------------------------------------------


class TestTemporalConstraint:
    def test_washout(self):
        tc = TemporalConstraint(
            id="tc_001",
            type=TemporalType.WASHOUT,
            value=36,
            unit="hours",
            reference_event="last_ACEi_dose",
            relation="after",
        )
        assert tc.type == TemporalType.WASHOUT
        assert tc.value == 36

    def test_minimal(self):
        tc = TemporalConstraint(id="tc_x", type=TemporalType.DURATION)
        assert tc.value is None
        assert tc.unit is None


# ---------------------------------------------------------------------------
# Administrative tests
# ---------------------------------------------------------------------------


class TestOrganization:
    def test_valid(self):
        org = Organization(
            id="aha", name="American Heart Association", abbreviation="AHA", country="US"
        )
        assert org.abbreviation == "AHA"


class TestCareSetting:
    def test_valid(self):
        cs = CareSetting(id="outpatient", name="outpatient")
        assert cs.name == "outpatient"


class TestCareTeamRole:
    def test_valid(self):
        ctr = CareTeamRole(id="cardiologist", name="cardiologist")
        assert ctr.name == "cardiologist"


# ---------------------------------------------------------------------------
# Edge property model tests
# ---------------------------------------------------------------------------


class TestIndicatedForProps:
    def test_valid(self):
        p = IndicatedForProps(
            strength=RecommendationStrength.STRONG_FOR,
            evidence_quality=EvidenceQuality.HIGH,
            conditions_json='[{"variable": "LVEF", "operator": "<=", "threshold": 40}]',
        )
        assert p.strength == RecommendationStrength.STRONG_FOR


class TestContraindicatedInProps:
    def test_valid(self):
        p = ContraindicatedInProps(
            strength=RecommendationStrength.STRONG_AGAINST,
            severity=ContraindicationSeverity.ABSOLUTE,
        )
        assert p.severity == ContraindicationSeverity.ABSOLUTE


class TestInteractsWithProps:
    def test_valid(self):
        p = InteractsWithProps(
            severity=InteractionSeverity.MAJOR,
            mechanism="CYP3A4 inhibition",
            clinical_effect="Increased bleeding risk",
        )
        assert p.severity == InteractionSeverity.MAJOR


class TestDosedForProps:
    def test_valid(self):
        p = DosedForProps(
            starting_dose="2.5 mg BID",
            target_dose="10 mg BID",
            max_dose="10 mg BID",
            route="oral",
            frequency="BID",
        )
        assert p.starting_dose == "2.5 mg BID"

    def test_all_optional(self):
        p = DosedForProps()
        assert p.starting_dose is None


class TestMonitoredByProps:
    def test_valid(self):
        p = MonitoredByProps(
            frequency="weekly for first month",
            threshold_alert="K+ > 5.5 mEq/L",
            threshold_stop="K+ > 6.0 mEq/L",
        )
        assert p.threshold_alert == "K+ > 5.5 mEq/L"


class TestCausesSideEffectProps:
    def test_valid(self):
        p = CausesSideEffectProps(frequency=Likelihood.COMMON, severity="mild")
        assert p.frequency == Likelihood.COMMON


class TestPresentsWithProps:
    pass  # Covered by PresentsWithProps — same pattern as CausesSideEffectProps


class TestDiagnosedByProps:
    def test_valid(self):
        p = DiagnosedByProps(
            sensitivity="95%", specificity="85%", when_to_order="Initial evaluation"
        )
        assert p.sensitivity == "95%"


class TestDefinesProps:
    def test_valid(self):
        p = DefinesProps(operator="<=", threshold=40, unit="%")
        assert p.threshold == 40


# ---------------------------------------------------------------------------
# Registry / constant tests
# ---------------------------------------------------------------------------


class TestNodeLabelMap:
    def test_all_node_types_present(self):
        expected_labels = {
            "Drug", "DrugClass", "Disease", "Symptom", "Lab", "Procedure", "Device",
            "Guideline", "Recommendation", "EvidenceChunk", "Publication",
            "Population", "PatientVariable", "TemporalConstraint",
            "Organization", "CareSetting", "CareTeamRole",
        }
        assert set(NODE_LABEL_MAP.keys()) == expected_labels


class TestClinicalLabels:
    def test_clinical_labels(self):
        assert CLINICAL_LABELS == frozenset(
            {"Drug", "DrugClass", "Disease", "Symptom", "Lab", "Procedure", "Device"}
        )


class TestSemanticEdgeTypes:
    def test_expected_edges(self):
        assert "INDICATED_FOR" in SEMANTIC_EDGE_TYPES
        assert "CONTRAINDICATED_IN" in SEMANTIC_EDGE_TYPES
        assert "INTERACTS_WITH" in SEMANTIC_EDGE_TYPES
        assert "DOSED_FOR" in SEMANTIC_EDGE_TYPES
        assert "MONITORED_BY" in SEMANTIC_EDGE_TYPES
        assert "MEMBER_OF" in SEMANTIC_EDGE_TYPES

    def test_no_generic_edges(self):
        assert "PARTICIPATES_IN" not in SEMANTIC_EDGE_TYPES


class TestEvidenceEdgeTypes:
    def test_expected_edges(self):
        assert "RECOMMENDS" in EVIDENCE_EDGE_TYPES
        assert "SOURCED_FROM" in EVIDENCE_EDGE_TYPES
        assert "DEFINED_BY" in EVIDENCE_EDGE_TYPES
        assert "FOR_CONDITION" in EVIDENCE_EDGE_TYPES
