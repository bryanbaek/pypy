"""Tests for repository-owned Postgres bootstrap assets."""

import src.backend.db.postgres as postgres
from src.backend.db.postgres import (
    BOOTSTRAP_SQL_PATH,
    BOOTSTRAP_TABLES,
    read_bootstrap_sql,
)


def test_read_bootstrap_sql_loads_expected_tables() -> None:
    sql = read_bootstrap_sql()

    assert BOOTSTRAP_SQL_PATH.exists()
    for table_name in BOOTSTRAP_TABLES:
        assert f"CREATE TABLE IF NOT EXISTS {table_name}" in sql


def test_bootstrap_sql_documents_additive_contract() -> None:
    sql = read_bootstrap_sql()

    for snippet in (
        "CONTRACT:",
        "Keep this file strictly additive and idempotent.",
        "DROP TRIGGER IF EXISTS immediately followed by",
        "Do not add DROP TABLE, DROP COLUMN, ALTER COLUMN, TRUNCATE",
    ):
        assert snippet in sql


def test_bootstrap_sql_rejects_destructive_ddl_patterns() -> None:
    sql_lines = [
        line.strip().upper()
        for line in read_bootstrap_sql().splitlines()
        if line.strip() and not line.lstrip().startswith("--")
    ]

    for line in sql_lines:
        if line.startswith("DROP "):
            assert line.startswith("DROP TRIGGER IF EXISTS "), (
                "bootstrap SQL must stay additive/idempotent; only DROP TRIGGER IF EXISTS "
                "is allowed"
            )

    for forbidden_snippet in ("DROP COLUMN", "ALTER COLUMN", "TRUNCATE "):
        assert all(forbidden_snippet not in line for line in sql_lines), (
            "bootstrap SQL must stay additive/idempotent; found forbidden snippet "
            f"{forbidden_snippet!r}"
        )


def test_postgres_module_only_exports_bootstrap_helpers() -> None:
    assert postgres.__all__ == [
        "BOOTSTRAP_SQL_PATH",
        "BOOTSTRAP_TABLES",
        "read_bootstrap_sql",
    ]
