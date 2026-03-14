"""Pydantic request/response models for the API."""

from pydantic import BaseModel, Field
from app.config import settings


class ChatMessage(BaseModel):
    role: str = Field(..., pattern=r"^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=10000)


class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="The user's question about the database.",
    )
    chat_history: list[ChatMessage] = Field(
        default_factory=list,
        max_length=50,
        description="Previous messages for context.",
    )


class AskResponse(BaseModel):
    answer: str
    chart_path: str | None = None
    data_preview: list[dict] | None = None


class HealthResponse(BaseModel):
    status: str
    postgres: str
    qdrant: str
    ollama: str


class SchemaLoadResponse(BaseModel):
    indexed_chunks: int
    message: str


# ─── OpenAI-compatible models (for AnythingLLM) ─────────────
class OpenAIChatMessage(BaseModel):
    role: str = Field(..., pattern=r"^(system|user|assistant)$")
    content: str


class OpenAIChatRequest(BaseModel):
    model: str = Field(default_factory=lambda: settings.agent_name)
    messages: list[OpenAIChatMessage] = Field(..., min_length=1)
    temperature: float = Field(default=0.0)
    max_tokens: int | None = Field(default=None)
    stream: bool = Field(default=False)


class OpenAIUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class OpenAIChatChoice(BaseModel):
    index: int = 0
    message: OpenAIChatMessage
    finish_reason: str = "stop"


class OpenAIChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str = Field(default_factory=lambda: settings.agent_name)
    choices: list[OpenAIChatChoice]
    usage: OpenAIUsage = OpenAIUsage()


class OpenAIModel(BaseModel):
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = Field(default_factory=lambda: settings.agent_name)


class OpenAIModelList(BaseModel):
    object: str = "list"
    data: list[OpenAIModel]
