"""z_score_anomalies — Phase 2 analytics function.

Returns per-group failure-rate anomaly scores using a leave-one-out baseline.

Metric (L10):
    per-group failure rate = failed / total
    failed = COUNT(btest_status != 0), total = COUNT(*) per group in window.

Baseline (L12 / R1-W4):
    For each group g: baseline_mean and baseline_std are computed over the
    failure rates of all OTHER groups (leave-one-out).
    if len(peers) < 2: baseline_std = 0.0  (do NOT call statistics.stdev)
    else: baseline_std = statistics.stdev(peers)  (ddof=1)
    z = (value - baseline_mean) / baseline_std if baseline_std > 0 else 0.0

Ordering (L16 — severity-first, diverges from slice-1 group_key ASC):
    abs(z_score) DESC, group_key ASC.

Window contract (mirrors slice-1):
    anchor = MAX(test_runs.start_ts); overridable via as_of (naive UTC only).
    Window: [anchor - window_days, anchor], both ends inclusive.
"""

from __future__ import annotations

import statistics
from datetime import datetime

import duckdb

from .models import AnomalyRow
from ._window import _compute_window_bounds, _resolve_anchor

# ---------------------------------------------------------------------------
# Group-by configuration table (mirrors slice-1 _GROUP_BY_CONFIG shape)
#
# Maps by name → (SELECT expression, JOIN clause)
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

_ALLOWED_BY = tuple(_GROUP_BY_CONFIG.keys())

# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------


def z_score_anomalies(
    con: duckdb.DuckDBPyConnection,
    *,
    window_days: int = 30,
    threshold: float = 3.0,
    by: str = "board",
    as_of: datetime | None = None,
) -> list[AnomalyRow]:
    """Return leave-one-out z-score anomaly scores per group.

    Parameters
    ----------
    con:
        Open DuckDB connection initialised with ``init_database``.
    window_days:
        Look-back window in days.  Must be >= 1.
    threshold:
        Absolute z-score threshold for flagging.  Must be > 0.
    by:
        Grouping dimension.  One of ``'board'``, ``'shift'``, ``'line'``,
        ``'operator'``.
    as_of:
        Window upper-bound override.  Must be a naive (tzinfo=None) UTC
        datetime.  Defaults to ``MAX(test_runs.start_ts)``.

    Returns
    -------
    list[AnomalyRow]
        Rows sorted by ``abs(z_score) DESC, group_key ASC``.  Empty list when
        fewer than 2 groups exist in the window (L15) or the DB is empty.

    Raises
    ------
    ValueError
        If ``by`` is not in the allowed set.
    ValueError
        If ``threshold <= 0``.
    ValueError
        If ``window_days < 1``.
    ValueError
        If ``as_of`` carries tzinfo (tz-aware datetime).
    """
    # Validate by before DB access (mirrors slice-1 enum guard).
    if by not in _GROUP_BY_CONFIG:
        allowed = ", ".join(f"{v!r}" for v in _ALLOWED_BY)
        raise ValueError(
            f"by={by!r} is not supported. "
            f"Allowed values: {allowed}"
        )

    if threshold <= 0:
        raise ValueError(f"threshold must be > 0; received {threshold!r}")

    if window_days < 1:
        raise ValueError(f"window_days must be >= 1; received {window_days!r}")

    anchor = _resolve_anchor(con, as_of)
    if anchor is None:
        return []

    lower, upper = _compute_window_bounds(anchor, window_days)

    select_col, join_clause = _GROUP_BY_CONFIG[by]

    sql = f"""
        SELECT
            {select_col} AS group_key,
            COUNT(*) AS total,
            SUM(CASE WHEN tr.btest_status != 0 THEN 1 ELSE 0 END) AS failed
        FROM test_runs tr
        {join_clause}
        WHERE tr.start_ts >= ? AND tr.start_ts <= ?
        GROUP BY {select_col}
    """

    db_rows = con.execute(sql, [lower, upper]).fetchall()

    # Build rates dict — only groups with total > 0 are candidates.
    rates: dict[str, float] = {}
    for row in db_rows:
        group_key = str(row[0])
        total = int(row[1])
        failed = int(row[2])
        if total > 0:
            rates[group_key] = failed / total

    # Single group → no peers → return [] (L15).
    if len(rates) < 2:
        return []

    # Leave-one-out per group (R1-W4).
    group_keys = sorted(rates.keys())
    result: list[AnomalyRow] = []

    for g in group_keys:
        peers = [rates[k] for k in rates if k != g]
        # peers always has >= 1 element (len(rates) >= 2).
        baseline_mean = statistics.fmean(peers)
        if len(peers) < 2:
            baseline_std = 0.0
        else:
            baseline_std = statistics.stdev(peers)

        if baseline_std > 0:
            z = (rates[g] - baseline_mean) / baseline_std
            flagged = abs(z) >= threshold
        else:
            z = 0.0
            flagged = False

        result.append(
            AnomalyRow(
                group_key=g,
                value=rates[g],
                baseline_mean=baseline_mean,
                baseline_std=baseline_std,
                z_score=z,
                flagged=flagged,
            )
        )

    # Sort by abs(z_score) DESC, then group_key ASC (L16).
    result.sort(key=lambda r: (-abs(r.z_score), r.group_key))

    return result
