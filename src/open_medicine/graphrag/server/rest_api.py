from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from open_medicine.graphrag.config import get_settings
from open_medicine.graphrag.graph.connection import GraphConnection
from open_medicine.graphrag.graph.queries import ReasoningQueries
from open_medicine.graphrag.reasoning.engine import ReasoningEngine
from open_medicine.graphrag.reasoning.fallback import FallbackEngine
from open_medicine.graphrag.reasoning.types import ClinicalQuery, GraphRAGResult
from open_medicine.graphrag.server.auth import require_api_key


class DosingRequest(BaseModel):
    drug: str
    patient_vars: dict[str, float | str | bool] = Field(default_factory=dict)
    guideline_filter: str | None = None


class ContraindicationRequest(BaseModel):
    intervention: str
    patient_vars: dict[str, float | str | bool] = Field(default_factory=dict)


class InteractionRequest(BaseModel):
    drug_a: str
    drug_b: str
    patient_vars: dict[str, float | str | bool] = Field(default_factory=dict)


class MonitoringRequest(BaseModel):
    intervention: str
    patient_vars: dict[str, float | str | bool] = Field(default_factory=dict)


class TreatmentRequest(BaseModel):
    condition: str
    patient_vars: dict[str, float | str | bool] = Field(default_factory=dict)


class QueryRequest(BaseModel):
    intent: str
    concepts: list[str]
    patient_vars: dict[str, float | str | bool] = Field(default_factory=dict)
    guideline_filter: str | None = None
    include_source_text: bool = True


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="OpenMedicine GraphRAG", version="0.1.0")

    conn = GraphConnection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    engine = ReasoningEngine(conn)
    fallback = FallbackEngine(conn, voyage_api_key=settings.voyage_api_key)
    auth = require_api_key(settings.valid_api_keys)

    def _query(q: ClinicalQuery) -> GraphRAGResult:
        result = engine.query(q)
        if not result.matches and result.confidence == "low":
            return fallback.query(q)
        return result

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy"}

    @app.get("/v1/guidelines", dependencies=[auth])
    async def list_guidelines() -> dict:
        cypher, params = ReasoningQueries.list_guidelines()
        rows = conn.execute_read(cypher, params)
        return {"guidelines": rows}

    @app.post("/v1/dosing", dependencies=[auth])
    async def check_dosing(req: DosingRequest) -> dict:
        q = ClinicalQuery(
            intent="dosing", concepts=[req.drug],
            patient_vars=req.patient_vars, guideline_filter=req.guideline_filter,
        )
        return _query(q).model_dump()

    @app.post("/v1/contraindications", dependencies=[auth])
    async def check_contraindications(req: ContraindicationRequest) -> dict:
        q = ClinicalQuery(
            intent="contraindication", concepts=[req.intervention],
            patient_vars=req.patient_vars,
        )
        return _query(q).model_dump()

    @app.post("/v1/interactions", dependencies=[auth])
    async def check_interactions(req: InteractionRequest) -> dict:
        q = ClinicalQuery(
            intent="interaction", concepts=[req.drug_a, req.drug_b],
            patient_vars=req.patient_vars,
        )
        return _query(q).model_dump()

    @app.post("/v1/monitoring", dependencies=[auth])
    async def check_monitoring(req: MonitoringRequest) -> dict:
        q = ClinicalQuery(
            intent="monitoring", concepts=[req.intervention],
            patient_vars=req.patient_vars,
        )
        return _query(q).model_dump()

    @app.post("/v1/treatments", dependencies=[auth])
    async def find_treatments(req: TreatmentRequest) -> dict:
        q = ClinicalQuery(
            intent="treatment_selection", concepts=[req.condition],
            patient_vars=req.patient_vars,
        )
        return _query(q).model_dump()

    @app.post("/v1/query", dependencies=[auth])
    async def query_graph(req: QueryRequest) -> dict:
        q = ClinicalQuery(**req.model_dump())
        return _query(q).model_dump()

    @app.get("/v1/evidence/{chunk_id}", dependencies=[auth])
    async def get_evidence(chunk_id: str) -> dict:
        cypher, params = ReasoningQueries.get_evidence_chunk(chunk_id)
        rows = conn.execute_read(cypher, params)
        if not rows:
            return {"error": "Chunk not found"}
        return rows[0]

    return app
