"""Tests for failure_pareto() — Phase 2 Analytics.

Test IDs map to the Test-Case Plan (2026-06-16-test-plan.md):
  P-01 … P-14 as listed, plus R1-E (all-null refdes) and R1-K boundary
  tests and R1-L validation tests.

The ``_make_pareto_db`` helper from conftest.py is used to build
deterministic per-test fixtures (R1-D resolution).
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import duckdb
import pytest

from flying_probe_copilot.analytics import ParetoRow, failure_pareto
from flying_probe_copilot.db.schema import init_database

# ---------------------------------------------------------------------------
# Shared fixture spec helpers
# ---------------------------------------------------------------------------

# Anchor timestamp used across tests that need window control
_ANCHOR = datetime(2026, 5, 14, 12, 0, 0)


def _ts(days_before_anchor: float = 0.0) -> datetime:
    """Return a timestamp ``days_before_anchor`` days before _ANCHOR."""
    return _ANCHOR - timedelta(days=days_before_anchor)


# ---------------------------------------------------------------------------
# P-01 — orders descending by count
# ---------------------------------------------------------------------------


def test_pareto_by_record_type_orders_descending(_make_pareto_db):
    """P-01: failure_pareto rows sorted by count DESC."""
    spec = [
        {"record_type": "A-RES", "failure_category": "open",   "target_refdes": "R1",  "start_ts": _ts(1)},
        {"record_type": "A-RES", "failure_category": "open",   "target_refdes": "R2",  "start_ts": _ts(1)},
        {"record_type": "A-RES", "failure_category": "open",   "target_refdes": "R3",  "start_ts": _ts(1)},
        {"record_type": "A-RES", "failure_category": "open",   "target_refdes": "R4",  "start_ts": _ts(1)},
        {"record_type": "A-RES", "failure_category": "open",   "target_refdes": "R5",  "start_ts": _ts(1)},
        {"record_type": "A-RES", "failure_category": "open",   "target_refdes": "R6",  "start_ts": _ts(1)},
        {"record_type": "A-RES", "failure_category": "open",   "target_refdes": "R7",  "start_ts": _ts(1)},
        {"record_type": "A-RES", "failure_category": "open",   "target_refdes": "R8",  "start_ts": _ts(1)},
        {"record_type": "A-RES", "failure_category": "open",   "target_refdes": "R9",  "start_ts": _ts(1)},
        {"record_type": "A-RES", "failure_category": "open",   "target_refdes": "R10", "start_ts": _ts(1)},
        {"record_type": "D-T",   "failure_category": "digital","target_refdes": "U1",  "start_ts": _ts(1)},
        {"record_type": "D-T",   "failure_category": "digital","target_refdes": "U2",  "start_ts": _ts(1)},
        {"record_type": "D-T",   "failure_category": "digital","target_refdes": "U3",  "start_ts": _ts(1)},
        {"record_type": "D-T",   "failure_category": "digital","target_refdes": "U4",  "start_ts": _ts(1)},
        {"record_type": "D-T",   "failure_category": "digital","target_refdes": "U5",  "start_ts": _ts(1)},
        {"record_type": "D-T",   "failure_category": "digital","target_refdes": "U6",  "start_ts": _ts(1)},
        {"record_type": "TS",    "failure_category": "short",  "target_refdes": None,  "start_ts": _ts(1)},
        {"record_type": "TS",    "failure_category": "short",  "target_refdes": None,  "start_ts": _ts(1)},
        {"record_type": "TS",    "failure_category": "short",  "target_refdes": None,  "start_ts": _ts(1)},
        {"record_type": "A-DIO", "failure_category": "open",   "target_refdes": "D1",  "start_ts": _ts(1)},
    ]
    con = _make_pareto_db(spec)
    rows = failure_pareto(con, by="record_type", top_n=10, as_of=_ANCHOR)
    con.close()

    assert len(rows) == 4, f"Expected 4 rows, got {len(rows)}"
    for i in range(len(rows) - 1):
        assert rows[i].count >= rows[i + 1].count, (
            f"Row {i} count={rows[i].count} < row {i+1} count={rows[i+1].count}"
        )
    assert rows[0].key == "A-RES", f"Expected A-RES first, got {rows[0].key!r}"


# ---------------------------------------------------------------------------
# P-02 — tiebreak orders by key ASC when counts equal
# ---------------------------------------------------------------------------


def test_pareto_tiebreak_orders_by_key_asc(_make_pareto_db):
    """P-02: Tied counts are broken by key ASC (L15)."""
    spec = [
        {"record_type": "A-CAP", "failure_category": "open", "target_refdes": "C1", "start_ts": _ts(1)},
        {"record_type": "A-CAP", "failure_category": "open", "target_refdes": "C2", "start_ts": _ts(1)},
        {"record_type": "A-CAP", "failure_category": "open", "target_refdes": "C3", "start_ts": _ts(1)},
        {"record_type": "A-IND", "failure_category": "open", "target_refdes": "L1", "start_ts": _ts(1)},
        {"record_type": "A-IND", "failure_category": "open", "target_refdes": "L2", "start_ts": _ts(1)},
        {"record_type": "A-IND", "failure_category": "open", "target_refdes": "L3", "start_ts": _ts(1)},
    ]
    con = _make_pareto_db(spec)
    rows = failure_pareto(con, by="record_type", top_n=10, as_of=_ANCHOR)
    con.close()

    assert len(rows) == 2, f"Expected 2 rows, got {len(rows)}"
    assert rows[0].count == rows[1].count, "Tie not set up correctly in fixture"
    assert rows[0].key == "A-CAP", f"A-CAP should come before A-IND; got {rows[0].key!r}"
    assert rows[1].key == "A-IND", f"Expected A-IND second; got {rows[1].key!r}"


# ---------------------------------------------------------------------------
# P-03 — cumulative_pct is non-decreasing, last row ≈ 100.0 when top_n >= N
# ---------------------------------------------------------------------------


def test_pareto_by_record_type_cumulative_pct_monotonic(_make_pareto_db):
    """P-03: cumulative_pct is non-decreasing; last row ≈ 100.0 when all groups included."""
    spec = [
        {"record_type": "A-RES", "failure_category": "open",   "target_refdes": "R1", "start_ts": _ts(1)},
        {"record_type": "A-RES", "failure_category": "open",   "target_refdes": "R2", "start_ts": _ts(1)},
        {"record_type": "A-RES", "failure_category": "open",   "target_refdes": "R3", "start_ts": _ts(1)},
        {"record_type": "A-RES", "failure_category": "open",   "target_refdes": "R4", "start_ts": _ts(1)},
        {"record_type": "D-T",   "failure_category": "digital","target_refdes": "U1", "start_ts": _ts(1)},
        {"record_type": "D-T",   "failure_category": "digital","target_refdes": "U2", "start_ts": _ts(1)},
        {"record_type": "TS",    "failure_category": "short",  "target_refdes": None, "start_ts": _ts(1)},
        {"record_type": "A-DIO", "failure_category": "open",   "target_refdes": "D1", "start_ts": _ts(1)},
    ]
    con = _make_pareto_db(spec)
    # top_n == distinct group count (4) → last row should reach ≈ 100%
    rows = failure_pareto(con, by="record_type", top_n=4, as_of=_ANCHOR)
    con.close()

    assert len(rows) == 4, f"Expected 4 rows, got {len(rows)}"
    for i in range(len(rows) - 1):
        assert rows[i].cumulative_pct <= rows[i + 1].cumulative_pct, (
            f"cumulative_pct not monotonic at position {i}: "
            f"{rows[i].cumulative_pct} > {rows[i+1].cumulative_pct}"
        )
    assert math.isclose(rows[-1].cumulative_pct, 100.0, abs_tol=1e-6), (
        f"Last row cumulative_pct should ≈ 100.0, got {rows[-1].cumulative_pct}"
    )
    assert math.isclose(rows[0].cumulative_pct, rows[0].pct_of_total, abs_tol=1e-9), (
        f"First row cumulative_pct should equal pct_of_total: "
        f"{rows[0].cumulative_pct} != {rows[0].pct_of_total}"
    )


# ---------------------------------------------------------------------------
# P-04 — sum of counts equals total failures in window
# ---------------------------------------------------------------------------


def test_pareto_by_record_type_sum_equals_total_failures(_make_pareto_db):
    """P-04: sum(r.count for r in rows) equals COUNT(*) FROM failures in same window."""
    spec = [
        {"record_type": "A-RES", "failure_category": "open",   "target_refdes": "R1", "start_ts": _ts(1)},
        {"record_type": "A-RES", "failure_category": "open",   "target_refdes": "R2", "start_ts": _ts(1)},
        {"record_type": "D-T",   "failure_category": "digital","target_refdes": "U1", "start_ts": _ts(1)},
        {"record_type": "TS",    "failure_category": "short",  "target_refdes": None, "start_ts": _ts(1)},
        {"record_type": "A-DIO", "failure_category": "open",   "target_refdes": "D1", "start_ts": _ts(1)},
    ]
    con = _make_pareto_db(spec)

    lower = _ANCHOR - timedelta(days=7)
    rows = failure_pareto(con, by="record_type", top_n=10, as_of=_ANCHOR)
    db_count = con.execute(
        "SELECT COUNT(*) FROM failures f "
        "JOIN test_runs tr ON tr.test_run_id = f.test_run_id "
        "WHERE tr.start_ts >= ? AND tr.start_ts <= ?",
        [lower, _ANCHOR],
    ).fetchone()[0]
    con.close()

    assert sum(r.count for r in rows) == db_count, (
        f"Sum of pareto counts ({sum(r.count for r in rows)}) != DB count ({db_count})"
    )


# ---------------------------------------------------------------------------
# P-05 — default top_n=10 returns at most 10 rows
# ---------------------------------------------------------------------------


def test_pareto_default_top_n_returns_at_most_ten(_make_pareto_db):
    """P-05: With 15 distinct record_types, default top_n=10 returns exactly 10."""
    record_types = [
        "A-RES", "A-CAP", "A-IND", "A-DIO", "A-NPN",
        "A-PNP", "A-FET", "A-IC", "A-XSTR", "A-BJT",
        "A-OPAMP", "A-REG", "D-T", "TS", "TJET",
    ]
    spec = [
        {
            "record_type": rt,
            "failure_category": "open",
            "target_refdes": f"R{i}",
            "start_ts": _ts(1),
        }
        for i, rt in enumerate(record_types, 1)
    ]
    con = _make_pareto_db(spec)
    rows = failure_pareto(con, by="record_type", as_of=_ANCHOR)  # default top_n=10
    con.close()

    assert len(rows) == 10, f"Expected exactly 10 rows, got {len(rows)}"


# ---------------------------------------------------------------------------
# P-06 — top_n limits results
# ---------------------------------------------------------------------------


def test_pareto_top_n_limits_results(_make_pareto_db):
    """P-06: top_n=3 returns at most 3 rows from a fixture with ≥4 distinct groups."""
    spec = [
        {"record_type": "A-RES", "failure_category": "open",   "target_refdes": "R1", "start_ts": _ts(1)},
        {"record_type": "A-RES", "failure_category": "open",   "target_refdes": "R2", "start_ts": _ts(1)},
        {"record_type": "A-RES", "failure_category": "open",   "target_refdes": "R3", "start_ts": _ts(1)},
        {"record_type": "D-T",   "failure_category": "digital","target_refdes": "U1", "start_ts": _ts(1)},
        {"record_type": "D-T",   "failure_category": "digital","target_refdes": "U2", "start_ts": _ts(1)},
        {"record_type": "TS",    "failure_category": "short",  "target_refdes": None, "start_ts": _ts(1)},
        {"record_type": "A-DIO", "failure_category": "open",   "target_refdes": "D1", "start_ts": _ts(1)},
    ]
    con = _make_pareto_db(spec)
    rows = failure_pareto(con, by="record_type", top_n=3, as_of=_ANCHOR)
    con.close()

    assert len(rows) == 3, f"Expected 3 rows with top_n=3, got {len(rows)}"


# ---------------------------------------------------------------------------
# P-07 — top_n truncates tied groups at cutoff deterministically
# ---------------------------------------------------------------------------


def test_pareto_top_n_truncates_tied_groups_at_cutoff_deterministically(_make_pareto_db):
    """P-07: Ties at the cutoff are truncated; strict LIMIT; tiebreak by key ASC (L8/L15)."""
    # ranks: A-RES=10, D-T=8, A-CAP=5, TS=5, A-DIO=2
    spec = (
        [{"record_type": "A-RES", "failure_category": "open", "target_refdes": f"R{i}", "start_ts": _ts(1)} for i in range(10)]
        + [{"record_type": "D-T",  "failure_category": "dig",  "target_refdes": f"U{i}", "start_ts": _ts(1)} for i in range(8)]
        + [{"record_type": "A-CAP","failure_category": "open", "target_refdes": f"C{i}", "start_ts": _ts(1)} for i in range(5)]
        + [{"record_type": "TS",   "failure_category": "short","target_refdes": None,    "start_ts": _ts(1)} for _ in range(5)]
        + [{"record_type": "A-DIO","failure_category": "open", "target_refdes": f"D{i}", "start_ts": _ts(1)} for i in range(2)]
    )
    con = _make_pareto_db(spec)
    rows = failure_pareto(con, by="record_type", top_n=3, as_of=_ANCHOR)
    con.close()

    # top_n=3 → A-RES(10), D-T(8), A-CAP(5) [A-CAP < TS alphabetically, so A-CAP wins]
    assert len(rows) == 3, f"Expected exactly 3 rows, got {len(rows)}"
    assert rows[0].key == "A-RES", f"Expected A-RES first, got {rows[0].key!r}"
    assert rows[1].key == "D-T",   f"Expected D-T second, got {rows[1].key!r}"
    assert rows[2].key == "A-CAP", f"Expected A-CAP third (tiebreak ASC), got {rows[2].key!r}"
    assert rows[2].count == 5, f"Expected count=5, got {rows[2].count}"


# ---------------------------------------------------------------------------
# P-08 — by="refdes" skips NULL refdes rows
# ---------------------------------------------------------------------------


def test_pareto_by_refdes_skips_null_refdes(_make_pareto_db):
    """P-08: by='refdes' excludes rows where target_refdes IS NULL."""
    spec = [
        {"record_type": "A-RES", "failure_category": "open",  "target_refdes": "R1",  "start_ts": _ts(1)},
        {"record_type": "A-RES", "failure_category": "open",  "target_refdes": "R1",  "start_ts": _ts(1)},
        {"record_type": "A-CAP", "failure_category": "open",  "target_refdes": "C1",  "start_ts": _ts(1)},
        {"record_type": "TS",    "failure_category": "short", "target_refdes": None,   "start_ts": _ts(1)},
        {"record_type": "TS",    "failure_category": "short", "target_refdes": None,   "start_ts": _ts(1)},
        {"record_type": "TS",    "failure_category": "short", "target_refdes": None,   "start_ts": _ts(1)},
    ]
    con = _make_pareto_db(spec)

    lower = _ANCHOR - timedelta(days=7)
    rows = failure_pareto(con, by="refdes", top_n=10, as_of=_ANCHOR)

    # No NULL keys in result
    for row in rows:
        assert row.key is not None, "Got None key in refdes pareto"
        assert row.key not in ("None", ""), f"Got invalid key {row.key!r}"

    # Count should match only the non-NULL refdes failures
    non_null_count = con.execute(
        "SELECT COUNT(*) FROM failures f "
        "JOIN test_runs tr ON tr.test_run_id = f.test_run_id "
        "WHERE tr.start_ts >= ? AND tr.start_ts <= ? AND f.target_refdes IS NOT NULL",
        [lower, _ANCHOR],
    ).fetchone()[0]
    con.close()

    assert sum(r.count for r in rows) == non_null_count, (
        f"Sum {sum(r.count for r in rows)} != non-null count {non_null_count}"
    )


# ---------------------------------------------------------------------------
# P-09 — window excludes failures outside window
# ---------------------------------------------------------------------------


def test_pareto_window_excludes_old_failures(_make_pareto_db):
    """P-09: Failures with start_ts > 7 days before anchor are excluded."""
    spec = [
        # In-window failures (2 days before anchor)
        {"record_type": "A-RES", "failure_category": "open", "target_refdes": "R1", "start_ts": _ts(2)},
        {"record_type": "A-RES", "failure_category": "open", "target_refdes": "R2", "start_ts": _ts(2)},
        {"record_type": "D-T",   "failure_category": "dig",  "target_refdes": "U1", "start_ts": _ts(2)},
        # Out-of-window failures (8 days before anchor)
        {"record_type": "TS",    "failure_category": "short","target_refdes": None,  "start_ts": _ts(8)},
        {"record_type": "TS",    "failure_category": "short","target_refdes": None,  "start_ts": _ts(8)},
        {"record_type": "TS",    "failure_category": "short","target_refdes": None,  "start_ts": _ts(8)},
    ]
    con = _make_pareto_db(spec)
    rows = failure_pareto(con, by="record_type", top_n=10, as_of=_ANCHOR)
    con.close()

    # Only in-window failures should appear; TS (out-of-window) must not appear
    keys = {r.key for r in rows}
    assert "TS" not in keys, f"TS (out-of-window) appeared in pareto: {keys}"
    assert sum(r.count for r in rows) == 3, (
        f"Expected 3 in-window failures, got {sum(r.count for r in rows)}"
    )


# ---------------------------------------------------------------------------
# P-10 — zero failures returns []
# ---------------------------------------------------------------------------


def test_pareto_with_zero_failures_returns_empty_list(empty_db):
    """P-10: empty DB → failure_pareto returns [] for all by values."""
    for by in ("record_type", "refdes"):
        result = failure_pareto(empty_db, by=by, top_n=10)
        assert result == [], f"Expected [] for by={by!r}, got {result!r}"


# ---------------------------------------------------------------------------
# P-11 — invalid by raises ValueError
# ---------------------------------------------------------------------------


def test_pareto_invalid_by_raises_value_error(empty_db):
    """P-11: by='component_family' raises ValueError listing allowed values."""
    with pytest.raises(ValueError, match=r"by="):
        failure_pareto(empty_db, by="component_family", top_n=10)


# ---------------------------------------------------------------------------
# P-14 — pct_of_total sums to ≈ 100.0 when all groups included
# ---------------------------------------------------------------------------


def test_pareto_pct_of_total_sums_to_one_hundred_within_tolerance(_make_pareto_db):
    """P-14: sum(pct_of_total) ≈ 100.0 when top_n >= distinct group count."""
    spec = [
        {"record_type": "A-RES", "failure_category": "open",   "target_refdes": "R1", "start_ts": _ts(1)},
        {"record_type": "A-RES", "failure_category": "open",   "target_refdes": "R2", "start_ts": _ts(1)},
        {"record_type": "D-T",   "failure_category": "digital","target_refdes": "U1", "start_ts": _ts(1)},
        {"record_type": "TS",    "failure_category": "short",  "target_refdes": None, "start_ts": _ts(1)},
    ]
    con = _make_pareto_db(spec)
    rows = failure_pareto(con, by="record_type", top_n=10, as_of=_ANCHOR)
    con.close()

    total_pct = sum(r.pct_of_total for r in rows)
    assert math.isclose(total_pct, 100.0, abs_tol=1e-6), (
        f"Expected pct_of_total sum ≈ 100.0, got {total_pct}"
    )


# ---------------------------------------------------------------------------
# R1-E — all-null refdes returns [] (not ZeroDivisionError)
# ---------------------------------------------------------------------------


def test_pareto_by_refdes_with_all_null_refdes_returns_empty_list(_make_pareto_db):
    """R1-E: by='refdes' with all-NULL target_refdes → [] (no ZeroDivisionError)."""
    spec = [
        {"record_type": "TS", "failure_category": "short", "target_refdes": None, "start_ts": _ts(1)},
        {"record_type": "TS", "failure_category": "short", "target_refdes": None, "start_ts": _ts(1)},
    ]
    con = _make_pareto_db(spec)
    result = failure_pareto(con, by="refdes", top_n=10, as_of=_ANCHOR)
    con.close()

    assert result == [], f"Expected [] when all refdes are NULL, got {result!r}"


# ---------------------------------------------------------------------------
# R1-K — lower window bound included
# ---------------------------------------------------------------------------


def test_pareto_failure_at_lower_window_bound_included(_make_pareto_db):
    """R1-K lower: A failure at start_ts == as_of - window_days is INCLUDED."""
    lower_bound = _ANCHOR - timedelta(days=7)
    spec = [
        {
            "record_type": "A-RES",
            "failure_category": "open",
            "target_refdes": "R1",
            "start_ts": lower_bound,
        }
    ]
    con = _make_pareto_db(spec)
    rows = failure_pareto(con, by="record_type", top_n=10, as_of=_ANCHOR)
    con.close()

    assert len(rows) == 1, (
        f"Expected failure at lower bound to be included, got {len(rows)} rows"
    )
    assert rows[0].count == 1


# ---------------------------------------------------------------------------
# R1-K — upper window bound included
# ---------------------------------------------------------------------------


def test_pareto_failure_at_upper_window_bound_included(_make_pareto_db):
    """R1-K upper: A failure at start_ts == as_of is INCLUDED."""
    spec = [
        {
            "record_type": "A-RES",
            "failure_category": "open",
            "target_refdes": "R1",
            "start_ts": _ANCHOR,  # exactly as_of
        }
    ]
    con = _make_pareto_db(spec)
    rows = failure_pareto(con, by="record_type", top_n=10, as_of=_ANCHOR)
    con.close()

    assert len(rows) == 1, (
        f"Expected failure at upper bound to be included, got {len(rows)} rows"
    )
    assert rows[0].count == 1


# ---------------------------------------------------------------------------
# R1-L — negative top_n raises ValueError
# ---------------------------------------------------------------------------


def test_pareto_negative_top_n_raises(empty_db):
    """R1-L: top_n < 0 raises ValueError (Decision #5)."""
    with pytest.raises(ValueError, match=r"top_n"):
        failure_pareto(empty_db, by="record_type", top_n=-1)


# ---------------------------------------------------------------------------
# R1-L — zero top_n raises ValueError
# ---------------------------------------------------------------------------


def test_pareto_zero_top_n_raises(empty_db):
    """R1-L: top_n == 0 raises ValueError (Decision #5)."""
    with pytest.raises(ValueError, match=r"top_n"):
        failure_pareto(empty_db, by="record_type", top_n=0)
