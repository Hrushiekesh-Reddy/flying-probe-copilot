"""Tests for yield_over_time() — Phase 2 Analytics.

Test IDs map to the Test-Case Plan (2026-06-16-test-plan.md):
  Y-01 … Y-15 as listed there, plus R1-K boundary tests and R1-L / R1-M
  validation tests added by Revision 1.

The canonical SQL (_YIELD_BY_BOARD_LAST_WEEK_SQL) is copied inline from
tests/test_parser/test_yield_query.py per R1-F (no cross-package import).
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import duckdb
import pytest

from flying_probe_copilot.analytics import YieldRow, yield_over_time
from flying_probe_copilot.db.schema import init_database

# ---------------------------------------------------------------------------
# Canonical SQL — copied from tests/test_parser/test_yield_query.py
# (R1-F: no cross-package import; duplication is intentional)
# ---------------------------------------------------------------------------

_YIELD_BY_BOARD_LAST_WEEK_SQL = """
WITH anchor_cte AS (
  SELECT MAX(start_ts) AS anchor FROM test_runs
)
SELECT
  p.board_profile_id,
  COUNT(*)                                                        AS total,
  SUM(CASE WHEN tr.btest_status = 0 THEN 1 ELSE 0 END)            AS passed,
  100.0 * SUM(CASE WHEN tr.btest_status = 0 THEN 1 ELSE 0 END)
        / COUNT(*)                                                AS yield_pct
FROM test_runs tr
JOIN panels p ON p.panel_serial = tr.panel_serial
WHERE tr.start_ts >= (SELECT anchor - INTERVAL 7 DAY FROM anchor_cte)
GROUP BY p.board_profile_id
ORDER BY p.board_profile_id
"""

# ---------------------------------------------------------------------------
# Y-01 — matches canonical notebook query row-for-row
# ---------------------------------------------------------------------------


def test_yield_by_board_matches_canonical_notebook_query(analytics_two_week_db):
    """Y-01: yield_over_time(group_by='board') matches _YIELD_BY_BOARD_LAST_WEEK_SQL
    row-for-row on the two-week fixture.

    Per R1-J, scoped to group_by='board' only (parser BUG-007 placeholder
    data would make shift/line/operator assertions meaningless here).
    """
    con, _gt = analytics_two_week_db

    sql_rows = con.execute(_YIELD_BY_BOARD_LAST_WEEK_SQL).fetchall()
    # sql_rows: [(board_profile_id, total, passed, yield_pct), ...]

    fn_rows: list[YieldRow] = yield_over_time(con, window_days=7, group_by="board")

    assert len(fn_rows) == len(sql_rows), (
        f"Row count mismatch: function returned {len(fn_rows)}, SQL returned {len(sql_rows)}"
    )

    # Both ordered by group_key / board_profile_id ASC (L15 + R1-B)
    for fn_row, sql_row in zip(fn_rows, sql_rows):
        board_id, total, passed, yield_pct = sql_row
        assert fn_row.group_key == board_id, (
            f"group_key mismatch: {fn_row.group_key!r} != {board_id!r}"
        )
        assert fn_row.total == total, (
            f"total mismatch for {board_id}: {fn_row.total} != {total}"
        )
        assert fn_row.passed == passed, (
            f"passed mismatch for {board_id}: {fn_row.passed} != {passed}"
        )
        assert math.isclose(fn_row.yield_pct, yield_pct, rel_tol=1e-9), (
            f"yield_pct mismatch for {board_id}: {fn_row.yield_pct} != {yield_pct}"
        )


# ---------------------------------------------------------------------------
# Y-02 — empty DB returns []
# ---------------------------------------------------------------------------


def test_yield_with_empty_db_returns_empty_list(empty_db):
    """Y-02: yield_over_time on an empty DB returns [] without raising."""
    result = yield_over_time(empty_db, group_by="board")
    assert result == [], f"Expected [], got {result!r}"


# ---------------------------------------------------------------------------
# Y-03 — empty DB returns [] for every group_by value
# ---------------------------------------------------------------------------


def test_yield_with_empty_db_returns_empty_list_for_every_group_by(empty_db):
    """Y-03: All four group_by values return [] on an empty DB."""
    for gb in ("board", "shift", "operator", "line"):
        result = yield_over_time(empty_db, group_by=gb)
        assert result == [], (
            f"Expected [] for group_by={gb!r} on empty DB, got {result!r}"
        )


# ---------------------------------------------------------------------------
# Y-04 — window excludes rows outside lookback
# ---------------------------------------------------------------------------


def test_yield_window_excludes_old_rows(analytics_two_week_db):
    """Y-04: Week-1 rows (> 7 days before MAX start_ts) must not be counted."""
    con, gt = analytics_two_week_db

    rows = yield_over_time(con, window_days=7, group_by="board")
    result = {r.group_key: r for r in rows}

    assert result["small"].total == gt["small_w2_total"], (
        f"small total: expected {gt['small_w2_total']}, got {result['small'].total}"
    )
    assert result["medium"].total == gt["medium_w2_total"], (
        f"medium total: expected {gt['medium_w2_total']}, got {result['medium'].total}"
    )


# ---------------------------------------------------------------------------
# Y-05 — custom as_of overrides DB anchor
# ---------------------------------------------------------------------------


def test_yield_with_custom_as_of_uses_caller_value(analytics_two_week_db):
    """Y-05: Caller-supplied as_of is used as anchor instead of MAX(start_ts)."""
    con, gt = analytics_two_week_db

    # as_of falls just before any week-2 row; only week-1 data falls in window
    as_of = gt["week1_as_of"]  # datetime(2026, 4, 7, 0, 0, 0)
    rows = yield_over_time(con, window_days=7, group_by="board", as_of=as_of)

    # Week-1 data is all-pass, totals <= 5 (small) and <= 3 (medium)
    result = {r.group_key: r for r in rows}

    # At least one board should be present (week-1 data is in window [2026-03-31, 2026-04-07])
    assert len(rows) > 0, "Expected at least one row for week-1 window"

    if "small" in result:
        assert result["small"].total <= gt["small_w1_count"], (
            f"small total {result['small'].total} exceeds w1 count {gt['small_w1_count']}"
        )
    if "medium" in result:
        assert result["medium"].total <= gt["medium_w1_count"], (
            f"medium total {result['medium'].total} exceeds w1 count {gt['medium_w1_count']}"
        )


# ---------------------------------------------------------------------------
# Y-06 — invalid group_by raises ValueError
# ---------------------------------------------------------------------------


def test_yield_invalid_group_by_raises_value_error(analytics_two_week_db):
    """Y-06: group_by='day' (out-of-scope) raises ValueError listing allowed values."""
    con, _gt = analytics_two_week_db

    with pytest.raises(ValueError, match=r"group_by"):
        yield_over_time(con, group_by="day")


# ---------------------------------------------------------------------------
# Y-08 — board group_by has empty placeholder tuple
# ---------------------------------------------------------------------------


def test_yield_by_board_has_empty_placeholder_tuple(analytics_two_week_db):
    """Y-08: group_by='board' rows always have placeholder_fields == ()."""
    con, _gt = analytics_two_week_db

    rows = yield_over_time(con, group_by="board")
    assert len(rows) > 0, "Fixture should return non-empty result"
    for row in rows:
        assert row.placeholder_fields == (), (
            f"Expected () for board group, got {row.placeholder_fields!r}"
        )


# ---------------------------------------------------------------------------
# Y-09 — shift group_by marks placeholder
# ---------------------------------------------------------------------------


def test_yield_by_shift_marks_placeholder(analytics_two_week_db):
    """Y-09: group_by='shift' rows carry placeholder_fields == ('shift',)."""
    con, _gt = analytics_two_week_db

    rows = yield_over_time(con, group_by="shift")
    assert len(rows) > 0, "Fixture should return at least one shift group"
    for row in rows:
        assert row.placeholder_fields == ("shift",), (
            f"Expected ('shift',), got {row.placeholder_fields!r}"
        )


# ---------------------------------------------------------------------------
# Y-10 — line group_by marks placeholder
# ---------------------------------------------------------------------------


def test_yield_by_line_marks_placeholder(analytics_two_week_db):
    """Y-10: group_by='line' rows carry placeholder_fields == ('line_id',)."""
    con, _gt = analytics_two_week_db

    rows = yield_over_time(con, group_by="line")
    assert len(rows) > 0, "Fixture should return at least one line group"
    for row in rows:
        assert row.placeholder_fields == ("line_id",), (
            f"Expected ('line_id',), got {row.placeholder_fields!r}"
        )


# ---------------------------------------------------------------------------
# Y-11 — operator group_by marks placeholder
# ---------------------------------------------------------------------------


def test_yield_by_operator_marks_placeholder(analytics_two_week_db):
    """Y-11: group_by='operator' rows carry placeholder_fields == ('operator_id',)."""
    con, _gt = analytics_two_week_db

    rows = yield_over_time(con, group_by="operator")
    assert len(rows) > 0, "Fixture should return at least one operator group"
    for row in rows:
        assert row.placeholder_fields == ("operator_id",), (
            f"Expected ('operator_id',), got {row.placeholder_fields!r}"
        )


# ---------------------------------------------------------------------------
# Y-12 — NULL operator_id bucketed as '<unknown>'
# ---------------------------------------------------------------------------


def test_yield_null_operator_id_bucketed_as_unknown(analytics_two_week_db):
    """Y-12: NULL operator_id → group_key == '<unknown>' (L14)."""
    con, _gt = analytics_two_week_db

    rows = yield_over_time(con, group_by="operator")
    # Fixture has all operator_id NULL → should produce exactly one group
    assert len(rows) == 1, (
        f"Expected 1 group for all-NULL operators, got {len(rows)}"
    )
    assert rows[0].group_key == "<unknown>", (
        f"Expected '<unknown>', got {rows[0].group_key!r}"
    )


# ---------------------------------------------------------------------------
# Y-13 — tiebreak orders by group_key ASC
# ---------------------------------------------------------------------------


def test_yield_tiebreak_orders_by_group_key_asc():
    """Y-13: When total/passed/yield_pct tie, rows are sorted by group_key ASC (L15)."""
    con = duckdb.connect(":memory:")
    init_database(con)

    con.execute("""
        INSERT OR IGNORE INTO boards
            (board_profile_id, name, component_count, net_count, typical_test_count)
        VALUES ('small', 'small', 50, 80, 120), ('medium', 'medium', 200, 300, 450)
    """)
    con.execute("""
        INSERT INTO runs
            (run_id, board_profile_id, seed, fault_rate, fault_profile, panel_count, failing_boards)
        VALUES ('run_s', 'small', 1, 0.0, 'random', 2, 0),
               ('run_m', 'medium', 2, 0.0, 'random', 2, 0)
    """)
    # 2 panels per board, both pass → identical yield 100%
    panels_data = [
        ("TIE-S-001", "small",  1, "LINE-A", "A", "2026-05-01 10:00:00"),
        ("TIE-S-002", "small",  2, "LINE-A", "A", "2026-05-02 10:00:00"),
        ("TIE-M-001", "medium", 1, "LINE-A", "A", "2026-05-01 10:00:00"),
        ("TIE-M-002", "medium", 2, "LINE-A", "A", "2026-05-02 10:00:00"),
    ]
    for i, (serial, profile, pos, line, shift, ts) in enumerate(panels_data, 1):
        con.execute(
            "INSERT INTO panels "
            "(panel_serial, board_profile_id, panel_position, line_id, shift, scheduled_ts) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [serial, profile, pos, line, shift, ts],
        )

    runs_data = [
        (1, "TIE-S-001", "run_s", "2026-05-01 10:00:00"),
        (2, "TIE-S-002", "run_s", "2026-05-02 10:00:00"),
        (3, "TIE-M-001", "run_m", "2026-05-01 10:00:00"),
        (4, "TIE-M-002", "run_m", "2026-05-02 10:00:00"),
    ]
    for tr_id, serial, run_id, ts in runs_data:
        con.execute(
            "INSERT INTO test_runs "
            "(test_run_id, panel_serial, run_id, operator_id, btest_status, "
            " start_ts, end_ts, duration_s, multiple_test, learning, known_good, board_number) "
            "VALUES (?, ?, ?, NULL, 0, ?, ?, 12, false, false, false, 1)",
            [tr_id, serial, run_id, ts, ts],
        )

    rows = yield_over_time(con, group_by="board")
    con.close()

    assert len(rows) == 2, f"Expected 2 rows, got {len(rows)}"
    # Alphabetical: medium < small
    assert rows[0].group_key == "medium", (
        f"Expected rows[0].group_key='medium', got {rows[0].group_key!r}"
    )
    assert rows[1].group_key == "small", (
        f"Expected rows[1].group_key='small', got {rows[1].group_key!r}"
    )


# ---------------------------------------------------------------------------
# R1-K — boundary inclusion: lower bound
# ---------------------------------------------------------------------------


def test_yield_row_at_lower_window_bound_included():
    """R1-K lower: A row at start_ts == as_of - window_days is INCLUDED (L4)."""
    con = duckdb.connect(":memory:")
    init_database(con)

    con.execute("""
        INSERT OR IGNORE INTO boards
            (board_profile_id, name, component_count, net_count, typical_test_count)
        VALUES ('small', 'small', 50, 80, 120)
    """)
    con.execute("""
        INSERT INTO runs
            (run_id, board_profile_id, seed, fault_rate, fault_profile, panel_count, failing_boards)
        VALUES ('run_lb', 'small', 1, 0.0, 'random', 1, 0)
    """)
    con.execute("""
        INSERT INTO panels
            (panel_serial, board_profile_id, panel_position, line_id, shift, scheduled_ts)
        VALUES ('LB-001', 'small', 1, 'LINE-A', 'A', '2026-05-01 00:00:00')
    """)

    as_of = datetime(2026, 5, 8, 0, 0, 0)
    lower_bound_ts = "2026-05-01 00:00:00"  # exactly as_of - 7 days

    con.execute(
        "INSERT INTO test_runs "
        "(test_run_id, panel_serial, run_id, operator_id, btest_status, "
        " start_ts, end_ts, duration_s, multiple_test, learning, known_good, board_number) "
        "VALUES (1, 'LB-001', 'run_lb', NULL, 0, ?, ?, 12, false, false, false, 1)",
        [lower_bound_ts, lower_bound_ts],
    )

    rows = yield_over_time(con, window_days=7, group_by="board", as_of=as_of)
    con.close()

    assert len(rows) == 1, (
        f"Expected row at lower bound to be included, got {len(rows)} rows"
    )
    assert rows[0].total == 1, f"Expected total=1, got {rows[0].total}"


# ---------------------------------------------------------------------------
# R1-K — boundary inclusion: upper bound
# ---------------------------------------------------------------------------


def test_yield_row_at_upper_window_bound_included():
    """R1-K upper: A row at start_ts == as_of is INCLUDED (L4)."""
    con = duckdb.connect(":memory:")
    init_database(con)

    con.execute("""
        INSERT OR IGNORE INTO boards
            (board_profile_id, name, component_count, net_count, typical_test_count)
        VALUES ('small', 'small', 50, 80, 120)
    """)
    con.execute("""
        INSERT INTO runs
            (run_id, board_profile_id, seed, fault_rate, fault_profile, panel_count, failing_boards)
        VALUES ('run_ub', 'small', 1, 0.0, 'random', 1, 0)
    """)
    con.execute("""
        INSERT INTO panels
            (panel_serial, board_profile_id, panel_position, line_id, shift, scheduled_ts)
        VALUES ('UB-001', 'small', 1, 'LINE-A', 'A', '2026-05-08 12:00:00')
    """)

    as_of = datetime(2026, 5, 8, 12, 0, 0)
    upper_bound_ts = "2026-05-08 12:00:00"  # exactly as_of

    con.execute(
        "INSERT INTO test_runs "
        "(test_run_id, panel_serial, run_id, operator_id, btest_status, "
        " start_ts, end_ts, duration_s, multiple_test, learning, known_good, board_number) "
        "VALUES (1, 'UB-001', 'run_ub', NULL, 0, ?, ?, 12, false, false, false, 1)",
        [upper_bound_ts, upper_bound_ts],
    )

    rows = yield_over_time(con, window_days=7, group_by="board", as_of=as_of)
    con.close()

    assert len(rows) == 1, (
        f"Expected row at upper bound to be included, got {len(rows)} rows"
    )
    assert rows[0].total == 1, f"Expected total=1, got {rows[0].total}"


# ---------------------------------------------------------------------------
# R1-L — validation: negative window_days raises
# ---------------------------------------------------------------------------


def test_yield_negative_window_days_raises(empty_db):
    """R1-L: window_days < 0 raises ValueError (Decision #4)."""
    with pytest.raises(ValueError, match=r"window_days"):
        yield_over_time(empty_db, window_days=-1, group_by="board")


# ---------------------------------------------------------------------------
# R1-L — validation: zero window_days raises
# ---------------------------------------------------------------------------


def test_yield_zero_window_days_raises(empty_db):
    """R1-L: window_days == 0 raises ValueError (Decision #4)."""
    with pytest.raises(ValueError, match=r"window_days"):
        yield_over_time(empty_db, window_days=0, group_by="board")


# ---------------------------------------------------------------------------
# R1-M — tz-aware as_of raises ValueError
# ---------------------------------------------------------------------------


def test_yield_tz_aware_as_of_raises(empty_db):
    """R1-M: Passing a tz-aware datetime as as_of raises ValueError (Decision #6)."""
    tz_aware = datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match=r"as_of must be naive UTC"):
        yield_over_time(empty_db, group_by="board", as_of=tz_aware)
