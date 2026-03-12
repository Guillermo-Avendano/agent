"""LangChain tools exposed to the agent for SQL execution and charting."""

import json
import re

import pandas as pd
from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.executor import run_query
from app.db.safety import UnsafeSQLError
from app.charts.generator import create_chart


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
    if _session_ref is None:
        return "Error: No database session available."
    try:
        df = await run_query(_session_ref, query)
        _last_dataframe = df
        if df.empty:
            return "Query returned no results."
        return df.to_markdown(index=False)
    except UnsafeSQLError as e:
        return f"Blocked: {e}"
    except Exception as e:
        return f"SQL Error: {e}"


@tool
def generate_chart(spec_json: str) -> str:
    """Generate a chart from the last SQL query results.

    Args:
        spec_json: JSON string with keys: chart_type, x, y, title.
            Example: {"chart_type": "bar", "x": "category", "y": "total_sales", "title": "Sales by Category"}
    """
    global _last_dataframe
    if _last_dataframe is None or _last_dataframe.empty:
        return "Error: No data available. Execute a SQL query first."
    try:
        spec = json.loads(spec_json)
    except json.JSONDecodeError:
        # Try to extract JSON from markdown/text
        match = re.search(r'\{.*\}', spec_json, re.DOTALL)
        if match:
            spec = json.loads(match.group())
        else:
            return "Error: Invalid JSON specification."

    chart_type = spec.get("chart_type", "bar")
    x_col = spec.get("x")
    y_col = spec.get("y")
    title = spec.get("title", "Chart")

    if x_col not in _last_dataframe.columns:
        return f"Error: Column '{x_col}' not found. Available: {list(_last_dataframe.columns)}"
    if y_col and y_col not in _last_dataframe.columns:
        return f"Error: Column '{y_col}' not found. Available: {list(_last_dataframe.columns)}"

    filepath = create_chart(
        df=_last_dataframe,
        chart_type=chart_type,
        x=x_col,
        y=y_col,
        title=title,
    )
    return f"Chart saved to: {filepath}"


from app.agent.web_tools import WEB_TOOLS

AGENT_TOOLS = [execute_sql, generate_chart] + WEB_TOOLS
