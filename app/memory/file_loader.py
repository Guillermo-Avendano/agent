"""Load PDFs and text files from files_for_memory/ into Qdrant.

Supported formats: .pdf, .txt, .md
Files are split into overlapping chunks and upserted into the same
Qdrant collection used for schema descriptions so the agent can
retrieve them as context.
"""

from pathlib import Path

import structlog
from pypdf import PdfReader

from app.config import settings
from app.memory.qdrant_store import (
    get_qdrant_client,
    get_embeddings,
    ensure_collection,
    upsert_texts,
)

logger = structlog.get_logger(__name__)

FILES_DIR = Path("/app/files_for_memory")

CHUNK_SIZE = 1000  # characters per chunk
CHUNK_OVERLAP = 200


# ── Readers ──────────────────────────────────────────────────

def _read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


_READERS: dict[str, callable] = {
    ".pdf": _read_pdf,
    ".txt": _read_text,
    ".md": _read_text,
}


# ── Chunker ──────────────────────────────────────────────────

def _split_text(text: str, chunk_size: int = CHUNK_SIZE,
                overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks by character count."""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


# ── Public API ───────────────────────────────────────────────

def load_files_for_memory() -> int:
    """Read every supported file in FILES_DIR and upsert to Qdrant.

    Returns total number of indexed chunks.
    """
    if not FILES_DIR.exists():
        logger.info("file_loader.dir_missing", path=str(FILES_DIR))
        return 0

    supported = list(FILES_DIR.iterdir())
    supported = [f for f in supported if f.suffix.lower() in _READERS and f.is_file()]

    if not supported:
        logger.info("file_loader.no_files")
        return 0

    client = get_qdrant_client()
    embeddings = get_embeddings()
    collection = settings.qdrant_collection
    ensure_collection(client, collection)

    total = 0
    for fpath in sorted(supported):
        reader_fn = _READERS[fpath.suffix.lower()]
        try:
            raw = reader_fn(fpath)
        except Exception as e:
            logger.error("file_loader.read_error", file=fpath.name, error=str(e))
            continue

        chunks = _split_text(raw)
        if not chunks:
            continue

        metas = [{"source": fpath.name, "type": "document"} for _ in chunks]
        count = upsert_texts(client, embeddings, collection, chunks, metas)
        logger.info("file_loader.indexed", file=fpath.name, chunks=count)
        total += count

    logger.info("file_loader.done", total_chunks=total)
    return total
