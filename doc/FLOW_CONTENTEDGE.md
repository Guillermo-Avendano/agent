# FLOW_CONTENTEDGE — ContentEdge MCP Integration

## Overview

Describes the ContentEdge MCP server, its 7 tools, how the agent connects
to it via the standard MCP protocol, and the key workflows: Smart Chat,
document search, and document viewer URLs.

---

## 1. MCP Server Architecture

The ContentEdge MCP server is a **standard-compliant MCP server** built
with `FastMCP` and SSE transport. It can be consumed by:

- **Guille-Agent** (via the official MCP Python SDK)
- **Claude Desktop** (via SSE URL)
- **Cursor** (via SSE URL)
- **Any MCP-compatible client**

```
┌──────────────────┐     MCP Standard Protocol     ┌─────────────────────────┐
│   agent-api      │ ────── SSE (port 8001) ──────▸ │   contentedge-mcp       │
│   (LangChain)    │                                │   (FastMCP server)      │
│                  │     ClientSession               │                         │
│  contentedge_    │     + sse_client                │   7 MCP tools           │
│  tools.py        │     (official SDK)              │                         │
└──────────────────┘                                │                         │
                                                    │                         │
┌──────────────────┐                                │                         │
│ Claude Desktop   │ ────── SSE (port 8001) ──────▸ │                         │
│ Cursor           │                                │                         │
│ Any MCP Client   │                                │                         │
└──────────────────┘                                └──────────┬──────────────┘
                                                               │
                                                               ▼
                                                    ┌─────────────────────┐
                                                    │ Content Repository  │
                                                    │ (Mobius REST API)   │
                                                    │  /conversations     │
                                                    │  /searches          │
                                                    │  /hostviewer        │
                                                    │  /archive-write     │
                                                    └─────────────────────┘
```

---

## 2. MCP Tools

All tools verify the repository is active before execution.

| MCP Tool | Mobius Endpoint | Description |
|---|---|---|
| `list_content_classes` | Admin REST `/reports` | List content classes (record types) |
| `list_indexes` | Admin REST `/topicgroups` + `/topics` | List indexes and index groups |
| `search_documents` | `POST /searches` | Search documents by index values |
| `archive_documents` | `POST /archive-write` | Archive files (PDF, TXT, JPG, PNG) with metadata |
| `retrieve_document` | `POST /hostviewer` | Get a Mobius View browser URL for a document |
| `get_versions` | Navigation API `/folders` | Get document versions by date range |
| `smart_chat` | `POST /conversations` | Ask questions to Smart Chat AI |

---

## 3. Smart Chat — Internal Flow

Smart Chat enables natural language Q&A against documents in the
Content Repository. It uses the Mobius Conversations API.

```
smart_chat(question, document_ids, conversation_id)
   │
   ▼
ContentSmartChat.smart_chat()            ← lib/content_smart_chat.py
   │
   ├─ URL: {repo_url}/conversations
   │
   ├─ Headers:
   │    Content-Type: application/vnd.conversation-request.v1+json
   │    Accept: application/vnd.conversation-response.v1+json
   │    Authorization-Repo-{repo_id}: Basic {credentials}
   │
   ├─ Payload:
   │    {
   │      "userQuery": "Who is the loan applicant?",
   │      "documentIDs": ["objectId1", "objectId2"],
   │      "context": { "conversation": "prev_conversation_id" },
   │      "repositories": [{ "id": "repo_uuid" }]
   │    }
   │
   ├─ POST → Content Repository
   │
   └─ Response parsed into SmartChatResponse:
        ├─ answer: AI-generated text answer
        ├─ conversation: conversation ID for follow-ups
        └─ object_ids: list of matching document objectIds
```

### Two Modes

1. **Repository-wide** — `document_ids = []`
   Smart Chat searches ALL documents in the repository.

2. **Document-scoped** — `document_ids = ["id1", "id2", ...]`
   Smart Chat only analyzes the specified documents.

### Conversation Continuity

Each response includes a `conversation_id`. Pass it in subsequent
calls to maintain multi-turn context:

```
Call 1: smart_chat("Who is the applicant?", docs, "")
  → answer + conversation_id = "abc123"

Call 2: smart_chat("What are the details?", docs, "abc123")
  → continues the conversation
```

---

## 4. Document Viewer URLs — retrieve_document

Instead of downloading files, `retrieve_document` calls the Hostviewer
API to get a browser URL for viewing the document in Mobius View.

```
retrieve_document(object_id)
   │
   ▼
ContentDocument.retrieve_document()      ← lib/content_document.py
   │
   ├─ URL: {base_url}/mobius/rest/hostviewer
   │
   ├─ Payload:
   │    { "objectId": "encrypted_id", "repositoryId": "repo_uuid" }
   │
   ├─ POST → Content Repository
   │
   └─ Returns: viewer URL string
        e.g. "https://server:port/mobius/view/..."
```

---

## 5. Document Search — search_documents

Searches for documents by index values using the Mobius Search API.

```
search_documents(constraints, conjunction)
   │
   ▼
ContentSearch.search_index()             ← lib/content_search.py
   │
   ├─ URL: {repo_url}/searches?returnresults=true&limit=200
   │
   ├─ Headers:
   │    Content-Type: application/vnd.asg-mobius-search.v1+json
   │    Accept: application/vnd.asg-mobius-search.v1+json
   │
   ├─ Payload (built by IndexSearch):
   │    {
   │      "indexSearch": {
   │        "conjunction": "AND",
   │        "constraints": [
   │          { "name": "CUST_ID", "operator": "EQ", "values": [{"value": "1000"}] }
   │        ],
   │        "repositories": [{ "id": "repo_uuid" }]
   │      }
   │    }
   │
   ├─ POST → Content Repository
   │
   └─ Returns: list of objectIds
```

### Search Operators

| Operator | Meaning |
|---|---|
| `EQ` | Equal |
| `NE` | Not equal |
| `LT` | Less than |
| `LE` | Less or equal |
| `GT` | Greater than |
| `GE` | Greater or equal |
| `LK` | Like (pattern match) |
| `BT` | Between |
| `NB` | Not between |
| `NU` | Is null |
| `NN` | Is not null |

---

## 6. Agent Integration — LangChain Tools

The agent connects to the MCP server using the **official MCP Python SDK**.

```
contentedge_tools.py

_MCP_SSE_URL = "http://contentedge-mcp:8001/sse"

@asynccontextmanager
async def _mcp_session():
    async with sse_client(url=_MCP_SSE_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session

async def _call_mcp_tool(tool_name, arguments):
    async with _mcp_session() as session:
        result = await session.call_tool(tool_name, arguments=arguments)
    # Parse MCP response content items
    return json.loads(text_content)
```

### LangChain Tools → MCP Tool Mapping

| LangChain Tool | MCP Tool Called | Purpose |
|---|---|---|
| `contentedge_search` | `search_documents` | Find documents by index |
| `contentedge_smart_chat` | `smart_chat` | Ask AI about documents |
| `contentedge_get_document_url` | `retrieve_document` | Get viewer URL |

---

## 7. Critical Workflow — Person/Entity Query

When a user asks about a person or entity (e.g. "Tell me about John Smith"),
the agent follows this workflow:

```
User: "Tell me everything about John Smith"
   │
   ▼
STEP 1: SQL Database
   │  execute_sql("SELECT * FROM customers WHERE name ILIKE '%John Smith%'")
   │  → customer_id=2, email=john@example.com, orders info
   │
   ▼
STEP 2: ContentEdge Smart Chat
   │  contentedge_smart_chat("Tell me about John Smith", "[]")
   │  → answer: "John Smith is a loan applicant..."
   │  → matching_document_ids: ["docA", "docB", "docC"]
   │
   ▼
STEP 3: Document Viewer URLs
   │  contentedge_get_document_url("docA") → viewer_url_1
   │  contentedge_get_document_url("docB") → viewer_url_2
   │  contentedge_get_document_url("docC") → viewer_url_3
   │
   ▼
STEP 4: Combined Answer
   │  "John Smith (customer #2, john@example.com) has 2 orders...
   │   
   │   From the Content Repository:
   │   John Smith is a loan applicant who submitted financial documents...
   │   
   │   Documents:
   │   - Loan Application: [viewer link 1]
   │   - Financial Statements: [viewer link 2]
   │   - Reference Letter: [viewer link 3]"
```

When the user has a known index value (e.g. customer ID), the agent
can also scope Smart Chat to specific documents:

```
STEP 2a: contentedge_search([{"index_name":"CUST_ID","value":"1000"}])
         → object_ids: ["id1", "id2", "id3"]

STEP 2b: contentedge_smart_chat("Summarize the loan", '["id1","id2","id3"]')
         → answer scoped to only those documents
```

---

## 8. ContentEdge Library (lib/)

| File | Class | Purpose |
|---|---|---|
| `content_config.py` | `ContentConfig` | YAML config, auth headers, repo ID discovery |
| `content_search.py` | `IndexSearch` | Builds search constraint payloads |
| `content_search.py` | `ContentSearch` | Executes index searches |
| `content_smart_chat.py` | `ContentSmartChat` | Smart Chat API client |
| `content_smart_chat.py` | `SmartChatResponse` | Parsed Smart Chat response |
| `content_document.py` | `ContentDocument` | Hostviewer URL + document delete |
| `content_archive_metadata.py` | `ContentArchiveMetadata` | Archive with metadata |
| `content_class_navigator.py` | `ContentClassNavigator` | Navigate content classes + versions |

---

## 9. Configuration

Environment variables (from `.env`):

| Variable | Example | Purpose |
|---|---|---|
| `CE_SOURCE_REPO_URL` | `https://server:11567` | Content Repository URL |
| `CE_SOURCE_REPO_NAME` | `Mobius` | Repository name |
| `CE_SOURCE_REPO_USER` | `admin` | Repository user |
| `CE_SOURCE_REPO_PASS` | `admin` | Repository password |
| `CE_SOURCE_REPO_SERVER_USER` | `ADMIN` | Server admin user |
| `CE_SOURCE_REPO_SERVER_PASS` | — | Server admin password |
| `MCP_TRANSPORT` | `sse` | MCP transport (sse or stdio) |
| `MCP_HOST` | `0.0.0.0` | MCP server bind host |
| `MCP_PORT` | `8001` | MCP server port |
| `CONTENTEDGE_MCP_URL` | `http://contentedge-mcp:8001` | Agent-side MCP server URL |

---

## 10. Files Involved

| File | Purpose |
|---|---|
| `contentedge/mcp_server.py` | MCP server — 7 tools + health check |
| `contentedge/lib/content_config.py` | Configuration and authentication |
| `contentedge/lib/content_search.py` | Document search (IndexSearch + ContentSearch) |
| `contentedge/lib/content_smart_chat.py` | Smart Chat API (ContentSmartChat + SmartChatResponse) |
| `contentedge/lib/content_document.py` | Document viewer URL (Hostviewer) |
| `contentedge/lib/content_archive_metadata.py` | Archive documents with metadata |
| `contentedge/lib/content_class_navigator.py` | Content class navigation and versions |
| `contentedge/conf/repository_source.yaml` | Repository connection settings |
| `app/agent/contentedge_tools.py` | LangChain tools wrapping MCP calls |
| `app/config.py` | `contentedge_mcp_url` setting |
