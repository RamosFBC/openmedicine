"""GraphRAG Index Definitions v2 — Label-per-type indexes and constraints.

Supersedes indexes.py (single Concept label indexes).
"""


def get_constraint_statements() -> list[str]:
    """Uniqueness constraints for all node types."""
    return [
        # Clinical core
        "CREATE CONSTRAINT drug_id IF NOT EXISTS FOR (n:Drug) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT drugclass_id IF NOT EXISTS FOR (n:DrugClass) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT disease_id IF NOT EXISTS FOR (n:Disease) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT symptom_id IF NOT EXISTS FOR (n:Symptom) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT lab_id IF NOT EXISTS FOR (n:Lab) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT procedure_id IF NOT EXISTS FOR (n:Procedure) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT device_id IF NOT EXISTS FOR (n:Device) REQUIRE n.id IS UNIQUE",
        # Evidence & recommendations
        "CREATE CONSTRAINT guideline_id IF NOT EXISTS FOR (n:Guideline) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT recommendation_id IF NOT EXISTS FOR (n:Recommendation) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT evidence_chunk_id IF NOT EXISTS FOR (n:EvidenceChunk) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT publication_doi IF NOT EXISTS FOR (n:Publication) REQUIRE n.doi IS UNIQUE",
        # Patient context
        "CREATE CONSTRAINT population_id IF NOT EXISTS FOR (n:Population) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT patient_variable_id IF NOT EXISTS FOR (n:PatientVariable) REQUIRE n.id IS UNIQUE",
        # Temporal
        "CREATE CONSTRAINT temporal_constraint_id IF NOT EXISTS FOR (n:TemporalConstraint) REQUIRE n.id IS UNIQUE",
        # Administrative
        "CREATE CONSTRAINT organization_id IF NOT EXISTS FOR (n:Organization) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT care_setting_id IF NOT EXISTS FOR (n:CareSetting) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT care_team_role_id IF NOT EXISTS FOR (n:CareTeamRole) REQUIRE n.id IS UNIQUE",
    ]


def get_index_statements() -> list[str]:
    """Property indexes, full-text search, and vector indexes."""
    return [
        # -- Label-based property indexes (fast lookups) -----------------------
        # Drug
        "CREATE INDEX drug_name IF NOT EXISTS FOR (n:Drug) ON (n.name)",
        "CREATE INDEX drug_rxnorm IF NOT EXISTS FOR (n:Drug) ON (n.rxnorm_code)",
        # DrugClass
        "CREATE INDEX drugclass_name IF NOT EXISTS FOR (n:DrugClass) ON (n.name)",
        "CREATE INDEX drugclass_atc IF NOT EXISTS FOR (n:DrugClass) ON (n.atc_code)",
        # Disease
        "CREATE INDEX disease_name IF NOT EXISTS FOR (n:Disease) ON (n.name)",
        "CREATE INDEX disease_snomed IF NOT EXISTS FOR (n:Disease) ON (n.snomed_code)",
        "CREATE INDEX disease_icd10 IF NOT EXISTS FOR (n:Disease) ON (n.icd10_code)",
        # Lab
        "CREATE INDEX lab_name IF NOT EXISTS FOR (n:Lab) ON (n.name)",
        "CREATE INDEX lab_loinc IF NOT EXISTS FOR (n:Lab) ON (n.loinc_code)",
        # Procedure
        "CREATE INDEX procedure_name IF NOT EXISTS FOR (n:Procedure) ON (n.name)",
        "CREATE INDEX procedure_snomed IF NOT EXISTS FOR (n:Procedure) ON (n.snomed_code)",
        # Device
        "CREATE INDEX device_name IF NOT EXISTS FOR (n:Device) ON (n.name)",
        "CREATE INDEX device_snomed IF NOT EXISTS FOR (n:Device) ON (n.snomed_code)",
        # Symptom
        "CREATE INDEX symptom_name IF NOT EXISTS FOR (n:Symptom) ON (n.name)",
        "CREATE INDEX symptom_snomed IF NOT EXISTS FOR (n:Symptom) ON (n.snomed_code)",
        # Recommendation
        "CREATE INDEX recommendation_type IF NOT EXISTS FOR (n:Recommendation) ON (n.type)",
        "CREATE INDEX recommendation_guideline IF NOT EXISTS FOR (n:Recommendation) ON (n.guideline_id)",
        # PatientVariable
        "CREATE INDEX patient_variable_loinc IF NOT EXISTS FOR (n:PatientVariable) ON (n.loinc_code)",
        # -- Full-text search (clinical entity name search) --------------------
        "CREATE FULLTEXT INDEX clinical_entity_search IF NOT EXISTS "
        "FOR (n:Drug | n:DrugClass | n:Disease | n:Lab | n:Procedure | n:Device | n:Symptom) "
        "ON EACH [n.name]",
        # -- Vector index (semantic search on evidence) ------------------------
        "CREATE VECTOR INDEX evidence_embedding IF NOT EXISTS "
        "FOR (n:EvidenceChunk) ON (n.embedding) "
        "OPTIONS {indexConfig: {`vector.dimensions`: 1024, `vector.similarity_function`: 'cosine'}}",
    ]
