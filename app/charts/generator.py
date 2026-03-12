"""Chart generation using Matplotlib and Plotly."""

import uuid
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for server
import matplotlib.pyplot as plt
import pandas as pd

CHARTS_DIR = Path("/app/charts_output")
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

_CHART_BUILDERS = {}


def _register(name: str):
    def wrapper(fn):
        _CHART_BUILDERS[name] = fn
        return fn
    return wrapper


@_register("bar")
def _bar(df: pd.DataFrame, x: str, y: str, title: str, ax):
    df.plot.bar(x=x, y=y, ax=ax, legend=False)
    ax.set_title(title)
    ax.set_ylabel(y)
    plt.xticks(rotation=45, ha="right")


@_register("line")
def _line(df: pd.DataFrame, x: str, y: str, title: str, ax):
    df.plot.line(x=x, y=y, ax=ax, marker="o")
    ax.set_title(title)


@_register("pie")
def _pie(df: pd.DataFrame, x: str, y: str, title: str, ax):
    ax.pie(df[y], labels=df[x], autopct="%1.1f%%", startangle=90)
    ax.set_title(title)


@_register("scatter")
def _scatter(df: pd.DataFrame, x: str, y: str, title: str, ax):
    df.plot.scatter(x=x, y=y, ax=ax)
    ax.set_title(title)


@_register("histogram")
def _histogram(df: pd.DataFrame, x: str, y: str, title: str, ax):
    df[x].plot.hist(ax=ax, bins=20)
    ax.set_title(title)
    ax.set_xlabel(x)


def create_chart(
    df: pd.DataFrame,
    chart_type: str,
    x: str,
    y: str | None,
    title: str = "Chart",
) -> str:
    """Create a chart and save as PNG. Returns the file path."""
    builder = _CHART_BUILDERS.get(chart_type)
    if builder is None:
        supported = ", ".join(_CHART_BUILDERS.keys())
        raise ValueError(f"Unsupported chart type '{chart_type}'. Use: {supported}")

    fig, ax = plt.subplots(figsize=(10, 6))
    builder(df, x, y or x, title, ax)
    plt.tight_layout()

    filename = f"{chart_type}_{uuid.uuid4().hex[:8]}.png"
    filepath = CHARTS_DIR / filename
    fig.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return str(filepath)
