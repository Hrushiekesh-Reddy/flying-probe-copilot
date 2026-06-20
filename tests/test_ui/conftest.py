"""Shared fixtures for tests/test_ui/.

``ui_db_path`` builds a temp file-backed DuckDB with:
  - 2 boards (small, medium)
  - panels across shifts A/B/C, lines LINE-A/LINE-B, operators OP-1/OP-2
  - test_runs: shift C has an elevated failure rate so z_score_anomalies flags it
  - components + >=15 measurements with non-null measured_value for
    (board_profile_id='small', refdes='R1') — required by individuals_chart
  - matching failures rows

Teardown calls ``data.get_connection.clear()`` BEFORE the temp file is removed
so Windows releases the read-only file handle before deletion.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import duckdb
import pytest

from flying_probe_copilot.db.schema import init_database


# ---------------------------------------------------------------------------
# Helper: insert all required rows into a writable connection
# ---------------------------------------------------------------------------

def _populate_ui_db(con: duckdb.DuckDBPyConnection) -> None:
    """Insert multi-board / multi-shift / multi-line / multi-operator rows."""

    # --- boards ---
    con.execute("""
        INSERT INTO boards
            (board_profile_id, name, component_count, net_count, typical_test_count)
        VALUES
            ('small',  'small',   50,  80, 120),
            ('medium', 'medium', 200, 300, 450)
    """)

    # --- operators ---
    con.execute("""
        INSERT OR IGNORE INTO operators (operator_id) VALUES ('OP-1'), ('OP-2')
    """)

    # --- runs ---
    con.execute("""
        INSERT INTO runs
            (run_id, board_profile_id, seed, fault_rate, fault_profile,
             panel_count, failing_boards)
        VALUES
            ('run_ui_small',  'small',  42, 0.05, 'random', 40, 5),
            ('run_ui_medium', 'medium', 43, 0.10, 'random', 20, 4)
    """)

    # --- components ---
    # component_id 1: small/R1 (will have >=15 measurements)
    # component_id 2: small/C1 (few measurements)
    # component_id 3: medium/U1 (medium board)
    con.execute("""
        INSERT INTO components
            (component_id, board_profile_id, refdes, component_family)
        VALUES
            (1, 'small',  'R1', 'resistor'),
            (2, 'small',  'C1', 'capacitor'),
            (3, 'medium', 'U1', 'ic')
    """)

    # --- synthetic tests row (needed for measurements FK) ---
    con.execute("""
        INSERT INTO tests
            (test_id, board_profile_id, block_designator, record_type, target_refdes)
        VALUES
            (1, 'small',  'BLK-001', 'A-RES', 'R1'),
            (2, 'small',  'BLK-002', 'A-CAP', 'C1'),
            (3, 'medium', 'BLK-003', 'A-IC',  'U1')
    """)

    # --- anchor timestamp ---
    # All in-window runs are placed in the last 30 days relative to anchor.
    anchor = datetime(2026, 4, 14, 10, 0, 0)

    # We build panels + test_runs with these combinations:
    #   - board=small, shifts A/B/C, lines LINE-A/LINE-B, ops OP-1/OP-2
    #   - shift A: 8 panels, 0 fail  → rate 0.0
    #   - shift B: 8 panels, 0 fail  → rate 0.0
    #   - shift C: 8 panels, 6 fail  → rate 0.75  (elevated — anomaly flag expected)
    #   - medium board: 8 panels, 2 fail

    panel_rows = []
    test_run_rows = []
    tr_id = 1
    panel_id = 1

    # small board panels: shift A, B, C with 2 lines and 2 operators interleaved
    small_plan = [
        # (shift, line, op, btest_status)
        ("A", "LINE-A", "OP-1", 0),
        ("A", "LINE-A", "OP-2", 0),
        ("A", "LINE-B", "OP-1", 0),
        ("A", "LINE-B", "OP-2", 0),
        ("A", "LINE-A", "OP-1", 0),
        ("A", "LINE-B", "OP-2", 0),
        ("A", "LINE-A", "OP-1", 0),
        ("A", "LINE-B", "OP-2", 0),
        ("B", "LINE-A", "OP-1", 0),
        ("B", "LINE-A", "OP-2", 0),
        ("B", "LINE-B", "OP-1", 0),
        ("B", "LINE-B", "OP-2", 0),
        ("B", "LINE-A", "OP-1", 0),
        ("B", "LINE-B", "OP-2", 0),
        ("B", "LINE-A", "OP-1", 0),
        ("B", "LINE-B", "OP-2", 0),
        # shift C — 6 of 8 fail (elevated anomaly)
        ("C", "LINE-A", "OP-1", 6),
        ("C", "LINE-A", "OP-2", 6),
        ("C", "LINE-B", "OP-1", 6),
        ("C", "LINE-B", "OP-2", 6),
        ("C", "LINE-A", "OP-1", 6),
        ("C", "LINE-B", "OP-2", 6),
        ("C", "LINE-A", "OP-1", 0),
        ("C", "LINE-B", "OP-2", 0),
    ]

    for i, (shift, line, op, status) in enumerate(small_plan):
        serial = f"UI-S-{panel_id:04d}"
        panel_id += 1
        ts = anchor - timedelta(days=7, seconds=i * 300)
        start_str = ts.strftime("%Y-%m-%d %H:%M:%S")
        end_str = (ts + timedelta(seconds=12)).strftime("%Y-%m-%d %H:%M:%S")
        sched_str = start_str

        panel_rows.append(
            (serial, "small", i + 1, line, shift, sched_str)
        )
        test_run_rows.append(
            (tr_id, serial, "run_ui_small", op, status, start_str, end_str)
        )
        tr_id += 1

    # medium board panels: shift A/B, line LINE-A, operator OP-1
    medium_plan = [
        ("A", "LINE-A", "OP-1", 0),
        ("A", "LINE-A", "OP-2", 0),
        ("A", "LINE-A", "OP-1", 6),
        ("A", "LINE-A", "OP-2", 0),
        ("B", "LINE-B", "OP-1", 0),
        ("B", "LINE-B", "OP-2", 0),
        ("B", "LINE-B", "OP-1", 6),
        ("B", "LINE-B", "OP-2", 0),
    ]
    for i, (shift, line, op, status) in enumerate(medium_plan):
        serial = f"UI-M-{panel_id:04d}"
        panel_id += 1
        ts = anchor - timedelta(days=5, seconds=i * 600)
        start_str = ts.strftime("%Y-%m-%d %H:%M:%S")
        end_str = (ts + timedelta(seconds=12)).strftime("%Y-%m-%d %H:%M:%S")
        sched_str = start_str

        panel_rows.append(
            (serial, "medium", i + 1, line, shift, sched_str)
        )
        test_run_rows.append(
            (tr_id, serial, "run_ui_medium", op, status, start_str, end_str)
        )
        tr_id += 1

    # Insert panels
    for row in panel_rows:
        con.execute(
            "INSERT INTO panels "
            "(panel_serial, board_profile_id, panel_position, line_id, shift, scheduled_ts) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            list(row),
        )

    # Insert test_runs
    for row in test_run_rows:
        con.execute(
            "INSERT INTO test_runs "
            "(test_run_id, panel_serial, run_id, operator_id, btest_status, "
            " start_ts, end_ts, duration_s, multiple_test, learning, known_good, board_number) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 12, false, false, false, 1)",
            list(row),
        )

    # --- measurements: >=15 non-null measured_value for small/R1 ---
    # Use the first 20 small panel test_run_ids (tr_id started at 1, first 24 are small)
    # We insert 20 measurements for R1, each on a different test_run
    # test_run_ids for small panels are 1..24, use the first 20
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

    # A few null measurements (should be excluded by individuals_chart)
    con.execute(
        "INSERT INTO measurements "
        "(measurement_id, test_run_id, test_id, component_id, record_type, "
        " status, measured_value) "
        "VALUES (21, 21, 1, 1, 'A-RES', 0, NULL)"
    )

    # A measurement for C1 (different refdes — for distinct_refdes test)
    con.execute(
        "INSERT INTO measurements "
        "(measurement_id, test_run_id, test_id, component_id, record_type, "
        " status, measured_value) "
        "VALUES (22, 1, 2, 2, 'A-CAP', 0, 47.5)"
    )

    # --- failures rows ---
    # Insert failure rows for test_runs with btest_status != 0
    # Shift C failures: test_run_ids 17..22 (first 6 shift-C rows)
    fid = 1
    failure_tr_ids = [17, 18, 19, 20, 21, 22,  # shift C small
                      27, 31]                    # medium board failures (3rd + 7th medium)
    for ftrid in failure_tr_ids:
        # Determine panel_serial: build a mapping from tr_id
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


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def ui_db_path(tmp_path_factory):
    """Write a temp file-backed DuckDB and return its path.

    Teardown: clears the ``get_connection`` cache resource before the temp
    directory is removed, so Windows releases the read-only handle.
    """
    # Import here (after the data module exists) so the fixture resolves lazily.
    from flying_probe_copilot.ui import data as ui_data

    tmp_dir = tmp_path_factory.mktemp("ui_db")
    db_path = str(tmp_dir / "test_ui.duckdb")

    # Build the DB with a writable connection, then close it.
    con_w = duckdb.connect(db_path)
    init_database(con_w)
    _populate_ui_db(con_w)
    con_w.close()

    yield db_path

    # Teardown: release the cache_resource handle before tmp dir removal.
    try:
        ui_data.get_connection.clear()
    except Exception:
        pass
