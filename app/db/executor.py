"""Execute validated SQL queries against PostgreSQL."""

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.safety import validate_sql, UnsafeSQLError


async def run_query(session: AsyncSession, raw_sql: str) -> pd.DataFrame:
    """Validate and execute a SELECT query, return results as DataFrame.

    Raises UnsafeSQLError if the query is blocked.
    """
    cleaned = validate_sql(raw_sql, readonly=settings.sql_readonly)

    result = await session.execute(text(cleaned))
    rows = result.fetchmany(settings.max_query_rows)
    columns = list(result.keys())

    return pd.DataFrame(rows, columns=columns)
