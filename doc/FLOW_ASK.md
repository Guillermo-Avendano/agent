# FLOW_ASK — Question Processing

## Overview

Describes the complete flow from receiving a user question to returning
the response. This is the central flow of the agent.

---

## 1. Entry Points

Two endpoints receive questions. Both converge on `ask_agent()`.

```
┌──────────────────────────┐     ┌─────────────────────────────────┐
│  POST /ask               │     │  POST /v1/chat/completions      │
│  (routes.py)             │     │  (openai_compat.py)             │
│                          │     │                                  │
│  Body: AskRequest        │     │  Body: OpenAIChatRequest        │
│  { question,             │     │  { model, messages[],           │
│    chat_history[] }      │     │    temperature, stream }        │
│                          │     │                                  │
│  Pydantic validation:    │     │  Processing:                    │
│  - question: 1-5000 ch   │     │  - Ignores role="system"        │
│  - history: max 50 msgs  │     │  - Last role="user" = question  │
│  - content: 1-10000 ch   │     │  - role="assistant" → history   │
└────────────┬─────────────┘     └───────────────┬─────────────────┘
             │                                    │
             └─────────── both call ──────────────┘
                              │
                              ▼
                    ask_agent(question, session, chat_history)
                              │
                         core.py
```

---

## 2. `ask_agent()` — Step by Step

```
ask_agent(question, session, chat_history)
   │
   │  ┌─────────────────────────────────────────────────┐
   │  │ STEP 1: Bind session                            │
   │  │                                                  │
   │  │ bind_session(session)            ← tools.py     │
   │  │   └─ _session_ref = session                     │
   │  │   Stores global reference so execute_sql        │
   │  │   can access the DB session.                    │
   │  └─────────────────────────────────────────────────┘
   │
   │  ┌─────────────────────────────────────────────────┐
   │  │ STEP 2: Retrieve schema context (RAG)           │
   │  │                                                  │
   │  │ _retrieve_schema_context(question)              │
   │  │   ├─ Fetches ALL table_schema chunks from Qdrant│
   │  │   ├─ Deduplicates by table name                 │
   │  │   └─ Returns: table/column description text     │
   │  │                                                  │
   │  │   Fallback: "No schema context available."       │
   │  └─────────────────────────────────────────────────┘
   │
   │  ┌─────────────────────────────────────────────────┐
   │  │ STEP 3: Retrieve document context (RAG)         │
   │  │                                                  │
   │  │ _retrieve_document_context(question, top_k=3)   │
   │  │   ├─ Searches Qdrant for type="document" chunks │
   │  │   ├─ Filters by score >= 0.35                   │
   │  │   └─ Returns: ContentEdge and self-knowledge    │
   │  │                                                  │
   │  │   Fallback: "" (empty)                           │
   │  └─────────────────────────────────────────────────┘
   │
   │  ┌─────────────────────────────────────────────────┐
   │  │ STEP 4: Build system prompt                     │
   │  │                                                  │
   │  │ SYSTEM_PROMPT.format(                           │
   │  │     schema_context, document_context, max_rows  │
   │  │ )                                               │
   │  │                                                  │
   │  │ The prompt defines 7 capabilities:              │
   │  │   1. SQL → execute_sql + generate_chart         │
   │  │   2. Web → web_search + fetch_webpage           │
   │  │   3. General knowledge → no tools               │
   │  │   4. ContentEdge → contentedge_* tools          │
   │  │   5. Self-knowledge → document context          │
   │  │                                                  │
   │  │ And the critical workflow:                      │
   │  │   Person/entity → SQL + Smart Chat + doc URLs   │
   │  └─────────────────────────────────────────────────┘
   │
   │  ┌─────────────────────────────────────────────────┐
   │  │ STEP 5: Build message list                      │
   │  │                                                  │
   │  │ messages = [                                    │
   │  │   SystemMessage(system_prompt),                 │
   │  │   ...chat_history (HumanMessage/AIMessage),     │
   │  │   HumanMessage(question)                        │
   │  │ ]                                               │
   │  └─────────────────────────────────────────────────┘
   │
   │  ┌─────────────────────────────────────────────────┐
   │  │ STEP 6: Create ReAct agent                      │
   │  │                                                  │
   │  │ llm = ChatOllama(temperature=0)                 │
   │  │                                                  │
   │  │ agent = create_react_agent(llm, AGENT_TOOLS)    │
   │  │   Tools: [execute_sql, generate_chart,          │
   │  │           web_search, fetch_webpage,            │
   │  │           contentedge_search,                   │
   │  │           contentedge_smart_chat,               │
   │  │           contentedge_get_document_url]         │
   │  └─────────────────────────────────────────────────┘
   │
   │  ┌─────────────────────────────────────────────────┐
   │  │ STEP 7: Invoke agent (ReAct Loop)               │
   │  │                                                  │
   │  │ result = await agent.ainvoke(messages)           │
   │  │ (see ARCHITECTURE.md §3 — ReAct Loop)           │
   │  └─────────────────────────────────────────────────┘
   │
   │  ┌─────────────────────────────────────────────────┐
   │  │ STEP 8: Extract results                         │
   │  │                                                  │
   │  │ answer:                                         │
   │  │   └─ Last AIMessage with content and no         │
   │  │      tool_calls                                 │
   │  │                                                  │
   │  │ chart_path:                                     │
   │  │   └─ Scans messages for "Chart saved to:"      │
   │  │                                                  │
   │  │ data_preview:                                   │
   │  │   └─ _last_dataframe.head(20).to_dict()        │
   │  └─────────────────────────────────────────────────┘
   │
   ▼
Returns: { answer, chart_path, data_preview }
```

---

## 3. Decision Matrix

| Question Type | Tool(s) Called | Iterations |
|---|---|---|
| Database data | `execute_sql` | 2 |
| Chart request | `execute_sql` → `generate_chart` | 3 |
| External info | `web_search` [→ `fetch_webpage`] | 2–3 |
| Person/entity (SQL + CE) | `execute_sql` → `contentedge_search` → `contentedge_smart_chat` → `contentedge_get_document_url` | 4–6 |
| ContentEdge docs only | `contentedge_smart_chat` | 2–3 |
| About the agent | — (document context) | 1 |
| Conversational | — (direct answer) | 1 |

---

## 4. Response Format

### POST /ask → AskResponse

```json
{
  "answer": "Alice has 3 orders, Bob has 2...",
  "chart_path": "/app/charts_output/bar_a1b2c3d4.png",
  "data_preview": [
    {"name": "Alice", "order_count": 3},
    {"name": "Bob", "order_count": 2}
  ]
}
```

### POST /v1/chat/completions → OpenAI format

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "model": "guille-agent",
  "choices": [{
    "index": 0,
    "message": { "role": "assistant", "content": "..." },
    "finish_reason": "stop"
  }]
}
```

---

## 5. Example Flows

### Example A: "How many orders per customer?"

```
Iter 1 │ LLM → "Need SQL" → execute_sql(SELECT c.name, COUNT(o.id)...)
       │   → DataFrame returned as markdown table
Iter 2 │ LLM → analyzes results → generates text response → END
```

### Example B: "Bar chart of sales by category"

```
Iter 1 │ LLM → execute_sql(SELECT category, SUM...)
       │   → DataFrame saved in _last_dataframe
Iter 2 │ LLM → generate_chart(bar, category, total_sales, ...)
       │   → "Chart saved to: /app/charts_output/bar_xxxx.png"
Iter 3 │ LLM → "Here is the sales chart..." → END
```

### Example C: "Tell me everything about John Smith"

```
Iter 1 │ LLM → execute_sql(SELECT * FROM customers WHERE name ILIKE '%John Smith%')
       │   → customer_id=2, email, orders info
Iter 2 │ LLM → contentedge_smart_chat("Tell me about John Smith", "[]")
       │   → answer + matching_document_ids
Iter 3 │ LLM → contentedge_get_document_url(doc_id_1) → viewer_url_1
Iter 4 │ LLM → contentedge_get_document_url(doc_id_2) → viewer_url_2
Iter 5 │ LLM → combines SQL data + Smart Chat answer + viewer links → END
```

### Example D: "Hello, how are you?"

```
Iter 1 │ LLM → conversational → direct answer → END
```

---

## 6. Files Involved

| File | Role |
|---|---|
| `app/api/routes.py` | Endpoint `/ask`, validation, session injection |
| `app/api/openai_compat.py` | Endpoint `/v1/chat/completions`, OpenAI adapter |
| `app/agent/core.py` | `ask_agent()` — orchestrates the full flow |
| `app/agent/prompts.py` | System prompt with capabilities and rules |
| `app/agent/tools.py` | `execute_sql`, `generate_chart`, `bind_session` |
| `app/agent/web_tools.py` | `web_search`, `fetch_webpage` |
| `app/agent/contentedge_tools.py` | `contentedge_search`, `contentedge_smart_chat`, `contentedge_get_document_url` |
| `app/memory/qdrant_store.py` | `search_similar()` for RAG |
| `app/models/schemas.py` | Pydantic request/response models |
