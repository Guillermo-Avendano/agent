# FLOW_MEMORY — Memory and RAG

## Overview

Describes the vector memory system: how documents and schemas are indexed
in Qdrant, and how relevant context is retrieved for each question.

---

## 1. Memory Architecture

```
                    ┌──────────────────────────────────┐
                    │     Collection: schema_memory     │
                    │                                    │
                    │  ┌──────────────────────────────┐ │
                    │  │ Type: table_schema            │ │
                    │  │ Source: schema_descriptions/  │ │
                    │  │ Loaded with POST /schema/load │ │
                    │  │ Content: tables + columns     │ │
                    │  └──────────────────────────────┘ │
                    │                                    │
                    │  ┌──────────────────────────────┐ │
                    │  │ Type: document                │ │
                    │  │ Source: files_for_memory/     │ │
                    │  │ Loaded at startup (automatic) │ │
                    │  │ Content: PDFs, TXT, MD        │ │
                    │  └──────────────────────────────┘ │
                    └──────────────────────────────────┘

                    Each point in the collection:
                    ├─ UUID (identifier)
                    ├─ Vector (768 dimensions)
                    └─ Payload:
                         ├─ text (chunk content)
                         ├─ source (file / table name)
                         └─ type ("table_schema" | "document")
```

---

## 2. Document Indexing — `load_files_for_memory()`

Runs **automatically at application startup** (in `lifespan()`).

```
load_files_for_memory()                   ← memory/file_loader.py
   │
   ├─ Scans /app/files_for_memory/
   │    Supported formats: .pdf, .txt, .md
   │
   ├─ client = get_qdrant_client()
   ├─ embeddings = get_embeddings()        ← OllamaEmbeddings(nomic-embed-text)
   ├─ ensure_collection("schema_memory")
   │
   ├─ DEDUP: Deletes previous chunks with type="document"
   │    └─ Prevents duplicates on each restart
   │
   ├─ For each file:
   │    ├─ Read by format:
   │    │    .pdf → PdfReader(file).extract_text()
   │    │    .txt → file.read_text()
   │    │    .md  → file.read_text()
   │    │
   │    ├─ _split_text(text, chunk_size=1000, overlap=200)
   │    │    └─ Splits text into overlapping chunks:
   │    │       Chunk 1: [chars 0-999]
   │    │       Chunk 2: [chars 800-1799]     ← 200 char overlap
   │    │       Chunk 3: [chars 1600-2599]
   │    │
   │    ├─ metadatas = [{ source: "file.pdf", type: "document" }]
   │    └─ upsert_texts(client, embeddings, collection, chunks, metadatas)
   │         ├─ vectors = embeddings.embed_documents(chunks)
   │         │    └─ nomic-embed-text → 768-dim per chunk
   │         └─ client.upsert(collection, points)
   │
   └─ Returns: total chunks indexed
```

---

## 3. Schema Indexing — `load_all_schemas()`

Runs **on demand** when `POST /schema/load` is called.

```
load_all_schemas()                        ← memory/schema_loader.py
   │
   ├─ Scans /app/schema_descriptions/*.json
   │
   ├─ For each JSON file:
   │    ├─ Parse the schema
   │    │    Expected format:
   │    │    { "tables": [{ "name": "...", "description": "...",
   │    │      "columns": [{ "name": "...", "type": "...", "description": "..." }] }] }
   │    │
   │    ├─ _build_description_texts(schema)
   │    │    Generates descriptive text per table:
   │    │    "Table: customers
   │    │     Description: Stores customer information
   │    │     Columns:
   │    │       - id (serial): Primary key
   │    │       - name (varchar(200)): Customer full name"
   │    │
   │    └─ upsert_texts(client, embeddings, collection, texts, metadatas)
   │         metadata = { table: "customers", type: "table_schema" }
   │
   └─ Returns: total chunks indexed
```

---

## 4. Retrieval

### 4.1 Schema Context — `_retrieve_schema_context()`

Runs **on every question** within `ask_agent()`.

```
_retrieve_schema_context(question)       ← agent/core.py
   │
   ├─ Fetches ALL table_schema chunks from Qdrant (scroll, not similarity)
   ├─ Deduplicates by table name
   ├─ Fallback: semantic search (top 5) if scroll returns nothing
   └─ Returns: concatenated table descriptions
```

### 4.2 Document Context — `_retrieve_document_context()`

Also runs **on every question**.

```
_retrieve_document_context(question, top_k=3)    ← agent/core.py
   │
   ├─ query_vector = embeddings.embed_query(question)
   ├─ query_points with filter: type="document", limit=3
   ├─ Filter by score >= 0.35 (discards low-relevance matches)
   ├─ Format: "[Source: {filename}]\n{text}"
   └─ Returns: joined document context string (or "" if none)
```

### How Context Is Used

```
SYSTEM_PROMPT.format(
    schema_context  = <table descriptions>,
    document_context = <document chunks>,
    max_rows = 1000
)
```

The LLM uses this context to:
- Know which tables and columns exist → write correct SQL
- Understand table relationships
- Answer questions about ContentEdge (document_context)
- Describe its own capabilities (document_context)

---

## 5. Full RAG Diagram

```
                    INDEXING (offline)
                    ═════════════════

  Source files                       Qdrant
  ┌──────────────┐                  ┌──────────────┐
  │ PDF/TXT/MD   │──── chunk ──────▸│              │
  │ (startup)    │    + embed       │  Collection: │
  └──────────────┘                  │  "schema_    │
                                    │   memory"    │
  ┌──────────────┐                  │              │
  │ JSON schemas │──── describe ───▸│  N points    │
  │ (/schema/load)   + embed       │  (768d each) │
  └──────────────┘                  └──────┬───────┘
                                           │
                    RETRIEVAL (per question)│
                    ═══════════════════════ │
                                           │
  User question                            │
        │                                  │
        ▼                                  ▼
  embed_query() → 768d vector → COSINE similarity search
        │
        ▼
  Top chunks injected into SYSTEM_PROMPT
  ({schema_context} + {document_context})
        │
        ▼
  LLM generates accurate responses
```

---

## 6. Qdrant Store Components

```
qdrant_store.py

VECTOR_SIZE = 768                  ← nomic-embed-text dimension
DISTANCE = COSINE                  ← similarity metric

Functions:
  get_qdrant_client() → QdrantClient
  get_embeddings()    → OllamaEmbeddings(nomic-embed-text)
  ensure_collection() → Creates collection if not exists
  upsert_texts()      → Embeds + upserts chunks
  search_similar()    → Semantic search by query
```

---

## 7. Configuration

| Variable | Default | Purpose |
|---|---|---|
| `QDRANT_HOST` | `"qdrant"` | Qdrant hostname |
| `QDRANT_PORT` | `6333` | Qdrant HTTP port |
| `QDRANT_COLLECTION` | `"schema_memory"` | Collection name |
| `OLLAMA_EMBED_MODEL` | `"nomic-embed-text"` | Embedding model |
| `OLLAMA_BASE_URL` | `"http://ollama:11434"` | Ollama URL |

---

## 8. Files Involved

| File | Key Function | Purpose |
|---|---|---|
| `app/memory/qdrant_store.py` | `get_qdrant_client()`, `upsert_texts()`, `search_similar()` | Qdrant operations |
| `app/memory/file_loader.py` | `load_files_for_memory()` | Indexes PDFs/TXT/MD at startup |
| `app/memory/schema_loader.py` | `load_all_schemas()` | Indexes JSON schemas on demand |
| `app/agent/core.py` | `_retrieve_schema_context()`, `_retrieve_document_context()` | RAG retrieval |
| `app/agent/prompts.py` | `SYSTEM_PROMPT` | Template with `{schema_context}` and `{document_context}` |
