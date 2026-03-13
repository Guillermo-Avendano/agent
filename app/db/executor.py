"""Execute validated SQL queries against PostgreSQL."""

import pandas as pd
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.safety import validate_sql, UnsafeSQLError

logger = structlog.get_logger(__name__)


async def run_query(session: AsyncSession, raw_sql: str) -> pd.DataFrame:
    """Validate and execute a SELECT query, return results as DataFrame.

    Raises UnsafeSQLError if the query is blocked.
    """
    logger.info("  │  │  validate_sql ...", readonly=settings.sql_readonly)
    cleaned = validate_sql(raw_sql, readonly=settings.sql_readonly)
    logger.info("  │  │  ✓ validation passed", cleaned_sql=cleaned[:300])

    logger.info("  │  │  executing query ...")
    result = await session.execute(text(cleaned))
    rows = result.fetchmany(settings.max_query_rows)
    columns = list(result.keys())
    logger.info("  │  │  ✓ query executed", rows_fetched=len(rows),
                columns=columns, max_rows=settings.max_query_rows)

    return pd.DataFrame(rows, columns=columns)
