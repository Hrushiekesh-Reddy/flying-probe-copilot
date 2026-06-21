"""Shared pytest fixtures — repo root.

Per Revision 1 Resolution #BLOCKER-2: this file MUST NOT import from
``flying_probe_copilot.*`` at module top level. Doing so would break pytest
collection during early TDD phases when the package modules don't yet exist.
Model-dependent fixtures live in ``tests/test_generator/conftest.py`` or
inline in their test files.

``ui_db_path`` is a session-scoped fixture that builds a temp DuckDB for UI +
capture-script tests. Lifted here from ``tests/test_ui/conftest.py`` (MD-3,
Phase 4 slice 2 Decision Gate) so ``tests/test_scripts/`` can use it without
cross-package imports.
"""

from __future__ import annotations

import random
from datetime import datetime

import pytest


@pytest.fixture
def seeded_random() -> random.Random:
    """A ``random.Random`` instance seeded with 42 for deterministic tests."""
    return random.Random(42)


@pytest.fixture
def small_profile_dict() -> dict:
    """Plain-dict representation of the canonical ``small`` board profile.

    Mirrors spec lines ~308-310. Tests that need a real ``BoardProfile`` model
    instance should construct it from this dict inside the test or via a
    fixture in ``tests/test_generator/conftest.py``.
    """
    return {
        "id": "small",
        "name": "small",
        "component_count": 50,
        "net_count": 80,
        "typical_test_count": 120,
        "component_mix": {"R": 25, "C": 15, "U": 4, "D": 3, "L": 1, "Q": 2},
    }


@pytest.fixture
def medium_profile_dict() -> dict:
    """Plain-dict representation of the canonical ``medium`` board profile."""
    return {
        "id": "medium",
        "name": "medium",
        "component_count": 200,
        "net_count": 300,
        "typical_test_count": 450,
        "component_mix": {"R": 100, "C": 60, "U": 16, "D": 10, "L": 4, "Q": 10},
    }


@pytest.fixture
def fixed_timestamp() -> datetime:
    """Reference timestamp for deterministic time-based tests."""
    return datetime(2026, 4, 1, 8, 30, 0)


# ---------------------------------------------------------------------------
# ui_db_path — populated temp DuckDB for UI + capture-script tests
#
# Lifted from tests/test_ui/conftest.py (Phase 4 slice 2, MD-3).
# Used by tests/test_ui/ and tests/test_scripts/test_capture_real.py.
# Session-scope: built once per test session.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def ui_db_path(tmp_path_factory):
    """Write a temp file-backed DuckDB with synthetic panel data and return its path.

    Teardown: clears the ``get_connection`` cache resource before the temp
    directory is removed, so Windows releases the read-only file handle.

    Used by: tests/test_ui/ and tests/test_scripts/test_capture_real.py
    """
    # Lazy imports per BLOCKER-2 rule (must not import flying_probe_copilot at module top)
    import duckdb
    from flying_probe_copilot.db.schema import init_database
    from flying_probe_copilot.ui import data as ui_data

    tmp_dir = tmp_path_factory.mktemp("ui_db")
    db_path = str(tmp_dir / "test_ui.duckdb")

    con_w = duckdb.connect(db_path)
    init_database(con_w)
    _populate_ui_db(con_w)
    con_w.close()

    yield db_path

    try:
        ui_data.get_connection.clear()
    except Exception:
        pass


def _populate_ui_db(con) -> None:
    """Insert multi-board / multi-shift / multi-line / multi-operator rows.

    Identical to the helper in tests/test_ui/conftest.py (kept in sync).
    This copy lives here so ui_db_path can be at the root conftest level.
    """
    from datetime import datetime, timedelta

    con.execute("""
        INSERT INTO boards
            (board_profile_id, name, component_count, net_count, typical_test_count)
        VALUES
            ('small',  'small',   50,  80, 120),
            ('medium', 'medium', 200, 300, 450)
    """)

    con.execute("""
        INSERT OR IGNORE INTO operators (operator_id) VALUES ('OP-1'), ('OP-2')
    """)

    con.execute("""
        INSERT INTO runs
            (run_id, board_profile_id, seed, fault_rate, fault_profile,
             panel_count, failing_boards)
        VALUES
            ('run_ui_small',  'small',  42, 0.05, 'random', 40, 5),
            ('run_ui_medium', 'medium', 43, 0.10, 'random', 20, 4)
    """)

    con.execute("""
        INSERT INTO components
            (component_id, board_profile_id, refdes, component_family)
        VALUES
            (1, 'small',  'R1', 'resistor'),
            (2, 'small',  'C1', 'capacitor'),
            (3, 'medium', 'U1', 'ic')
    """)

    con.execute("""
        INSERT INTO tests
            (test_id, board_profile_id, block_designator, record_type, target_refdes)
        VALUES
            (1, 'small',  'BLK-001', 'A-RES', 'R1'),
            (2, 'small',  'BLK-002', 'A-CAP', 'C1'),
            (3, 'medium', 'BLK-003', 'A-IC',  'U1')
    """)

    anchor = datetime(2026, 4, 14, 10, 0, 0)

    panel_rows = []
    test_run_rows = []
    tr_id = 1
    panel_id = 1

    small_plan = [
        ("A", "LINE-A", "OP-1", 0), ("A", "LINE-A", "OP-2", 0),
        ("A", "LINE-B", "OP-1", 0), ("A", "LINE-B", "OP-2", 0),
        ("A", "LINE-A", "OP-1", 0), ("A", "LINE-B", "OP-2", 0),
        ("A", "LINE-A", "OP-1", 0), ("A", "LINE-B", "OP-2", 0),
        ("B", "LINE-A", "OP-1", 0), ("B", "LINE-A", "OP-2", 0),
        ("B", "LINE-B", "OP-1", 0), ("B", "LINE-B", "OP-2", 0),
        ("B", "LINE-A", "OP-1", 0), ("B", "LINE-B", "OP-2", 0),
        ("B", "LINE-A", "OP-1", 0), ("B", "LINE-B", "OP-2", 0),
        ("C", "LINE-A", "OP-1", 6), ("C", "LINE-A", "OP-2", 6),
        ("C", "LINE-B", "OP-1", 6), ("C", "LINE-B", "OP-2", 6),
        ("C", "LINE-A", "OP-1", 6), ("C", "LINE-B", "OP-2", 6),
        ("C", "LINE-A", "OP-1", 0), ("C", "LINE-B", "OP-2", 0),
    ]

    for i, (shift, line, op, status) in enumerate(small_plan):
        serial = f"UI-S-{panel_id:04d}"
        panel_id += 1
        ts = anchor - timedelta(days=7, seconds=i * 300)
        start_str = ts.strftime("%Y-%m-%d %H:%M:%S")
        end_str = (ts + timedelta(seconds=12)).strftime("%Y-%m-%d %H:%M:%S")
        sched_str = start_str
        panel_rows.append((serial, "small", i + 1, line, shift, sched_str))
        test_run_rows.append((tr_id, serial, "run_ui_small", op, status, start_str, end_str))
        tr_id += 1

    medium_plan = [
        ("A", "LINE-A", "OP-1", 0), ("A", "LINE-A", "OP-2", 0),
        ("A", "LINE-A", "OP-1", 6), ("A", "LINE-A", "OP-2", 0),
        ("B", "LINE-B", "OP-1", 0), ("B", "LINE-B", "OP-2", 0),
        ("B", "LINE-B", "OP-1", 6), ("B", "LINE-B", "OP-2", 0),
    ]
    for i, (shift, line, op, status) in enumerate(medium_plan):
        serial = f"UI-M-{panel_id:04d}"
        panel_id += 1
        ts = anchor - timedelta(days=5, seconds=i * 600)
        start_str = ts.strftime("%Y-%m-%d %H:%M:%S")
        end_str = (ts + timedelta(seconds=12)).strftime("%Y-%m-%d %H:%M:%S")
        sched_str = start_str
        panel_rows.append((serial, "medium", i + 1, line, shift, sched_str))
        test_run_rows.append((tr_id, serial, "run_ui_medium", op, status, start_str, end_str))
        tr_id += 1

    for row in panel_rows:
        con.execute(
            "INSERT INTO panels "
            "(panel_serial, board_profile_id, panel_position, line_id, shift, scheduled_ts) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            list(row),
        )

    for row in test_run_rows:
        con.execute(
            "INSERT INTO test_runs "
            "(test_run_id, panel_serial, run_id, operator_id, btest_status, "
            " start_ts, end_ts, duration_s, multiple_test, learning, known_good, board_number) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 12, false, false, false, 1)",
            list(row),
        )

    spc_values = [
        10.1, 9.9, 10.0, 10.2, 9.8, 10.1, 10.3, 9.7, 10.0, 9.9,
        10.1, 10.0, 9.8, 10.2, 10.1, 9.9, 10.0, 10.2, 9.8, 10.1,
    ]
    for mid, (trid, val) in enumerate(zip(range(1, 21), spc_values), start=1):
        con.execute(
            "INSERT INTO measurements "
            "(measurement_id, test_run_id, test_id, component_id, record_type, "
            " status, measured_value) "
            "VALUES (?, ?, 1, 1, 'A-RES', 0, ?)",
            [mid, trid, val],
        )

    con.execute(
        "INSERT INTO measurements "
        "(measurement_id, test_run_id, test_id, component_id, record_type, "
        " status, measured_value) "
        "VALUES (21, 21, 1, 1, 'A-RES', 0, NULL)"
    )

    con.execute(
        "INSERT INTO measurements "
        "(measurement_id, test_run_id, test_id, component_id, record_type, "
        " status, measured_value) "
        "VALUES (22, 1, 2, 2, 'A-CAP', 0, 47.5)"
    )

    fid = 1
    failure_tr_ids = [17, 18, 19, 20, 21, 22, 27, 31]
    for ftrid in failure_tr_ids:
        con.execute(
            "INSERT INTO failures "
            "(failure_id, measurement_id, test_run_id, panel_serial, "
            " board_profile_id, record_type, status, failure_category, target_refdes) "
            "SELECT ?, ?, tr.test_run_id, tr.panel_serial, "
            "       p.board_profile_id, 'A-RES', 6, 'FAIL_ANALOG', 'R1' "
            "FROM test_runs tr "
            "JOIN panels p ON p.panel_serial = tr.panel_serial "
            "WHERE tr.test_run_id = ?",
            [fid, fid, ftrid],
        )
        fid += 1
