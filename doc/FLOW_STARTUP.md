# FLOW_STARTUP — Application Startup

## Overview

Describes the complete flow from `docker compose up` to the API
being ready to receive requests.

---

## 1. Container Startup Order

```
postgres ──────────┐
qdrant  ───────────┤
ollama ─▸ ollama-pull ─┤
browserless ───────────┼─▸ agent-api ──┬─▸ anythingllm
                       │              │
                       └──────────────┴─▸ contentedge-mcp
```

Each service declares a **healthcheck** in `docker-compose.yml`.
Dependent containers wait for `condition: service_healthy`.

| Service | Port | Healthcheck | Purpose |
|---|---|---|---|
| `postgres` | 5432 | `pg_isready` | Relational database |
| `qdrant` | 6333 | TCP port check | Vector database |
| `ollama` | 11434 | — | LLM server |
| `ollama-pull` | — | exit 0 | Downloads embedding model |
| `browserless` | 3000 (internal) | `/json/version` | Headless Chromium |
| `agent-api` | 8000 | `curl /health` | Agent API (FastAPI) |
| `contentedge-mcp` | 8001 | — | MCP server for ContentEdge |
| `anythingllm` | 3001 | — | Chat UI |

---

## 2. PostgreSQL Initialization

```
postgres starts
   └─▸ /docker-entrypoint-initdb.d/01_init.sql   ← scripts/init_db.sql
         ├─ CREATE TABLE customers, products, orders, order_items
         └─ INSERT seed data: 5 customers, 8 products, 8 orders, 14 items
```

---

## 3. Agent API Initialization (FastAPI)

### 3.1 Configuration Loading

```
config.py → class Settings(BaseSettings)
   ├─ Reads .env (or environment variables)
   │    POSTGRES_*, QDRANT_*, OLLAMA_*, BROWSERLESS_URL,
   │    CONTENTEDGE_MCP_URL, SQL_READONLY, MAX_QUERY_ROWS, ...
   └─ Generates DSNs:
        postgres_dsn = "postgresql+asyncpg://user:pass@host:5432/db"
```

### 3.2 FastAPI App Creation

```
main.py
   ├─ 1. Configure structlog (structured logging)
   ├─ 2. Create rate limiter (30 req/min per IP)
   ├─ 3. Instantiate FastAPI with lifespan()
   ├─ 4. Register CORS middleware
   └─ 5. Register routers:
          ├─ routes.py       → /health, /ask, /schema/load, /charts/{fn}
          └─ openai_compat.py → /v1/models, /v1/chat/completions
```

### 3.3 Lifespan — Startup

```
lifespan(app)
   │
   ├─▸ load_files_for_memory()            ← memory/file_loader.py
   │      ├─ DEDUP: Deletes all type="document" points from Qdrant
   │      ├─ Scans /app/files_for_memory/ for .pdf, .txt, .md
   │      ├─ For each file:
   │      │    ├─ Read content (pypdf for PDF, direct read for txt/md)
   │      │    ├─ Split into chunks (~1000 chars, 200 overlap)
   │      │    └─ upsert_texts() → Qdrant (nomic-embed-text → 768d vectors)
   │      └─ Returns: total chunks indexed
   │
   ├─▸ ──── yield ──── (app serves traffic)
   │
   └─▸ Shutdown: dispose_engine() ← closes PostgreSQL connection pool
```

### 3.4 PostgreSQL Connection Pool

```
connection.py
   ├─ engine = create_async_engine(pool_size=10, max_overflow=20, pool_pre_ping=True)
   ├─ async_session_factory = async_sessionmaker(engine)
   └─ get_session() → FastAPI Dependency (yields session with auto-commit/rollback)
```

---

## 4. ContentEdge MCP Server Initialization

```
contentedge-mcp starts
   │
   ├─ _patch_yaml_from_env()     ← Patches YAML config from CE_SOURCE_* env vars
   ├─ _init_configs()            ← Creates ContentConfig from YAML
   │    └─ Reads repo_url, repo_name, repo_user, repo_pass
   │    └─ Auto-discovers repo_id if not cached
   ├─ mcp = FastMCP("ContentEdge")
   │    └─ Registers 7 tools: list_content_classes, list_indexes,
   │       search_documents, archive_documents, retrieve_document,
   │       get_versions, smart_chat
   └─ mcp.run(transport="sse") on port 8001
```

---

## 5. Complete Timeline

```
t=0   docker compose up
      │
t=1   postgres: starts → executes init_db.sql → healthcheck OK
      qdrant: starts → healthcheck OK
      ollama: starts
      browserless: starts → healthcheck OK
      │
t=2   ollama-pull: downloads nomic-embed-text → exit 0
      │
t=3   agent-api: starts
      ├─ Read config from .env
      ├─ Create PostgreSQL pool (10 connections)
      ├─ Register routers + middleware
      ├─ lifespan startup:
      │    └─ load_files_for_memory()
      │         ├─ Connect to Qdrant
      │         ├─ Ensure collection "schema_memory" exists
      │         ├─ DEDUP: delete existing type="document" points
      │         ├─ Read files → chunks → embeddings → upsert
      │         └─ Log: "app.files_loaded"
      ├─ healthcheck: GET /health → 200 OK
      └─ Listening on 0.0.0.0:8000
      │
t=4   contentedge-mcp: starts
      ├─ FastMCP server (SSE transport)
      ├─ 7 MCP tools registered
      ├─ Repository health check validates Mobius connection
      └─ Listening on 0.0.0.0:8001
      │
      anythingllm: starts
      ├─ Configured with LLM_PROVIDER=generic-openai
      ├─ Points to http://agent-api:8000/v1
      └─ Listening on 0.0.0.0:3001
      │
      ═══════════════════════════════
       System ready for questions
      ═══════════════════════════════
```

---

## 6. Files Involved

| File | Role |
|---|---|
| `docker-compose.yml` | Service orchestration and dependencies |
| `scripts/init_db.sql` | DDL + seed data for PostgreSQL |
| `app/main.py` | Entry point, lifespan, middleware |
| `app/config.py` | Configuration from `.env` |
| `app/db/connection.py` | Async PostgreSQL pool |
| `app/memory/file_loader.py` | Indexes documents in Qdrant at startup |
| `app/memory/qdrant_store.py` | Qdrant client, embeddings, upsert |
| `contentedge/mcp_server.py` | MCP server for ContentEdge (7 tools) |
