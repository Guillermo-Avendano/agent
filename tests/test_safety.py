"""Tests for SQL safety validation layer."""

import pytest
from app.db.safety import validate_sql, UnsafeSQLError


class TestValidateSQL:
    def test_valid_select(self):
        result = validate_sql("SELECT * FROM users", readonly=True)
        assert result == "SELECT * FROM users"

    def test_valid_select_with_where(self):
        result = validate_sql("SELECT id, name FROM users WHERE id = 1", readonly=True)
        assert "SELECT" in result

    def test_blocks_insert(self):
        with pytest.raises(UnsafeSQLError, match="Write operation"):
            validate_sql("INSERT INTO users (name) VALUES ('test')", readonly=True)

    def test_blocks_update(self):
        with pytest.raises(UnsafeSQLError, match="Write"):
            validate_sql("UPDATE users SET name = 'hack'", readonly=True)

    def test_blocks_delete(self):
        with pytest.raises(UnsafeSQLError, match="Write"):
            validate_sql("DELETE FROM users WHERE id = 1", readonly=True)

    def test_blocks_drop(self):
        with pytest.raises(UnsafeSQLError):
            validate_sql("DROP TABLE users", readonly=True)

    def test_blocks_multiple_statements(self):
        with pytest.raises(UnsafeSQLError, match="single"):
            validate_sql("SELECT 1; DROP TABLE users", readonly=True)

    def test_blocks_pg_sleep(self):
        with pytest.raises(UnsafeSQLError, match="blocked pattern"):
            validate_sql("SELECT pg_sleep(10)", readonly=True)

    def test_blocks_file_read(self):
        with pytest.raises(UnsafeSQLError, match="blocked pattern"):
            validate_sql("SELECT pg_read_file('/etc/passwd')", readonly=True)

    def test_empty_query(self):
        with pytest.raises(UnsafeSQLError, match="Empty"):
            validate_sql("", readonly=True)

    def test_allows_write_when_not_readonly(self):
        result = validate_sql("INSERT INTO users (name) VALUES ('test')", readonly=False)
        assert "INSERT" in result

    def test_strips_trailing_semicolon(self):
        result = validate_sql("SELECT 1;", readonly=True)
        assert result == "SELECT 1"

    def test_complex_select(self):
        sql = """
        SELECT c.name, COUNT(o.id) as order_count, SUM(o.total) as total_spent
        FROM customers c
        JOIN orders o ON c.id = o.customer_id
        WHERE o.status = 'delivered'
        GROUP BY c.name
        ORDER BY total_spent DESC
        LIMIT 10
        """
        result = validate_sql(sql, readonly=True)
        assert "SELECT" in result
