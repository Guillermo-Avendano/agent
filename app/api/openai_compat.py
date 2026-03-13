"""OpenAI-compatible API routes for AnythingLLM integration.

Exposes /v1/chat/completions and /v1/models so AnythingLLM
can treat this agent as a custom LLM provider.
"""

import json
import time
import uuid

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection import get_session
from app.agent.core import ask_agent
from app.models.schemas import (
    OpenAIChatRequest,
    OpenAIChatResponse,
    OpenAIChatChoice,
    OpenAIChatMessage,
    OpenAIUsage,
    OpenAIModel,
    OpenAIModelList,
)

logger = structlog.get_logger(__name__)

openai_router = APIRouter(prefix="/v1", tags=["openai-compatible"])


@openai_router.get("/models", response_model=OpenAIModelList)
async def list_models():
    """List available models (AnythingLLM calls this on setup)."""
    return OpenAIModelList(
        data=[
            OpenAIModel(id="sql-agent", created=int(time.time())),
        ]
    )


@openai_router.post("/chat/completions")
async def chat_completions(
    request: OpenAIChatRequest,
    session: AsyncSession = Depends(get_session),
):
    """OpenAI-compatible chat completions — routes through the SQL agent."""

    # Extract the last user message as the question
    question = ""
    chat_history = []

    for msg in request.messages:
        if msg.role == "system":
            # System messages are handled by our agent's own prompt
            continue
        elif msg.role == "user":
            if question:
                # Previous user message becomes history
                chat_history.append({"role": "user", "content": question})
            question = msg.content
        elif msg.role == "assistant":
            chat_history.append({"role": "assistant", "content": msg.content})

    if not question:
        answer = "No user message provided."
    else:
        logger.info("openai_compat.ask", question=question[:100])
        try:
            result = await ask_agent(
                question=question,
                session=session,
                chat_history=chat_history if chat_history else None,
            )
            answer = result["answer"]

            # Append chart link if generated
            if result.get("chart_path"):
                filename = result["chart_path"].split("/")[-1]
                answer += f"\n\n📊 Chart: /charts/{filename}"

        except Exception as e:
            logger.error("openai_compat.error", error=str(e))
            answer = f"Error processing your question: {e}"

    completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(time.time())

    # ── Streaming response (SSE) ─────────────────────────────
    if request.stream:
        async def _stream_sse():
            # Single content chunk with the full answer
            chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": request.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": answer},
                        "finish_reason": None,
                    }
                ],
            }
            yield f"data: {json.dumps(chunk)}\n\n"

            # Final chunk signaling completion
            done_chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": request.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop",
                    }
                ],
            }
            yield f"data: {json.dumps(done_chunk)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            _stream_sse(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # ── Non-streaming response ───────────────────────────────
    return OpenAIChatResponse(
        id=completion_id,
        created=created,
        model=request.model,
        choices=[
            OpenAIChatChoice(
                message=OpenAIChatMessage(role="assistant", content=answer),
            )
        ],
        usage=OpenAIUsage(),
    )
