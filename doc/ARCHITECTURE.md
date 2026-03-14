# Architecture — Guille-Agent

## Overview

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│ AnythingLLM  │─────▸│  FastAPI API  │─────▸│   ReAct Agent   │
│  (chat UI)   │◂─────│   (Gateway)   │◂─────│  (LangGraph)    │
└─────────────┘      └──────────────┘      └────────┬────────┘
                                                     │
                    ┌────────────┬───────────┬────────┼────────┬─────────────┬──────────────┐
                    ▼            ▼           ▼        ▼        ▼             ▼              ▼
               ┌─────────┐ ┌────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐
               │PostgreSQL│ │Qdrant  │ │ Ollama │ │Browserless│ │Matplotlib│ │ContentEdge (MCP) │
               │  (data)  │ │(vector)│ │ (LLM)  │ │(web srch) │ │ (charts) │ │  (doc mgmt)      │
               └─────────┘ └────────┘ └────────┘ └──────────┘ └──────────┘ └──────────────────┘
```

---

## 1. Services

| Service | Port | Purpose |
|---|---|---|
| **postgres** | 5432 | PostgreSQL 16 relational database |
| **qdrant** | 6333 | Vector database for RAG |
| **ollama** | 11434 | LLM server |
| **ollama-pull** | — | Downloads `llama3` + `nomic-embed-text`, then exits |
| **browserless** | 3000 (internal) | Headless Chromium for web scraping |
| **agent-api** | 8000 | FastAPI — the agent's brain |
| **anythingllm** | 3001 | Chat web UI |
| **contentedge-mcp** | 8001 | Standard MCP server for Content Repository |

### Startup Order

```
postgres ─┐
qdrant  ──┤
ollama  ──┼─▸ ollama-pull ─┐
           │                ├─▸ agent-api ──┬─▸ anythingllm
browserless ────────────────┘              │
                                           └─▸ contentedge-mcp
```

---

## 2. Question Flow (Request → Response)

Two equivalent entry points:

| Via | Endpoint | Consumer |
|---|---|---|
| Direct API | `POST /ask` | Any HTTP client |
| OpenAI-compatible | `POST /v1/chat/completions` | AnythingLLM |

Both call **`ask_agent()`**.

### Full Step-by-Step Diagram

```
User / AnythingLLM
        │
        ▼
┌─ FastAPI ──────────────────────────────────────────────────────────────┐
│                                                                        │
│  routes.py ─ POST /ask              openai_compat.py ─ POST /v1/...   │
│       │                                   │                            │
│       └──────────── both call ────────────┘                            │
│                         │                                              │
│                         ▼                                              │
│               ask_agent(question, session, chat_history)               │
│                    │          core.py                                   │
│                    │                                                   │
│  ┌─────────────────┼─────────────────────────────────────────────┐    │
│  │  STEP 1: bind_session(session)                                │    │
│  │  → Stores DB session so execute_sql can use it                │    │
│  │                                                               │    │
│  │  STEP 2: _retrieve_schema_context(question)                   │    │
│  │  → Fetches ALL table_schema chunks from Qdrant                │    │
│  │  → Returns table/column descriptions                          │    │
│  │                                                               │    │
│  │  STEP 3: _retrieve_document_context(question)                 │    │
│  │  → Searches Qdrant for type="document" chunks (score >= 0.35) │    │
│  │  → Returns ContentEdge and self-knowledge context             │    │
│  │                                                               │    │
│  │  STEP 4: Build the SYSTEM_PROMPT                              │    │
│  │  → Injects {schema_context} + {document_context} + {max_rows}│    │
│  │  → Includes instructions for all capabilities                 │    │
│  │                                                               │    │
│  │  STEP 5: Build message list                                   │    │
│  │  [SystemMessage, ...chat_history, HumanMessage]               │    │
│  │                                                               │    │
│  │  STEP 6: create_react_agent(llm, AGENT_TOOLS)                │    │
│  │  → LLM = ChatOllama (temperature=0)                           │    │
│  │  → Tools = [execute_sql, generate_chart,                      │    │
│  │             web_search, fetch_webpage,                        │    │
│  │             contentedge_search, contentedge_smart_chat,       │    │
│  │             contentedge_get_document_url]                     │    │
│  │                                                               │    │
│  │  STEP 7: agent.ainvoke(messages) — ReAct LOOP                │    │
│  │                                                               │    │
│  │  STEP 8: Extract results                                      │    │
│  │  - answer (last agent message)                                │    │
│  │  - chart_path (if a chart was generated)                      │    │
│  │  - data_preview (first 20 rows of last query)                 │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                         │                                              │
│                         ▼                                              │
│              { answer, chart_path, data_preview }                      │
└─────────────────────────┼──────────────────────────────────────────────┘
                          ▼
                  Response to client
```

---

## 3. The ReAct Loop

The agent uses the **ReAct** pattern (Reasoning + Acting) from LangGraph:

```
                    ┌───────────────┐
                    │  LLM thinks   │
                    │  (Ollama)     │
                    └───────┬───────┘
                            │
                   Does it need a tool?
                      │             │
                     YES            NO
                      │             │
                      ▼             ▼
              ┌──────────────┐   Final answer
              │ Call tool    │
              └──────┬───────┘
                     │
                     ▼
              Tool returns result
                     │
                     ▼
              ┌──────────────┐
              │ LLM analyzes │
              │ the result   │
              └──────┬───────┘
                     │
            Need another tool?
               │          │
              YES         NO
               │          │
               └──(loop)  ▼
                       Final answer
```

### Decisions by Question Type

| Question Type | Tool(s) Called | Typical Iterations |
|---|---|---|
| Database data | `execute_sql` | 2 |
| Chart request | `execute_sql` → `generate_chart` | 3 |
| External info | `web_search` [→ `fetch_webpage`] | 2–3 |
| Person/entity (SQL + ContentEdge) | `execute_sql` → `contentedge_search` → `contentedge_smart_chat` → `contentedge_get_document_url` | 4–6 |
| ContentEdge docs only | `contentedge_smart_chat` | 2–3 |
| About the agent | — (uses document context) | 1 |
| Conversational | — (direct answer) | 1 |

---

## 4. Agent Tools

### Local Tools (agent-api)

| Tool | File | Description |
|---|---|---|
| `execute_sql` | `app/agent/tools.py` | Executes read-only SELECT against PostgreSQL |
| `generate_chart` | `app/agent/tools.py` | Generates PNG charts with Matplotlib |
| `web_search` | `app/agent/web_tools.py` | Searches DuckDuckGo via Browserless |
| `fetch_webpage` | `app/agent/web_tools.py` | Extracts text from a specific URL |

### ContentEdge Tools (via standard MCP protocol)

These tools connect to the ContentEdge MCP server using the official
MCP Python SDK (`ClientSession` + `sse_client`), maintaining full
protocol compliance with the MCP standard.

| Tool | File | MCP Tool Called | Description |
|---|---|---|---|
| `contentedge_search` | `app/agent/contentedge_tools.py` | `search_documents` | Search documents by index values |
| `contentedge_smart_chat` | `app/agent/contentedge_tools.py` | `smart_chat` | Ask questions to Smart Chat AI |
| `contentedge_get_document_url` | `app/agent/contentedge_tools.py` | `retrieve_document` | Get viewer URL for a document |

---

## 5. ContentEdge MCP Server (port 8001)

The MCP server is **standard-compliant** and can be consumed by
any MCP client — Claude Desktop, Cursor, or any other compatible tool.

| MCP Tool | Endpoint | Description |
|---|---|---|
| `list_content_classes` | Admin REST | List content classes in the repository |
| `list_indexes` | Admin REST | List indexes and index groups |
| `search_documents` | `POST /searches` | Search documents by index values |
| `archive_documents` | `POST /archive-write` | Archive files with metadata |
| `retrieve_document` | `POST /hostviewer` | Get a Mobius View browser URL for a document |
| `get_versions` | Navigation API | Get document versions by date range |
| `smart_chat` | `POST /conversations` | Ask questions to Smart Chat AI |

### MCP Integration Architecture

```
┌──────────────────┐     MCP Standard Protocol     ┌─────────────────────────┐
│   agent-api      │ ────── SSE (port 8001) ──────▸ │   contentedge-mcp       │
│   (LangChain     │                                │   (FastMCP server)      │
│    tools)        │     ClientSession               │                         │
│                  │     + sse_client                │   7 MCP tools           │
│  contentedge_    │     (official SDK)              │                         │
│  tools.py        │                                │                         │
└──────────────────┘                                │                         │
                                                    │                         │
┌──────────────────┐                                │                         │
│ Claude Desktop   │ ────── SSE (port 8001) ──────▸ │                         │
│ Cursor           │     (same standard URL)        │                         │
│ Any MCP Client   │                                │                         │
└──────────────────┘                                └──────────┬──────────────┘
                                                               │
                                                               ▼
                                                    ┌─────────────────────┐
                                                    │ Content Repository  │
                                                    │ (Mobius REST API)   │
                                                    └─────────────────────┘
```

---

## 6. Memory (Qdrant)

```
                    ┌──────────────────────────────────┐
                    │     Collection: schema_memory     │
                    │                                    │
                    │  ┌──────────────────────────────┐ │
                    │  │ Type: table_schema            │ │
                    │  │ Source: schema_descriptions/  │ │
                    │  │ Loaded with POST /schema/load │ │
                    │  └──────────────────────────────┘ │
                    │                                    │
                    │  ┌──────────────────────────────┐ │
                    │  │ Type: document                │ │
                    │  │ Source: files_for_memory/     │ │
                    │  │ Loaded at application startup │ │
                    │  └──────────────────────────────┘ │
                    └──────────────────────────────────┘
```

---

## 7. API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Checks PostgreSQL + Qdrant + Ollama |
| `POST` | `/schema/load` | Indexes JSON schema files into Qdrant |
| `POST` | `/ask` | Sends a question to the agent |
| `GET` | `/charts/{filename}` | Downloads a generated chart PNG |
| `GET` | `/v1/models` | Lists models (returns agent name) |
| `POST` | `/v1/chat/completions` | Chat completions — used by AnythingLLM |

---

## 8. Security

```
SQL Security Layer (safety.py):
  ✓ Only allows SELECT (readonly mode)
  ✓ Blocks multiple statements (anti SQL injection)
  ✓ Blocks dangerous functions (pg_sleep, lo_import, etc.)
  ✓ Queries executed with SQLAlchemy text() (parameterized)

API:
  ✓ Rate limiting (30 req/min per IP)
  ✓ CORS configured with allowed origins
  ✓ Path traversal prevented in /charts/{filename}

ContentEdge:
  ✓ Repository health check before every MCP tool call
  ✓ Standard MCP protocol (no custom endpoints)
  ✓ Base64 auth credentials managed in ContentConfig
```

---

## 9. File Structure

```
agent/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env / .env.example
│
├── doc/                         # All documentation
├── schema_descriptions/         # JSON files with table descriptions
├── files_for_memory/            # PDFs/TXT/MD for agent memory
├── charts_output/               # Generated charts (auto-created)
├── scripts/
│   └── init_db.sql              # DDL + seed data
│
├── app/
│   ├── main.py                  # FastAPI entry point + lifespan
│   ├── config.py                # Settings from .env (Pydantic)
│   ├── api/
│   │   ├── routes.py            # /health, /ask, /schema/load, /charts/
│   │   └── openai_compat.py     # /v1/models, /v1/chat/completions
│   ├── agent/
│   │   ├── core.py              # ask_agent() — orchestrates the full flow
│   │   ├── tools.py             # execute_sql, generate_chart
│   │   ├── web_tools.py         # web_search, fetch_webpage
│   │   ├── contentedge_tools.py # contentedge_search, smart_chat, get_document_url
│   │   └── prompts.py           # System prompt with all capabilities
│   ├── db/
│   │   ├── connection.py        # Async engine + session factory
│   │   ├── executor.py          # run_query() — validates and executes SQL
│   │   └── safety.py            # SQL validation (readonly, anti-injection)
│   ├── memory/
│   │   ├── qdrant_store.py      # Qdrant client, embed, upsert, search
│   │   ├── schema_loader.py     # Loads schema JSONs → Qdrant
│   │   └── file_loader.py       # Loads PDFs/TXT/MD → Qdrant (with dedup)
│   ├── charts/
│   │   └── generator.py         # Matplotlib: bar, line, pie, scatter, hist
│   └── models/
│       └── schemas.py           # Pydantic models (request/response)
│
├── contentedge/                  # ContentEdge MCP Server (standard-compliant)
│   ├── mcp_server.py             # 7 MCP tools + repository health check
│   ├── lib/
│   │   ├── content_config.py     # Configuration and authentication
│   │   ├── content_search.py     # Document search by indexes
│   │   ├── content_smart_chat.py # Smart Chat AI conversations
│   │   ├── content_archive_metadata.py  # Archive with metadata
│   │   ├── content_document.py   # Document viewer URL (Hostviewer)
│   │   └── content_class_navigator.py   # Class navigation and versions
│   ├── Dockerfile
│   └── conf/                     # Repository YAML configuration
│
└── tests/
    ├── test_safety.py
    └── test_charts.py
```
