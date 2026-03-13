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
    """Search Qdrant for schema descriptions relevant to the question."""
    try:
        client = get_qdrant_client()
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
    # Bind the DB session for agent tools
    bind_session(session)

    # Retrieve relevant schema context from Qdrant
    schema_context = _retrieve_schema_context(question)

    system_text = SYSTEM_PROMPT.format(
        schema_context=schema_context,
        max_rows=settings.max_query_rows,
    )

    # Build the agent
    llm = _get_llm()
    agent = create_react_agent(llm, AGENT_TOOLS)

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

    logger.info("agent.invoke", question=question[:100])

    # Invoke agent
    result = await agent.ainvoke({"messages": messages})

    # Extract the final answer
    final_messages = result.get("messages", [])
    answer = ""
    for msg in reversed(final_messages):
        if hasattr(msg, "content") and msg.content and not getattr(msg, "tool_calls", None):
            answer = msg.content
            break

    # Check for chart output
    df = get_last_dataframe()
    data_preview = None
    if df is not None and not df.empty:
        data_preview = df.head(20).to_dict(orient="records")

    # Detect chart path in tool messages
    chart_path = None
    for msg in final_messages:
        if hasattr(msg, "content") and "Chart saved to:" in str(msg.content):
            chart_path = str(msg.content).split("Chart saved to:")[-1].strip()

    return {
        "answer": answer,
        "chart_path": chart_path,
        "data_preview": data_preview,
    }
