# FLOW_MEMORY — Memoria y RAG (Retrieval-Augmented Generation)

## Resumen

Describe el sistema de memoria vectorial del agente: cómo se indexan
documentos y esquemas en Qdrant, y cómo se recupera contexto relevante
para cada pregunta.

---

## 1. Arquitectura de memoria

```
                       ┌──────────────────────────────────────┐
                       │      Qdrant — Colección:             │
                       │         "schema_memory"              │
                       │                                      │
                       │  ┌────────────────────────────────┐  │
                       │  │ Tipo: table_schema             │  │
                       │  │ Fuente: schema_descriptions/   │  │
                       │  │ Carga: POST /schema/load       │  │
                       │  │ Contenido: tablas + columnas   │  │
                       │  └────────────────────────────────┘  │
                       │                                      │
                       │  ┌────────────────────────────────┐  │
                       │  │ Tipo: document                 │  │
                       │  │ Fuente: files_for_memory/      │  │
                       │  │ Carga: automática al startup   │  │
                       │  │ Contenido: PDFs, TXT, MD       │  │
                       │  └────────────────────────────────┘  │
                       └──────────────────┬───────────────────┘
                                          │
                                    Cada punto:
                                    ├─ UUID (identificador)
                                    ├─ Vector (768 dimensiones)
                                    └─ Payload:
                                         ├─ text (contenido del chunk)
                                         ├─ source (archivo / tabla)
                                         └─ type ("table_schema" | "document")
```

---

## 2. Indexación de documentos — `load_files_for_memory()`

Se ejecuta **automáticamente al iniciar la app** (en `lifespan()`).

```
load_files_for_memory()                   ← memory/file_loader.py
   │
   ├─ Escanea /app/files_for_memory/
   │    Formatos soportados: .pdf, .txt, .md
   │
   ├─ client = get_qdrant_client()
   ├─ embeddings = get_embeddings()        ← OllamaEmbeddings(nomic-embed-text)
   ├─ ensure_collection("schema_memory")
   │
   ├─ Por cada archivo encontrado:
   │    │
   │    ├─ Lectura según formato:
   │    │    .pdf → PdfReader(file).extract_text()     ← pypdf
   │    │    .txt → file.read_text()
   │    │    .md  → file.read_text()
   │    │
   │    ├─ _split_text(text, chunk_size=1000, overlap=200)
   │    │    │
   │    │    │  Divide el texto en chunks con solapamiento:
   │    │    │
   │    │    │  Texto original: [========================]
   │    │    │                        1000 chars
   │    │    │
   │    │    │  Chunk 1: [chars 0-999]
   │    │    │  Chunk 2: [chars 800-1799]     ← overlap de 200
   │    │    │  Chunk 3: [chars 1600-2599]
   │    │    │  ...
   │    │    │
   │    │    └─ Retorna: lista de strings
   │    │
   │    ├─ metadatas = [{ source: "archivo.pdf", type: "document" }] * n_chunks
   │    │
   │    └─ upsert_texts(client, embeddings, "schema_memory", chunks, metadatas)
   │         │
   │         ├─ vectors = embeddings.embed_documents(chunks)
   │         │    └─ Ollama nomic-embed-text → 768d por chunk
   │         │
   │         ├─ points = [
   │         │    PointStruct(
   │         │      id = uuid4(),
   │         │      vector = vector,
   │         │      payload = { text: chunk_text, source: ..., type: ... }
   │         │    )
   │         │    for each (chunk, vector, metadata)
   │         │  ]
   │         │
   │         └─ client.upsert("schema_memory", points)
   │
   └─ Retorna: total de chunks indexados
        └─ Log: "file_loader.done", chunks=N
```

---

## 3. Indexación de esquemas — `load_all_schemas()`

Se ejecuta **bajo demanda** al llamar `POST /schema/load`.

```
load_all_schemas()                        ← memory/schema_loader.py
   │
   ├─ client = get_qdrant_client()
   ├─ embeddings = get_embeddings()
   ├─ ensure_collection("schema_memory")
   │
   ├─ Escanea /app/schema_descriptions/*.json
   │
   ├─ Por cada archivo JSON:
   │    │
   │    ├─ schema = json.load(file)
   │    │
   │    │  Formato esperado:
   │    │  {
   │    │    "tables": [
   │    │      {
   │    │        "name": "customers",
   │    │        "description": "Stores customer information",
   │    │        "columns": [
   │    │          { "name": "id", "type": "serial", "description": "Primary key" },
   │    │          { "name": "name", "type": "varchar(200)", "description": "..." },
   │    │          ...
   │    │        ]
   │    │      },
   │    │      ...
   │    │    ]
   │    │  }
   │    │
   │    ├─ _build_description_texts(schema)
   │    │    │
   │    │    │  Por cada tabla, genera un texto descriptivo:
   │    │    │
   │    │    │  "Table: customers
   │    │    │   Description: Stores customer information
   │    │    │   Columns:
   │    │    │     - id (serial): Primary key
   │    │    │     - name (varchar(200)): Customer full name
   │    │    │     - email (varchar(255)): Unique email address
   │    │    │     - created_at (timestamptz): Registration date"
   │    │    │
   │    │    └─ Retorna: (texts[], metadatas[])
   │    │         metadata = { table: "customers", type: "table_schema" }
   │    │
   │    └─ upsert_texts(client, embeddings, "schema_memory", texts, metadatas)
   │         └─ (mismo flujo que en documentos)
   │
   └─ Retorna: total de chunks indexados
        └─ Log: "schema_loader.done", chunks=N
```

---

## 4. Retrieval — `_retrieve_schema_context()`

Se ejecuta **en cada pregunta** dentro de `ask_agent()`.

```
_retrieve_schema_context(question, top_k=5)    ← agent/core.py
   │
   ├─ client = get_qdrant_client()
   ├─ embeddings = get_embeddings()
   │
   ├─ results = search_similar(
   │      client, embeddings,
   │      collection = "schema_memory",
   │      query = question,
   │      top_k = 5
   │  )
   │    │
   │    │  search_similar()                    ← memory/qdrant_store.py
   │    │    │
   │    │    ├─ query_vector = embeddings.embed_query(question)
   │    │    │    └─ Ollama nomic-embed-text → vector 768d
   │    │    │
   │    │    ├─ hits = client.query_points(
   │    │    │      "schema_memory",
   │    │    │      query = query_vector,
   │    │    │      limit = 5,
   │    │    │      with_payload = True
   │    │    │  )
   │    │    │    └─ Qdrant busca los 5 vectores más cercanos (distancia COSINE)
   │    │    │
   │    │    └─ Retorna: [
   │    │         { text: "Table: customers...", score: 0.89, ... },
   │    │         { text: "Table: orders...",    score: 0.85, ... },
   │    │         { text: "Chunk de PDF...",     score: 0.72, ... },
   │    │         ...
   │    │       ]
   │    │
   │    └─ Top 5 resultados más relevantes
   │
   ├─ schema_context = "\n\n".join(r["text"] for r in results)
   │    └─ Concatena los 5 textos con doble salto de línea
   │
   └─ Retorna: string con el contexto relevante
        │
        └─ Fallback: "No schema context available."
             (si Qdrant no responde o colección vacía)
```

### ¿Cómo se usa el contexto recuperado?

```
SYSTEM_PROMPT.format(
    schema_context = <resultado del retrieval>,
    max_rows = 1000
)

Ejemplo del prompt resultante (sección de contexto):

   "### Database context
    Table: customers
    Description: Stores customer information
    Columns:
      - id (serial): Primary key
      - name (varchar(200)): Customer full name
      ...

    Table: orders
    Description: Customer orders with status tracking
    Columns:
      - id (serial): Primary key
      - customer_id (integer): FK to customers
      ..."
```

El LLM usa este contexto para:
- Saber qué tablas y columnas existen
- Escribir SQL con los nombres correctos
- Entender las relaciones entre tablas

---

## 5. Componentes de Qdrant Store

```
qdrant_store.py                           ← memory/qdrant_store.py

VECTOR_SIZE = 768                         ← dimensión de nomic-embed-text
DISTANCE = COSINE                         ← métrica de similitud

Funciones:

get_qdrant_client() → QdrantClient
   └─ QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
      (cliente síncrono)

get_embeddings() → OllamaEmbeddings
   └─ OllamaEmbeddings(
        model = "nomic-embed-text",
        base_url = "http://ollama:11434"
      )

ensure_collection(client, collection_name)
   ├─ Verifica si la colección existe
   └─ Si no: client.create_collection(
                vectors_config = VectorParams(
                  size = 768,
                  distance = COSINE
                )
             )

upsert_texts(client, embeddings, collection, texts, metadatas)
   ├─ vectors = embeddings.embed_documents(texts)
   ├─ points = [PointStruct(uuid, vector, payload) for each]
   └─ client.upsert(collection, points)
      Retorna: count de puntos upsertados

search_similar(client, embeddings, collection, query, top_k=5)
   ├─ query_vector = embeddings.embed_query(query)
   ├─ hits = client.query_points(collection, query_vector, limit=top_k)
   └─ Retorna: [{text, score, ...payload}, ...]
```

---

## 6. Diagrama del flujo completo de RAG

```
                    INDEXACIÓN (offline)
                    ══════════════════

  Archivos fuente                    Qdrant
  ┌──────────────┐                  ┌──────────────┐
  │ PDF/TXT/MD   │──── chunk ──────▸│              │
  │ (startup)    │    + embed       │  Colección:  │
  └──────────────┘                  │  "schema_    │
                                    │   memory"    │
  ┌──────────────┐                  │              │
  │ JSON schemas │──── describe ───▸│  N puntos    │
  │ (/schema/load)   + embed       │  (768d cada  │
  └──────────────┘                  │   uno)       │
                                    └──────┬───────┘
                                           │
                    RETRIEVAL (por pregunta)│
                    ═══════════════════════ │
                                           │
  Pregunta usuario                         │
  "¿Cuántos pedidos?"                      │
        │                                  │
        ▼                                  │
  embed_query()                            │
  → vector 768d                            │
        │                                  │
        ▼                                  ▼
  query_points(limit=5) ──── COSINE ─── busca similares
        │
        ▼
  Top 5 chunks más relevantes
        │
        ▼
  Se inyectan como {schema_context}
  en el SYSTEM_PROMPT del agente
        │
        ▼
  El LLM "conoce" las tablas y columnas
  → genera SQL correcto
```

---

## 7. Ejemplo paso a paso

### Pregunta: "¿Cuáles son los productos más vendidos?"

```
1. _retrieve_schema_context("¿Cuáles son los productos más vendidos?")

2. embed_query("¿Cuáles son los productos más vendidos?")
   → vector de 768 dimensiones

3. query_points("schema_memory", vector, limit=5):

   Resultado (ordenado por similitud coseno):

   Score  │ Tipo          │ Texto
   ───────┼───────────────┼──────────────────────────────────────
   0.91   │ table_schema  │ "Table: products\n  - name, price, category, stock"
   0.88   │ table_schema  │ "Table: order_items\n  - order_id, product_id, quantity"
   0.84   │ table_schema  │ "Table: orders\n  - customer_id, total, status"
   0.72   │ document      │ "Chunk de README sobre el sistema de ventas..."
   0.65   │ table_schema  │ "Table: customers\n  - name, email"

4. schema_context = chunks[0].text + "\n\n" + chunks[1].text + ...

5. SYSTEM_PROMPT incluye ahora:
   "### Database context
    Table: products
    Description: Available products for sale
    Columns:
      - id (serial): Primary key
      - name (varchar(200)): Product name
      - price (numeric(10,2)): Unit price
      ...

    Table: order_items
    ..."

6. El LLM genera:
   "SELECT p.name, SUM(oi.quantity) as total_sold
    FROM products p
    JOIN order_items oi ON p.id = oi.product_id
    GROUP BY p.name
    ORDER BY total_sold DESC"

   → Usa los nombres correctos (products, order_items, quantity)
     porque los vio en el contexto inyectado.
```

---

## 8. Archivos involucrados

| Archivo | Función clave | Propósito |
|---|---|---|
| `app/memory/qdrant_store.py` | `get_qdrant_client()` | Cliente Qdrant |
| `app/memory/qdrant_store.py` | `get_embeddings()` | Modelo de embeddings (Ollama) |
| `app/memory/qdrant_store.py` | `ensure_collection()` | Crea colección si no existe |
| `app/memory/qdrant_store.py` | `upsert_texts()` | Indexa chunks en Qdrant |
| `app/memory/qdrant_store.py` | `search_similar()` | Busca chunks relevantes |
| `app/memory/file_loader.py` | `load_files_for_memory()` | Indexa PDFs/TXT/MD al startup |
| `app/memory/file_loader.py` | `_split_text()` | Divide texto en chunks |
| `app/memory/schema_loader.py` | `load_all_schemas()` | Indexa JSONs de esquema |
| `app/memory/schema_loader.py` | `_build_description_texts()` | Genera texto de tablas |
| `app/agent/core.py` | `_retrieve_schema_context()` | RAG: recupera contexto por pregunta |
| `app/agent/prompts.py` | `SYSTEM_PROMPT` | Template con `{schema_context}` |

---

## 9. Configuración relevante

| Variable | Valor por defecto | Uso |
|---|---|---|
| `QDRANT_HOST` | `"qdrant"` | Hostname de Qdrant |
| `QDRANT_PORT` | `6333` | Puerto HTTP de Qdrant |
| `QDRANT_COLLECTION` | `"schema_memory"` | Nombre de la colección |
| `OLLAMA_EMBED_MODEL` | `"nomic-embed-text"` | Modelo de embeddings |
| `OLLAMA_BASE_URL` | `"http://ollama:11434"` | URL de Ollama |
