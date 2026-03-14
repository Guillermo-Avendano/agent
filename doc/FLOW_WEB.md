# FLOW_WEB — Web Search

## Overview

Describes the flow of the `web_search` and `fetch_webpage` tools that
allow the agent to search the internet using DuckDuckGo and Browserless
(headless Chromium).

---

## 1. Web Scraping Architecture

```
Agent (tools)
   │
   ▼
web_tools.py
   ├─ web_search(query)      → searches DuckDuckGo
   └─ fetch_webpage(url)     → reads a specific URL
         │
         ▼
   _fetch_via_browserless(url)
         │
         ▼
┌────────────────────────┐
│ Browserless v2.39.0    │
│ (Headless Chromium)    │
│                        │
│ POST /content          │
│ ├─ Navigates to URL    │
│ ├─ Renders JavaScript  │
│ ├─ Waits for body      │
│ └─ Returns HTML        │
└────────────────────────┘
         │
         ▼
   HTML cleanup:
   ├─ Remove <script>, <style>
   ├─ Strip all HTML tags
   └─ Truncate to 4000 chars
         │
         ▼
   Clean text → returned to LLM
```

---

## 2. Tool: `web_search(query)`

```
web_search(query)                          ← agent/web_tools.py
   │
   │  PHASE 1: Search DuckDuckGo
   │
   ├─▸ _search_duckduckgo(query, max_results=3)
   │      ├─ URL: "https://html.duckduckgo.com/html/?q={query}"
   │      ├─▸ _fetch_via_browserless(ddg_url)
   │      │      └─ POST http://browserless:3000/content → HTML
   │      ├─ Extract links and snippets with regex
   │      ├─ Filter out DuckDuckGo internal links
   │      └─ Returns: [{url, snippet}, ...] (max 3)
   │
   │  PHASE 2: Read top result
   │
   ├─▸ _fetch_via_browserless(top_url)
   │      └─ Full page content → cleaned text (max 4000 chars)
   │
   │  PHASE 3: Format output
   │
   └─ Returns:
        "## Web Search Results
         **1. https://...**
         snippet...
         ## Top Result Content
         {page_content}"
```

---

## 3. Tool: `fetch_webpage(url)`

```
fetch_webpage(url)                         ← agent/web_tools.py
   │
   ├─▸ _fetch_via_browserless(url)
   │      ├─ POST http://browserless:3000/content
   │      │    Body: {
   │      │      "url": "...",
   │      │      "waitForSelector": { "selector": "body", "timeout": 10000 },
   │      │      "gotoOptions": { "waitUntil": "domcontentloaded", "timeout": 15000 }
   │      │    }
   │      ├─ Browserless renders the full page
   │      ├─ Clean HTML → plain text
   │      └─ Truncate to 4000 chars
   │
   └─ Returns: extracted text content
```

---

## 4. Browserless Configuration

| Setting | Value | Purpose |
|---|---|---|
| Image | `ghcr.io/browserless/chromium:v2.39.0` | Headless Chromium |
| Port | 3000 (internal only) | Not exposed externally |
| `TIMEOUT` | 30000 ms | Page load timeout |
| `CONCURRENT` | 5 | Max concurrent sessions |
| `QUEUED` | 10 | Max queued requests |
| Launch args | `--no-sandbox`, `--disable-setuid-sandbox` | Docker compatibility |

---

## 5. Step-by-Step Example

### Question: "Who won the Nobel Prize in Physics?"

```
Iter 1 │ LLM → "Not in the database" → web_search("Nobel Prize Physics winner")
       │
       │   _search_duckduckgo("Nobel Prize Physics winner"):
       │     ├─ Browserless → DuckDuckGo HTML page
       │     ├─ Extract 3 result links + snippets
       │     └─ Return [{url: "https://nobelprize.org/...", snippet: "..."}]
       │
       │   _fetch_via_browserless("https://nobelprize.org/..."):
       │     └─ Full page content (4000 chars max)
       │
       │   Returns formatted results to LLM

Iter 2 │ LLM → analyzes web information → generates response → END
```

---

## 6. Error Handling

| Error | Cause | Behavior |
|---|---|---|
| Browserless timeout | Page too slow | Warning logged, empty results |
| No results | DuckDuckGo returned nothing | `"Web search returned no results."` |
| Page fetch failed | URL unreachable | Warning logged, only snippets returned |
| HTTP error | Browserless down | `"Web search error: ..."` |

---

## 7. Files Involved

| File | Key Function | Purpose |
|---|---|---|
| `app/agent/web_tools.py` | `web_search()` | DuckDuckGo search tool |
| `app/agent/web_tools.py` | `fetch_webpage()` | Single URL content extraction |
| `app/agent/web_tools.py` | `_fetch_via_browserless()` | Browserless HTTP client |
| `app/agent/web_tools.py` | `_search_duckduckgo()` | DuckDuckGo HTML parser |
| `app/config.py` | `browserless_url` | Browserless URL config |
