"""Core agent — binds Ollama LLM + tools + Qdrant context into a ReAct agent."""

import structlog
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import create_react_agent

from app.config import settings
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import AGENT_TOOLS, bind_session, get_last_dataframe
from app.memory.qdrant_store import (
    get_qdrant_client,
    get_embeddings,
    search_similar,
)
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


def _get_llm() -> ChatOllama:
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0,
    )


def _retrieve_schema_context(question: str, top_k: int = 5) -> str:
    """Retrieve ALL schema table descriptions from Qdrant.

    Uses a payload filter to fetch every table_schema chunk so the LLM
    always sees the full database structure regardless of the question.
    Falls back to semantic search if the filter returns nothing.
    """
    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        client = get_qdrant_client()

        # Fetch ALL schema chunks (not similarity-based)
        schema_filter = Filter(
            must=[FieldCondition(key="type", match=MatchValue(value="table_schema"))]
        )
        all_schema, _ = client.scroll(
            collection_name=settings.qdrant_collection,
            scroll_filter=schema_filter,
            limit=100,
            with_payload=True,
        )
        if all_schema:
            # Deduplicate by table name
            seen = set()
            texts = []
            for point in all_schema:
                table = point.payload.get("table", "")
                if table not in seen:
                    seen.add(table)
                    texts.append(point.payload.get("text", ""))
            logger.info("schema_context.loaded", tables=list(seen))
            return "\n\n".join(texts)

        # Fallback to semantic search
        embeddings = get_embeddings()
        results = search_similar(
            client, embeddings, settings.qdrant_collection, question, top_k
        )
        if not results:
            return "No schema context available."
        return "\n\n".join(r["text"] for r in results)
    except Exception as e:
        logger.warning("schema_context.error", error=str(e))
        return "Schema context unavailable."


async def ask_agent(
    question: str,
    session: AsyncSession,
    chat_history: list[dict] | None = None,
) -> dict:
    """Process a user question through the agent pipeline.

    Returns a dict with keys: answer, sql, chart_path, data_preview.
    """
    logger.info("▶ agent.start", question=question[:200])

    # Bind the DB session for agent tools
    bind_session(session)
    logger.info("  ├─ session bound")

    # Retrieve relevant schema context from Qdrant
    schema_context = _retrieve_schema_context(question)
    ctx_preview = schema_context[:200].replace("\n", " ")
    logger.info("  ├─ schema context retrieved", preview=ctx_preview)

    system_text = SYSTEM_PROMPT.format(
        schema_context=schema_context,
        max_rows=settings.max_query_rows,
    )

    # Build the agent
    llm = _get_llm()
    agent = create_react_agent(llm, AGENT_TOOLS)
    logger.info("  ├─ ReAct agent built", model=settings.ollama_model,
                tools=[t.name for t in AGENT_TOOLS])

    # Build messages
    messages = [SystemMessage(content=system_text)]
    if chat_history:
        for msg in chat_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            else:
                from langchain_core.messages import AIMessage
                messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=question))
    logger.info("  ├─ messages built", count=len(messages),
                history_msgs=len(chat_history) if chat_history else 0)

    # Invoke agent
    logger.info("  ├─ invoking LLM + agent loop ...")
    result = await agent.ainvoke(
        {"messages": messages},
        config={"recursion_limit": 50},
    )

    # ── Log every message in the agent trace ──
    final_messages = result.get("messages", [])
    logger.info("  ├─ agent loop done", total_messages=len(final_messages))
    for i, msg in enumerate(final_messages):
        msg_type = type(msg).__name__
        content_raw = getattr(msg, "content", "") or ""
        content_preview = str(content_raw)[:300].replace("\n", " ")
        tool_calls = getattr(msg, "tool_calls", None)
        tool_name = getattr(msg, "name", None)  # ToolMessage has .name
        extras = {}
        if tool_calls:
            extras["tool_calls"] = [
                {"name": tc.get("name"), "args_preview": str(tc.get("args", ""))[:200]}
                for tc in tool_calls
            ]
        if tool_name:
            extras["tool_name"] = tool_name
        logger.info(f"  │  [{i}] {msg_type}",
                    content_preview=content_preview, **extras)

    # Extract the final answer
    answer = ""
    for msg in reversed(final_messages):
        if type(msg).__name__ == "ToolMessage":
            continue
        content = getattr(msg, "content", None)
        if content and not getattr(msg, "tool_calls", None):
            answer = content if isinstance(content, str) else str(content)
            break

    logger.info("  ├─ answer extracted",
                length=len(answer),
                preview=answer[:200].replace("\n", " "))

    # Check for chart output
    df = get_last_dataframe()
    data_preview = None
    if df is not None and not df.empty:
        data_preview = df.head(20).to_dict(orient="records")
        logger.info("  ├─ dataframe available", rows=len(df),
                    columns=list(df.columns))

    # Detect chart path in tool messages
    chart_path = None
    for msg in final_messages:
        if hasattr(msg, "content") and "Chart saved to:" in str(msg.content):
            chart_path = str(msg.content).split("Chart saved to:")[-1].strip()

    if chart_path:
        logger.info("  ├─ chart generated", path=chart_path)

    logger.info("  └─ agent.done")

    return {
        "answer": answer,
        "chart_path": chart_path,
        "data_preview": data_preview,
    }
