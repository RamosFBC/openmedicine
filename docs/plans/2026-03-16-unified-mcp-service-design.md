# Unified MCP Server + Service Design

**Date:** 2026-03-16
**Status:** Approved

## Goal

Merge the two separate MCP servers (`open-medicine-mcp` for calculators and `open-medicine-graphrag` for the graph) into a single unified MCP server. Then wrap it as an HTTP service for remote AI agents.

## Two Phases

### Phase 1: Unified Local MCP Server (stdio)

Merge calculator and GraphRAG tools into a single `open-medicine-mcp` entry point. 10 tools total:

| Tool | Source |
|------|--------|
| `search_clinical_calculators` | Calculator registry |
| `execute_clinical_calculator` | Calculator registry |
| `check_drug_dosing` | ReasoningEngine → Neo4j |
| `check_contraindications` | ReasoningEngine → Neo4j |
| `check_drug_interaction` | ReasoningEngine → Neo4j |
| `check_monitoring_requirements` | ReasoningEngine → Neo4j |
| `find_treatment_options` | ReasoningEngine → Neo4j |
| `query_clinical_graph` | ReasoningEngine → Neo4j |
| `fetch_evidence_chunk` | ReasoningEngine → Neo4j |
| `list_available_guidelines` | ReasoningEngine → Neo4j |

Guidelines, differentials, and semantic search tools removed — the graph layer subsumes them.

**Graceful degradation:** If Neo4j env vars are missing, graph tools return a clear "GraphRAG not configured" error. Calculator tools always work.

**Entry points:**
- `open-medicine-mcp` → unified server (stdio, 10 tools)
- `open-medicine-graphrag` → deprecated, thin redirect to unified server

### Phase 2: HTTP Service Layer

Wrap the unified MCP server as a remote service for AI agents.

#### Architecture

```
┌─────────────────────────────────────────────────┐
│              Unified FastAPI Service             │
│                                                  │
│  ┌──────────────┐    ┌────────────────────────┐  │
│  │  /mcp         │    │  /v1/*  (REST API)     │  │
│  │  Streamable   │    │  Existing endpoints    │  │
│  │  HTTP         │    │  + health + docs       │  │
│  └──────┬───────┘    └──────────┬─────────────┘  │
│         │                       │                │
│  ┌──────▼───────────────────────▼─────────────┐  │
│  │         Shared Service Layer                │  │
│  │  ┌─────────────┐  ┌─────────────────────┐  │  │
│  │  │ Calculator  │  │  ReasoningEngine v2  │  │  │
│  │  │ Registry    │  │  (Neo4j + Embeddings)│  │  │
│  │  └─────────────┘  └─────────────────────┘  │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │           Auth Middleware (JWT/OAuth2)      │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  Uvicorn · 0.0.0.0:8000                         │
└─────────────────────────────────────────────────┘
```

#### Transport

MCP Streamable HTTP on `/mcp`. Single HTTP endpoint supporting request-response and SSE streaming.

#### Authentication (3 modes)

```
AUTH_MODE=none       # local dev (default)
AUTH_MODE=api_key    # simple deployments
AUTH_MODE=oauth2     # production
```

- `none`: No auth. For local dev and contributors.
- `api_key`: Bearer token from `GRAPHRAG_API_KEYS` env var (comma-separated).
- `oauth2`: Standard OIDC/JWT validation. Provider-agnostic (Auth0, Clerk, Keycloak, Cognito).

OAuth2 config:
```
AUTH_OAUTH2_ISSUER=https://your-tenant.auth0.com/
AUTH_OAUTH2_AUDIENCE=https://api.openmedicine.ai
AUTH_OAUTH2_JWKS_URI=...  # auto-discovered from issuer if omitted
```

JWT `sub` claim used for rate limiting and audit logging.

Dependencies: `PyJWT[crypto]` (RS256 verification). No heavy auth SDK.

#### New dependencies

```toml
[project.optional-dependencies]
service = [
    "fastapi>=0.110.0",
    "uvicorn>=0.30.0",
    "PyJWT[crypto]>=2.8.0",
    "httpx>=0.27.0",
]
```

#### File structure

```
src/open_medicine/
├── mcp/
│   ├── server.py              # MODIFIED: unified MCP server (10 tools)
│   └── calculators/           # unchanged
├── graphrag/
│   └── server/
│       ├── mcp_server.py      # DEPRECATED: redirects to unified
│       └── rest_api.py        # unchanged
└── server/                    # NEW: service layer
    ├── app.py                 # FastAPI app (mounts /mcp + /v1)
    ├── auth.py                # JWT/OAuth2 middleware
    └── config.py              # pydantic-settings
```

## Deployment

### Railway (now)

- Single service, single container, single port (8000)
- Neo4j Aura as remote managed DB
- Railway handles TLS termination and custom domain
- Secrets in Railway dashboard env vars

### AWS (later)

- Same Docker image on ECS/Fargate
- ALB routing `/mcp` and `/v1/*` (split into separate services when traffic justifies)
- Cognito or Auth0 for OAuth2
- Secrets in AWS Secrets Manager
- WAF + rate limiting at ALB level

## Graceful Degradation

| Component Down | Behavior |
|---------------|----------|
| Neo4j unreachable | Graph tools return error, calculator tools work |
| OAuth2 issuer unreachable | JWKS cached, continues for cache TTL |
| Embedding API unreachable | Vector fallback skipped, keyword matching works |

## Open Source Considerations

- All application code in the repo (auth middleware, tool handlers, engines)
- No secrets in code — everything via environment variables
- `docker-compose up` for local self-hosting (Neo4j + service)
- Graceful degradation means contributors can run with just calculators (no Neo4j needed)
