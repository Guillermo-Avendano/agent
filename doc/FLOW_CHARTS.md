# FLOW_CHARTS — Chart Generation

## Overview

Describes the flow from when the agent decides to create a chart
to when the PNG is saved and served to the client.

---

## 1. General Diagram

```
LLM decides to generate a chart
   │
   │  (Previously executed execute_sql → _last_dataframe has data)
   │
   ▼
generate_chart(chart_type, x, y, title)     ← agent/tools.py
   │
   ├─ Verify _last_dataframe is not None/empty
   ├─ Validate columns x, y exist in the DataFrame
   │
   ├─▸ create_chart(df, chart_type, x, y, title)   ← charts/generator.py
   │      │
   │      ├─ builder = _CHART_BUILDERS[chart_type]
   │      ├─ fig, ax = plt.subplots(figsize=(10, 6))
   │      ├─ builder(df, x, y, title, ax)
   │      ├─ plt.tight_layout()
   │      ├─ filename = f"{chart_type}_{uuid[:8]}.png"
   │      ├─ fig.savefig(filepath, dpi=150, bbox_inches="tight")
   │      ├─ plt.close(fig)
   │      └─ return filepath  → /app/charts_output/{filename}
   │
   └─ return f"Chart saved to: {filepath}"
         │
         ▼
   LLM receives the path → includes in response to user
```

---

## 2. Supported Chart Types

| Type | Method | Notes |
|---|---|---|
| `bar` | `df.plot.bar(x, y)` | Rotated X-axis labels |
| `line` | `df.plot.line(x, y, marker="o")` | With markers |
| `pie` | `ax.pie(df[y], labels=df[x])` | Percentage labels |
| `scatter` | `df.plot.scatter(x, y)` | Point cloud |
| `histogram` | `df[x].plot.hist(bins=20)` | Does not use Y column |

---

## 3. PNG File Generation

```
create_chart(df, chart_type, x, y, title)
   │
   ├─ matplotlib.use("Agg")     ← non-interactive backend (server)
   ├─ builder = _CHART_BUILDERS.get(chart_type)
   │    └─ Unknown type → raise ValueError("Unsupported chart type")
   ├─ fig, ax = plt.subplots(figsize=(10, 6))
   ├─ builder(df, x, y, title, ax)
   ├─ plt.tight_layout()
   ├─ filename = f"{chart_type}_{uuid4().hex[:8]}.png"
   ├─ fig.savefig(filepath, dpi=150, bbox_inches="tight")
   ├─ plt.close(fig)             ← frees memory (important on server)
   └─ return filepath
```

---

## 4. Serving Charts to the Client

```
GET /charts/{filename}                    ← api/routes.py
   │
   ├─ Sanitization: path = Path(filename).name
   │    └─ Prevents path traversal (../../etc/passwd)
   ├─ filepath = /app/charts_output/{sanitized_name}
   ├─ File exists? NO → 404 Not Found
   │               YES → FileResponse(filepath, media_type="image/png")
   └─ Client displays the image
```

### Flow with AnythingLLM

```
AnythingLLM
   ├─ POST /v1/chat/completions → ask_agent()
   │    └─ answer includes chart_path
   ├─ openai_compat.py adds: "\n\n![chart](/charts/pie_xxxx.png)"
   └─ AnythingLLM renders markdown → <img src="/charts/pie_xxxx.png">
```

---

## 5. Step-by-Step Example

### Question: "Show me a bar chart of sales by category"

```
Iter 1 │ LLM → execute_sql(SELECT category, SUM(quantity*unit_price) as total...)
       │   → DataFrame saved in _last_dataframe

Iter 2 │ LLM → generate_chart("bar", "category", "total_sales", "Sales by Category")
       │   create_chart():
       │     ├─ fig, ax = plt.subplots(10, 6)
       │     ├─ df.plot.bar(x="category", y="total_sales", ax=ax)
       │     ├─ filename = "bar_f7e2a1c9.png"
       │     └─ savefig → /app/charts_output/bar_f7e2a1c9.png
       │   → "Chart saved to: /app/charts_output/bar_f7e2a1c9.png"

Iter 3 │ LLM → "Here is the sales chart by category..." → END

Result: { answer: "...", chart_path: "bar_f7e2a1c9.png", data_preview: [...] }
```

---

## 6. Error Handling

| Error | Cause | Result for LLM |
|---|---|---|
| `_last_dataframe` is None | No SQL executed first | `"No data available. Run execute_sql first."` |
| Column not found | x or y not in DataFrame | `"Column '{col}' not found. Available: [...]"` |
| Unsupported type | Unknown chart_type | `ValueError("Unsupported chart type")` |

---

## 7. Files Involved

| File | Key Function | Purpose |
|---|---|---|
| `app/agent/tools.py` | `generate_chart()` | Agent tool |
| `app/charts/generator.py` | `create_chart()` | Generates PNG with Matplotlib |
| `app/charts/generator.py` | `_bar()`, `_line()`, `_pie()`, etc. | Builders per type |
| `app/api/routes.py` | `get_chart()` | Serves PNGs via HTTP |
| `app/api/openai_compat.py` | `chat_completions()` | Adds chart link in response |

---

## 8. Related Tests

```
tests/test_charts.py
   ├─ Verifies generation of each chart type
   ├─ Checks that PNG file is created on disk
   └─ Validates handling of unsupported types
```
