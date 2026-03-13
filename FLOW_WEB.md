# FLOW_WEB — Búsqueda Web

## Resumen

Describe el flujo de los tools `web_search` y `fetch_webpage` que
permiten al agente buscar información en internet usando DuckDuckGo
y Browserless (Chromium headless).

---

## 1. Arquitectura de web scraping

```
Agente (tools)
   │
   ▼
web_tools.py
   │
   ├─ web_search(query)      → busca en DuckDuckGo
   └─ fetch_webpage(url)     → lee una URL específica
         │
         ▼
   _fetch_via_browserless(url)
         │
         ▼
┌────────────────────────┐
│ Browserless v2.39.0    │
│ (Chromium headless)    │
│                        │
│ POST /content          │
│ ├─ Navega a la URL     │
│ ├─ Renderiza JS        │
│ ├─ Espera body cargado │
│ └─ Devuelve HTML       │
└────────────────────────┘
         │
         ▼
   Limpieza de HTML:
   ├─ Elimina <script>, <style>
   ├─ Strip de todas las tags HTML
   └─ Trunca a 4000 caracteres
         │
         ▼
   Texto limpio → retorna al LLM
```

---

## 2. Tool: `web_search(query)` — Flujo detallado

```
web_search(query: str)                         ← agent/web_tools.py
   │
   │  ═══════════════════════════════
   │  FASE 1: Buscar en DuckDuckGo
   │  ═══════════════════════════════
   │
   ├─▸ _search_duckduckgo(query, max_results=3)
   │      │
   │      ├─ Construye URL:
   │      │    "https://html.duckduckgo.com/html/?q={query_encoded}"
   │      │
   │      ├─▸ _fetch_via_browserless(ddg_url)
   │      │      ├─ POST http://browserless:3000/content
   │      │      │    Body: {
   │      │      │      "url": "https://html.duckduckgo.com/html/?q=...",
   │      │      │      "waitForSelector": "body",
   │      │      │      "gotoOptions": {
   │      │      │        "waitUntil": "domcontentloaded",
   │      │      │        "timeout": 15000
   │      │      │      }
   │      │      │    }
   │      │      │
   │      │      ├─ Browserless:
   │      │      │    ├─ Abre Chromium
   │      │      │    ├─ Navega a DuckDuckGo
   │      │      │    ├─ Espera DOM cargado
   │      │      │    └─ Devuelve HTML de la página
   │      │      │
   │      │      └─ Limpia HTML → texto plano
   │      │
   │      ├─ Extrae links y snippets con regex del HTML
   │      ├─ Filtra links internos de DuckDuckGo
   │      └─ Retorna: [ {url, snippet}, {url, snippet}, {url, snippet} ]
   │                     (máximo 3 resultados)
   │
   │  ═══════════════════════════════
   │  FASE 2: Leer primer resultado
   │  ═══════════════════════════════
   │
   ├─ top_url = results[0].url
   │
   ├─▸ _fetch_via_browserless(top_url)
   │      ├─ POST http://browserless:3000/content
   │      │    Body: { url: top_url, ... }
   │      ├─ Browserless renderiza la página completa
   │      ├─ Limpia HTML → texto plano
   │      └─ Trunca a máximo 4000 caracteres
   │
   │  ═══════════════════════════════
   │  FASE 3: Componer respuesta
   │  ═══════════════════════════════
   │
   └─ Retorna string formateado:
        "## Web Search Results
         1. {url_1}
            {snippet_1}
         2. {url_2}
            {snippet_2}
         3. {url_3}
            {snippet_3}

         ## Top Result Content
         {contenido_completo_del_primer_resultado}"
```

---

## 3. Tool: `fetch_webpage(url)` — Flujo detallado

```
fetch_webpage(url: str)                        ← agent/web_tools.py
   │
   ├─▸ _fetch_via_browserless(url)
   │      ├─ POST http://browserless:3000/content
   │      │    Body: {
   │      │      "url": url,
   │      │      "waitForSelector": "body",
   │      │      "gotoOptions": {
   │      │        "waitUntil": "domcontentloaded",
   │      │        "timeout": 15000
   │      │      }
   │      │    }
   │      │
   │      ├─ Browserless renderiza la página
   │      ├─ Limpia: elimina <script>, <style>, strip tags
   │      └─ Trunca a 4000 caracteres
   │
   └─ Retorna: texto limpio de la página
        │
        └─ Error: f"Failed to fetch page: {e}"
```

### ¿Cuándo se usa `fetch_webpage` vs `web_search`?

| Tool | Uso |
|---|---|
| `web_search` | Cuando no se sabe la URL — busca primero en DuckDuckGo |
| `fetch_webpage` | Cuando ya se tiene la URL (el LLM la vio en resultados anteriores) |

---

## 4. Función auxiliar: `_fetch_via_browserless(url)`

```
_fetch_via_browserless(url: str) → str
   │
   ├─ POST {BROWSERLESS_URL}/content
   │    Headers: Content-Type: application/json
   │    Body: {
   │      "url": url,
   │      "waitForSelector": "body",
   │      "gotoOptions": {
   │        "waitUntil": "domcontentloaded",
   │        "timeout": 15000
   │      }
   │    }
   │
   ├─ Respuesta: HTML renderizado de la página
   │
   ├─ Limpieza del HTML:
   │    ├─ Elimina bloques <script>...</script>
   │    ├─ Elimina bloques <style>...</style>
   │    ├─ Strip de todas las tags HTML restantes
   │    ├─ Colapsa whitespace excesivo
   │    └─ Trunca a 4000 caracteres
   │
   └─ Retorna: texto plano limpio
```

### Configuración de Browserless

```
docker-compose.yml:

  browserless:
    image: ghcr.io/browserless/chromium:v2.39.0
    environment:
      TIMEOUT: 30000          ← timeout por página (ms)
      CONCURRENT: 5           ← máximo 5 páginas simultáneas
      QUEUED: 10              ← cola de espera
      DEFAULT_LAUNCH_ARGS: '["--no-sandbox","--disable-setuid-sandbox"]'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/json/version"]
```

---

## 5. Ejemplo paso a paso

### Pregunta: "¿Cuántos habitantes tiene Japón?"

```
Iteración 1 del ReAct:
   │
   ├─ LLM → "Esto no está en la BD, voy a buscar en la web"
   │
   ├─ web_search("¿Cuántos habitantes tiene Japón?")
   │
   │   Fase 1 - DuckDuckGo:
   │     URL: https://html.duckduckgo.com/html/?q=%C2%BFCu%C3%A1ntos+habitantes+tiene+Jap%C3%B3n%3F
   │     Browserless renderiza → extrae 3 resultados:
   │       1. https://en.wikipedia.org/wiki/Japan → "Japan population..."
   │       2. https://worldpopulationreview.com/... → "Japan: 125 million..."
   │       3. https://www.worldometers.info/... → "Japan Population Live..."
   │
   │   Fase 2 - Leer primer resultado:
   │     Browserless renderiza Wikipedia → limpia HTML → 4000 chars
   │     "Japan is an island country... population of approximately 125 million..."
   │
   │   Retorna al LLM:
   │     "## Web Search Results
   │      1. https://en.wikipedia.org/wiki/Japan
   │         Japan population...
   │      2. https://worldpopulationreview.com/...
   │         Japan: 125 million...
   │      3. https://www.worldometers.info/...
   │         Japan Population Live...
   │
   │      ## Top Result Content
   │      Japan is an island country... population of approximately 125 million..."

Iteración 2 del ReAct:
   │
   └─ LLM → analiza resultados web
      → "Japón tiene aproximadamente 125 millones de habitantes..."
      → FIN

Resultado:
   {
     answer: "Japón tiene aproximadamente 125 millones de habitantes...",
     chart_path: null,
     data_preview: null
   }
```

---

## 6. Manejo de errores

```
web_search(query):
   │
   ├─ Si _search_duckduckgo falla:
   │    └─ log.warning("web_search.search_failed")
   │    └─ return "Error performing web search: {e}"
   │
   ├─ Si fetch del primer resultado falla:
   │    └─ log.warning("web_search.fetch_failed")
   │    └─ Retorna solo los snippets (sin contenido completo)
   │
   └─ Si no hay resultados:
        └─ return "No results found."

fetch_webpage(url):
   │
   └─ Si _fetch_via_browserless falla:
        └─ return f"Failed to fetch page: {e}"
```

---

## 7. Archivos involucrados

| Archivo | Función clave | Propósito |
|---|---|---|
| `app/agent/web_tools.py` | `web_search()` | Tool: busca en DuckDuckGo + lee primer resultado |
| `app/agent/web_tools.py` | `fetch_webpage()` | Tool: lee una URL específica |
| `app/agent/web_tools.py` | `_search_duckduckgo()` | Busca y parsea resultados de DDG |
| `app/agent/web_tools.py` | `_fetch_via_browserless()` | Renderiza URL via Chromium headless |
| `app/config.py` | `BROWSERLESS_URL` | URL del servicio Browserless |
