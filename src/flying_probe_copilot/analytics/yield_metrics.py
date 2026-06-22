"""yield_over_time — Phase 2 analytics function.

Returns per-group yield metrics for test_runs within a rolling time window.

Window contract (L3 / L4 / R1-B):
    anchor = MAX(test_runs.start_ts) by default; caller may override with as_of.
    Window: [anchor - window_days, anchor], both ends inclusive.

Ordering (R1-B / Decision #2):
    All group_by values return rows ordered by group_key ASC.
    This matches notebook Q1 (board_profile_id ASC) and is divergent from
    notebook Q4 (panels_tested DESC, operator_id) — see DECISION_LOG 2026-06-16.
"""

from __future__ import annotations

from datetime import datetime

import duckdb

from ._window import _compute_window_bounds, _resolve_anchor
from .models import YieldRow

# ---------------------------------------------------------------------------
# Group-by configuration table
#
# Maps group_by name → (SELECT expression, JOIN clause)
# ---------------------------------------------------------------------------

_GROUP_BY_CONFIG: dict[str, tuple[str, str]] = {
    "board": (
        "p.board_profile_id",
        "JOIN panels p ON p.panel_serial = tr.panel_serial",
    ),
    "shift": (
        "p.shift",
        "JOIN panels p ON p.panel_serial = tr.panel_serial",
    ),
    "line": (
        "p.line_id",
        "JOIN panels p ON p.panel_serial = tr.panel_serial",
    ),
    "operator": (
        "COALESCE(tr.operator_id, '<unknown>')",
        "",  # no extra JOIN — operator_id is on test_runs
    ),
}

_ALLOWED_GROUP_BY = tuple(_GROUP_BY_CONFIG.keys())

# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------


def yield_over_time(
    con: duckdb.DuckDBPyConnection,
    *,
    window_days: int = 7,
    group_by: str = "board",
    as_of: datetime | None = None,
) -> list[YieldRow]:
    """Return yield metrics grouped by ``group_by`` over a rolling window.

    Parameters
    ----------
    con:
        Open DuckDB connection to a database initialised with
        ``flying_probe_copilot.db.schema.init_database``.
    window_days:
        Number of days in the look-back window.  Must be >= 1 (Decision #4).
    group_by:
        Grouping dimension.  One of ``'board'``, ``'shift'``, ``'line'``,
        ``'operator'``.  ``'day'`` is not supported in Phase 2 slice 1.
    as_of:
        Window upper-bound override.  Must be a naive (tzinfo=None) UTC
        datetime (Decision #6 / R1-M).  Defaults to ``MAX(test_runs.start_ts)``.

    Returns
    -------
    list[YieldRow]
        Rows sorted by ``group_key`` ASC.  Empty list when DB has no rows or
        the window contains no test_runs (L11).

    Raises
    ------
    ValueError
        If ``group_by`` is not in the allowed set.
    ValueError
        If ``window_days < 1``.
    ValueError
        If ``as_of`` carries tzinfo (tz-aware datetime).
    """
    if group_by not in _GROUP_BY_CONFIG:
        allowed = ", ".join(f"{v!r}" for v in _ALLOWED_GROUP_BY)
        raise ValueError(f"group_by={group_by!r} is not supported. Allowed values: {allowed}")

    # Validate window_days before hitting the DB (Decision #4 / R1-L).
    if window_days < 1:
        raise ValueError(f"window_days must be >= 1; received {window_days!r}")

    # _resolve_anchor validates as_of timezone (Decision #6 / R1-M).
    anchor = _resolve_anchor(con, as_of)
    if anchor is None:
        return []

    lower, upper = _compute_window_bounds(anchor, window_days)

    select_col, join_clause = _GROUP_BY_CONFIG[group_by]

    sql = f"""
        SELECT
            {select_col} AS group_key,
            COUNT(*) AS total,
            SUM(CASE WHEN tr.btest_status = 0 THEN 1 ELSE 0 END) AS passed,
            100.0 * SUM(CASE WHEN tr.btest_status = 0 THEN 1 ELSE 0 END)
                  / COUNT(*) AS yield_pct
        FROM test_runs tr
        {join_clause}
        WHERE tr.start_ts >= ? AND tr.start_ts <= ?
        GROUP BY {select_col}
        ORDER BY group_key ASC
    """

    rows = con.execute(sql, [lower, upper]).fetchall()

    return [
        YieldRow(
            group_key=str(row[0]),
            total=int(row[1]),
            passed=int(row[2]),
            yield_pct=float(row[3]),
        )
        for row in rows
    ]
