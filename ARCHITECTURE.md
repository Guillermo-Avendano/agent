# Arquitectura y Flujo de Ejecución del Agente

## Visión General

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│ AnythingLLM  │─────▸│  FastAPI API  │─────▸│   ReAct Agent   │
│  (chat UI)   │◂─────│   (Gateway)   │◂─────│  (LangGraph)    │
└─────────────┘      └──────────────┘      └────────┬────────┘
                                                     │
                              ┌───────────┬──────────┼──────────┬────────────┐
                              ▼           ▼          ▼          ▼            ▼
                         ┌─────────┐ ┌────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐
                         │PostgreSQL│ │Qdrant  │ │ Ollama │ │Browserless│ │Matplotlib│
                         │  (datos) │ │(vector)│ │ (LLM)  │ │(web srch) │ │ (charts) │
                         └─────────┘ └────────┘ └────────┘ └──────────┘ └──────────┘
```

---

## 1. Arranque (`docker compose up`)

### 1.1 Orden de inicio (dependencias Docker)

```
postgres ─┐
qdrant  ──┤
ollama  ──┼─▸ ollama-pull ─┐
           │                ├─▸ agent-api ─▸ anythingllm
browserless ────────────────┘
```

| Servicio | Puerto | Propósito |
|---|---|---|
| **postgres** | 5432 | Base de datos PostgreSQL 16 |
| **qdrant** | 6333 | Base de datos vectorial |
| **ollama** | 11434 | Servidor de modelos LLM |
| **ollama-pull** | — | Descarga `llama3` + `nomic-embed-text` y termina |
| **browserless** | 3000 (interno) | Chromium headless para web scraping |
| **agent-api** | 8000 | API FastAPI — el cerebro del agente |
| **anythingllm** | 3001 | Interfaz de chat web |

### 1.2 Inicio de la aplicación FastAPI

```
main.py → lifespan()
   │
   ├─▸ 1. Configura structured logging (structlog)
   ├─▸ 2. Crea rate limiter (30 req/min)
   ├─▸ 3. Registra routers (routes.py + openai_compat.py)
   ├─▸ 4. Carga CORS middleware
   │
   └─▸ 5. lifespan startup:
         └─▸ load_files_for_memory()          ← file_loader.py
              ├─ Lee PDFs/TXT/MD de /app/files_for_memory/
              ├─ Divide en chunks de ~1000 caracteres con overlap
              ├─ Genera embeddings con nomic-embed-text (via Ollama)
              └─ Upserta chunks en la colección Qdrant "schema_memory"
```

> **Nota**: Los archivos de `schema_descriptions/` se cargan bajo demanda
> cuando se llama al endpoint `POST /schema/load`.

---

## 2. Flujo de una Pregunta (Request → Response)

Hay dos caminos de entrada equivalentes:

| Vía | Endpoint | Quién lo usa |
|---|---|---|
| API directa | `POST /ask` | Cualquier cliente HTTP |
| OpenAI-compatible | `POST /v1/chat/completions` | AnythingLLM |

Ambos terminan llamando a la misma función: **`ask_agent()`**.

### 2.1 Diagrama completo paso a paso

```
Usuario / AnythingLLM
        │
        ▼
┌─ FastAPI ────────────────────────────────────────────────────────┐
│                                                                   │
│  routes.py ─ POST /ask           openai_compat.py ─ POST /v1/... │
│       │                                │                          │
│       └──────────── ambos llaman ──────┘                          │
│                         │                                         │
│                         ▼                                         │
│               ask_agent(question, session, chat_history)          │
│                    │          core.py                              │
│                    │                                              │
│  ┌─────────────────┼────────────────────────────────────┐        │
│  │  PASO 1         ▼                                     │        │
│  │  bind_session(session)                                │        │
│  │  → Guarda referencia a la sesión de BD para que       │        │
│  │    el tool execute_sql pueda usarla.                  │        │
│  │                                                       │        │
│  │  PASO 2                                               │        │
│  │  _retrieve_schema_context(question)                   │        │
│  │  → Busca en Qdrant los 5 chunks más relevantes        │        │
│  │    a la pregunta (esquemas + documentos cargados)     │        │
│  │  → Devuelve texto con descripciones de tablas/columnas│        │
│  │                                                       │        │
│  │  PASO 3                                               │        │
│  │  Construye el SYSTEM_PROMPT                           │        │
│  │  → Inyecta {schema_context} + {max_rows}             │        │
│  │  → Incluye instrucciones de las 3 capacidades:        │        │
│  │    SQL, Web Search, Conocimiento General              │        │
│  │                                                       │        │
│  │  PASO 4                                               │        │
│  │  Arma la lista de mensajes:                           │        │
│  │  [SystemMessage, ...chat_history, HumanMessage]       │        │
│  │                                                       │        │
│  │  PASO 5                                               │        │
│  │  create_react_agent(llm, AGENT_TOOLS)                 │        │
│  │  → LLM = ChatOllama (llama3, temperature=0)           │        │
│  │  → Tools = [execute_sql, generate_chart,              │        │
│  │             web_search, fetch_webpage]                │        │
│  │                                                       │        │
│  │  PASO 6                                               │        │
│  │  agent.ainvoke(messages)                              │        │
│  │  → Aquí entra el LOOP REACT (ver sección 3)          │        │
│  │                                                       │        │
│  │  PASO 7                                               │        │
│  │  Extrae del resultado:                                │        │
│  │  - answer (último mensaje del agente)                 │        │
│  │  - chart_path (si se generó un gráfico)              │        │
│  │  - data_preview (primeras 20 filas del último query)  │        │
│  └───────────────────────────────────────────────────────┘        │
│                         │                                         │
│                         ▼                                         │
│              { answer, chart_path, data_preview }                 │
│                         │                                         │
└─────────────────────────┼─────────────────────────────────────────┘
                          ▼
                  Respuesta al cliente
```

---

## 3. El Loop ReAct (Razonamiento + Acción)

El agente usa el patrón **ReAct** de LangGraph. En cada iteración:

```
                    ┌───────────────┐
                    │  LLM piensa   │
                    │  (Ollama)     │
                    └───────┬───────┘
                            │
                   ¿Necesita una herramienta?
                      │             │
                     SÍ             NO
                      │             │
                      ▼             ▼
              ┌──────────────┐   Respuesta
              │ Llama al tool│   final
              │ seleccionado │
              └──────┬───────┘
                     │
                     ▼
              Tool devuelve resultado
                     │
                     ▼
              ┌──────────────┐
              │ LLM analiza  │
              │ el resultado │
              └──────┬───────┘
                     │
            ¿Necesita otro tool?
               │          │
              SÍ          NO
               │          │
               └──(loop)  ▼
                       Respuesta final
```

### Ejemplo: "¿Cuántos pedidos hay por cliente?"

```
Iteration 1:
  LLM → "Necesito consultar la BD" → llama execute_sql
  execute_sql:
    1. validate_sql() — verifica que sea SELECT, sin inyección
    2. session.execute(text(sql)) — ejecuta contra PostgreSQL
    3. Devuelve DataFrame como tabla markdown

Iteration 2:
  LLM → analiza resultados → genera respuesta textual
  → FIN
```

### Ejemplo: "Muéstrame un gráfico de ventas por categoría"

```
Iteration 1:
  LLM → llama execute_sql con SELECT de ventas

Iteration 2:
  LLM → llama generate_chart con spec JSON
  generate_chart:
    1. Toma el DataFrame guardado del query anterior
    2. Llama a create_chart() (Matplotlib)
    3. Guarda el PNG en /app/charts_output/
    4. Devuelve "Chart saved to: /app/charts_output/xxx.png"

Iteration 3:
  LLM → "Aquí está el gráfico..." → FIN
```

### Ejemplo: "¿Quién ganó el último premio Nobel de Física?"

```
Iteration 1:
  LLM → "Esto no está en la BD" → llama web_search
  web_search:
    1. Construye URL de DuckDuckGo
    2. Envía a Browserless Chromium para renderizar
    3. Extrae links + snippets del HTML
    4. Fetch del primer resultado para más detalle
    5. Devuelve resumen con fuentes

Iteration 2:
  LLM → analiza los resultados web → responde → FIN
```

### Ejemplo: "Hola, ¿cómo estás?"

```
Iteration 1:
  LLM → "Es una pregunta conversacional" → responde directamente
  → FIN (no se llama ningún tool)
```

---

## 4. Los Tools (Herramientas)

| Tool | Archivo | Descripción |
|---|---|---|
| `execute_sql` | `agent/tools.py` | Ejecuta SELECT contra PostgreSQL |
| `generate_chart` | `agent/tools.py` | Genera gráficos PNG con Matplotlib |
| `web_search` | `agent/web_tools.py` | Busca en DuckDuckGo via Browserless |
| `fetch_webpage` | `agent/web_tools.py` | Extrae texto de una URL específica |

### execute_sql — Flujo interno

```
query (string)
   │
   ▼
validate_sql()                  ← safety.py
   ├─ ¿Query vacío? → Error
   ├─ ¿Contiene pg_sleep, lo_import, etc? → Bloqueado
   ├─ ¿Múltiples statements (;)? → Bloqueado
   ├─ ¿Es INSERT/UPDATE/DELETE/DROP? → Bloqueado (modo readonly)
   └─ OK → query limpio
         │
         ▼
   session.execute(text(query))  ← executor.py
         │
         ▼
   DataFrame (max 1000 filas)
         │
         ▼
   Retorna tabla markdown
```

### generate_chart — Flujo interno

```
spec_json (string)
   │
   ▼
json.loads(spec_json)
   ├─ chart_type: bar|line|pie|scatter|histogram
   ├─ x: columna eje X
   ├─ y: columna eje Y
   └─ title: título
         │
         ▼
   create_chart(df, ...)         ← charts/generator.py
   → Matplotlib genera PNG
   → Guarda en /app/charts_output/chart_XXXXXX.png
         │
         ▼
   "Chart saved to: /app/charts_output/chart_XXXXXX.png"
```

### web_search — Flujo interno

```
query (string)
   │
   ▼
_search_duckduckgo(query)
   ├─ URL: https://html.duckduckgo.com/html/?q=...
   ├─ _fetch_via_browserless(url)
   │    └─ POST a browserless:3000/content
   │       └─ Chromium renderiza la página
   │       └─ Devuelve HTML
   ├─ Extrae links y snippets del HTML
   └─ Retorna top 3 resultados
         │
         ▼
_fetch_via_browserless(top_result_url)
   └─ Lee el contenido completo del primer resultado
         │
         ▼
Retorna: resultados + contenido (máx ~4000 chars)
```

---

## 5. La Memoria (Qdrant)

```
                    ┌──────────────────────────────────┐
                    │     Colección: schema_memory      │
                    │                                    │
                    │  ┌──────────────────────────────┐ │
                    │  │ Tipo: table_schema            │ │
                    │  │ Fuente: schema_descriptions/  │ │
                    │  │ Se carga con POST /schema/load │ │
                    │  └──────────────────────────────┘ │
                    │                                    │
                    │  ┌──────────────────────────────┐ │
                    │  │ Tipo: document                │ │
                    │  │ Fuente: files_for_memory/     │ │
                    │  │ Se carga automáticamente       │ │
                    │  │ al iniciar la app              │ │
                    │  └──────────────────────────────┘ │
                    └──────────────────────────────────┘
                                     │
                                     ▼
                    Cada pregunta busca los top-5 chunks
                    más similares y los inyecta en el
                    system prompt como contexto.
```

### Proceso de indexación

```
Archivo (PDF/TXT/MD/JSON)
   │
   ▼
Lectura y extracción de texto
   │
   ▼
Split en chunks (~1000 chars, 200 overlap)
   │
   ▼
embed_documents() → nomic-embed-text (Ollama)
   │                  → vector de 768 dimensiones
   ▼
upsert_texts() → Qdrant
   └─ Cada chunk = 1 punto con UUID, vector, payload
      payload = { text, source/table, type }
```

### Proceso de retrieval (cada pregunta)

```
Pregunta del usuario
   │
   ▼
embed_query() → vector de 768 dim
   │
   ▼
query_points(limit=5) → top 5 chunks más similares
   │
   ▼
Texto de los chunks se concatena
   │
   ▼
Se inyecta en {schema_context} del SYSTEM_PROMPT
```

---

## 6. API Endpoints

### Endpoints principales (`routes.py`)

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Chequea PostgreSQL + Qdrant + Ollama |
| `POST` | `/schema/load` | Indexa archivos JSON de `schema_descriptions/` en Qdrant |
| `POST` | `/ask` | Envía pregunta al agente, recibe respuesta |
| `GET` | `/charts/{filename}` | Descarga imagen PNG de un gráfico |

### Endpoints OpenAI-compatible (`openai_compat.py`)

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/v1/models` | Lista modelos (devuelve "sql-agent") |
| `POST` | `/v1/chat/completions` | Chat completions — usado por AnythingLLM |

### Flujo AnythingLLM → Agente

```
AnythingLLM
   │
   ├─ En setup: GET /v1/models → recibe "sql-agent"
   │
   └─ Cada mensaje:
      POST /v1/chat/completions
        { model: "sql-agent", messages: [...] }
              │
              ▼
      openai_compat.py
        ├─ Extrae último mensaje del usuario como pregunta
        ├─ Arma chat_history de mensajes anteriores
        ├─ Llama a ask_agent(question, session, history)
        └─ Formatea respuesta como OpenAI ChatCompletion
              │
              ▼
      AnythingLLM muestra la respuesta
```

---

## 7. Seguridad

```
Capa de seguridad (safety.py):
  ✓ Solo permite SELECT (modo readonly)
  ✓ Bloquea múltiples statements (anti SQL injection)
  ✓ Bloquea funciones peligrosas (pg_sleep, lo_import, etc.)
  ✓ Queries ejecutados con text() de SQLAlchemy (parametrizados)

API:
  ✓ Rate limiting (30 req/min por IP)
  ✓ CORS configurado con orígenes permitidos
  ✓ Path traversal prevenido en /charts/{filename}
```

---

## 8. Estructura de Archivos

```
agent/
├── docker-compose.yml          # Orquestación de servicios
├── Dockerfile                  # Imagen Python 3.12
├── requirements.txt            # Dependencias Python
├── .env / .env.example         # Variables de entorno
│
├── schema_descriptions/        # JSONs con descripción de tablas
│   └── example_schema.json
│
├── files_for_memory/           # PDFs/TXT/MD para memoria del agente
│   └── README.md
│
├── charts_output/              # Gráficos generados (auto-creado)
├── scripts/
│   └── init_db.sql             # DDL + datos iniciales
│
├── app/
│   ├── main.py                 # Entry point FastAPI + lifespan
│   ├── config.py               # Settings desde .env (Pydantic)
│   │
│   ├── api/
│   │   ├── routes.py           # /health, /ask, /schema/load, /charts/
│   │   └── openai_compat.py    # /v1/models, /v1/chat/completions
│   │
│   ├── agent/
│   │   ├── core.py             # ask_agent() — orquesta el flujo
│   │   ├── tools.py            # execute_sql, generate_chart
│   │   ├── web_tools.py        # web_search, fetch_webpage
│   │   └── prompts.py          # System prompt + chart instructions
│   │
│   ├── db/
│   │   ├── connection.py       # Engine async + session factory
│   │   ├── executor.py         # run_query() — valida y ejecuta SQL
│   │   └── safety.py           # Validación SQL (readonly, anti-injection)
│   │
│   ├── memory/
│   │   ├── qdrant_store.py     # Cliente Qdrant, embed, upsert, search
│   │   ├── schema_loader.py    # Carga JSONs de esquema → Qdrant
│   │   └── file_loader.py      # Carga PDFs/TXT/MD → Qdrant
│   │
│   ├── charts/
│   │   └── generator.py        # Matplotlib: bar, line, pie, scatter, hist
│   │
│   └── models/
│       └── schemas.py          # Pydantic models (request/response)
│
└── tests/
    ├── test_safety.py
    └── test_charts.py
```
