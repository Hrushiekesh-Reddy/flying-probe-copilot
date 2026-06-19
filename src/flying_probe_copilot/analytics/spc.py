"""individuals_chart — Phase 2 analytics function.

Returns a Shewhart individuals (XmR) control chart over a chosen component's
parametric reading, with Wheeler-doctrine alarm rules.

Sigma estimator (L3 / R1-B1):
    sigma_hat = MR_bar / 1.128  (d2 for span-2 moving ranges)
    ucl = mean + 3 * sigma_hat
    lcl = mean - 3 * sigma_hat
    The literal 2.66 (= 3/1.128 rounded) is NEVER used in code or assertions.

Window contract (mirrors slice-1):
    anchor = MAX(test_runs.start_ts); overridable via as_of (naive UTC only).
    Window: [anchor - window_days, anchor], both ends inclusive.

Ordering (R1-W3):
    Points evaluated left-to-right in start_ts ASC, panel_serial ASC order.
    Alarm rule flags every point whose trailing window satisfies the pattern.
"""

from __future__ import annotations

from datetime import datetime

import duckdb

from .models import SPCPoint
from ._window import _compute_window_bounds, _resolve_anchor

# ---------------------------------------------------------------------------
# Allowed rule names
# ---------------------------------------------------------------------------

_ALLOWED_RULES = frozenset({"rule_1", "rule_2", "rule_3", "rule_4"})

# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------


def individuals_chart(
    con: duckdb.DuckDBPyConnection,
    *,
    board_profile_id: str,
    refdes: str,
    record_type: str | None = None,
    window_days: int = 30,
    rules: tuple[str, ...] = ("rule_1", "rule_4"),
    as_of: datetime | None = None,
) -> list[SPCPoint]:
    """Return a Shewhart XmR control chart for ``refdes`` on ``board_profile_id``.

    Parameters
    ----------
    con:
        Open DuckDB connection initialised with ``init_database``.
    board_profile_id:
        Board profile to filter on (matches ``components.board_profile_id``).
    refdes:
        Component reference designator to chart (e.g. ``'R1'``).
    record_type:
        Optional measurement record type filter (e.g. ``'A-RES'``).  When
        ``None``, all record types for the refdes are included.
    window_days:
        Look-back window in days.  Must be >= 1.
    rules:
        Alarm rules to evaluate.  Each element must be one of
        ``'rule_1'``, ``'rule_2'``, ``'rule_3'``, ``'rule_4'``.
    as_of:
        Window upper-bound override.  Must be a naive (tzinfo=None) UTC
        datetime.  Defaults to ``MAX(test_runs.start_ts)``.

    Returns
    -------
    list[SPCPoint]
        Points in ``start_ts ASC, panel_serial ASC`` order.  Empty list when
        no matching measurements exist or the DB is empty.

    Raises
    ------
    ValueError
        If any element of ``rules`` is not in the allowed set.
    ValueError
        If ``window_days < 1``.
    ValueError
        If ``as_of`` carries tzinfo (tz-aware datetime).
    """
    # Validate rules first (before DB access).
    bad = [r for r in rules if r not in _ALLOWED_RULES]
    if bad:
        raise ValueError(
            f"rules contains unsupported value {bad[0]!r}. "
            f"Allowed values: 'rule_1', 'rule_2', 'rule_3', 'rule_4'"
        )

    if window_days < 1:
        raise ValueError(f"window_days must be >= 1; received {window_days!r}")

    anchor = _resolve_anchor(con, as_of)
    if anchor is None:
        return []

    lower, upper = _compute_window_bounds(anchor, window_days)

    # Build SQL — join measurements → test_runs → components for refdes filter.
    if record_type is not None:
        sql = """
            SELECT tr.panel_serial, tr.start_ts, AVG(m.measured_value) AS value
            FROM measurements m
            JOIN test_runs tr ON tr.test_run_id = m.test_run_id
            JOIN components c ON c.component_id = m.component_id
            WHERE c.board_profile_id = ?
              AND c.refdes = ?
              AND m.measured_value IS NOT NULL
              AND m.record_type = ?
              AND tr.start_ts >= ?
              AND tr.start_ts <= ?
            GROUP BY tr.panel_serial, tr.start_ts
            ORDER BY tr.start_ts ASC, tr.panel_serial ASC
        """
        params: list = [board_profile_id, refdes, record_type, lower, upper]
    else:
        sql = """
            SELECT tr.panel_serial, tr.start_ts, AVG(m.measured_value) AS value
            FROM measurements m
            JOIN test_runs tr ON tr.test_run_id = m.test_run_id
            JOIN components c ON c.component_id = m.component_id
            WHERE c.board_profile_id = ?
              AND c.refdes = ?
              AND m.measured_value IS NOT NULL
              AND tr.start_ts >= ?
              AND tr.start_ts <= ?
            GROUP BY tr.panel_serial, tr.start_ts
            ORDER BY tr.start_ts ASC, tr.panel_serial ASC
        """
        params = [board_profile_id, refdes, lower, upper]

    rows = con.execute(sql, params).fetchall()

    if not rows:
        return []

    # Extract time-ordered values.
    serials = [r[0] for r in rows]
    timestamps = [r[1] for r in rows]
    values = [float(r[2]) for r in rows]
    n = len(values)

    # Compute sigma via MR-bar / 1.128 (R1-B1 canonical form).
    if n < 2:
        mr_bar = 0.0
    else:
        moving_ranges = [abs(values[i] - values[i - 1]) for i in range(1, n)]
        mr_bar = sum(moving_ranges) / len(moving_ranges)

    sigma_hat = mr_bar / 1.128
    center = sum(values) / n
    ucl = center + 3.0 * sigma_hat
    lcl = center - 3.0 * sigma_hat

    # Build alarm flags for each point.
    rules_set = set(rules)
    result: list[SPCPoint] = []

    # Precompute side for each point: +1 above center, -1 below, 0 on center.
    # A point exactly == center is on neither side and breaks a run.
    sides = []
    for v in values:
        diff = v - center
        if diff > 0:
            sides.append(1)
        elif diff < 0:
            sides.append(-1)
        else:
            sides.append(0)

    # Rule-4 run tracking: track current run length and current side.
    run_len = 0
    run_side = 0  # side of the current unbroken run (0 = no run)

    for i in range(n):
        flags: list[str] = []
        v = values[i]
        side = sides[i]

        # Update rule-4 run state before evaluating rules.
        if side != 0:
            if side == run_side:
                run_len += 1
            else:
                run_side = side
                run_len = 1
        else:
            # Point exactly on center breaks the run.
            run_side = 0
            run_len = 0

        # rule_1: one point beyond 3-sigma.
        if "rule_1" in rules_set and (v > ucl or v < lcl):
            flags.append("rule_1")

        # rule_4: run of 8+ consecutive same-side points (Wheeler run length = 8).
        if "rule_4" in rules_set and run_len >= 8:
            flags.append("rule_4")

        # rule_2 (opt-in): 2 of 3 trailing points beyond 2-sigma, same side as i.
        # Point i must be on a side (not exactly center); at least 2 of the 3
        # points in [i-2, i-1, i] must be beyond 2*sigma on i's side.
        if "rule_2" in rules_set and i >= 2 and side != 0 and sigma_hat > 0:
            window_3 = [i - 2, i - 1, i]
            count_beyond_2s = sum(
                1 for j in window_3
                if sides[j] == side and abs(values[j] - center) > 2.0 * sigma_hat
            )
            if count_beyond_2s >= 2:
                flags.append("rule_2")

        # rule_3 (opt-in): 4 of 5 trailing points beyond 1-sigma, same side as i.
        # Point i must be on a side; at least 4 of the 5 points in [i-4..i]
        # must be beyond 1*sigma on i's side.
        if "rule_3" in rules_set and i >= 4 and side != 0 and sigma_hat > 0:
            window_5 = [i - 4, i - 3, i - 2, i - 1, i]
            count_beyond_1s = sum(
                1 for j in window_5
                if sides[j] == side and abs(values[j] - center) > 1.0 * sigma_hat
            )
            if count_beyond_1s >= 4:
                flags.append("rule_3")

        result.append(
            SPCPoint(
                panel_serial=serials[i],
                start_ts=timestamps[i],
                value=v,
                mean=center,
                ucl=ucl,
                lcl=lcl,
                alarm_flags=tuple(flags),
            )
        )

    return result
