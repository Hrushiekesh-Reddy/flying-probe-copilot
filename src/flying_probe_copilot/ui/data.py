"""data.py — connection management, caching wrappers, and pure helpers.

Public API
----------
get_db_path() -> str
get_connection(db_path) -> duckdb.DuckDBPyConnection   # @st.cache_resource, read_only
date_range_to_window(start, end) -> tuple[int, datetime]
data_date_span(con) -> tuple[date, date] | None
distinct_values(con, dimension) -> list[str]
distinct_boards(con) -> list[str]
distinct_refdes(con, board_profile_id) -> list[str]
yield_rows_to_df(rows) -> pd.DataFrame
pareto_rows_to_df(rows) -> pd.DataFrame
spc_points_to_df(rows) -> pd.DataFrame
anomaly_rows_to_df(rows) -> pd.DataFrame
filter_df_by_key(df, key_col, selected) -> pd.DataFrame
overview_kpis(yield_df, pareto_df, anomaly_df) -> dict
Filters — dataclass(window_days: int, as_of: datetime)
cached_yield / cached_pareto / cached_spc / cached_anomaly  — @st.cache_data wrappers
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, time

import duckdb
import pandas as pd
import streamlit as st

from flying_probe_copilot.analytics import (
    failure_pareto,
    individuals_chart,
    yield_over_time,
    z_score_anomalies,
)
from flying_probe_copilot.analytics.models import (
    AnomalyRow,
    ParetoRow,
    SPCPoint,
    YieldRow,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_DB_PATH = "data/db/sample.duckdb"
DB_PATH_ENV = "FPC_DB_PATH"

_ALLOWED_DIMENSIONS = {"board", "shift", "line", "operator"}

# ---------------------------------------------------------------------------
# Filters dataclass
# ---------------------------------------------------------------------------


@dataclass
class Filters:
    """Global date-range filter state propagated to every page."""

    window_days: int
    as_of: datetime


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------


def get_db_path() -> str:
    """Return the DuckDB file path from the environment or the default."""
    return os.environ.get(DB_PATH_ENV, DEFAULT_DB_PATH)


@st.cache_resource
def get_connection(db_path: str) -> duckdb.DuckDBPyConnection:
    """Open a read-only DuckDB connection (cached for the app lifetime).

    The returned connection is shared across all Streamlit reruns.
    Uses ``read_only=True`` so multiple threads/watchers cannot modify the DB.
    """
    return duckdb.connect(db_path, read_only=True)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def date_range_to_window(start: date, end: date) -> tuple[int, datetime]:
    """Convert a calendar date range to (window_days, as_of).

    Parameters
    ----------
    start, end:
        Calendar dates (inclusive on both ends).

    Returns
    -------
    window_days:
        ``max(1, (end - start).days + 1)`` — always >= 1.
    as_of:
        Naive UTC datetime at ``datetime.combine(end, time(23, 59, 59))``.

    Raises
    ------
    ValueError
        If ``end < start``.
    """
    if end < start:
        raise ValueError(f"end ({end}) is before start ({start}); end must be >= start")
    window_days = max(1, (end - start).days + 1)
    as_of = datetime.combine(end, time(23, 59, 59))
    return window_days, as_of


def data_date_span(con: duckdb.DuckDBPyConnection) -> tuple[date, date] | None:
    """Return (min_date, max_date) of test_runs.start_ts, or None if empty."""
    row = con.execute("SELECT MIN(start_ts)::DATE, MAX(start_ts)::DATE FROM test_runs").fetchone()
    if row is None or row[0] is None:
        return None
    return (row[0], row[1])


_DIM_SQL: dict[str, str] = {
    "board": (
        "SELECT DISTINCT p.board_profile_id "
        "FROM test_runs tr "
        "JOIN panels p ON p.panel_serial = tr.panel_serial "
        "ORDER BY p.board_profile_id"
    ),
    "shift": (
        "SELECT DISTINCT p.shift "
        "FROM test_runs tr "
        "JOIN panels p ON p.panel_serial = tr.panel_serial "
        "ORDER BY p.shift"
    ),
    "line": (
        "SELECT DISTINCT p.line_id "
        "FROM test_runs tr "
        "JOIN panels p ON p.panel_serial = tr.panel_serial "
        "ORDER BY p.line_id"
    ),
    "operator": (
        "SELECT DISTINCT COALESCE(tr.operator_id, '<unknown>') FROM test_runs tr ORDER BY 1"
    ),
}


def distinct_values(con: duckdb.DuckDBPyConnection, dimension: str) -> list[str]:
    """Return sorted distinct values for a grouping dimension.

    Parameters
    ----------
    dimension:
        One of ``'board'``, ``'shift'``, ``'line'``, ``'operator'``.

    Raises
    ------
    ValueError
        If ``dimension`` is not in the allowed set.
    """
    if dimension not in _ALLOWED_DIMENSIONS:
        allowed = ", ".join(sorted(_ALLOWED_DIMENSIONS))
        raise ValueError(f"Unknown dimension {dimension!r}. Allowed: {allowed}")
    sql = _DIM_SQL[dimension]
    rows = con.execute(sql).fetchall()
    return [str(r[0]) for r in rows]


def distinct_boards(con: duckdb.DuckDBPyConnection) -> list[str]:
    """Return sorted distinct board_profile_id values."""
    return distinct_values(con, "board")


def distinct_refdes(con: duckdb.DuckDBPyConnection, board_profile_id: str) -> list[str]:
    """Return sorted distinct refdes values for a board that have measurements.

    Only refdes with at least one non-null ``measured_value`` row in
    ``measurements`` are included (required by ``individuals_chart``).
    """
    rows = con.execute(
        """
        SELECT DISTINCT c.refdes
        FROM components c
        JOIN measurements m ON m.component_id = c.component_id
        WHERE c.board_profile_id = ?
          AND m.measured_value IS NOT NULL
        ORDER BY c.refdes
        """,
        [board_profile_id],
    ).fetchall()
    return [str(r[0]) for r in rows]


# ---------------------------------------------------------------------------
# Row-to-DataFrame converters
# ---------------------------------------------------------------------------

_YIELD_COLS = ["group_key", "total", "passed", "yield_pct"]
_PARETO_COLS = ["key", "count", "pct_of_total", "cumulative_pct"]
_SPC_BASE_COLS = ["panel_serial", "start_ts", "value", "mean", "ucl", "lcl", "alarm_flags"]
_SPC_COLS = _SPC_BASE_COLS + ["alarmed", "alarms"]
_ANOMALY_BASE_COLS = ["group_key", "value", "baseline_mean", "baseline_std", "z_score", "flagged"]
_ANOMALY_COLS = _ANOMALY_BASE_COLS + ["flag_label"]


def yield_rows_to_df(rows: list[YieldRow]) -> pd.DataFrame:
    """Convert a list of YieldRow to a DataFrame with declared columns."""
    if not rows:
        return pd.DataFrame(columns=_YIELD_COLS)
    return pd.DataFrame(
        [
            {
                "group_key": r.group_key,
                "total": r.total,
                "passed": r.passed,
                "yield_pct": r.yield_pct,
            }
            for r in rows
        ],
        columns=_YIELD_COLS,
    )


def pareto_rows_to_df(rows: list[ParetoRow]) -> pd.DataFrame:
    """Convert a list of ParetoRow to a DataFrame with declared columns."""
    if not rows:
        return pd.DataFrame(columns=_PARETO_COLS)
    return pd.DataFrame(
        [
            {
                "key": r.key,
                "count": r.count,
                "pct_of_total": r.pct_of_total,
                "cumulative_pct": r.cumulative_pct,
            }
            for r in rows
        ],
        columns=_PARETO_COLS,
    )


def spc_points_to_df(rows: list[SPCPoint]) -> pd.DataFrame:
    """Convert a list of SPCPoint to a DataFrame, adding derived columns.

    Derived columns
    ---------------
    alarmed : bool
        True when ``alarm_flags`` is non-empty.
    alarms : str
        Comma-joined alarm flag names, or ``""`` when none.
    """
    if not rows:
        return pd.DataFrame(columns=_SPC_COLS)
    records = []
    for r in rows:
        records.append(
            {
                "panel_serial": r.panel_serial,
                "start_ts": r.start_ts,
                "value": r.value,
                "mean": r.mean,
                "ucl": r.ucl,
                "lcl": r.lcl,
                "alarm_flags": r.alarm_flags,
                "alarmed": len(r.alarm_flags) > 0,
                "alarms": ", ".join(r.alarm_flags),
            }
        )
    return pd.DataFrame(records, columns=_SPC_COLS)


def anomaly_rows_to_df(rows: list[AnomalyRow]) -> pd.DataFrame:
    """Convert a list of AnomalyRow to a DataFrame, adding ``flag_label``.

    ``flag_label`` is ``"⚠"`` for flagged rows, ``""`` otherwise.
    """
    if not rows:
        return pd.DataFrame(columns=_ANOMALY_COLS)
    records = []
    for r in rows:
        records.append(
            {
                "group_key": r.group_key,
                "value": r.value,
                "baseline_mean": r.baseline_mean,
                "baseline_std": r.baseline_std,
                "z_score": r.z_score,
                "flagged": r.flagged,
                "flag_label": "⚠" if r.flagged else "",
            }
        )
    return pd.DataFrame(records, columns=_ANOMALY_COLS)


# ---------------------------------------------------------------------------
# filter_df_by_key
# ---------------------------------------------------------------------------


def filter_df_by_key(df: pd.DataFrame, key_col: str, selected: list[str] | None) -> pd.DataFrame:
    """Post-filter a DataFrame to rows where ``key_col`` is in ``selected``.

    Parameters
    ----------
    df:
        Input DataFrame.
    key_col:
        Column name to filter on.
    selected:
        List of allowed values.  Falsy (``[]``, ``None``) → return ``df``
        unchanged.

    Returns
    -------
    pd.DataFrame
        Filtered (or unchanged) DataFrame.
    """
    if not selected:
        return df
    return df[df[key_col].isin(selected)].reset_index(drop=True)


# ---------------------------------------------------------------------------
# overview_kpis
# ---------------------------------------------------------------------------


def overview_kpis(
    yield_df: pd.DataFrame,
    pareto_df: pd.DataFrame,
    anomaly_df: pd.DataFrame,
) -> dict:
    """Compute KPI dict for the Overview page.

    Returns
    -------
    dict with keys:
        overall_yield_pct : float   (weighted mean from yield_df; 0.0 if empty)
        panels_tested     : int
        total_failures    : int     (sum of pareto_df["count"])
        top_failure_mode  : str     (first row of pareto_df["key"] or "—")
        flagged_anomalies : int     (count of anomaly_df["flagged"] == True)
    """
    if yield_df.empty:
        panels_tested = 0
        overall_yield_pct = 0.0
    else:
        panels_tested = int(yield_df["total"].sum())
        total_passed = int(yield_df["passed"].sum())
        overall_yield_pct = (100.0 * total_passed / panels_tested) if panels_tested > 0 else 0.0

    if pareto_df.empty:
        total_failures = 0
        top_failure_mode = "—"
    else:
        total_failures = int(pareto_df["count"].sum())
        top_failure_mode = str(pareto_df.iloc[0]["key"])

    if anomaly_df.empty:
        flagged_anomalies = 0
    else:
        flagged_anomalies = int(anomaly_df["flagged"].sum())

    return {
        "overall_yield_pct": overall_yield_pct,
        "panels_tested": panels_tested,
        "total_failures": total_failures,
        "top_failure_mode": top_failure_mode,
        "flagged_anomalies": flagged_anomalies,
    }


# ---------------------------------------------------------------------------
# st.cache_data wrappers
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def cached_yield(
    _con: duckdb.DuckDBPyConnection,
    *,
    db_path: str,
    window_days: int,
    as_of: datetime,
    group_by: str = "board",
) -> pd.DataFrame:
    """Cached wrapper around yield_over_time → DataFrame."""
    rows = yield_over_time(_con, window_days=window_days, group_by=group_by, as_of=as_of)
    return yield_rows_to_df(rows)


@st.cache_data(show_spinner=False)
def cached_pareto(
    _con: duckdb.DuckDBPyConnection,
    *,
    db_path: str,
    window_days: int,
    as_of: datetime,
    by: str = "record_type",
    top_n: int = 10,
) -> pd.DataFrame:
    """Cached wrapper around failure_pareto → DataFrame."""
    rows = failure_pareto(_con, window_days=window_days, by=by, top_n=top_n, as_of=as_of)
    return pareto_rows_to_df(rows)


@st.cache_data(show_spinner=False)
def cached_spc(
    _con: duckdb.DuckDBPyConnection,
    *,
    db_path: str,
    window_days: int,
    as_of: datetime,
    board_profile_id: str,
    refdes: str,
    record_type: str | None = None,
    rules: tuple[str, ...] = ("rule_1", "rule_4"),
) -> pd.DataFrame:
    """Cached wrapper around individuals_chart → DataFrame."""
    rows = individuals_chart(
        _con,
        board_profile_id=board_profile_id,
        refdes=refdes,
        record_type=record_type,
        window_days=window_days,
        rules=rules,
        as_of=as_of,
    )
    return spc_points_to_df(rows)


@st.cache_data(show_spinner=False)
def cached_anomaly(
    _con: duckdb.DuckDBPyConnection,
    *,
    db_path: str,
    window_days: int,
    as_of: datetime,
    by: str = "shift",
    threshold: float = 3.0,
) -> pd.DataFrame:
    """Cached wrapper around z_score_anomalies → DataFrame."""
    rows = z_score_anomalies(_con, window_days=window_days, by=by, threshold=threshold, as_of=as_of)
    return anomaly_rows_to_df(rows)
