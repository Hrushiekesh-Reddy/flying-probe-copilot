"""Window-resolution helpers shared by yield_metrics and pareto.

Short-circuit behaviour (R1-E / G-7):
    ``_resolve_anchor`` returns ``None`` when the DB has no test_runs rows.
    Public functions that receive ``None`` MUST return ``[]`` immediately
    without executing the main analytic SELECT.  This avoids NULL-arithmetic
    on ``anchor - INTERVAL ...`` and prevents ZeroDivisionError on empty
    cumulative-pct calculations.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import duckdb


def _resolve_anchor(
    con: duckdb.DuckDBPyConnection,
    as_of: datetime | None,
) -> datetime | None:
    """Return the window anchor datetime, or ``None`` if the DB is empty.

    If ``as_of`` is provided:
        - Raises ``ValueError`` if it carries timezone info (R1-M / Decision #6).
        - Returns it as-is (caller's value, not DB-derived).

    If ``as_of`` is ``None``:
        - Executes ``SELECT MAX(start_ts) FROM test_runs``.
        - Returns ``None`` if the result is NULL (empty DB).
        - Returns the ``datetime`` otherwise.
    """
    if as_of is not None:
        if as_of.tzinfo is not None:
            raise ValueError(
                f"as_of must be naive UTC (tzinfo=None); received tzinfo={as_of.tzinfo!r}"
            )
        return as_of

    row = con.execute("SELECT MAX(start_ts) FROM test_runs").fetchone()
    if row is None or row[0] is None:
        return None
    return row[0]


def _compute_window_bounds(
    anchor: datetime,
    window_days: int,
) -> tuple[datetime, datetime]:
    """Return ``(lower_bound, upper_bound)`` for the query window.

    Both bounds are inclusive (L4 / R1-K).

    Raises
    ------
    ValueError
        If ``window_days < 1`` (Decision #4 / R1-L).
    """
    if window_days < 1:  # pragma: no cover — callers validate before calling
        raise ValueError(f"window_days must be >= 1; received {window_days!r}")
    lower = anchor - timedelta(days=window_days)
    return lower, anchor
