# FLOW_SQL — Ejecución de Consultas SQL

## Resumen

Describe el flujo completo desde que el agente decide ejecutar SQL
hasta que los resultados vuelven al LLM como texto markdown.

---

## 1. Diagrama general

```
LLM decide ejecutar SQL
   │
   ▼
execute_sql(query)                    ← agent/tools.py
   │
   ├─ Verifica que _session_ref exista
   │
   ├─▸ run_query(session, query)      ← db/executor.py
   │      │
   │      ├─▸ validate_sql(query, readonly=True)   ← db/safety.py
   │      │      │
   │      │      ├─ ¿Query vacío?               → UnsafeSQLError
   │      │      ├─ ¿Contiene patrón bloqueado? → UnsafeSQLError
   │      │      ├─ ¿Múltiples statements?      → UnsafeSQLError
   │      │      ├─ ¿Es escritura (readonly)?   → UnsafeSQLError
   │      │      └─ OK → retorna query limpio (sin ; final)
   │      │
   │      ├─ result = await session.execute(text(cleaned_sql))
   │      ├─ rows = result.fetchmany(MAX_QUERY_ROWS)  ← 1000 por defecto
   │      └─ return pd.DataFrame(rows, columns=result.keys())
   │
   ├─ _last_dataframe = df     ← guardado global para generate_chart
   │
   ├─ return df.to_markdown(index=False)
   │
   └─ El LLM recibe la tabla markdown como resultado del tool
```

---

## 2. Validación SQL — `validate_sql()` detalle

```
validate_sql(raw_sql, readonly=True)
   │
   │  ═══════════════════════════════
   │  CHECK 1: Query no vacío
   │  ═══════════════════════════════
   │
   ├─ raw_sql.strip() == "" ?
   │    → raise UnsafeSQLError("Empty query.")
   │
   │  ═══════════════════════════════
   │  CHECK 2: Patrones bloqueados
   │  ═══════════════════════════════
   │
   ├─ Busca substrings (case-insensitive) en el query:
   │
   │   PATRONES BLOQUEADOS:
   │   ┌─────────────────────┬───────────────────────────────┐
   │   │ Patrón              │ Razón                         │
   │   ├─────────────────────┼───────────────────────────────┤
   │   │ pg_sleep            │ Denial of Service             │
   │   │ lo_import           │ Lectura de archivos del SO    │
   │   │ lo_export           │ Escritura de archivos del SO  │
   │   │ pg_read_file        │ Lectura de archivos del SO    │
   │   │ pg_read_binary_file │ Lectura binaria del SO        │
   │   │ pg_ls_dir           │ Listado de directorios del SO │
   │   │ pg_stat_file        │ Info de archivos del SO       │
   │   │ copy                │ COPY FROM/TO                  │
   │   │ \copy               │ psql COPY                     │
   │   └─────────────────────┴───────────────────────────────┘
   │
   │    → raise UnsafeSQLError("Query contains blocked pattern: {p}")
   │
   │  ═══════════════════════════════
   │  CHECK 3: Un solo statement
   │  ═══════════════════════════════
   │
   ├─ parsed = sqlparse.parse(cleaned_sql)
   │  len(parsed) > 1 ?
   │    → raise UnsafeSQLError("Only single SQL statements allowed.")
   │
   │  ═══════════════════════════════
   │  CHECK 4: Modo readonly
   │  ═══════════════════════════════
   │
   ├─ Si readonly=True:
   │    ├─ stmt.get_type() → tipo del statement
   │    ├─ Escanea tokens buscando keywords DML/DDL:
   │    │
   │    │   KEYWORDS BLOQUEADAS:
   │    │   INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE,
   │    │   CREATE, REPLACE, GRANT, REVOKE, MERGE
   │    │
   │    └─ Si encuentra alguna:
   │         → raise UnsafeSQLError("Write operation '{type}' is not allowed in readonly mode.")
   │
   │  ═══════════════════════════════
   │  RESULTADO
   │  ═══════════════════════════════
   │
   └─ Retorna: query limpio (sin ; al final)
```

---

## 3. Ejecución del query — `run_query()` detalle

```
run_query(session, raw_sql)
   │
   ├─ cleaned = validate_sql(raw_sql, readonly=settings.sql_readonly)
   │    └─ Si falla → UnsafeSQLError se propaga
   │
   ├─ result = await session.execute(text(cleaned))
   │    │
   │    │  text() es de SQLAlchemy:
   │    │  - Marca el SQL como texto literal
   │    │  - Se ejecuta a través del pool async (asyncpg)
   │    │  - La sesión viene del get_session() dependency
   │    │
   │    └─ Si falla → excepción SQLAlchemy (capturada arriba)
   │
   ├─ rows = result.fetchmany(settings.max_query_rows)
   │    └─ Máximo 1000 filas (configurable via MAX_QUERY_ROWS)
   │
   └─ return pd.DataFrame(rows, columns=result.keys())
```

---

## 4. Manejo de errores en `execute_sql`

```
execute_sql(query)
   │
   ├─ try:
   │    └─ run_query(session, query) → DataFrame
   │
   ├─ except UnsafeSQLError as e:
   │    └─ return f"Blocked: {e}"
   │       (el LLM recibe esto y puede reformular o explicar al usuario)
   │
   └─ except Exception as e:
        └─ return f"SQL Error: {e}"
           (error de conexión, tabla inexistente, error de sintaxis, etc.)
```

El LLM **siempre recibe un string**, nunca una excepción:
- Éxito → tabla markdown
- Bloqueado → `"Blocked: ..."`
- Error → `"SQL Error: ..."`

Esto permite al agente ReAct **razonar sobre el error** y potencialmente
corregir el query en la siguiente iteración.

---

## 5. Ejemplo paso a paso

### Pregunta: "¿Cuántos pedidos tiene cada cliente?"

```
1. LLM genera:
   query = "SELECT c.name, COUNT(o.id) as total_orders
            FROM customers c
            LEFT JOIN orders o ON c.id = o.customer_id
            GROUP BY c.name
            ORDER BY total_orders DESC"

2. execute_sql(query):

   2a. validate_sql(query, readonly=True):
       ✓ No vacío
       ✓ Sin patrones bloqueados (pg_sleep, etc.)
       ✓ Un solo statement
       ✓ Es SELECT (no INSERT/UPDATE/DELETE)
       → retorna query limpio

   2b. run_query(session, cleaned):
       → session.execute(text(query))
       → fetchmany(1000) → 5 filas
       → DataFrame:
           name    | total_orders
           --------|-------------
           Alice   | 3
           Bob     | 2
           Carmen  | 2
           David   | 1
           Elena   | 0

   2c. _last_dataframe = df  (guardado para posible chart)

   2d. Retorna:
       "| name   | total_orders |
        |--------|------------- |
        | Alice  | 3            |
        | Bob    | 2            |
        | Carmen | 2            |
        | David  | 1            |
        | Elena  | 0            |"

3. LLM recibe la tabla → genera respuesta textual
```

---

## 6. Ejemplo de query bloqueado

```
1. LLM genera (erróneamente):
   query = "DELETE FROM orders WHERE status = 'cancelled'"

2. execute_sql(query):

   2a. validate_sql(query, readonly=True):
       ✓ No vacío
       ✓ Sin patrones bloqueados
       ✓ Un solo statement
       ✗ Contiene DELETE → modo readonly
       → raise UnsafeSQLError("Write operation 'DELETE' is not allowed in readonly mode.")

   2b. except UnsafeSQLError:
       → return "Blocked: Write operation 'DELETE' is not allowed in readonly mode."

3. LLM recibe "Blocked: ..." → explica al usuario que no puede modificar datos
```

---

## 7. Archivos involucrados

| Archivo | Función clave | Propósito |
|---|---|---|
| `app/agent/tools.py` | `execute_sql()` | Tool del agente, gateway |
| `app/db/executor.py` | `run_query()` | Valida + ejecuta + retorna DataFrame |
| `app/db/safety.py` | `validate_sql()` | Validación de seguridad SQL |
| `app/db/safety.py` | `UnsafeSQLError` | Excepción personalizada |
| `app/db/connection.py` | `get_session()` | Provee la sesión async |
| `app/config.py` | `SQL_READONLY`, `MAX_QUERY_ROWS` | Configuración |

---

## 8. Tests relacionados

```
tests/test_safety.py
   ├─ ✅ SELECT queries válidos pasan
   ├─ ❌ INSERT/UPDATE/DELETE/DROP bloqueados en readonly
   ├─ ❌ Múltiples statements bloqueados
   ├─ ❌ Funciones peligrosas (pg_sleep, pg_read_file) bloqueadas
   └─ ✅ Escritura permitida cuando readonly=False
```
