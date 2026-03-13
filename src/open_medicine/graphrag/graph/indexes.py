def get_constraint_statements() -> list[str]:
    return [
        "CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (n:Concept) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT logic_node_id IF NOT EXISTS FOR (n:LogicNode) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT evidence_chunk_id IF NOT EXISTS FOR (n:EvidenceChunk) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT guideline_id IF NOT EXISTS FOR (n:Guideline) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT patient_variable_id IF NOT EXISTS FOR (n:PatientVariable) REQUIRE n.id IS UNIQUE",
    ]


def get_index_statements() -> list[str]:
    return [
        "CREATE INDEX concept_snomed IF NOT EXISTS FOR (n:Concept) ON (n.snomed_code)",
        "CREATE INDEX concept_type IF NOT EXISTS FOR (n:Concept) ON (n.type)",
        "CREATE INDEX logic_node_type IF NOT EXISTS FOR (n:LogicNode) ON (n.type)",
        "CREATE INDEX logic_node_guideline IF NOT EXISTS FOR (n:LogicNode) ON (n.guideline_id)",
        "CREATE FULLTEXT INDEX evidence_text IF NOT EXISTS FOR (n:EvidenceChunk) ON EACH [n.text]",
    ]
