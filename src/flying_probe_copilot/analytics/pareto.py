"""failure_pareto — Phase 2 analytics function.

Returns a ranked failure Pareto for test_runs failures within a rolling window.

SQL shape (R1-O):
    Grouped CTE → totals CTE → ranked CTE with window-function cumulative_pct
    → SELECT * ... LIMIT top_n.

Cumulative pct semantics (R1-O):
    cumulative_pct is computed over the FULL group set (before LIMIT).
    With top_n < distinct_groups, the last returned row's cumulative_pct < 100.

Placeholder marker:
    record_type and refdes are not BUG-007-affected; placeholder_fields == ()
    for both.
"""

from __future__ import annotations

from datetime import datetime

import duckdb

from .models import ParetoRow
from ._window import _compute_window_bounds, _resolve_anchor

# ---------------------------------------------------------------------------
# By-value configuration
# ---------------------------------------------------------------------------

_BY_CONFIG: dict[str, tuple[str, str]] = {
    "record_type": ("f.record_type", ""),
    "refdes": ("f.target_refdes", "AND f.target_refdes IS NOT NULL"),
}

_ALLOWED_BY = tuple(_BY_CONFIG.keys())

# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------


def failure_pareto(
    con: duckdb.DuckDBPyConnection,
    *,
    window_days: int = 7,
    by: str = "record_type",
    top_n: int = 10,
    as_of: datetime | None = None,
) -> list[ParetoRow]:
    """Return a failure Pareto chart sorted descending by failure count.

    Parameters
    ----------
    con:
        Open DuckDB connection.
    window_days:
        Look-back window in days.  Must be >= 1 (Decision #4).
    by:
        Grouping dimension.  One of ``'record_type'``, ``'refdes'``.
    top_n:
        Maximum rows to return.  Must be >= 1 (Decision #5).  Ties at the
        cutoff are broken by ascending key and the last tied group is dropped
        (strict ``LIMIT top_n``, L8).
    as_of:
        Window upper-bound override (naive UTC datetime, Decision #6 / R1-M).

    Returns
    -------
    list[ParetoRow]
        Rows sorted by count DESC, key ASC.  Empty list when DB is empty or
        window contains no qualifying failures (L11 / R1-E).

    Raises
    ------
    ValueError
        If ``by`` is not in the allowed set.
    ValueError
        If ``window_days < 1``.
    ValueError
        If ``top_n < 1``.
    ValueError
        If ``as_of`` carries tzinfo.
    """
    if by not in _BY_CONFIG:
        allowed = ", ".join(f"{v!r}" for v in _ALLOWED_BY)
        raise ValueError(
            f"by={by!r} is not supported. Allowed values: {allowed}"
        )

    if top_n < 1:
        raise ValueError(f"top_n must be >= 1; received {top_n!r}")

    # Validate window_days before hitting the DB (Decision #4 / R1-L).
    if window_days < 1:
        raise ValueError(f"window_days must be >= 1; received {window_days!r}")

    # _resolve_anchor validates as_of timezone (Decision #6 / R1-M).
    anchor = _resolve_anchor(con, as_of)
    if anchor is None:
        return []

    lower, upper = _compute_window_bounds(anchor, window_days)

    key_col, extra_where = _BY_CONFIG[by]

    sql = f"""
        WITH grouped AS (
            SELECT {key_col} AS key, COUNT(*) AS cnt
            FROM failures f
            JOIN test_runs tr ON tr.test_run_id = f.test_run_id
            WHERE tr.start_ts >= ? AND tr.start_ts <= ?
              {extra_where}
            GROUP BY {key_col}
        ),
        totals AS (SELECT SUM(cnt) AS overall_total FROM grouped),
        ranked AS (
            SELECT
                key,
                cnt AS count,
                100.0 * cnt / (SELECT overall_total FROM totals) AS pct_of_total,
                100.0 * SUM(cnt) OVER (
                    ORDER BY cnt DESC, key ASC
                    ROWS UNBOUNDED PRECEDING
                ) / (SELECT overall_total FROM totals) AS cumulative_pct
            FROM grouped
        )
        SELECT * FROM ranked ORDER BY count DESC, key ASC LIMIT ?
    """

    rows = con.execute(sql, [lower, upper, top_n]).fetchall()

    if not rows:
        return []

    return [
        ParetoRow(
            key=str(row[0]),
            count=int(row[1]),
            pct_of_total=float(row[2]),
            cumulative_pct=float(row[3]),
            placeholder_fields=(),
        )
        for row in rows
    ]
