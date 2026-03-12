"""Qdrant vector store for schema descriptions and conversation memory."""

import uuid
import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_ollama import OllamaEmbeddings

from app.config import settings

logger = structlog.get_logger(__name__)

VECTOR_SIZE = 768  # nomic-embed-text dimension


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


def get_embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(
        model=settings.ollama_embed_model,
        base_url=settings.ollama_base_url,
    )


def ensure_collection(client: QdrantClient, collection_name: str) -> None:
    """Create the collection if it does not already exist."""
    existing = [c.name for c in client.get_collections().collections]
    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=VECTOR_SIZE, distance=Distance.COSINE
            ),
        )
        logger.info("qdrant.collection_created", name=collection_name)


def upsert_texts(
    client: QdrantClient,
    embeddings: OllamaEmbeddings,
    collection_name: str,
    texts: list[str],
    metadatas: list[dict] | None = None,
) -> int:
    """Embed and upsert a batch of texts into Qdrant. Returns count."""
    vectors = embeddings.embed_documents(texts)
    points = []
    for idx, (vec, txt) in enumerate(zip(vectors, texts)):
        payload = {"text": txt}
        if metadatas and idx < len(metadatas):
            payload.update(metadatas[idx])
        points.append(PointStruct(id=str(uuid.uuid4()), vector=vec, payload=payload))

    client.upsert(collection_name=collection_name, points=points)
    logger.info("qdrant.upserted", collection=collection_name, count=len(points))
    return len(points)


def search_similar(
    client: QdrantClient,
    embeddings: OllamaEmbeddings,
    collection_name: str,
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """Return the top-k most similar documents with scores."""
    query_vector = embeddings.embed_query(query)
    results = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=top_k,
        with_payload=True,
    )
    return [
        {"text": hit.payload.get("text", ""), "score": hit.score, **hit.payload}
        for hit in results.points
    ]
