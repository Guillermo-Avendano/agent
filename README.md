# Guille-Agent — AI-Powered Intelligent Assistant

Agente de IA versátil que consulta PostgreSQL, explica resultados, genera gráficos, busca en la web y gestiona documentos en ContentEdge.  
Usa **Ollama** como LLM local, **Qdrant** para memoria vectorial, **LangChain** como framework de agente y **ContentEdge MCP** para gestión documental.

## Arquitectura

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│ AnythingLLM  │────▶│  LangChain   │────▶│   Ollama     │
│   (chat UI)  │     │  ReAct Agent │     │  (gpt-oss)   │
└──────┬───────┘     └──────┬───────┘     └──────────────┘
       │                    │
       │         ┌──────────┼──────────┬────────────┐
       │         │          │          │            │
  ┌────▼─────┐ ┌─▼────────┐ ┌────▼──────┐ ┌────────▼─────┐
  │PostgreSQL │ │  Qdrant  │ │Matplotlib │ │ ContentEdge  │
  │ (datos)   │ │(memoria) │ │ (charts)  │ │  MCP Server  │
  └───────────┘ └──────────┘ └───────────┘ └──────────────┘
```

## Stack Tecnológico

| Componente       | Tecnología              |
|------------------|-------------------------|
| LLM              | Ollama (gpt-oss)        |
| Embeddings       | nomic-embed-text (768d) |
| Framework agente | LangChain + LangGraph   |
| Base de datos    | PostgreSQL 16           |
| Vector store     | Qdrant                  |
| API              | FastAPI                 |
| Gráficos         | Matplotlib              |
| Web Search       | Browserless + DuckDuckGo|
| Content Mgmt     | ContentEdge MCP Server  |
| Chat UI          | AnythingLLM             |
| Contenedores     | Docker Compose          |

## Requisitos

- Docker y Docker Compose
- 8 GB+ RAM (para Ollama)
- GPU NVIDIA opcional (descomenta la sección GPU en `docker-compose.yml`)

## Inicio Rápido

### 1. Clonar y configurar

```bash
cp .env.example .env
# Edita .env con tus credenciales si es necesario
```

### 2. Levantar servicios

```bash
docker compose up -d --build
```

Esto levanta: PostgreSQL, Qdrant, Ollama (auto-descarga modelos) y la API.

### 3. Cargar descripciones del esquema

```bash
curl -X POST http://localhost:8000/schema/load
```

### 4. Hacer preguntas

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "¿Cuáles son los 5 clientes que más han gastado?"}'
```

### 5. Pedir un gráfico

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Muéstrame un gráfico de barras con las ventas por categoría de producto"}'
```

Los gráficos se sirven desde: `GET /charts/{filename}`

## Endpoints API

| Método | Ruta            | Descripción                              |
|--------|-----------------|------------------------------------------|
| GET    | `/health`       | Estado de salud de todos los servicios   |
| POST   | `/schema/load`  | Indexar descripciones de schema en Qdrant|
| POST   | `/ask`          | Enviar pregunta al agente                |
| GET    | `/charts/{file}`| Descargar un gráfico generado            |
| GET    | `/v1/models`    | Lista modelos (devuelve "guille-agent")  |
| POST   | `/v1/chat/completions` | Chat completions (AnythingLLM)  |

## Estructura del Proyecto

```
agent/
├── docker-compose.yml          # Orquestación de servicios
├── Dockerfile                  # Imagen de la API
├── requirements.txt            # Dependencias Python
├── .env.example                # Variables de entorno template
├── schema_descriptions/        # JSONs con descripción de tablas
│   └── example_schema.json
├── scripts/
│   └── init_db.sql             # Schema + datos de ejemplo
├── app/
│   ├── main.py                 # Entry point FastAPI
│   ├── config.py               # Configuración (pydantic-settings)
│   ├── api/
│   │   └── routes.py           # Endpoints REST
│   ├── models/
│   │   └── schemas.py          # Modelos Pydantic request/response
│   ├── db/
│   │   ├── connection.py       # Pool async SQLAlchemy
│   │   ├── safety.py           # Validador SQL anti-inyección
│   │   └── executor.py         # Ejecución segura de queries
│   ├── agent/
│   │   ├── core.py             # Agente ReAct (LangChain + Ollama)
│   │   ├── prompts.py          # System prompts (5 capacidades)
│   │   ├── tools.py            # Tools: execute_sql, generate_chart
│   │   └── web_tools.py        # Tools: web_search, fetch_webpage
│   ├── memory/
│   │   ├── qdrant_store.py     # Cliente Qdrant + embed/search
│   │   ├── schema_loader.py    # Carga JSONs → Qdrant
│   │   └── file_loader.py      # Carga PDFs/TXT/MD → Qdrant (con dedup)
│   └── charts/
│       └── generator.py        # Generador Matplotlib
├── contentedge/                 # ContentEdge MCP Server
│   ├── mcp_server.py            # 6 MCP tools + health check
│   ├── lib/                     # Python library para Content Repository
│   ├── Dockerfile               # Imagen MCP server
│   └── conf/                    # Configuración YAML del repositorio
└── tests/
    ├── test_safety.py          # Tests de validación SQL
    └── test_charts.py          # Tests de generación de charts
```

## Personalización del Schema

Crea archivos JSON en `schema_descriptions/` con este formato:

```json
{
  "tables": [
    {
      "name": "mi_tabla",
      "description": "Descripción detallada de la tabla.",
      "columns": [
        {
          "name": "columna1",
          "type": "varchar(100)",
          "description": "Qué contiene esta columna."
        }
      ]
    }
  ]
}
```

Luego ejecuta `POST /schema/load` para indexar.

## Seguridad

- **SQL Injection**: Queries validadas con `sqlparse` + ejecutadas con `text()` parametrizado
- **Modo readonly**: Bloquea INSERT/UPDATE/DELETE/DROP por defecto
- **Funciones peligrosas bloqueadas**: `pg_sleep`, `pg_read_file`, `lo_import`, etc.
- **Multi-statement bloqueado**: Solo una sentencia SQL por request
- **Rate limiting**: 30 requests/minuto por IP
- **CORS**: Orígenes configurables
- **Path traversal**: Nombres de archivo sanitizados en endpoint de charts
- **Validación de entrada**: Modelos Pydantic con restricciones de longitud

## GPU (Opcional)

Para usar GPU NVIDIA con Ollama, descomenta en `docker-compose.yml`:

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
# Dentro del contenedor
docker compose exec agent-api pytest tests/ -v

# O localmente con virtualenv
pip install -r requirements.txt
pytest tests/ -v
```
