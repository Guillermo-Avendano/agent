"""SQL safety layer — validates and sanitises queries before execution.

Prevents destructive operations when SQL_READONLY is enabled.
Uses sqlparse for structural analysis; all queries run through
SQLAlchemy's parameterised `text()` to prevent injection.
"""

import sqlparse
from sqlparse.sql import Statement
from sqlparse.tokens import Keyword, DML

# Statements that modify data or schema
_WRITE_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "CREATE", "REPLACE", "GRANT", "REVOKE", "MERGE",
}

# Dangerous functions / patterns even inside SELECT
_BLOCKED_PATTERNS = {
    "pg_sleep", "lo_import", "lo_export",
    "pg_read_file", "pg_read_binary_file",
    "pg_ls_dir", "pg_stat_file",
    "copy ", "\\copy",
}


class UnsafeSQLError(Exception):
    """Raised when a query fails safety validation."""


def validate_sql(raw_sql: str, *, readonly: bool = True) -> str:
    """Return the cleaned SQL string or raise UnsafeSQLError.

    Parameters
    ----------
    raw_sql : str
        The user-provided SQL query.
    readonly : bool
        If True (default), block all write operations.
    """
    if not raw_sql or not raw_sql.strip():
        raise UnsafeSQLError("Empty query.")

    cleaned = raw_sql.strip().rstrip(";")
    lower = cleaned.lower()

    # Block dangerous built-in functions / commands
    for pattern in _BLOCKED_PATTERNS:
        if pattern in lower:
            raise UnsafeSQLError(
                f"Query contains blocked pattern: {pattern!r}"
            )

    # Block multiple statements (prevents piggy-backed injection)
    parsed = sqlparse.parse(cleaned)
    if len(parsed) > 1:
        raise UnsafeSQLError("Only single SQL statements are allowed.")

    if readonly:
        stmt: Statement = parsed[0]
        stmt_type = stmt.get_type()

        # get_type() returns 'SELECT', 'INSERT', etc. or None
        if stmt_type and stmt_type.upper() in _WRITE_KEYWORDS:
            raise UnsafeSQLError(
                f"Write operation '{stmt_type}' is not allowed in readonly mode."
            )

        # Extra check: scan tokens for DML/DDL keywords
        for token in stmt.flatten():
            if token.ttype is DML or token.ttype is Keyword:
                word = token.value.upper()
                if word in _WRITE_KEYWORDS:
                    raise UnsafeSQLError(
                        f"Write keyword '{word}' is not allowed in readonly mode."
                    )

    return cleaned
