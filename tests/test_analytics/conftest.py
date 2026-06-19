"""Shared pytest fixtures for tests/test_analytics/.

NOTE on fixture duplication (R1-F resolution):
  The ``analytics_two_week_db`` fixture below is a hand-rebuilt inline copy of
  the ``two_week_db`` fixture from ``tests/test_parser/test_yield_query.py``.
  This duplication is intentional — it preserves the additive-only-edits
  guarantee (no edits to ``tests/test_parser/`` or ``tests/conftest.py``).
  When both fixture sets converge on a shared pattern in a future session,
  they should be promoted to a top-level ``tests/conftest.py`` helper.
"""

from __future__ import annotations

from datetime import datetime

import duckdb
import pytest

from flying_probe_copilot.db.schema import init_database


# ---------------------------------------------------------------------------
# empty_db fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def empty_db():
    """In-memory DuckDB connection with schema applied and zero data rows."""
    con = duckdb.connect(":memory:")
    init_database(con)
    yield con
    con.close()


# ---------------------------------------------------------------------------
# analytics_two_week_db fixture
#
# Inline rebuild of tests/test_parser/test_yield_query.py::two_week_db.
# Anchor = 2026-04-14T10:00:00 (MAX start_ts, week-2 data).
# 7-day window lower bound = 2026-04-07T10:00:00.
#
# Week 2 (inside window: 2026-04-08 to 2026-04-14):
#   small:  5 rows — 4 pass, 1 fail → yield 80%
#   medium: 3 rows — 2 pass, 1 fail → yield 66.7%
#
# Week 1 (outside window: 2026-03-31 to 2026-04-06):
#   small:  5 rows, all pass
#   medium: 3 rows, all pass
#
# operator_id is NULL on every test_run (BUG-007 placeholder).
# shift='A' and line_id='LINE-A' on every panel (BUG-007 placeholder).
# ---------------------------------------------------------------------------


@pytest.fixture
def analytics_two_week_db():
    """In-memory 2-week x 2-board fixture for analytics tests.

    Returns ``(con, ground_truth)`` where ``ground_truth`` is a dict with
    known counts for window-exclusion assertions.
    """
    con = duckdb.connect(":memory:")
    init_database(con)

    con.execute("""
        INSERT OR IGNORE INTO boards
            (board_profile_id, name, component_count, net_count, typical_test_count)
        VALUES
            ('small', 'small', 50, 80, 120),
            ('medium', 'medium', 200, 300, 450)
    """)

    con.execute("""
        INSERT INTO runs
            (run_id, board_profile_id, seed, fault_rate, fault_profile,
             panel_count, failing_boards)
        VALUES
            ('run_w1_small',  'small',  100, 0.05, 'random', 5, 0),
            ('run_w1_medium', 'medium', 101, 0.05, 'random', 3, 0),
            ('run_w2_small',  'small',  102, 0.10, 'random', 5, 1),
            ('run_w2_medium', 'medium', 103, 0.30, 'random', 3, 1)
    """)

    panels = [
        # W1 small (outside window)
        ("SYN-W1-S-001", "small",  1, "LINE-A", "A", "2026-03-31 08:00:00"),
        ("SYN-W1-S-002", "small",  2, "LINE-A", "A", "2026-04-01 08:00:00"),
        ("SYN-W1-S-003", "small",  3, "LINE-A", "A", "2026-04-02 08:00:00"),
        ("SYN-W1-S-004", "small",  4, "LINE-A", "A", "2026-04-03 08:00:00"),
        ("SYN-W1-S-005", "small",  5, "LINE-A", "A", "2026-04-04 08:00:00"),
        # W1 medium (outside window)
        ("SYN-W1-M-001", "medium", 1, "LINE-A", "A", "2026-04-01 09:00:00"),
        ("SYN-W1-M-002", "medium", 2, "LINE-A", "A", "2026-04-03 09:00:00"),
        ("SYN-W1-M-003", "medium", 3, "LINE-A", "A", "2026-04-05 09:00:00"),
        # W2 small (inside window)
        ("SYN-W2-S-001", "small",  1, "LINE-A", "A", "2026-04-08 10:00:00"),
        ("SYN-W2-S-002", "small",  2, "LINE-A", "A", "2026-04-09 10:00:00"),
        ("SYN-W2-S-003", "small",  3, "LINE-A", "A", "2026-04-10 10:00:00"),
        ("SYN-W2-S-004", "small",  4, "LINE-A", "A", "2026-04-12 10:00:00"),
        ("SYN-W2-S-005", "small",  5, "LINE-A", "A", "2026-04-13 10:00:00"),
        # W2 medium (inside window)
        ("SYN-W2-M-001", "medium", 1, "LINE-A", "A", "2026-04-11 10:00:00"),
        ("SYN-W2-M-002", "medium", 2, "LINE-A", "A", "2026-04-13 10:00:00"),
        ("SYN-W2-M-003", "medium", 3, "LINE-A", "A", "2026-04-14 10:00:00"),  # MAX anchor
    ]
    for serial, profile, pos, line, shift, ts in panels:
        con.execute(
            "INSERT INTO panels "
            "(panel_serial, board_profile_id, panel_position, line_id, shift, scheduled_ts) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [serial, profile, pos, line, shift, ts],
        )

    # btest_status=0 → PASS, btest_status=6 → FAIL_ANALOG
    test_runs_data = [
        # W1 small — all pass
        ("SYN-W1-S-001", "run_w1_small",  0, "2026-03-31 08:00:00", "2026-03-31 08:00:12"),
        ("SYN-W1-S-002", "run_w1_small",  0, "2026-04-01 08:00:00", "2026-04-01 08:00:12"),
        ("SYN-W1-S-003", "run_w1_small",  0, "2026-04-02 08:00:00", "2026-04-02 08:00:12"),
        ("SYN-W1-S-004", "run_w1_small",  0, "2026-04-03 08:00:00", "2026-04-03 08:00:12"),
        ("SYN-W1-S-005", "run_w1_small",  0, "2026-04-04 08:00:00", "2026-04-04 08:00:12"),
        # W1 medium — all pass
        ("SYN-W1-M-001", "run_w1_medium", 0, "2026-04-01 09:00:00", "2026-04-01 09:00:12"),
        ("SYN-W1-M-002", "run_w1_medium", 0, "2026-04-03 09:00:00", "2026-04-03 09:00:12"),
        ("SYN-W1-M-003", "run_w1_medium", 0, "2026-04-05 09:00:00", "2026-04-05 09:00:12"),
        # W2 small — 4 pass, 1 fail → yield 80%
        ("SYN-W2-S-001", "run_w2_small",  0, "2026-04-08 10:00:00", "2026-04-08 10:00:12"),
        ("SYN-W2-S-002", "run_w2_small",  0, "2026-04-09 10:00:00", "2026-04-09 10:00:12"),
        ("SYN-W2-S-003", "run_w2_small",  0, "2026-04-10 10:00:00", "2026-04-10 10:00:12"),
        ("SYN-W2-S-004", "run_w2_small",  6, "2026-04-12 10:00:00", "2026-04-12 10:00:12"),  # fail
        ("SYN-W2-S-005", "run_w2_small",  0, "2026-04-13 10:00:00", "2026-04-13 10:00:12"),
        # W2 medium — 2 pass, 1 fail → yield 66.7%
        ("SYN-W2-M-001", "run_w2_medium", 0, "2026-04-11 10:00:00", "2026-04-11 10:00:12"),
        ("SYN-W2-M-002", "run_w2_medium", 6, "2026-04-13 10:00:00", "2026-04-13 10:00:12"),  # fail
        ("SYN-W2-M-003", "run_w2_medium", 0, "2026-04-14 10:00:00", "2026-04-14 10:00:12"),
    ]
    for seq, (serial, run_id, status, start, end) in enumerate(test_runs_data, 1):
        con.execute(
            "INSERT INTO test_runs "
            "(test_run_id, panel_serial, run_id, operator_id, btest_status, "
            " start_ts, end_ts, duration_s, multiple_test, learning, known_good, board_number) "
            "VALUES (?, ?, ?, 'OP-001', ?, ?, ?, 12, false, false, false, 1)",
            [seq, serial, run_id, status, start, end],
        )

    ground_truth = {
        "small_w2_total":   5,
        "small_w2_passed":  4,
        "medium_w2_total":  3,
        "medium_w2_passed": 2,
        "small_w1_count":   5,
        "medium_w1_count":  3,
        # Anchor timestamp for custom-as_of tests
        "anchor": datetime(2026, 4, 14, 10, 0, 0),
        "week1_as_of": datetime(2026, 4, 7, 0, 0, 0),
    }

    yield con, ground_truth
    con.close()


# ---------------------------------------------------------------------------
# _build_pareto_db — internal helper function (not a fixture directly)
#
# R1-D resolution: per-test inline DB via helper, not a shared fixture.
# Each P-* test calls `_make_pareto_db` fixture (below), which returns this
# helper so tests can build their own deterministic DB.
# ---------------------------------------------------------------------------


def _build_pareto_db(failures_spec: list[dict]) -> duckdb.DuckDBPyConnection:
    """Create a fresh in-memory DuckDB with exactly the failures in ``failures_spec``.

    Each dict in ``failures_spec`` must have:
        - ``record_type``: str
        - ``failure_category``: str
        - ``target_refdes``: str | None
        - ``start_ts``: datetime

    One board ('small'), one panel per distinct start_ts (de-duplicated), one
    test_run per panel, and one failure row per spec entry are inserted.
    The helper inserts the minimum parent rows needed to satisfy FK expectations
    (DuckDB does not enforce FKs in Phase 1b DDL, but the joins in analytics
    SQL must still resolve).
    """
    con = duckdb.connect(":memory:")
    init_database(con)

    con.execute("""
        INSERT OR IGNORE INTO boards
            (board_profile_id, name, component_count, net_count, typical_test_count)
        VALUES ('small', 'small', 50, 80, 120)
    """)

    con.execute("""
        INSERT INTO runs
            (run_id, board_profile_id, seed, fault_rate, fault_profile,
             panel_count, failing_boards)
        VALUES ('run_pareto', 'small', 42, 0.10, 'random', 1, 1)
    """)

    # Build one panel+test_run per distinct start_ts.
    seen_ts: dict[datetime, int] = {}
    test_run_id_counter = 1

    for spec in failures_spec:
        ts: datetime = spec["start_ts"]
        if ts not in seen_ts:
            serial = f"PAR-{len(seen_ts) + 1:04d}"
            seen_ts[ts] = test_run_id_counter
            con.execute(
                "INSERT INTO panels "
                "(panel_serial, board_profile_id, panel_position, line_id, shift, scheduled_ts) "
                "VALUES (?, 'small', 1, 'LINE-A', 'A', ?)",
                [serial, ts.strftime("%Y-%m-%d %H:%M:%S")],
            )
            con.execute(
                "INSERT INTO test_runs "
                "(test_run_id, panel_serial, run_id, operator_id, btest_status, "
                " start_ts, end_ts, duration_s, multiple_test, learning, known_good, board_number) "
                "VALUES (?, ?, 'run_pareto', 'OP-001', 6, ?, ?, 12, false, false, false, 1)",
                [
                    test_run_id_counter,
                    serial,
                    ts.strftime("%Y-%m-%d %H:%M:%S"),
                    ts.strftime("%Y-%m-%d %H:%M:%S"),
                ],
            )
            test_run_id_counter += 1

    # Insert failures
    ts_list = list(seen_ts.keys())
    for fid, spec in enumerate(failures_spec, 1):
        ts = spec["start_ts"]
        tr_id = seen_ts[ts]
        serial = f"PAR-{ts_list.index(ts) + 1:04d}"
        refdes = spec.get("target_refdes")
        con.execute(
            "INSERT INTO failures "
            "(failure_id, measurement_id, test_run_id, panel_serial, board_profile_id, "
            " record_type, status, failure_category, target_refdes) "
            "VALUES (?, ?, ?, ?, 'small', ?, 1, ?, ?)",
            [fid, fid, tr_id, serial,
             spec["record_type"], spec["failure_category"], refdes],
        )

    return con


# ---------------------------------------------------------------------------
# _make_pareto_db fixture
#
# Returns the ``_build_pareto_db`` helper so tests can call it directly:
#
#     def test_foo(_make_pareto_db):
#         con = _make_pareto_db([{...}, ...])
#         ...
#         con.close()
# ---------------------------------------------------------------------------


@pytest.fixture
def _make_pareto_db():
    """Fixture that provides the ``_build_pareto_db`` helper to test functions."""
    return _build_pareto_db


# ---------------------------------------------------------------------------
# _build_spc_db — internal helper for SPC tests
#
# Accepts an explicit ordered list of (refdes, measured_value, start_ts) rows
# and inserts the full parent hierarchy required by the measurements join
# (boards → runs → panels → test_runs → components → measurements).
# ---------------------------------------------------------------------------


def _build_spc_db(
    rows: list[tuple[str, float | None, datetime]],
    *,
    board_profile_id: str = "small",
    extra_components: list[tuple[str, str]] | None = None,
) -> duckdb.DuckDBPyConnection:
    """Create a fresh in-memory DuckDB with exactly the measurement rows in ``rows``.

    Parameters
    ----------
    rows:
        List of ``(refdes, measured_value, start_ts)`` tuples.  Rows sharing
        the same ``start_ts`` are grouped into one panel / test_run (same
        ``panel_serial``), so that a single panel can hold multiple
        measurements for the same refdes (SPC-22 multi-row per panel).
    board_profile_id:
        The board profile to use for all inserted data.
    extra_components:
        Optional additional ``(refdes, component_family)`` entries to insert
        so that refdes-isolation tests (SPC-23) can populate a second refdes
        without measurements.

    Notes
    -----
    - Each unique ``(start_ts, panel_serial)`` pair maps to one test_run.
    - ``component_id`` is derived from the refdes string's position in the
      unique-refdes list, starting at 1.
    - ``measurement_id`` is a global counter across all rows.
    - The ``test_id`` column is required (NOT NULL in schema) — a single
      synthetic test_id=1 is shared for simplicity.
    """
    con = duckdb.connect(":memory:")
    init_database(con)

    con.execute("""
        INSERT OR IGNORE INTO boards
            (board_profile_id, name, component_count, net_count, typical_test_count)
        VALUES (?, ?, 50, 80, 120)
    """, [board_profile_id, board_profile_id])

    con.execute("""
        INSERT INTO runs
            (run_id, board_profile_id, seed, fault_rate, fault_profile,
             panel_count, failing_boards)
        VALUES ('run_spc', ?, 42, 0.05, 'random', 1, 0)
    """, [board_profile_id])

    # Insert a synthetic tests row (required for measurements FK).
    con.execute("""
        INSERT INTO tests
            (test_id, board_profile_id, block_designator, record_type, target_refdes)
        VALUES (1, ?, 'BLOCK-001', 'A-RES', NULL)
    """, [board_profile_id])

    # Collect unique refdes values to assign component_ids.
    seen_refdes: dict[str, int] = {}
    all_refdes = [r[0] for r in rows]
    for rd in all_refdes:
        if rd not in seen_refdes:
            seen_refdes[rd] = len(seen_refdes) + 1

    # Insert extra_components (e.g. for SPC-23 refdes isolation).
    if extra_components:
        for rd, family in extra_components:
            if rd not in seen_refdes:
                seen_refdes[rd] = len(seen_refdes) + 1

    # Insert components for every distinct refdes.
    for rd, cid in seen_refdes.items():
        con.execute("""
            INSERT OR IGNORE INTO components
                (component_id, board_profile_id, refdes, component_family)
            VALUES (?, ?, ?, 'resistor')
        """, [cid, board_profile_id, rd])

    # Group rows by start_ts to assign panel_serial / test_run_id.
    # Rows with the same start_ts go into the same panel/test_run.
    # Use (start_ts, panel_serial) pairs — derive panel_serial from
    # insertion order within unique timestamps.
    seen_ts: dict[datetime, tuple[str, int]] = {}  # ts → (panel_serial, test_run_id)
    tr_counter = 1

    for _, _, ts in rows:
        if ts not in seen_ts:
            serial = f"SPC-{len(seen_ts) + 1:04d}"
            seen_ts[ts] = (serial, tr_counter)
            con.execute(
                "INSERT INTO panels "
                "(panel_serial, board_profile_id, panel_position, line_id, shift, scheduled_ts) "
                "VALUES (?, ?, 1, 'LINE-A', 'A', ?)",
                [serial, board_profile_id, ts.strftime("%Y-%m-%d %H:%M:%S")],
            )
            con.execute(
                "INSERT INTO test_runs "
                "(test_run_id, panel_serial, run_id, operator_id, btest_status, "
                " start_ts, end_ts, duration_s, multiple_test, learning, known_good, board_number) "
                "VALUES (?, ?, 'run_spc', 'OP-001', 0, ?, ?, 12, false, false, false, 1)",
                [
                    tr_counter,
                    serial,
                    ts.strftime("%Y-%m-%d %H:%M:%S"),
                    ts.strftime("%Y-%m-%d %H:%M:%S"),
                ],
            )
            tr_counter += 1

    # Insert measurements.
    for mid, (refdes, measured_value, ts) in enumerate(rows, 1):
        serial, tr_id = seen_ts[ts]
        cid = seen_refdes[refdes]
        if measured_value is None:
            con.execute(
                "INSERT INTO measurements "
                "(measurement_id, test_run_id, test_id, component_id, record_type, "
                " status, measured_value) "
                "VALUES (?, ?, 1, ?, 'A-RES', 0, NULL)",
                [mid, tr_id, cid],
            )
        else:
            con.execute(
                "INSERT INTO measurements "
                "(measurement_id, test_run_id, test_id, component_id, record_type, "
                " status, measured_value) "
                "VALUES (?, ?, 1, ?, 'A-RES', 0, ?)",
                [mid, tr_id, cid, measured_value],
            )

    return con


@pytest.fixture
def _make_spc_db():
    """Fixture that provides the ``_build_spc_db`` helper to test functions."""
    return _build_spc_db


# ---------------------------------------------------------------------------
# _build_anomaly_db — internal helper for anomaly tests
#
# Builds groups across a ``by`` dimension with explicit per-group
# (total, failed) counts so anomaly tests can set exact rates.
# ---------------------------------------------------------------------------


def _build_anomaly_db(
    groups: list[dict],
    *,
    by: str = "board",
    anchor_ts: datetime | None = None,
    window_days: int = 30,
) -> duckdb.DuckDBPyConnection:
    """Create a fresh in-memory DuckDB with per-group (total, failed) counts.

    Parameters
    ----------
    groups:
        List of dicts with keys:
            - ``key``: group identifier (board_profile_id / shift / line_id /
              operator_id depending on ``by``)
            - ``total``: number of test_runs to insert for this group
            - ``failed``: number of those test_runs with btest_status != 0
            - ``in_window``: optional bool (default True); set False to place
              all runs for this group outside the window (for window-exclusion
              tests)
    by:
        Grouping dimension — determines which column to set per group.
    anchor_ts:
        Anchor timestamp (MAX start_ts).  Defaults to
        ``datetime(2026, 4, 14, 10, 0, 0)``.
    window_days:
        Window size in days; in-window runs are placed 1 day before anchor.
        Out-of-window runs are placed ``window_days + 2`` days before anchor.

    Notes
    -----
    - Each group gets a distinct board_profile_id so panels can be inserted
      (required for the panels JOIN in board/shift/line groupings).
    - For ``by='operator'``, multiple boards share panel rows but test_runs
      carry distinct operator_ids.
    - A unique run_id and panel_serial_prefix are derived per group.
    """
    con = duckdb.connect(":memory:")
    init_database(con)

    if anchor_ts is None:
        anchor_ts = datetime(2026, 4, 14, 10, 0, 0)

    from datetime import timedelta

    in_window_ts = anchor_ts - timedelta(days=1)
    out_window_ts = anchor_ts - timedelta(days=window_days + 2)

    tr_counter = 1
    panel_counter = 1

    for gidx, grp in enumerate(groups, 1):
        key = str(grp["key"])
        total = int(grp["total"])
        failed = int(grp["failed"])
        in_window = grp.get("in_window", True)
        run_ts = in_window_ts if in_window else out_window_ts

        # Each group gets its own board_profile_id (needed for panels FK).
        board_id = f"board_{gidx}"
        con.execute("""
            INSERT OR IGNORE INTO boards
                (board_profile_id, name, component_count, net_count, typical_test_count)
            VALUES (?, ?, 50, 80, 120)
        """, [board_id, board_id])

        con.execute("""
            INSERT INTO runs
                (run_id, board_profile_id, seed, fault_rate, fault_profile,
                 panel_count, failing_boards)
            VALUES (?, ?, 42, 0.05, 'random', ?, ?)
        """, [f"run_{gidx}", board_id, total, failed])

        # Determine the shift/line_id/board_profile_id to use for panels.
        if by == "board":
            panel_board_id = key
            panel_shift = "A"
            panel_line = "LINE-A"
        elif by == "shift":
            panel_board_id = board_id
            panel_shift = key
            panel_line = "LINE-A"
        elif by == "line":
            panel_board_id = board_id
            panel_shift = "A"
            panel_line = key
        else:  # operator — board_profile_id on panels is board_id
            panel_board_id = board_id
            panel_shift = "A"
            panel_line = "LINE-A"

        # Ensure the panel's board_profile_id exists in boards.
        con.execute("""
            INSERT OR IGNORE INTO boards
                (board_profile_id, name, component_count, net_count, typical_test_count)
            VALUES (?, ?, 50, 80, 120)
        """, [panel_board_id, panel_board_id])

        for i in range(total):
            serial = f"ANM-{panel_counter:06d}"
            panel_counter += 1
            btest_status = 6 if i < failed else 0

            # Offset each run by a few seconds so start_ts is unique per row.
            from datetime import timedelta as td
            row_ts = run_ts + td(seconds=i)

            con.execute(
                "INSERT INTO panels "
                "(panel_serial, board_profile_id, panel_position, line_id, shift, scheduled_ts) "
                "VALUES (?, ?, 1, ?, ?, ?)",
                [serial, panel_board_id, panel_line, panel_shift,
                 row_ts.strftime("%Y-%m-%d %H:%M:%S")],
            )

            # operator_id: use the key for operator grouping, 'OP-001' otherwise.
            op_id = key if by == "operator" else "OP-001"

            con.execute(
                "INSERT INTO test_runs "
                "(test_run_id, panel_serial, run_id, operator_id, btest_status, "
                " start_ts, end_ts, duration_s, multiple_test, learning, known_good, board_number) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 12, false, false, false, 1)",
                [
                    tr_counter,
                    serial,
                    f"run_{gidx}",
                    op_id,
                    btest_status,
                    row_ts.strftime("%Y-%m-%d %H:%M:%S"),
                    row_ts.strftime("%Y-%m-%d %H:%M:%S"),
                ],
            )
            tr_counter += 1

    return con


@pytest.fixture
def _make_anomaly_db():
    """Fixture that provides the ``_build_anomaly_db`` helper to test functions."""
    return _build_anomaly_db
