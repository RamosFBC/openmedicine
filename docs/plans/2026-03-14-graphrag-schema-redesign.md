# GraphRAG Schema Redesign — Production-Grade Clinical Knowledge Graph

**Date:** 2026-03-14
**Status:** Draft
**Supersedes:** Original schema in `graph/schema.py` and `graph/queries.py`
**Research basis:** Hetionet (24 edge types), PrimeKG (30 edge types), CKG (47 edge types), Biolink Model, UMLS Semantic Network, OMOP CDM, FHIR R4/R5 Clinical Reasoning

## 1. Problem Statement

The current GraphRAG schema has 5 fundamental architectural problems that make it unsuitable for production clinical decision support:

1. **Single-label `Concept` node** — All clinical entities (drugs, diseases, labs, procedures, symptoms) share one label. Neo4j cannot use label-based indexing; every query must filter on `.type` property.

2. **Generic `PARTICIPATES_IN` relationship** — One edge type connects ALL concepts to LogicNodes regardless of clinical role. A drug and the disease it treats have identical edges to the same node. The graph cannot natively answer "What treats HFrEF?" without multi-hop traversal and type filtering.

3. **LogicNode overload** — The LogicNode simultaneously acts as a recommendation, condition evaluator, relationship proxy, and evidence container. This violates single-responsibility and makes the graph opaque.

4. **1:1 EvidenceChunk:LogicNode** — Every LogicNode gets its own EvidenceChunk even when the same source text produces multiple rules. This creates text duplication and defeats the purpose of chunking.

5. **PatientVariable/Concept disconnection** — `LVEF` exists as both a PatientVariable and a Concept(type=lab) with no link between them. Two parallel systems model the same reality.

### What production biomedical KGs do differently

| Pattern | Hetionet | PrimeKG | CKG | Our Current |
|---------|----------|---------|-----|-------------|
| Node labels per type | 11 distinct | 10 distinct | 36 distinct | 1 (`Concept`) |
| Relationship types | 24 specific | 30 specific | 47 specific | 1 (`PARTICIPATES_IN`) |
| Drug class modeling | Separate `PharmacologicClass` label | Single `Drug` | Single `Drug` | None |
| Evidence on edges | Edge properties | Edge properties | Edge properties + Publication nodes | Trapped in LogicNode |
| Ontology alignment | DOID, DrugBank, MeSH | MONDO, DrugBank | Disease Ontology, UniProt | Ad-hoc snake_case IDs |

## 2. BioCypher Assessment

**Decision: Do not adopt BioCypher.**

BioCypher (v0.12.5, Jan 2026) is designed for integrating multiple existing databases (DrugBank, UniProt, STRING) into unified KGs using adapter patterns. Our use case — LLM-extracted clinical rules from guideline PDFs loaded into Neo4j Aura — doesn't match:

- BioCypher's primary output is CSV files for `neo4j-admin import` (bulk import). Our pipeline needs MERGE-based idempotent loading for incremental guideline additions.
- BioCypher mandates ontology mapping to Biolink Model. Our clinical guideline domain (recommendations, evidence strength, patient eligibility criteria) isn't well-modeled by Biolink's molecular-biology-focused hierarchy.
- BioCypher is still Alpha status. Adding a framework dependency for what amounts to a Cypher query builder is unjustified.
- Our loader already handles the hard parts: agent-based extraction, concept normalization, batch Neo4j writes.

**What we take from BioCypher's philosophy:** Ontology-driven schema definition, adapter pattern for data sources, consistent ID systems per entity type.

## 3. Redesigned Schema

### 3.1 Node Labels (Type-Native)

Every clinical entity type gets its own Neo4j label. This enables label-based indexing, type-safe queries, and schema enforcement.

#### Clinical Core

| Label | What It Represents | Primary ID System | Properties |
|-------|-------------------|-------------------|------------|
| `Drug` | Specific medications | RxNorm CUI | `name`, `rxnorm_code`, `snomed_code`, `atc_code`, `aliases[]` |
| `DrugClass` | Pharmacologic classes (ATC L2-L4) | ATC code | `name`, `atc_code`, `fda_epc`, `aliases[]` |
| `Disease` | Conditions, syndromes, clinical states | SNOMED-CT | `name`, `snomed_code`, `icd10_code`, `mondo_id`, `aliases[]` |
| `Symptom` | Patient-reported symptoms, signs | SNOMED-CT | `name`, `snomed_code`, `aliases[]` |
| `Lab` | Lab tests, biomarkers, measurements, vitals | LOINC | `name`, `loinc_code`, `snomed_code`, `unit`, `reference_range` |
| `Procedure` | Diagnostic/therapeutic procedures | SNOMED-CT | `name`, `snomed_code`, `cpt_code`, `aliases[]` |
| `Device` | Medical devices (ICD, CRT, LVAD, CPAP) | SNOMED-CT | `name`, `snomed_code`, `gmdn_code`, `aliases[]` |

#### Evidence & Recommendations

| Label | What It Represents | Primary ID System | Properties |
|-------|-------------------|-------------------|------------|
| `Guideline` | Source document | DOI | `id`, `title`, `doi`, `year`, `organization`, `version` |
| `Recommendation` | A single clinical recommendation (replaces LogicNode) | Deterministic | `id`, `type` (enum), `action`, `action_detail`, `strength`, `evidence_quality`, `grade_direction`, `conditions_json`, `guideline_id`, `section`, `page` |
| `EvidenceChunk` | Source text passage (shared across Recommendations) | Content hash | `id`, `text`, `section`, `page_start`, `page_end`, `embedding[]` |
| `Publication` | Cited study/trial supporting a recommendation | DOI | `doi`, `title`, `authors`, `journal`, `year`, `study_type` |

#### Patient Context

| Label | What It Represents | Primary ID System | Properties |
|-------|-------------------|-------------------|------------|
| `PatientVariable` | Evaluable patient parameter | LOINC where applicable | `id`, `name`, `loinc_code`, `unit`, `var_type` (continuous/categorical/boolean) |
| `Population` | Defined patient cohort for a recommendation | Deterministic | `id`, `description`, `criteria_json` (structured FHIR-like criteria) |

#### Temporal

| Label | What It Represents | Properties |
|-------|-------------------|------------|
| `TemporalConstraint` | Timing requirement for an action | `id`, `type` (duration/frequency/relative/sequence), `value`, `unit`, `reference_event`, `relation` (within/before/after/during) |

#### Administrative

| Label | What It Represents | Properties |
|-------|-------------------|------------|
| `Organization` | Guideline publisher (AHA, ACC, ESC) | `id`, `name`, `abbreviation`, `country` |
| `CareSetting` | Where care is delivered | `id`, `name` (inpatient/outpatient/ICU/ED/ambulatory) |
| `CareTeamRole` | Specialist type for referrals | `id`, `name` (cardiologist/electrophysiologist/surgeon) |

### 3.2 Relationship Types (Semantic Edges)

The core insight from Hetionet/PrimeKG: **the relationship type IS the clinical semantics**. No generic edges.

#### Drug Relationships

| Relationship | Source → Target | Edge Properties | Derivation from Current Data |
|-------------|----------------|-----------------|------------------------------|
| `INDICATED_FOR` | Drug/DrugClass → Disease | `strength`, `evidence_quality`, `grade_direction`, `conditions_json` | LogicNode.type == `treatment_selection`, concept types drug+disease |
| `CONTRAINDICATED_IN` | Drug/DrugClass → Disease | `strength`, `severity` (absolute/relative), `conditions_json` | LogicNode.type == `contraindication`, concept types drug+disease |
| `INTERACTS_WITH` | Drug → Drug | `severity` (major/moderate/minor), `mechanism`, `clinical_effect` | LogicNode.type == `interaction`, both concepts type drug |
| `DOSED_FOR` | Drug → Disease | `starting_dose`, `target_dose`, `max_dose`, `route`, `frequency`, `titration_schedule`, `conditions_json` | LogicNode.type == `dosing`, concept types drug+disease |
| `MONITORED_BY` | Drug → Lab | `frequency`, `threshold_alert`, `threshold_stop`, `conditions_json` | LogicNode.type == `monitoring`, concept types drug+lab |
| `CAUSES_SIDE_EFFECT` | Drug → Symptom/Disease | `frequency` (common/uncommon/rare), `severity` | Extracted from contraindication/monitoring context |
| `MEMBER_OF` | Drug → DrugClass | (none) | Drug class membership (carvedilol MEMBER_OF Beta Blocker) |

#### Disease Relationships

| Relationship | Source → Target | Edge Properties |
|-------------|----------------|-----------------|
| `PRESENTS_WITH` | Disease → Symptom | `frequency` (common/uncommon/rare), `specificity` |
| `DIAGNOSED_BY` | Disease → Procedure/Lab | `sensitivity`, `specificity`, `when_to_order`, `conditions_json` |
| `RISK_FACTOR_FOR` | Disease/Exposure → Disease | `relative_risk`, `strength` |
| `STAGE_OF` | Disease → Disease | `stage_system`, `stage_value` (e.g., HFrEF STAGE_OF Heart Failure, Stage C) |
| `COMPLICATES` | Disease → Disease | `frequency`, `mechanism` |

#### Procedure/Device Relationships

| Relationship | Source → Target | Edge Properties |
|-------------|----------------|-----------------|
| `INDICATED_FOR` | Procedure/Device → Disease | `strength`, `evidence_quality`, `conditions_json` |
| `CONTRAINDICATED_IN` | Procedure/Device → Disease | `strength`, `severity` |
| `REQUIRES_MONITORING` | Procedure → Lab | `frequency`, `threshold` |

#### Evidence Provenance (Layer 2)

| Relationship | Source → Target | Edge Properties |
|-------------|----------------|-----------------|
| `RECOMMENDS` | Recommendation → Drug/DrugClass/Procedure/Device | `role` (primary/alternative/adjunct) |
| `FOR_CONDITION` | Recommendation → Disease | (none) |
| `SOURCED_FROM` | Recommendation → EvidenceChunk | (none) |
| `DEFINED_BY` | Recommendation → Guideline | (none) |
| `CITED_IN` | Publication → Recommendation | `citation_context` |
| `PUBLISHED_BY` | Guideline → Organization | (none) |
| `EVALUATES` | Recommendation → PatientVariable | (none) |
| `APPLIES_TO` | Recommendation → Population | (none) |
| `TIMED_BY` | Recommendation → TemporalConstraint | (none) |
| `DELIVERED_IN` | Recommendation → CareSetting | (none) |
| `REFERRED_TO` | Recommendation → CareTeamRole | (none) |

#### Cross-Guideline

| Relationship | Source → Target | Edge Properties |
|-------------|----------------|-----------------|
| `CONFLICTS_WITH` | Recommendation → Recommendation | `resolution` (newer/stronger/specialist), `resolution_detail` |
| `SUPERSEDES` | Recommendation → Recommendation | `reason` |
| `CORROBORATES` | Recommendation → Recommendation | (none — same conclusion from different sources) |

#### Patient Context

| Relationship | Source → Target | Edge Properties |
|-------------|----------------|-----------------|
| `MEASURES` | PatientVariable → Lab | (none — links the evaluable parameter to the lab entity) |
| `DEFINES` | Population → Disease/Lab/PatientVariable | `operator`, `threshold`, `unit` |

### 3.3 Recommendation Types (replaces LogicNodeType)

```python
class RecommendationType(StrEnum):
    TREATMENT_SELECTION = "treatment_selection"   # When to choose a treatment
    DOSING = "dosing"                              # Specific drug dosing
    CONTRAINDICATION = "contraindication"          # When NOT to use
    INTERACTION = "interaction"                     # Drug-drug interactions
    MONITORING = "monitoring"                       # What to monitor and when
    DIAGNOSTIC_CRITERIA = "diagnostic_criteria"    # How to diagnose/classify
    PREVENTION = "prevention"                      # Primary/secondary prevention
    REFERRAL = "referral"                          # When to refer to specialist
    DEVICE_THERAPY = "device_therapy"              # Device-based interventions
    LIFESTYLE = "lifestyle"                        # Non-pharmacologic interventions
    DISCHARGE = "discharge"                        # Discharge/transition of care
    FOLLOW_UP = "follow_up"                        # Follow-up scheduling/monitoring
```

### 3.4 Evidence Strength (GRADE-aligned)

```python
class EvidenceQuality(StrEnum):
    HIGH = "high"           # LOE A — RCTs, meta-analyses
    MODERATE = "moderate"   # LOE B-R — Randomized, moderate quality
    LOW = "low"             # LOE B-NR — Non-randomized
    VERY_LOW = "very_low"   # LOE C-LD — Limited data
    EXPERT = "expert"       # LOE C-EO — Expert opinion

class RecommendationStrength(StrEnum):
    STRONG_FOR = "strong_for"         # Class I — Benefit >>> Risk
    MODERATE_FOR = "moderate_for"     # Class IIa — Benefit >> Risk
    WEAK_FOR = "weak_for"             # Class IIb — Benefit >= Risk
    STRONG_AGAINST = "strong_against" # Class III (Harm) — Risk >>> Benefit
    NO_BENEFIT = "no_benefit"         # Class III (No Benefit) — No proven benefit
```

Stored as two separate properties on Recommendation nodes and semantic edges, rather than a single concatenated string like "Strong/A".

## 4. Dual-Layer Graph Architecture

The schema implements two traversal layers, following the CKG/Hetionet pattern:

### Layer 1: Semantic Knowledge Graph (direct clinical queries)

Direct typed edges between clinical entities. One-hop answers to clinical questions.

```
Query: "What treats HFrEF?"
Cypher: MATCH (d:Drug)-[r:INDICATED_FOR]->(dis:Disease {name: "HFrEF"})
        RETURN d.name, r.strength, r.evidence_quality

Query: "What are the contraindications for ACE Inhibitors?"
Cypher: MATCH (d:DrugClass {name: "ACE Inhibitor"})-[r:CONTRAINDICATED_IN]->(dis:Disease)
        RETURN dis.name, r.severity

Query: "What interacts with Digoxin?"
Cypher: MATCH (d:Drug {name: "Digoxin"})-[r:INTERACTS_WITH]-(other:Drug)
        RETURN other.name, r.severity, r.mechanism

Query: "What should be monitored for MRA?"
Cypher: MATCH (dc:DrugClass {name: "MRA"})-[r:MONITORED_BY]->(lab:Lab)
        RETURN lab.name, r.frequency, r.threshold_alert
```

### Layer 2: Evidence/Recommendation Layer (provenance trail)

When an agent needs the full evidence chain — source text, guideline citation, patient criteria, temporal constraints:

```
Query: "Show me the full recommendation for ARNi in HFrEF"
Cypher: MATCH (rec:Recommendation)-[:RECOMMENDS]->(d:Drug {name: "Sacubitril/Valsartan"})
        MATCH (rec)-[:FOR_CONDITION]->(dis:Disease {name: "HFrEF"})
        MATCH (rec)-[:SOURCED_FROM]->(ec:EvidenceChunk)
        MATCH (rec)-[:DEFINED_BY]->(g:Guideline)
        OPTIONAL MATCH (rec)-[:EVALUATES]->(pv:PatientVariable)
        OPTIONAL MATCH (rec)-[:TIMED_BY]->(tc:TemporalConstraint)
        RETURN rec, ec.text, g.doi, collect(pv), collect(tc)
```

### How the two layers connect

Every semantic edge (Layer 1) is backed by one or more Recommendation nodes (Layer 2). The semantic edge carries the strongest recommendation's properties. When multiple guidelines make the same recommendation, the edge reflects the most recent/strongest.

```
# Layer 1 semantic edge (fast lookup)
(Sacubitril/Valsartan:Drug)-[:INDICATED_FOR {
    strength: "strong_for",
    evidence_quality: "moderate",
    conditions_json: '[{"variable": "LVEF", "operator": "<=", "threshold": 40}]'
}]->(HFrEF:Disease)

# Layer 2 backing recommendations (full provenance)
(rec1:Recommendation {action: "Prescribe ARNi", strength: "strong_for"})
  -[:RECOMMENDS]->(Sacubitril/Valsartan:Drug)
(rec1)-[:FOR_CONDITION]->(HFrEF:Disease)
(rec1)-[:SOURCED_FROM]->(ec:EvidenceChunk {text: "In patients with HFrEF..."})
(rec1)-[:DEFINED_BY]->(g:Guideline {doi: "10.1161/CIR.0000000000001063"})
```

## 5. Concept Identity System

### Primary identifiers per entity type

| Entity Type | Primary ID System | ID Format | Example |
|-------------|-------------------|-----------|---------|
| Drug | RxNorm CUI | `rxnorm:{CUI}` | `rxnorm:1656354` (sacubitril/valsartan) |
| DrugClass | ATC L2-L4 | `atc:{code}` | `atc:C09DX04` (sacubitril/valsartan) |
| Disease | SNOMED-CT | `snomed:{code}` | `snomed:84114007` (heart failure) |
| Symptom | SNOMED-CT | `snomed:{code}` | `snomed:267036007` (dyspnea) |
| Lab | LOINC | `loinc:{code}` | `loinc:10230-1` (LVEF) |
| Procedure | SNOMED-CT | `snomed:{code}` | `snomed:40701008` (echocardiography) |
| Device | SNOMED-CT | `snomed:{code}` | `snomed:72506001` (ICD) |

### Cross-reference properties

Every clinical node carries cross-references to other ID systems as properties:

```python
class Drug(BaseModel):
    id: str              # Primary: "rxnorm:1656354"
    name: str            # Canonical: "Sacubitril/Valsartan"
    rxnorm_code: str     # "1656354"
    snomed_code: str | None  # "716083005"
    atc_code: str | None     # "C09DX04"
    drugbank_id: str | None  # "DB09292"
    aliases: list[str]   # ["ARNi", "Entresto", "sacubitril-valsartan"]
```

### Local terminology database

Instead of calling external services, we maintain a local SQLite or Python dict mapping for validated terminology. This is built by:

1. Extracting all unique concepts from guideline extractions
2. Looking up codes via one-time web search during concept normalization
3. Storing the validated mapping in `src/open_medicine/graphrag/terminology/`
4. The mapping is version-controlled and grows as new guidelines are ingested

Structure:
```
src/open_medicine/graphrag/terminology/
    drugs.json          # {canonical_name: {rxnorm, snomed, atc, aliases}}
    diseases.json       # {canonical_name: {snomed, icd10, mondo, aliases}}
    labs.json           # {canonical_name: {loinc, snomed, unit, reference_range}}
    procedures.json     # {canonical_name: {snomed, cpt, aliases}}
    devices.json        # {canonical_name: {snomed, gmdn, aliases}}
    symptoms.json       # {canonical_name: {snomed, aliases}}
    drug_classes.json   # {canonical_name: {atc, fda_epc, member_drugs[]}}
    variables.json      # {canonical_name: {loinc, unit, var_type, linked_lab}}
```

Each file is a curated, DOI-verified mapping. The linker resolves aliases to canonical names using this data. New concepts discovered during extraction trigger a normalization step that adds them to the appropriate file.

## 6. Drug Class Hierarchy

Following Hetionet's explicit `PharmacologicClass` separation:

```
(Carvedilol:Drug)-[:MEMBER_OF]->(Beta Blocker:DrugClass)
(Metoprolol Succinate:Drug)-[:MEMBER_OF]->(Beta Blocker:DrugClass)
(Bisoprolol:Drug)-[:MEMBER_OF]->(Beta Blocker:DrugClass)

(Beta Blocker:DrugClass)-[:INDICATED_FOR {strength: "strong_for"}]->(HFrEF:Disease)
```

Guidelines often recommend at the **class level** ("prescribe a beta-blocker") while also specifying **approved agents** ("carvedilol, metoprolol succinate, or bisoprolol"). Both must be queryable:

- "Which drugs treat HFrEF?" → traverse `MEMBER_OF` from class-level `INDICATED_FOR`
- "What class is carvedilol in?" → direct `MEMBER_OF` edge
- "Are all beta-blockers equivalent for HFrEF?" → compare individual drug `INDICATED_FOR` edges

## 7. Temporal Modeling

Clinical guidelines are full of temporal constraints that our current schema drops:

- "Washout period of 36 hours between ACEi and ARNi"
- "Reassess LVEF at 3-6 months"
- "Titrate every 2 weeks to target dose"
- "Initiate GDMT before hospital discharge"

```python
class TemporalType(StrEnum):
    DURATION = "duration"       # "for 12 weeks"
    FREQUENCY = "frequency"     # "every 2 weeks", "BID"
    RELATIVE = "relative"       # "within 36 hours of", "before discharge"
    SEQUENCE = "sequence"       # "start X before Y"
    WASHOUT = "washout"         # "36 hours between ACEi and ARNi"
    REASSESSMENT = "reassessment"  # "reassess at 3 months"
```

TemporalConstraint nodes connect to Recommendations via `TIMED_BY`:

```
(rec:Recommendation {action: "Switch from ACEi to ARNi"})
  -[:TIMED_BY]->(tc:TemporalConstraint {
      type: "washout",
      value: 36,
      unit: "hours",
      reference_event: "last_ACEi_dose",
      relation: "after"
  })
```

## 8. Population / Eligibility Criteria Modeling

Following FHIR EvidenceVariable patterns, each Recommendation can specify its target population:

```python
class PopulationCriterion(BaseModel):
    """Single criterion in a population definition."""
    variable: str           # "LVEF", "age", "HF_type"
    operator: str           # "<=", ">=", "==", "!="
    threshold: float | str  # 40, "HFrEF", "Stage C"
    unit: str | None        # "%", "years", None

class Population(BaseModel):
    """Defined patient cohort — boolean combination of criteria."""
    id: str
    description: str        # "HFrEF patients with LVEF <= 40% and NYHA II-IV"
    inclusion: list[PopulationCriterion]   # ALL must be true
    exclusion: list[PopulationCriterion]   # NONE must be true
```

```
(pop:Population {description: "HFrEF, LVEF <=40%, NYHA II-IV"})
  -[:DEFINES]->(pv1:PatientVariable {name: "LVEF"})     # with operator/threshold on edge
  -[:DEFINES]->(pv2:PatientVariable {name: "NYHA_class"})

(rec:Recommendation)-[:APPLIES_TO]->(pop:Population)
```

This replaces the current `conditions_json` stored as a string property on LogicNode.

## 9. Neo4j Index Strategy

```cypher
-- Label-based property indexes (fast lookups)
CREATE INDEX drug_name FOR (d:Drug) ON (d.name);
CREATE INDEX drug_rxnorm FOR (d:Drug) ON (d.rxnorm_code);
CREATE INDEX drugclass_name FOR (dc:DrugClass) ON (dc.name);
CREATE INDEX disease_name FOR (dis:Disease) ON (dis.name);
CREATE INDEX disease_snomed FOR (dis:Disease) ON (dis.snomed_code);
CREATE INDEX lab_name FOR (l:Lab) ON (l.name);
CREATE INDEX lab_loinc FOR (l:Lab) ON (l.loinc_code);
CREATE INDEX procedure_name FOR (p:Procedure) ON (p.name);
CREATE INDEX device_name FOR (d:Device) ON (d.name);
CREATE INDEX symptom_name FOR (s:Symptom) ON (s.name);
CREATE INDEX recommendation_id FOR (r:Recommendation) ON (r.id);
CREATE INDEX recommendation_type FOR (r:Recommendation) ON (r.type);
CREATE INDEX guideline_id FOR (g:Guideline) ON (g.id);
CREATE INDEX publication_doi FOR (p:Publication) ON (p.doi);
CREATE INDEX population_id FOR (p:Population) ON (p.id);
CREATE INDEX patient_var_id FOR (pv:PatientVariable) ON (pv.id);
CREATE INDEX evidence_chunk_id FOR (ec:EvidenceChunk) ON (ec.id);

-- Composite indexes (multi-property queries)
CREATE INDEX drug_indicated FOR ()-[r:INDICATED_FOR]-() ON (r.strength);
CREATE INDEX drug_contraindicated FOR ()-[r:CONTRAINDICATED_IN]-() ON (r.severity);

-- Full-text search (clinical name search)
CREATE FULLTEXT INDEX clinical_entity_search
FOR (d:Drug | dc:DrugClass | dis:Disease | l:Lab | p:Procedure | dev:Device | s:Symptom)
ON EACH [d.name, d.aliases];

-- Vector index (semantic search on evidence)
CREATE VECTOR INDEX evidence_embedding FOR (ec:EvidenceChunk) ON ec.embedding
OPTIONS {indexConfig: {`vector.dimensions`: 1024, `vector.similarity_function`: 'cosine'}};
```

## 10. Migration Strategy

### Phase 1: Schema Layer (new Pydantic models + Cypher builders)
- New `schema_v2.py` with all node/edge models
- New `queries_v2.py` with typed edge builders
- New `terminology/` directory with validated JSON mappings
- Unit tests for all models and query builders

### Phase 2: Ingestion Layer (extraction → new schema)
- Update section extractor agent to output typed relationships (not just concepts list)
- Update concept normalizer to assign proper IDs from terminology database
- New loader that creates typed nodes (Drug, Disease, etc.) and semantic edges
- Derive semantic edges from Recommendation.type + concept types

### Phase 3: Reasoning Layer (query engine for new schema)
- Rewrite ReasoningEngine to use semantic edges (one-hop queries)
- Layer 2 traversal for full evidence chains when needed
- Update FallbackEngine vector search for new node labels

### Phase 4: Data Migration
- Clear existing graph
- Re-run ingestion pipeline with new schema on AHA/ACC HF 2022 guideline
- Validate graph quality against criteria below

## 11. Quality Criteria

A production-grade graph must meet ALL of these:

### Node quality
- Every Drug/Disease/Lab/Procedure/Device/Symptom has at least one standard code (RxNorm/SNOMED/LOINC)
- No duplicate nodes (same clinical entity with different IDs)
- Every Drug links to its DrugClass via MEMBER_OF
- Naming is consistent — canonical names, no snake_case/CamelCase mix

### Edge quality
- INDICATED_FOR connects Drug/DrugClass/Procedure/Device → Disease only
- CONTRAINDICATED_IN connects Drug/DrugClass/Procedure/Device → Disease only
- INTERACTS_WITH connects Drug → Drug only
- MONITORED_BY connects Drug → Lab only
- Every semantic edge has `strength` and `evidence_quality` properties
- Every semantic edge is backed by at least one Recommendation node

### Structural quality
- Every Recommendation has SOURCED_FROM → EvidenceChunk
- Every Recommendation has DEFINED_BY → Guideline
- Every Recommendation has at least one RECOMMENDS → entity
- Multiple Recommendations can share one EvidenceChunk
- No orphan nodes (every node participates in at least one relationship)

### Distribution quality (for a cardiology guideline)
- Drug nodes: 15-25% of clinical entities
- Disease nodes: 25-35%
- Procedure nodes: 15-25%
- Lab nodes: 10-15%
- Symptom nodes: 2-5%
- Device nodes: 3-8%
- DrugClass nodes: 5-10%

## 12. File Change Map

| File | Action | What Changes |
|------|--------|-------------|
| `graph/schema.py` | Rewrite | New node models (Drug, Disease, Lab, etc.), edge models, enums |
| `graph/queries.py` | Rewrite | Typed edge builders, dual-layer query builders |
| `graph/connection.py` | Keep | Already uses managed transactions |
| `graph/indexes.py` | Rewrite | New indexes for all labels and relationship types |
| `ingestion/linker.py` | Rewrite | Use terminology/ JSON files instead of hardcoded dicts |
| `ingestion/loader.py` | Rewrite | Create typed nodes and semantic edges |
| `ingestion/extractor.py` | Modify | Output typed relationships in extraction |
| `reasoning/engine.py` | Rewrite | Semantic edge traversal, dual-layer queries |
| `reasoning/fallback.py` | Modify | Update for new node labels |
| `reasoning/types.py` | Modify | Update result types |
| `server/rest.py` | Modify | Update query endpoints |
| `server/mcp_server.py` | Modify | Update tool implementations |
| `terminology/` | Create | drugs.json, diseases.json, labs.json, etc. |
| `.claude/agents/graphrag-section-extractor.md` | Modify | Output typed relationships |
| `.claude/agents/graphrag-concept-normalizer.md` | Modify | Use terminology database |
| `.claude/commands/ingest-guideline.md` | Modify | New loader, quality gates |

## 13. What This Does NOT Include

- **Genomic/molecular nodes** (Gene, Protein, Pathway, BiologicalProcess) — not needed for clinical guideline decision support. Can be added later if pharmacogenomics guidelines are ingested.
- **FHIR PlanDefinition / CQL execution** — we model guideline recommendations, not executable clinical protocols. The graph is a knowledge layer, not a rules engine.
- **Multi-ontology alignment via UMLS** — we use direct standard codes (SNOMED, LOINC, RxNorm) without UMLS CUI bridging. Simpler, no licensing complexity.
- **Real-time EHR integration** — the graph is queried by AI agents, not embedded in clinical workflows.
