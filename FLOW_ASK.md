# FLOW_ASK — Procesamiento de una Pregunta (Guille-Agent)

## Resumen

Describe el flujo completo desde que llega una pregunta del usuario
hasta que se devuelve la respuesta. Es el flujo central del agente.

---

## 1. Puntos de entrada

Hay dos endpoints que reciben preguntas. Ambos convergen en `ask_agent()`.

```
┌──────────────────────────┐     ┌─────────────────────────────────┐
│  POST /ask               │     │  POST /v1/chat/completions      │
│  (routes.py)             │     │  (openai_compat.py)             │
│                          │     │                                  │
│  Body: AskRequest        │     │  Body: OpenAIChatRequest        │
│  { question,             │     │  { model, messages[],           │
│    chat_history[] }      │     │    temperature, stream }        │
│                          │     │                                  │
│  Validación Pydantic:    │     │  Procesamiento:                 │
│  - question: 1-5000 ch   │     │  - Ignora role="system"         │
│  - history: max 50 msgs  │     │  - Último role="user" = question│
│  - content: 1-10000 ch   │     │  - role="assistant" → history   │
└────────────┬─────────────┘     └───────────────┬─────────────────┘
             │                                    │
             └────────── ambos llaman ────────────┘
                              │
                              ▼
                    ask_agent(question, session, chat_history)
                              │
                         core.py
```

---

## 2. Flujo de `ask_agent()` — Paso a paso

```
ask_agent(question, session, chat_history)
   │
   │  ┌─────────────────────────────────────────────────┐
   │  │ PASO 1: Bind session                            │
   │  │                                                  │
   │  │ bind_session(session)            ← tools.py     │
   │  │   └─ _session_ref = session                     │
   │  │   Guarda referencia global para que execute_sql  │
   │  │   pueda acceder a la sesión de BD.              │
   │  └─────────────────────────────────────────────────┘
   │
   │  ┌─────────────────────────────────────────────────┐
   │  │ PASO 2: Recuperar contexto de esquema (RAG)     │
   │  │                                                  │
   │  │ _retrieve_schema_context(question, top_k=5)     │
   │  │   ├─ client = get_qdrant_client()               │
   │  │   ├─ embeddings = get_embeddings()  (Ollama)    │
   │  │   ├─ results = search_similar(                  │
   │  │   │      client, embeddings,                    │
   │  │   │      "schema_memory",                       │
   │  │   │      question, top_k=5                      │
   │  │   │  )                                          │
   │  │   │  └─ embed_query(question) → vector 768d     │
   │  │   │  └─ query_points(limit=5) → top 5 chunks   │
   │  │   │                                              │
   │  │   └─ Retorna: texto concatenado de los 5 chunks │
   │  │      (descripciones de tablas, columnas, docs)  │
   │  │                                                  │
   │  │   Fallback: "No schema context available."       │
   │  └─────────────────────────────────────────────────┘
   │
   │  ┌─────────────────────────────────────────────────┐
   │  │ PASO 3: Construir system prompt                 │
   │  │                                                  │
   │  │ SYSTEM_PROMPT.format(                           │
   │  │     schema_context = <resultado del paso 2>,    │
   │  │     max_rows = settings.max_query_rows (1000)   │
   │  │ )                                               │
   │  │                                                  │
   │  │ El prompt define 5 capacidades:                 │
   │  │   1. SQL → execute_sql + generate_chart         │
   │  │   2. Web → web_search + fetch_webpage           │
   │  │   3. Conocimiento general → sin tools           │
   │  │   4. ContentEdge → document context de Qdrant   │
   │  │   5. Auto-conocimiento (Guille-Agent) → doc ctx │
   │  │                                                  │
   │  │ Y reglas de decisión:                           │
   │  │   - Datos en BD → execute_sql                   │
   │  │   - Gráfico → execute_sql + generate_chart      │
   │  │   - Info externa → web_search                   │
   │  │   - ContentEdge → document context              │
   │  │   - Sobre el agente → document context          │
   │  │   - Todo lo demás → responder directo           │
   │  └─────────────────────────────────────────────────┘
   │
   │  ┌─────────────────────────────────────────────────┐
   │  │ PASO 4: Armar lista de mensajes                 │
   │  │                                                  │
   │  │ messages = [                                    │
   │  │   SystemMessage(system_prompt),                 │
   │  │   ...chat_history (como HumanMessage/AIMessage),│
   │  │   HumanMessage(question)                        │
   │  │ ]                                               │
   │  └─────────────────────────────────────────────────┘
   │
   │  ┌─────────────────────────────────────────────────┐
   │  │ PASO 5: Crear agente ReAct                      │
   │  │                                                  │
   │  │ llm = ChatOllama(                               │
   │  │     model = "llama3",                           │
   │  │     temperature = 0,         ← determinístico   │
   │  │     base_url = "http://ollama:11434"            │
   │  │ )                                               │
   │  │                                                  │
   │  │ agent = create_react_agent(                     │
   │  │     llm,                                        │
   │  │     tools = [execute_sql, generate_chart,       │
   │  │              web_search, fetch_webpage]          │
   │  │ )                  ← LangGraph prebuilt         │
   │  └─────────────────────────────────────────────────┘
   │
   │  ┌─────────────────────────────────────────────────┐
   │  │ PASO 6: Invocar agente (Loop ReAct)             │
   │  │                                                  │
   │  │ result = await agent.ainvoke(                   │
   │  │     {"messages": messages}                      │
   │  │ )                                               │
   │  │                                                  │
   │  │ (ver sección 3 — Loop ReAct)                    │
   │  └─────────────────────────────────────────────────┘
   │
   │  ┌─────────────────────────────────────────────────┐
   │  │ PASO 7: Extraer resultados                      │
   │  │                                                  │
   │  │ Del result.messages se extrae:                  │
   │  │                                                  │
   │  │ answer:                                         │
   │  │   └─ Último AIMessage que tiene content         │
   │  │      y NO tiene tool_calls                      │
   │  │                                                  │
   │  │ chart_path:                                     │
   │  │   └─ Busca en mensajes finales texto que        │
   │  │      contenga "Chart saved to:"                 │
   │  │   └─ Extrae el path del gráfico PNG             │
   │  │                                                  │
   │  │ data_preview:                                   │
   │  │   └─ Si _last_dataframe existe (del último SQL) │
   │  │      → df.head(20).to_dict(orient="records")    │
   │  │   └─ Primeras 20 filas como lista de dicts      │
   │  └─────────────────────────────────────────────────┘
   │
   ▼
Retorna: { answer, chart_path, data_preview }
```

---

## 3. Loop ReAct — El corazón del agente

El agente usa el patrón **ReAct** (Reasoning + Acting) implementado
por LangGraph. En cada iteración:

```
                    ┌───────────────────┐
                    │   LLM razona      │
                    │   (Ollama gpt-oss)│
                    └────────┬──────────┘
                             │
                    ¿Necesita una herramienta?
                       │              │
                      SÍ              NO
                       │              │
                       ▼              ▼
               ┌──────────────┐   RESPUESTA FINAL
               │ Ejecuta tool │   (termina el loop)
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
                └─(loop)   ▼
                        RESPUESTA FINAL
```

### Decisiones del LLM según tipo de pregunta

| Tipo de pregunta | Tool(s) llamado(s) | Iteraciones típicas |
|---|---|---|
| Datos en la BD | `execute_sql` | 2 (query + respuesta) |
| Gráfico | `execute_sql` → `generate_chart` | 3 (query + chart + respuesta) |
| Info externa | `web_search` [→ `fetch_webpage`] | 2-3 |
| ContentEdge | — (usa document context de Qdrant) | 1 |
| Sobre el agente | — (usa document context de Qdrant) | 1 |
| Conversacional | — (responde directo) | 1 |

---

## 4. Formato de respuesta por endpoint

### POST /ask → `AskResponse`

```json
{
  "answer": "Alice tiene 3 pedidos, Bob tiene 2...",
  "chart_path": "/app/charts_output/bar_a1b2c3d4.png",
  "data_preview": [
    {"name": "Alice", "order_count": 3},
    {"name": "Bob", "order_count": 2}
  ]
}
```

### POST /v1/chat/completions → `OpenAIChatResponse`

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1710300000,
  "model": "sql-agent",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Alice tiene 3 pedidos...\n\n![chart](/charts/bar_a1b2c3d4.png)"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
}
```

---

## 5. Ejemplos de flujos completos

### Ejemplo A: "¿Cuántos pedidos hay por cliente?"

```
Iter 1 │ LLM → "Necesito SQL" → execute_sql
       │   validate_sql() ✓ → session.execute() → DataFrame
       │   Retorna tabla markdown al LLM
       │
Iter 2 │ LLM → analiza resultados → genera respuesta textual
       │   → FIN
       │
Resultado: { answer: "Alice: 3, Bob: 2...", chart_path: null, data_preview: [...] }
```

### Ejemplo B: "Gráfico de ventas por categoría"

```
Iter 1 │ LLM → execute_sql (SELECT category, SUM...)
       │   → DataFrame guardado en _last_dataframe
       │
Iter 2 │ LLM → generate_chart ({"chart_type":"pie","x":"category",...})
       │   → create_chart() → PNG guardado
       │   → "Chart saved to: /app/charts_output/pie_xxxx.png"
       │
Iter 3 │ LLM → "Aquí está el gráfico de ventas..." → FIN
       │
Resultado: { answer: "...", chart_path: "pie_xxxx.png", data_preview: [...] }
```

### Ejemplo C: "¿Quién ganó el Nobel de Física?"

```
Iter 1 │ LLM → "No está en la BD" → web_search
       │   → DuckDuckGo via Browserless → 3 resultados + contenido
       │
Iter 2 │ LLM → analiza información web → responde → FIN
       │
Resultado: { answer: "El Nobel de Física 2023...", chart_path: null, data_preview: null }
```

### Ejemplo D: "Hola, ¿cómo estás?"

```
Iter 1 │ LLM → "Pregunta conversacional" → responde directo → FIN
       │
Resultado: { answer: "¡Hola! Estoy bien...", chart_path: null, data_preview: null }
```

---

## 6. Archivos involucrados

| Archivo | Rol en el flujo |
|---|---|
| `app/api/routes.py` | Endpoint `/ask`, validación, inyección de sesión |
| `app/api/openai_compat.py` | Endpoint `/v1/chat/completions`, adaptador OpenAI |
| `app/agent/core.py` | `ask_agent()` — orquesta todo el flujo |
| `app/agent/prompts.py` | System prompt con capacidades y reglas |
| `app/agent/tools.py` | `execute_sql`, `generate_chart`, `bind_session` |
| `app/agent/web_tools.py` | `web_search`, `fetch_webpage` |
| `app/memory/qdrant_store.py` | `search_similar()` para RAG |
| `app/models/schemas.py` | Modelos Pydantic de request/response |
