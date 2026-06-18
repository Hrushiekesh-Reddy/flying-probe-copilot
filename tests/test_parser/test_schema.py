"""Tests for src/flying_probe_copilot/db/schema.py.

Asserts the 9-table DuckDB schema is created correctly and idempotently.
"""

from __future__ import annotations

import duckdb
import pytest


@pytest.fixture
def con():
    """In-memory DuckDB connection for schema tests."""
    conn = duckdb.connect(":memory:")
    yield conn
    conn.close()


def test_init_database_creates_all_9_tables(con):
    """init_database must create exactly 9 tables with the canonical names."""
    from flying_probe_copilot.db.schema import TABLES, init_database

    init_database(con)
    rows = con.execute("SHOW TABLES").fetchall()
    actual_names = {r[0] for r in rows}
    expected_names = set(TABLES)
    assert actual_names == expected_names, (
        f"Expected tables {expected_names!r}, got {actual_names!r}"
    )
    assert len(TABLES) == 9, f"TABLES constant must have 9 entries, got {len(TABLES)}"


def test_init_database_idempotent_when_called_twice(con):
    """Calling init_database twice must not raise or create duplicate tables."""
    from flying_probe_copilot.db.schema import TABLES, init_database

    init_database(con)
    init_database(con)  # second call — must be safe
    rows = con.execute("SHOW TABLES").fetchall()
    assert len(rows) == 9, f"Expected 9 tables after double init, got {len(rows)}"


def test_each_table_has_expected_columns(con):
    """Every table must expose the locked set of column names."""
    from flying_probe_copilot.db.schema import init_database

    init_database(con)

    expected_columns: dict[str, set[str]] = {
        "boards": {
            "board_profile_id",
            "name",
            "component_count",
            "net_count",
            "typical_test_count",
        },
        "panels": {
            "panel_serial",
            "board_profile_id",
            "panel_position",
            "line_id",
            "shift",
            "scheduled_ts",
        },
        "operators": {"operator_id"},
        "components": {
            "component_id",
            "board_profile_id",
            "refdes",
            "component_family",
        },
        "tests": {
            "test_id",
            "board_profile_id",
            "block_designator",
            "record_type",
            "target_refdes",
        },
        "runs": {
            "run_id",
            "board_profile_id",
            "seed",
            "fault_rate",
            "fault_profile",
            "panel_count",
            "failing_boards",
            "ingested_at",
        },
        "test_runs": {
            "test_run_id",
            "panel_serial",
            "run_id",
            "operator_id",
            "btest_status",
            "start_ts",
            "end_ts",
            "duration_s",
            "multiple_test",
            "learning",
            "known_good",
            "board_number",
        },
        "measurements": {
            "measurement_id",
            "test_run_id",
            "test_id",
            "component_id",
            "record_type",
            "status",
            "measured_value",
            "limit_high",
            "limit_low",
            "limit_nominal",
            "substatus",
            "failing_vector",
            "failing_pin_count",
            "shorts_count",
            "opens_count",
            "phantoms_count",
            "pin_count",
        },
        "failures": {
            "failure_id",
            "measurement_id",
            "test_run_id",
            "panel_serial",
            "board_profile_id",
            "record_type",
            "status",
            "failure_category",
            "target_refdes",
        },
    }

    for table, cols in expected_columns.items():
        rows = con.execute(f"DESCRIBE {table}").fetchall()
        actual_cols = {r[0] for r in rows}
        missing = cols - actual_cols
        assert not missing, (
            f"Table '{table}' is missing columns: {missing!r}"
        )


def test_test_runs_operator_id_is_not_null(con):
    """test_runs.operator_id must be declared NOT NULL in the schema.

    Uses DESCRIBE (DuckDB introspection) to confirm the nullable column flag
    for operator_id is 'NO'. This is a locked contract — changing it requires
    a migration and owner sign-off.
    """
    from flying_probe_copilot.db.schema import init_database

    init_database(con)
    rows = con.execute("DESCRIBE test_runs").fetchall()
    # DESCRIBE returns: column_name, column_type, null, key, default, extra
    nullable_by_col = {r[0]: r[2] for r in rows}
    assert "operator_id" in nullable_by_col, (
        "Column 'operator_id' not found in test_runs"
    )
    assert nullable_by_col["operator_id"] == "NO", (
        f"test_runs.operator_id must be NOT NULL, "
        f"but nullable flag is {nullable_by_col['operator_id']!r}"
    )


def test_tables_constant_lists_all_9_canonical_names():
    """TABLES must contain exactly the 9 canonical table names."""
    from flying_probe_copilot.db.schema import TABLES

    canonical = {
        "boards",
        "panels",
        "operators",
        "components",
        "tests",
        "runs",
        "test_runs",
        "measurements",
        "failures",
    }
    assert set(TABLES) == canonical, (
        f"TABLES mismatch. Expected {canonical!r}, got {set(TABLES)!r}"
    )
