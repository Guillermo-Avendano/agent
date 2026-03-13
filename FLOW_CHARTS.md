# FLOW_CHARTS — Generación de Gráficos

## Resumen

Describe el flujo desde que el agente decide crear un gráfico
hasta que el PNG se guarda y se sirve al cliente.

---

## 1. Diagrama general

```
LLM decide generar un gráfico
   │
   │  (Previamente ejecutó execute_sql → _last_dataframe tiene datos)
   │
   ▼
generate_chart(spec_json)                     ← agent/tools.py
   │
   ├─ Verifica que _last_dataframe no sea None/vacío
   │
   ├─ Parsea spec_json:
   │    ├─ json.loads(spec_json)
   │    └─ Fallback: regex para extraer campos si JSON inválido
   │
   ├─ Valida que las columnas x, y existan en el DataFrame
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
   LLM recibe la ruta → incluye en la respuesta al usuario
```

---

## 2. Formato del spec JSON

El LLM genera un JSON con esta estructura:

```json
{
  "chart_type": "bar|line|pie|scatter|histogram",
  "x": "nombre_columna_eje_x",
  "y": "nombre_columna_eje_y",
  "title": "Título del Gráfico"
}
```

| Campo | Requerido | Descripción |
|---|---|---|
| `chart_type` | Sí | Tipo de gráfico |
| `x` | Sí | Columna para el eje X (o labels en pie) |
| `y` | Sí (excepto histogram) | Columna para el eje Y (o valores en pie) |
| `title` | Sí | Título del gráfico |

---

## 3. Tipos de gráficos soportados

```
charts/generator.py usa un patrón de registro con decorador:

   @_register("bar")      → _CHART_BUILDERS["bar"]     = _bar
   @_register("line")     → _CHART_BUILDERS["line"]    = _line
   @_register("pie")      → _CHART_BUILDERS["pie"]     = _pie
   @_register("scatter")  → _CHART_BUILDERS["scatter"] = _scatter
   @_register("histogram")→ _CHART_BUILDERS["histogram"]= _histogram
```

### Detalle por tipo

```
BAR:
   df.plot.bar(x=x, y=y, ax=ax)
   ax.set_title(title)
   Rota labels del eje X para legibilidad

LINE:
   df.plot.line(x=x, y=y, marker="o", ax=ax)
   ax.set_title(title)

PIE:
   ax.pie(df[y], labels=df[x], autopct="%1.1f%%")
   ax.set_title(title)

SCATTER:
   df.plot.scatter(x=x, y=y, ax=ax)
   ax.set_title(title)

HISTOGRAM:
   df[x].plot.hist(bins=20, ax=ax)
   ax.set_title(title)
   (no usa columna Y)
```

---

## 4. Generación del archivo PNG

```
create_chart(df, chart_type, x, y, title)
   │
   ├─ matplotlib.use("Agg")     ← backend no interactivo (servidor)
   │
   ├─ builder = _CHART_BUILDERS.get(chart_type)
   │    └─ Si no existe → raise ValueError("Unsupported chart type")
   │
   ├─ fig, ax = plt.subplots(figsize=(10, 6))
   │
   ├─ builder(df, x, y, title, ax)
   │    └─ Dibuja el gráfico en el axes
   │
   ├─ plt.tight_layout()
   │
   ├─ filename = f"{chart_type}_{uuid.uuid4().hex[:8]}.png"
   │    └─ Ejemplo: "pie_a1b2c3d4.png"
   │
   ├─ filepath = /app/charts_output/{filename}
   │
   ├─ fig.savefig(filepath, dpi=150, bbox_inches="tight")
   │    └─ 150 DPI, recortando márgenes
   │
   ├─ plt.close(fig)
   │    └─ Libera memoria (importante en servidor)
   │
   └─ return filepath
```

---

## 5. Servir el gráfico al cliente

```
GET /charts/{filename}                    ← api/routes.py
   │
   ├─ Sanitización:
   │    path = Path(filename).name
   │    └─ Previene path traversal (../../etc/passwd)
   │
   ├─ filepath = /app/charts_output/{sanitized_name}
   │
   ├─ ¿Existe el archivo?
   │    NO → 404 Not Found
   │    SÍ → FileResponse(filepath, media_type="image/png")
   │
   └─ El cliente/frontend muestra la imagen
```

### Flujo completo con AnythingLLM

```
AnythingLLM
   │
   ├─ POST /v1/chat/completions → ask_agent()
   │    └─ answer incluye: "Chart saved to: /app/charts_output/pie_xxxx.png"
   │
   ├─ openai_compat.py detecta chart_path
   │    └─ Agrega al content: "\n\n![chart](/charts/pie_xxxx.png)"
   │
   └─ AnythingLLM renderiza markdown
        └─ <img src="/charts/pie_xxxx.png"> → GET /charts/pie_xxxx.png
```

---

## 6. Ejemplo paso a paso

### Pregunta: "Muéstrame un gráfico de barras de ventas por categoría"

```
Iteración 1 del ReAct:
   │
   ├─ LLM → "Primero necesito los datos" → execute_sql
   │   query = "SELECT p.category, SUM(oi.quantity * oi.unit_price) as total_sales
   │            FROM products p
   │            JOIN order_items oi ON p.id = oi.product_id
   │            GROUP BY p.category"
   │
   │   → DataFrame guardado en _last_dataframe:
   │       category    | total_sales
   │       ------------|------------
   │       Electronics | 15420.00
   │       Furniture   | 8750.00

Iteración 2 del ReAct:
   │
   ├─ LLM → "Ahora genero el gráfico" → generate_chart
   │   spec = '{"chart_type":"bar","x":"category","y":"total_sales","title":"Ventas por Categoría"}'
   │
   │   generate_chart(spec):
   │     1. Parse JSON → chart_type="bar", x="category", y="total_sales"
   │     2. Columnas "category" y "total_sales" existen en df ✓
   │     3. create_chart(df, "bar", "category", "total_sales", "Ventas por Categoría")
   │          ├─ fig, ax = plt.subplots(10, 6)
   │          ├─ df.plot.bar(x="category", y="total_sales", ax=ax)
   │          ├─ filename = "bar_f7e2a1c9.png"
   │          ├─ savefig → /app/charts_output/bar_f7e2a1c9.png
   │          └─ return "/app/charts_output/bar_f7e2a1c9.png"
   │
   │     → return "Chart saved to: /app/charts_output/bar_f7e2a1c9.png"

Iteración 3 del ReAct:
   │
   └─ LLM → "Aquí tienes el gráfico de ventas por categoría..." → FIN

Resultado:
   {
     answer: "Aquí tienes el gráfico de ventas por categoría...",
     chart_path: "/app/charts_output/bar_f7e2a1c9.png",
     data_preview: [{"category":"Electronics","total_sales":15420}, ...]
   }
```

---

## 7. Manejo de errores

| Error | Causa | Resultado para el LLM |
|---|---|---|
| `_last_dataframe` es None | No se ejecutó SQL previamente | `"No data available. Run execute_sql first."` |
| JSON inválido | LLM generó JSON malformado | Intenta fallback regex, o error |
| Columna no existe | x o y no está en el DataFrame | `"Column '{col}' not found in data."` |
| Tipo no soportado | chart_type desconocido | `ValueError("Unsupported chart type")` |

---

## 8. Archivos involucrados

| Archivo | Función clave | Propósito |
|---|---|---|
| `app/agent/tools.py` | `generate_chart()` | Tool del agente, parsea spec |
| `app/charts/generator.py` | `create_chart()` | Genera PNG con Matplotlib |
| `app/charts/generator.py` | `_bar()`, `_line()`, `_pie()`, etc. | Builders por tipo |
| `app/api/routes.py` | `get_chart()` | Sirve PNGs via HTTP |
| `app/api/openai_compat.py` | `chat_completions()` | Agrega link del chart en respuesta |

---

## 9. Tests relacionados

```
tests/test_charts.py
   ├─ Verifica generación de cada tipo de gráfico
   ├─ Comprueba que el PNG se crea en disco
   └─ Valida manejo de tipos no soportados
```
