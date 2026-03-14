"""LangChain tools that call the ContentEdge MCP server.

The ContentEdge MCP server is a **standard MCP server** (FastMCP + SSE
transport) so it can be consumed by any compliant MCP client — Claude
Desktop, Cursor, etc.

These LangChain wrappers use the official ``mcp`` Python SDK
(``ClientSession`` + ``sse_client``) to connect to the server, keeping
full protocol compliance.
"""

import json
import structlog
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.sse import sse_client
from langchain_core.tools import tool

from app.config import settings

logger = structlog.get_logger(__name__)

# ── MCP standard client helper ─────────────────────────────────────────────

_MCP_SSE_URL = f"{settings.contentedge_mcp_url}/sse"


@asynccontextmanager
async def _mcp_session():
    """Open a standard MCP client session over SSE."""
    async with sse_client(url=_MCP_SSE_URL) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


async def _call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """Invoke a tool on the ContentEdge MCP server using the standard protocol."""
    logger.debug("mcp_call.request", tool=tool_name)
    async with _mcp_session() as session:
        result = await session.call_tool(tool_name, arguments=arguments)

    # MCP result.content is a list of content items
    text = ""
    for item in result.content:
        if item.type == "text":
            text += item.text
    if text:
        return json.loads(text)
    return {}


# ── LangChain tools ────────────────────────────────────────────────────────

@tool
async def contentedge_search(
    constraints: str,
    conjunction: str = "AND",
) -> str:
    """Search for documents in ContentEdge by index values.

    Use this to find documents matching a specific customer, date, etc.
    Returns a list of objectIds that can be passed to contentedge_smart_chat.

    Args:
        constraints: JSON array of search constraints.
                     Each element: {"index_name":"...", "operator":"EQ", "value":"..."}.
                     Example: [{"index_name":"CUST_ID","operator":"EQ","value":"1000"}]
        conjunction: How to combine constraints — "AND" or "OR". Default "AND".
    """
    logger.info("contentedge_search.start", constraints=constraints[:200])
    try:
        parsed = json.loads(constraints)
    except json.JSONDecodeError as e:
        return f"Error: invalid JSON in constraints — {e}"

    try:
        result = await _call_mcp_tool("search_documents", {
            "constraints": parsed,
            "conjunction": conjunction,
        })
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("contentedge_search.error", error=str(e))
        return f"Error calling ContentEdge search: {e}"


@tool
async def contentedge_smart_chat(
    question: str,
    document_ids: str = "[]",
    conversation_id: str = "",
) -> str:
    """Ask a question to ContentEdge Smart Chat AI about documents in the repository.

    Two modes:
    1. Repository-wide: pass document_ids as "[]" to query ALL documents.
    2. Scoped: pass a JSON array of objectIds (from contentedge_search) to
       limit the question to specific documents.

    For follow-up questions pass the conversation_id from the previous response.

    Args:
        question: The question to ask about the documents.
        document_ids: JSON array of objectIds, e.g. '["abc","def"]'. Use "[]" for repository-wide.
        conversation_id: conversation_id from a prior call to continue the conversation.
    """
    logger.info("contentedge_smart_chat.start", question=question[:200])
    try:
        ids = json.loads(document_ids)
    except json.JSONDecodeError:
        ids = []

    try:
        result = await _call_mcp_tool("smart_chat", {
            "question": question,
            "document_ids": ids if ids else None,
            "conversation_id": conversation_id,
        })
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("contentedge_smart_chat.error", error=str(e))
        return f"Error calling ContentEdge Smart Chat: {e}"


@tool
async def contentedge_get_document_url(object_id: str) -> str:
    """Get a viewer URL to open a ContentEdge document in the browser.

    Call this for each document objectId returned by Smart Chat to provide
    clickable links to the user.

    Args:
        object_id: The encrypted objectId of the document.
    """
    logger.info("contentedge_get_document_url.start", object_id=object_id[:60])
    try:
        result = await _call_mcp_tool("retrieve_document", {
            "object_id": object_id,
        })
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("contentedge_get_document_url.error", error=str(e))
        return f"Error getting document URL: {e}"


CONTENTEDGE_TOOLS = [contentedge_search, contentedge_smart_chat, contentedge_get_document_url]
