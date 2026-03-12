"""Tests for chart generator."""

import pytest
import pandas as pd
from unittest.mock import patch
from pathlib import Path


class TestChartGenerator:
    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame({
            "category": ["Electronics", "Furniture", "Books"],
            "total_sales": [5000, 3000, 1500],
            "quantity": [100, 50, 30],
        })

    def test_bar_chart(self, sample_df, tmp_path):
        with patch("app.charts.generator.CHARTS_DIR", tmp_path):
            from app.charts.generator import create_chart
            path = create_chart(sample_df, "bar", "category", "total_sales", "Sales by Category")
            assert Path(path).exists()
            assert path.endswith(".png")

    def test_line_chart(self, sample_df, tmp_path):
        with patch("app.charts.generator.CHARTS_DIR", tmp_path):
            from app.charts.generator import create_chart
            path = create_chart(sample_df, "line", "category", "total_sales", "Sales Trend")
            assert Path(path).exists()

    def test_pie_chart(self, sample_df, tmp_path):
        with patch("app.charts.generator.CHARTS_DIR", tmp_path):
            from app.charts.generator import create_chart
            path = create_chart(sample_df, "pie", "category", "total_sales", "Sales Distribution")
            assert Path(path).exists()

    def test_unsupported_chart_type(self, sample_df):
        from app.charts.generator import create_chart
        with pytest.raises(ValueError, match="Unsupported"):
            create_chart(sample_df, "radar", "category", "total_sales")
