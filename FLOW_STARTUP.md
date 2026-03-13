# FLOW_STARTUP — Arranque de la Aplicación

## Resumen

Describe el flujo completo desde `docker compose up` hasta que la API
está lista para recibir peticiones.

---

## 1. Orden de inicio de contenedores

```
postgres ──────────┐
qdrant  ───────────┤
ollama ─▸ ollama-pull ─┤
browserless ───────────┼─▸ agent-api ─▸ anythingllm
                       │
```

Cada servicio declara un **healthcheck** en `docker-compose.yml`.
Los contenedores dependientes esperan `condition: service_healthy`
antes de arrancar.

| Servicio | Puerto | Healthcheck | Propósito |
|---|---|---|---|
| `postgres` | 5432 | `pg_isready -U agent_user -d agent_db` | BD relacional |
| `qdrant` | 6333 / 6334 | TCP al puerto 6333 | BD vectorial |
| `ollama` | 11434 | — | Servidor LLM |
| `ollama-pull` | — | termina con exit 0 | Descarga `llama3` + `nomic-embed-text` |
| `browserless` | 3000 (interno) | `/json/version` | Chromium headless |
| `agent-api` | 8000 | `curl http://localhost:8000/health` | API FastAPI |
| `anythingllm` | 3001 | — | Chat UI |

---

## 2. Inicialización de PostgreSQL

```
postgres arranca
   │
   └─▸ /docker-entrypoint-initdb.d/01_init.sql   ← scripts/init_db.sql
         │
         ├─ CREATE TABLE customers (id, name, email, created_at)
         ├─ CREATE TABLE products  (id, name, price, category, stock)
         ├─ CREATE TABLE orders    (id, customer_id, total, status, created_at)
         ├─ CREATE TABLE order_items (id, order_id, product_id, quantity, unit_price)
         │
         └─ INSERT datos semilla:
              5 clientes, 8 productos, 8 órdenes, 14 ítems
```

---

## 3. Inicialización de `agent-api` (FastAPI)

### 3.1 Carga de configuración

```
config.py → class Settings(BaseSettings)
   │
   ├─ Lee .env (o variables de entorno)
   │    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
   │    QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION ("schema_memory")
   │    OLLAMA_BASE_URL, OLLAMA_MODEL ("llama3"), OLLAMA_EMBED_MODEL ("nomic-embed-text")
   │    BROWSERLESS_URL, SQL_READONLY (True), MAX_QUERY_ROWS (1000)
   │    LOG_LEVEL, ALLOWED_ORIGINS, APP_HOST, APP_PORT
   │
   └─ Genera DSNs:
        postgres_dsn      = "postgresql+asyncpg://user:pass@host:5432/db"
        postgres_dsn_sync = "postgresql://user:pass@host:5432/db"
```

### 3.2 Creación de la app FastAPI

```
main.py
   │
   ├─ 1. Configura structlog
   │      └─ Logging estructurado (consola o JSON según LOG_LEVEL)
   │
   ├─ 2. Crea rate limiter
   │      └─ slowapi.Limiter: 30 req/min por IP
   │
   ├─ 3. Instancia FastAPI con lifespan()
   │
   ├─ 4. Registra CORS middleware
   │      └─ allow_origins = ALLOWED_ORIGINS
   │
   └─ 5. Registra routers:
          ├─ routes.py       → /health, /ask, /schema/load, /charts/{fn}
          └─ openai_compat.py → /v1/models, /v1/chat/completions
```

### 3.3 Lifespan — Startup

```
lifespan(app)   ← asynccontextmanager
   │
   ├─▸ logger.info("app.startup")
   │
   ├─▸ load_files_for_memory()            ← memory/file_loader.py
   │      │
   │      ├─ Escanea /app/files_for_memory/ buscando .pdf, .txt, .md
   │      │
   │      ├─ Por cada archivo:
   │      │    ├─ Lee contenido (pypdf para PDF, lectura directa para txt/md)
   │      │    ├─ Divide en chunks de ~1000 caracteres con overlap de 200
   │      │    ├─ Metadata: { source: "nombre_archivo", type: "document" }
   │      │    └─ upsert_texts() → Qdrant colección "schema_memory"
   │      │         ├─ embed_documents() via nomic-embed-text (Ollama)
   │      │         │   → vectores de 768 dimensiones
   │      │         └─ client.upsert(points) en Qdrant
   │      │
   │      └─ Retorna: total de chunks indexados
   │
   ├─▸ logger.info("app.files_loaded", chunks=total)
   │
   ├─▸ ──── yield ──── (app sirve tráfico)
   │
   └─▸ Shutdown:
          └─ dispose_engine()   ← db/connection.py
               └─ Cierra pool de conexiones PostgreSQL
```

### 3.4 Pool de conexiones PostgreSQL

```
connection.py
   │
   ├─ engine = create_async_engine(
   │      postgres_dsn,
   │      pool_size=10,
   │      max_overflow=20,
   │      pool_pre_ping=True    ← verifica conexiones antes de usar
   │  )
   │
   ├─ async_session_factory = async_sessionmaker(
   │      engine,
   │      class_=AsyncSession,
   │      expire_on_commit=False
   │  )
   │
   └─ get_session() → FastAPI Dependency
        └─ yield session (con auto-commit/rollback)
```

---

## 4. Diagrama temporal completo

```
t=0   docker compose up
      │
t=1   postgres: arranca → ejecuta init_db.sql → healthcheck OK
      qdrant: arranca → healthcheck OK
      ollama: arranca
      browserless: arranca → healthcheck OK
      │
t=2   ollama-pull: descarga llama3 + nomic-embed-text → exit 0
      │
t=3   agent-api: arranca
      ├─ Lee .env / config
      ├─ Crea pool PostgreSQL (10 conexiones)
      ├─ Registra routers + middleware
      ├─ lifespan startup:
      │    └─ load_files_for_memory()
      │         ├─ Conecta a Qdrant
      │         ├─ Asegura existencia de colección "schema_memory"
      │         ├─ Lee archivos → chunks → embeddings → upsert
      │         └─ Log: "app.files_loaded"
      ├─ healthcheck: GET /health → 200 OK
      └─ Escucha en 0.0.0.0:8000
      │
t=4   anythingllm: arranca
      ├─ Configurado con LLM_PROVIDER=generic-openai
      ├─ Apunta a http://agent-api:8000/v1
      ├─ GET /v1/models → recibe "sql-agent"
      └─ Escucha en 0.0.0.0:3001
      │
      ═══════════════════════════════════
       Sistema listo para recibir preguntas
      ═══════════════════════════════════
```

---

## 5. Archivos involucrados

| Archivo | Rol en el arranque |
|---|---|
| `docker-compose.yml` | Orquestación de servicios y dependencias |
| `scripts/init_db.sql` | DDL + datos semilla para PostgreSQL |
| `app/main.py` | Entry point, lifespan, middleware |
| `app/config.py` | Carga de configuración desde `.env` |
| `app/db/connection.py` | Pool async de PostgreSQL |
| `app/memory/file_loader.py` | Indexa documentos en Qdrant al inicio |
| `app/memory/qdrant_store.py` | Cliente Qdrant, embeddings, upsert |
