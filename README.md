# Guille-Agent — AI-Powered Intelligent Assistant

Versatile AI agent that queries PostgreSQL, explains results, generates charts,
searches the web, and manages documents in ContentEdge.

Uses **Ollama** as local LLM, **Qdrant** for vector memory, **LangChain** as
agent framework, and **ContentEdge MCP** for document management.

## Quick Start

```bash
cp .env.example .env
docker compose up -d --build
curl -X POST http://localhost:8000/schema/load
```

Then open AnythingLLM at `http://localhost:3001` or call the API directly:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the top 5 customers by spending?"}'
```

## Documentation

All documentation is in the [`doc/`](doc/) directory:

| Document | Description |
|---|---|
| [README.md](doc/README.md) | Full project overview, tech stack, endpoints, security |
| [ARCHITECTURE.md](doc/ARCHITECTURE.md) | System architecture, services, tools, file structure |
| [FLOW_ASK.md](doc/FLOW_ASK.md) | Question processing flow |
| [FLOW_SQL.md](doc/FLOW_SQL.md) | SQL query execution and security |
| [FLOW_CHARTS.md](doc/FLOW_CHARTS.md) | Chart generation with Matplotlib |
| [FLOW_MEMORY.md](doc/FLOW_MEMORY.md) | RAG memory system (Qdrant) |
| [FLOW_STARTUP.md](doc/FLOW_STARTUP.md) | Application startup sequence |
| [FLOW_WEB.md](doc/FLOW_WEB.md) | Web search (Browserless + DuckDuckGo) |
| [FLOW_CONTENTEDGE.md](doc/FLOW_CONTENTEDGE.md) | ContentEdge MCP: Smart Chat, search, viewer URLs |

## Services

| Service | Port | Purpose |
|---|---|---|
| agent-api | 8000 | FastAPI — the agent's brain |
| contentedge-mcp | 8001 | Standard MCP server (7 tools) |
| anythingllm | 3001 | Chat web UI |
| postgres | 5432 | PostgreSQL 16 |
| qdrant | 6333 | Vector database |
| ollama | 11434 | LLM server |
