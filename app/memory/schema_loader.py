"""Load table/column descriptions from JSON and index them into Qdrant.

Expected JSON format (schema_descriptions/*.json):
{
  "tables": [
    {
      "name": "orders",
      "description": "Contains customer purchase orders.",
      "columns": [
        {
          "name": "id",
          "type": "integer",
          "description": "Primary key auto-incremented."
        },
        ...
      ]
    }
  ]
}
"""

import json
from pathlib import Path

import structlog

from app.memory.qdrant_store import (
    get_qdrant_client,
    get_embeddings,
    ensure_collection,
    upsert_texts,
)
from app.config import settings

logger = structlog.get_logger(__name__)

SCHEMA_DIR = Path("/app/schema_descriptions")


def _build_description_texts(schema: dict) -> tuple[list[str], list[dict]]:
    """Convert schema JSON into embeddable text chunks + metadata."""
    texts: list[str] = []
    metas: list[dict] = []

    for table in schema.get("tables", []):
        tname = table["name"]
        tdesc = table.get("description", "")

        # Table-level chunk
        col_summaries = []
        for col in table.get("columns", []):
            col_summaries.append(
                f"  - {col['name']} ({col.get('type','unknown')}): "
                f"{col.get('description','')}"
            )
        chunk = (
            f"Table: {tname}\nDescription: {tdesc}\nColumns:\n"
            + "\n".join(col_summaries)
        )
        texts.append(chunk)
        metas.append({"table": tname, "type": "table_schema"})

    return texts, metas


def load_all_schemas() -> int:
    """Read every JSON file in SCHEMA_DIR and upsert to Qdrant.

    Returns total number of indexed chunks.
    """
    client = get_qdrant_client()
    embeddings = get_embeddings()
    collection = settings.qdrant_collection

    ensure_collection(client, collection)

    total = 0
    if not SCHEMA_DIR.exists():
        logger.warning("schema_dir.missing", path=str(SCHEMA_DIR))
        return 0

    for fpath in sorted(SCHEMA_DIR.glob("*.json")):
        logger.info("schema_loader.loading", file=fpath.name)
        with open(fpath, "r", encoding="utf-8") as f:
            schema = json.load(f)
        texts, metas = _build_description_texts(schema)
        if texts:
            total += upsert_texts(client, embeddings, collection, texts, metas)

    logger.info("schema_loader.done", total_chunks=total)
    return total
