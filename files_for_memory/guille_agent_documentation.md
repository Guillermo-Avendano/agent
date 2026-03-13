# Guille-Agent — AI-Powered Intelligent Assistant

## What is Guille-Agent?

Guille-Agent is a versatile AI assistant that combines database analytics, web search, chart generation, and enterprise content management capabilities. It is accessible through AnythingLLM chat interface or directly via REST API.

When asked "what can you do?" or "¿qué puedes hacer por mí?" or any equivalent in any language, describe ALL capabilities below.

---

## Capabilities Overview

Guille-Agent has **five core capabilities**:

### 1. Database Analysis (SQL)
- Connected to a **PostgreSQL** database with full read-only query access
- Automatically writes SQL queries to answer data questions
- Returns results as formatted markdown tables
- Validates all queries for security (blocks injection, dangerous functions, write operations)
- Maximum 1000 rows per query by default

### 2. Chart Generation
- Generates professional charts and visualizations from query results
- Supported chart types: **bar, line, pie, scatter, histogram**
- Charts are generated using Matplotlib and saved as PNG images
- Access charts via the `/charts/{filename}` endpoint
- The agent first queries the data, then generates the visualization

### 3. Web Search
- Searches the internet using DuckDuckGo via Browserless (headless Chromium)
- Can fetch and read specific web pages for detailed information
- Useful for current events, general knowledge, or topics not in the database
- Returns cleaned text content (up to 4000 characters per page)

### 4. ContentEdge / Content Repository Management
- Integrated with a **ContentEdge MCP Server** (Model Context Protocol) running on port 8001
- ContentEdge is one of the most revolutionary tools in the enterprise content management market
- The MCP server provides 6 tools for Content Repository operations:
  - **list_content_classes**: Lists all content classes (e.g., LOAN, CLAIMS, POLICIES, PAYMENT)
  - **list_indexes**: Lists index groups (mandatory) and individual indexes with their data types
  - **search_documents**: Searches documents by index values with operators (EQ, LT, GT, LK, etc.)
  - **archive_documents**: Archives files (PDF, TXT, JPG, PNG) with metadata into content classes
  - **retrieve_document**: Downloads documents by objectId from the repository
  - **get_versions**: Gets document versions for a report within a date range
- Every MCP tool verifies the repository is active via `/repositories` before executing
- If the repository is down or unavailable, tools return a clear message to activate it
- More info: https://www.rocketsoftware.com/en-us/products/contentedge

### 5. General Knowledge
- Answers conversational questions, greetings, explanations directly
- Math, programming help, concept explanations — no tools needed
- Always responds in the same language the user writes in

---

## Architecture

```
AnythingLLM (Chat UI, port 3001)
    │
    ▼
FastAPI API Gateway (port 8000)
    │
    ▼
LangGraph ReAct Agent
    │
    ├── Ollama LLM (gpt-oss model, temperature=0)
    ├── Qdrant Vector Memory (nomic-embed-text embeddings, 768 dimensions)
    ├── PostgreSQL Database (read-only queries)
    ├── Browserless Chromium (web search via DuckDuckGo)
    ├── Matplotlib (chart generation)
    └── ContentEdge MCP Server (document management, port 8001)
```

### Technology Stack

| Component        | Technology              |
|------------------|-------------------------|
| LLM              | Ollama (gpt-oss)        |
| Embeddings       | nomic-embed-text (768d) |
| Agent Framework  | LangChain + LangGraph   |
| Database         | PostgreSQL 16           |
| Vector Store     | Qdrant                  |
| API              | FastAPI                 |
| Charts           | Matplotlib              |
| Web Search       | Browserless + DuckDuckGo|
| Content Mgmt     | ContentEdge MCP Server  |
| Chat UI          | AnythingLLM             |
| Containers       | Docker Compose          |

---

## How Guille-Agent Works

### The ReAct Loop (Reasoning + Action)

For each user question, the agent follows this pattern:

1. **Receive question** from user (via AnythingLLM or API)
2. **Load context** — schema descriptions + document knowledge from Qdrant
3. **Build system prompt** with context, capabilities, and rules
4. **LLM reasons** about what tools to use (or answer directly)
5. **Execute tools** if needed (SQL, chart, web search)
6. **Analyze results** and optionally call more tools
7. **Return final answer** in the user's language

### Decision Flow

- Question about data in the database → `execute_sql` tool
- Chart/visualization requested → `execute_sql` then `generate_chart`
- Fresh/external information needed → `web_search` tool
- Specific URL to read → `fetch_webpage` tool
- Question about ContentEdge → use document context from memory
- Question about the agent itself → use this documentation
- Everything else → answer directly from LLM knowledge

---

## Available Tools

### Agent Tools (built-in)

| Tool | Description |
|------|-------------|
| `execute_sql` | Runs read-only SELECT queries against PostgreSQL. Validates for safety. Returns markdown table. |
| `generate_chart` | Creates bar/line/pie/scatter/histogram charts from query results using Matplotlib. |
| `web_search` | Searches DuckDuckGo via Browserless Chromium, returns top 3 results with content. |
| `fetch_webpage` | Reads a specific URL, renders JavaScript, returns cleaned text content. |

### ContentEdge MCP Tools (via MCP server on port 8001)

| Tool | Description |
|------|-------------|
| `list_content_classes` | Lists all content classes with id, name, and description. |
| `list_indexes` | Lists index groups (mandatory) and individual indexes. |
| `search_documents` | Searches documents by index constraints (index_name, operator, value). |
| `archive_documents` | Archives files with metadata into a content class. |
| `retrieve_document` | Downloads a document by its objectId. |
| `get_versions` | Gets document versions for a report within a date range. |

All MCP tools check repository availability before executing. If the Content Repository
is not active, they return an error message asking to activate it.

---

## Memory System (RAG — Retrieval-Augmented Generation)

Guille-Agent uses **Qdrant** as its vector memory store with two types of data:

### Schema Memory (type: table_schema)
- Source: `schema_descriptions/` JSON files
- Loaded via `POST /schema/load` endpoint
- Contains database table and column descriptions
- Used to write accurate SQL queries

### Document Memory (type: document)
- Source: `files_for_memory/` directory (PDFs, TXT, MD files)
- Loaded automatically at startup (previous document chunks are cleaned first to avoid duplicates)
- Split into ~1000 character chunks with 200 character overlap
- Embedded using nomic-embed-text model (768 dimensions)
- Used for ContentEdge knowledge, agent documentation, and any uploaded documents
- Semantic search with score threshold (>= 0.35) filters irrelevant results

### How Retrieval Works
1. User asks a question
2. Question is embedded into a 768-dimension vector
3. Qdrant searches for the most similar chunks
4. Matching chunks are injected into the system prompt as context
5. The LLM uses this context to provide accurate answers

---

## API Endpoints

### Main Endpoints (routes.py)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check for PostgreSQL, Qdrant, and Ollama |
| `POST` | `/schema/load` | Index schema description JSON files into Qdrant |
| `POST` | `/ask` | Send a question to the agent, receive an answer |
| `GET` | `/charts/{filename}` | Download a generated chart PNG image |
| `GET` | `/docs` | Interactive Swagger API documentation |

### OpenAI-Compatible Endpoints (openai_compat.py)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/models` | List available models (returns "guille-agent") |
| `POST` | `/v1/chat/completions` | Chat completions — used by AnythingLLM |

### How AnythingLLM Connects

1. AnythingLLM calls `GET /v1/models` → receives "guille-agent"
2. Each user message: `POST /v1/chat/completions` with `model: "guille-agent"`
3. The API extracts the question, builds chat history, calls `ask_agent()`
4. Response is formatted as OpenAI ChatCompletion and returned
5. Supports SSE streaming for real-time responses

---

## Security Features

- **SQL Injection Prevention**: All queries validated with sqlparse + parameterized execution
- **Read-Only Mode**: Blocks INSERT, UPDATE, DELETE, DROP by default
- **Dangerous Functions Blocked**: pg_sleep, pg_read_file, lo_import, lo_export, etc.
- **Single Statement Only**: Multiple SQL statements are blocked
- **Rate Limiting**: 30 requests/minute per IP
- **CORS**: Configurable allowed origins
- **Path Traversal Prevention**: Sanitized filenames in chart endpoint
- **Input Validation**: Pydantic models with length constraints

---

## Docker Services

| Service | Port | Purpose |
|---------|------|---------|
| `postgres` | 5432 | PostgreSQL 16 relational database |
| `qdrant` | 6333 | Qdrant vector database for memory |
| `ollama` | 11434 | LLM model server |
| `browserless` | 3000 (internal) | Headless Chromium for web scraping |
| `agent-api` | 8000 | FastAPI — the agent brain |
| `anythingllm` | 3001 | Chat web interface |
| `contentedge-mcp` | 8001 | ContentEdge MCP server |

### Startup Order
```
postgres → qdrant → ollama → ollama-pull → browserless → agent-api → anythingllm
```

At startup, the agent automatically:
1. Configures structured logging
2. Loads files from `files_for_memory/` into Qdrant (PDFs, MD, TXT)
3. Exposes REST API on port 8000

Schema descriptions must be loaded manually via `POST /schema/load`.

---

## Quick Start

1. Configure environment: `cp .env.example .env`
2. Start all services: `docker compose up -d --build`
3. Load schema descriptions: `POST http://localhost:8000/schema/load`
4. Ask questions via AnythingLLM at `http://localhost:3001` or via API at `POST http://localhost:8000/ask`

---

## Project Structure

```
agent/
├── docker-compose.yml          # Service orchestration
├── Dockerfile                  # Python 3.12 API image
├── requirements.txt            # Python dependencies
├── .env / .env.example         # Environment variables
├── schema_descriptions/        # Table description JSONs
├── files_for_memory/           # Documents for agent memory (PDF/TXT/MD)
├── charts_output/              # Generated chart images
├── scripts/init_db.sql         # Database DDL + seed data
├── contentedge/                # ContentEdge MCP server
│   ├── mcp_server.py           # 6 MCP tools for Content Repository
│   ├── lib/                    # ContentEdge Python library
│   ├── Dockerfile              # MCP server container
│   └── conf/                   # Repository configuration
├── app/
│   ├── main.py                 # FastAPI entry point + lifespan
│   ├── config.py               # Settings from .env (Pydantic)
│   ├── api/
│   │   ├── routes.py           # /health, /ask, /schema/load, /charts/
│   │   └── openai_compat.py    # /v1/models, /v1/chat/completions
│   ├── agent/
│   │   ├── core.py             # ask_agent() — orchestrates the flow
│   │   ├── tools.py            # execute_sql, generate_chart
│   │   ├── web_tools.py        # web_search, fetch_webpage
│   │   └── prompts.py          # System prompt + chart instructions
│   ├── db/
│   │   ├── connection.py       # Async SQLAlchemy engine + session
│   │   ├── executor.py         # run_query() — validates and executes SQL
│   │   └── safety.py           # SQL validation (readonly, anti-injection)
│   ├── memory/
│   │   ├── qdrant_store.py     # Qdrant client, embed, upsert, search
│   │   ├── schema_loader.py    # Load schema JSONs → Qdrant
│   │   └── file_loader.py      # Load PDFs/TXT/MD → Qdrant
│   └── charts/
│       └── generator.py        # Matplotlib: bar, line, pie, scatter, histogram
└── tests/
    ├── test_safety.py          # SQL validation tests
    └── test_charts.py          # Chart generation tests
```
