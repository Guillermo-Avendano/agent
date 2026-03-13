"""LangChain tools exposed to the agent for SQL execution and charting."""

import pandas as pd
import structlog
from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.executor import run_query
from app.db.safety import UnsafeSQLError
from app.charts.generator import create_chart

logger = structlog.get_logger(__name__)

# These are bound at runtime by the agent core before each invocation.
_session_ref: AsyncSession | None = None
_last_dataframe: pd.DataFrame | None = None


def bind_session(session: AsyncSession) -> None:
    global _session_ref
    _session_ref = session


def get_last_dataframe() -> pd.DataFrame | None:
    return _last_dataframe


@tool
async def execute_sql(query: str) -> str:
    """Execute a read-only SQL query against PostgreSQL and return the results as a markdown table.

    Args:
        query: A valid SELECT SQL query.
    """
    global _last_dataframe
    logger.info("  │  ▶ execute_sql called", query=query[:500])
    if _session_ref is None:
        logger.error("  │  ✗ no database session")
        return "Error: No database session available."
    try:
        df = await run_query(_session_ref, query)
        _last_dataframe = df
        if df.empty:
            logger.info("  │  ✓ query OK — 0 rows")
            return "Query returned no results."
        logger.info("  │  ✓ query OK", rows=len(df), columns=list(df.columns))
        return df.to_markdown(index=False)
    except UnsafeSQLError as e:
        logger.warning("  │  ✗ blocked by safety", reason=str(e))
        return f"Blocked: {e}"
    except Exception as e:
        logger.error("  │  ✗ SQL error", error=str(e))
        return f"SQL Error: {e}"


@tool
def generate_chart(chart_type: str, x: str, y: str, title: str = "Chart") -> str:
    """Generate a chart from the last SQL query results.

    Args:
        chart_type: Type of chart: bar, line, pie, scatter, or histogram.
        x: Column name for the x-axis.
        y: Column name for the y-axis.
        title: Chart title.
    """
    global _last_dataframe
    logger.info("  │  ▶ generate_chart called", chart_type=chart_type,
                x=x, y=y, title=title)
    if _last_dataframe is None or _last_dataframe.empty:
        logger.warning("  │  ✗ no dataframe available")
        return "Error: No data available. Execute a SQL query first."

    if x not in _last_dataframe.columns:
        return f"Error: Column '{x}' not found. Available: {list(_last_dataframe.columns)}"
    if y and y not in _last_dataframe.columns:
        return f"Error: Column '{y}' not found. Available: {list(_last_dataframe.columns)}"

    filepath = create_chart(
        df=_last_dataframe,
        chart_type=chart_type,
        x=x,
        y=y,
        title=title,
    )
    logger.info("  │  ✓ chart created", path=filepath)
    return f"Chart saved to: {filepath}"


from app.agent.web_tools import WEB_TOOLS

AGENT_TOOLS = [execute_sql, generate_chart] + WEB_TOOLS
