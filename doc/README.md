# Guille-Agent — AI-Powered Intelligent Assistant

Versatile AI agent that queries PostgreSQL, explains results, generates charts,
searches the web, and manages documents in ContentEdge.
Uses **Ollama** as local LLM, **Qdrant** for vector memory, **LangChain** as
agent framework, and **ContentEdge MCP** for document management.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│ AnythingLLM  │────▶│  LangChain   │────▶│   Ollama     │
│   (chat UI)  │     │  ReAct Agent │     │   (LLM)      │
└──────┬───────┘     └──────┬───────┘     └──────────────┘
       │                    │
       │         ┌──────────┼──────────┬────────────┐
       │         │          │          │            │
  ┌────▼─────┐ ┌─▼────────┐ ┌────▼──────┐ ┌────────▼─────┐
  │PostgreSQL │ │  Qdrant  │ │Matplotlib │ │ ContentEdge  │
  │  (data)   │ │(memory)  │ │ (charts)  │ │  MCP Server  │
  └───────────┘ └──────────┘ └───────────┘ └──────────────┘
```

## Tech Stack

| Component | Technology |
|---|---|
| LLM | Ollama |
| Embeddings | nomic-embed-text (768d) |
| Agent Framework | LangChain + LangGraph |
| Database | PostgreSQL 16 |
| Vector Store | Qdrant |
| API | FastAPI |
| Charts | Matplotlib |
| Web Search | Browserless + DuckDuckGo |
| Content Management | ContentEdge MCP Server |
| Chat UI | AnythingLLM |
| Containers | Docker Compose |

## Requirements

- Docker and Docker Compose
- 8 GB+ RAM (for Ollama)
- NVIDIA GPU optional (uncomment GPU section in `docker-compose.yml`)

## Quick Start

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env with your credentials if needed
```

### 2. Start services

```bash
docker compose up -d --build
```

This starts: PostgreSQL, Qdrant, Ollama (auto-downloads models), the API,
ContentEdge MCP server, and AnythingLLM.

### 3. Load schema descriptions

```bash
curl -X POST http://localhost:8000/schema/load
```

### 4. Ask questions

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the top 5 customers by spending?"}'
```

### 5. Request a chart

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Show me a bar chart of sales by product category"}'
```

Charts are served from: `GET /charts/{filename}`

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check for all services |
| POST | `/schema/load` | Index schema descriptions into Qdrant |
| POST | `/ask` | Send a question to the agent |
| GET | `/charts/{file}` | Download a generated chart |
| GET | `/v1/models` | List models (returns agent name) |
| POST | `/v1/chat/completions` | Chat completions (AnythingLLM) |

## Agent Capabilities

1. **SQL Database Analysis** — Query PostgreSQL, analyze data, generate charts
2. **Web Search** — Search the internet via DuckDuckGo + Browserless
3. **ContentEdge Document Management** — Search, query, and link documents via MCP
4. **Smart Chat** — Ask AI questions about Content Repository documents
5. **General Knowledge** — Answer questions directly from LLM knowledge
6. **Multi-language** — Responds in whatever language the user writes in

## ContentEdge MCP Server

The MCP server (port 8001) is **standard-compliant** and can be consumed by
any MCP client (Claude Desktop, Cursor, etc.):

| MCP Tool | Description |
|---|---|
| `list_content_classes` | List content classes in the repository |
| `list_indexes` | List indexes and index groups |
| `search_documents` | Search documents by index values |
| `archive_documents` | Archive files with metadata |
| `retrieve_document` | Get a Mobius View browser URL for a document |
| `get_versions` | Get document versions by date range |
| `smart_chat` | Ask questions to Smart Chat AI |

## Documentation

All flow and architecture documentation is in the `doc/` directory:

| Document | Description |
|---|---|
| [ARCHITECTURE.md](doc/ARCHITECTURE.md) | System architecture, services, tools, file structure |
| [FLOW_ASK.md](doc/FLOW_ASK.md) | Question processing flow (entry points → response) |
| [FLOW_SQL.md](doc/FLOW_SQL.md) | SQL query execution and security validation |
| [FLOW_CHARTS.md](doc/FLOW_CHARTS.md) | Chart generation with Matplotlib |
| [FLOW_MEMORY.md](doc/FLOW_MEMORY.md) | RAG memory system (Qdrant indexing + retrieval) |
| [FLOW_STARTUP.md](doc/FLOW_STARTUP.md) | Application startup sequence |
| [FLOW_WEB.md](doc/FLOW_WEB.md) | Web search via Browserless + DuckDuckGo |
| [FLOW_CONTENTEDGE.md](doc/FLOW_CONTENTEDGE.md) | ContentEdge MCP integration, Smart Chat, viewer URLs |

## Schema Customization

Create JSON files in `schema_descriptions/`:

```json
{
  "tables": [{
    "name": "my_table",
    "description": "Detailed table description.",
    "columns": [
      { "name": "col1", "type": "varchar(100)", "description": "Column purpose." }
    ]
  }]
}
```

Then run `POST /schema/load` to index.

## Security

- **SQL Injection**: Queries validated with `sqlparse` + executed with `text()`
- **Readonly mode**: Blocks INSERT/UPDATE/DELETE/DROP by default
- **Dangerous functions blocked**: `pg_sleep`, `pg_read_file`, `lo_import`, etc.
- **Multi-statement blocked**: Only one SQL statement per request
- **Rate limiting**: 30 requests/minute per IP
- **CORS**: Configurable allowed origins
- **Path traversal**: Sanitized filenames in chart endpoint
- **Input validation**: Pydantic models with length constraints

## GPU (Optional)

To use NVIDIA GPU with Ollama, uncomment in `docker-compose.yml`:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

## Tests

```bash
# Inside the container
docker compose exec agent-api pytest tests/ -v

# Or locally with virtualenv
pip install -r requirements.txt
pytest tests/ -v
```
