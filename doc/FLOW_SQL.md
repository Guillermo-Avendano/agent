# FLOW_SQL — SQL Query Execution

## Overview

Describes the complete flow from when the agent decides to execute SQL
to when the results return to the LLM as a markdown table.

---

## 1. General Diagram

```
LLM decides to execute SQL
   │
   ▼
execute_sql(query)                    ← agent/tools.py
   │
   ├─ Verify _session_ref exists
   │
   ├─▸ run_query(session, query)      ← db/executor.py
   │      │
   │      ├─▸ validate_sql(query, readonly=True)   ← db/safety.py
   │      │      │
   │      │      ├─ Empty query?                → UnsafeSQLError
   │      │      ├─ Contains blocked pattern?   → UnsafeSQLError
   │      │      ├─ Multiple statements?        → UnsafeSQLError
   │      │      ├─ Write operation (readonly)? → UnsafeSQLError
   │      │      └─ OK → returns cleaned query (without trailing ;)
   │      │
   │      ├─ result = await session.execute(text(cleaned_sql))
   │      ├─ rows = result.fetchmany(MAX_QUERY_ROWS)  ← 1000 default
   │      └─ return pd.DataFrame(rows, columns=result.keys())
   │
   ├─ _last_dataframe = df     ← saved globally for generate_chart
   │
   ├─ return df.to_markdown(index=False)
   │
   └─ LLM receives the markdown table as tool result
```

---

## 2. SQL Validation — `validate_sql()` Detail

```
validate_sql(raw_sql, readonly=True)
   │
   │  CHECK 1: Non-empty query
   ├─ raw_sql.strip() == "" → raise UnsafeSQLError("Empty query.")
   │
   │  CHECK 2: Blocked patterns
   ├─ Searches case-insensitive substrings:
   │
   │   ┌─────────────────────┬───────────────────────────────┐
   │   │ Pattern             │ Reason                        │
   │   ├─────────────────────┼───────────────────────────────┤
   │   │ pg_sleep            │ Denial of Service             │
   │   │ lo_import           │ OS file read                  │
   │   │ lo_export           │ OS file write                 │
   │   │ pg_read_file        │ OS file read                  │
   │   │ pg_read_binary_file │ OS binary file read           │
   │   │ pg_ls_dir           │ OS directory listing          │
   │   │ pg_stat_file        │ OS file info                  │
   │   │ copy                │ COPY FROM/TO                  │
   │   │ \copy               │ psql COPY                     │
   │   └─────────────────────┴───────────────────────────────┘
   │
   │  CHECK 3: Single statement only
   ├─ parsed = sqlparse.parse(cleaned_sql)
   │  len(parsed) > 1 → raise UnsafeSQLError("Only single SQL statements allowed.")
   │
   │  CHECK 4: Readonly mode
   ├─ If readonly=True:
   │    Scans tokens for blocked keywords:
   │    INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE,
   │    CREATE, REPLACE, GRANT, REVOKE, MERGE
   │    → raise UnsafeSQLError("Write operation '{type}' is not allowed in readonly mode.")
   │
   └─ Returns: cleaned query (without trailing ;)
```

---

## 3. Query Execution — `run_query()`

```
run_query(session, raw_sql)
   │
   ├─ cleaned = validate_sql(raw_sql, readonly=settings.sql_readonly)
   │    └─ Raises UnsafeSQLError on failure
   │
   ├─ result = await session.execute(text(cleaned))
   │    └─ SQLAlchemy text() → parameterized execution via asyncpg
   │
   ├─ rows = result.fetchmany(settings.max_query_rows)  ← max 1000
   │
   └─ return pd.DataFrame(rows, columns=result.keys())
```

---

## 4. Error Handling in `execute_sql`

The LLM **always receives a string**, never an exception:

| Outcome | Return Value |
|---|---|
| Success | Markdown table |
| Blocked | `"Blocked: Write operation 'DELETE' is not allowed..."` |
| SQL Error | `"SQL Error: relation 'foo' does not exist"` |

This allows the ReAct agent to **reason about the error** and
potentially correct the query in the next iteration.

---

## 5. Step-by-Step Example

### Question: "How many orders does each customer have?"

```
1. LLM generates:
   SELECT c.name, COUNT(o.id) as total_orders
   FROM customers c LEFT JOIN orders o ON c.id = o.customer_id
   GROUP BY c.name ORDER BY total_orders DESC

2. execute_sql(query):
   2a. validate_sql → ✓ Non-empty ✓ No blocked patterns ✓ Single stmt ✓ SELECT
   2b. run_query → session.execute(text(query)) → 5 rows → DataFrame
   2c. _last_dataframe = df
   2d. Returns markdown table

3. LLM receives table → generates text response
```

---

## 6. Blocked Query Example

```
1. LLM generates: DELETE FROM orders WHERE status = 'cancelled'
2. validate_sql → ✗ Contains DELETE → readonly mode
   → raise UnsafeSQLError
3. execute_sql returns: "Blocked: Write operation 'DELETE' is not allowed in readonly mode."
4. LLM explains to user that data cannot be modified
```

---

## 7. Files Involved

| File | Key Function | Purpose |
|---|---|---|
| `app/agent/tools.py` | `execute_sql()` | Agent tool, gateway |
| `app/db/executor.py` | `run_query()` | Validates + executes + returns DataFrame |
| `app/db/safety.py` | `validate_sql()` | SQL security validation |
| `app/db/connection.py` | `get_session()` | Provides the async session |
| `app/config.py` | `sql_readonly`, `max_query_rows` | Configuration |

---

## 8. Related Tests

```
tests/test_safety.py
   ├─ ✅ Valid SELECT queries pass
   ├─ ❌ INSERT/UPDATE/DELETE/DROP blocked in readonly
   ├─ ❌ Multiple statements blocked
   ├─ ❌ Dangerous functions (pg_sleep, pg_read_file) blocked
   └─ ✅ Writes allowed when readonly=False
```
