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
