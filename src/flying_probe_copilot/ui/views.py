"""views.py — 5 page render functions for the Streamlit dashboard.

Each function accepts a read-only DuckDB connection and a Filters dataclass
and renders one dashboard page using Streamlit + Plotly.

Pages
-----
render_overview   — KPI metric cards + compact yield bar + mini Pareto
render_yield      — dimension selector + yield bar
render_pareto     — by/top_n controls + Pareto bar+cumulative chart
render_spc        — board/refdes pickers + SPC individuals chart
render_anomalies  — by selector + threshold slider + anomaly z-score bar

All pages guard against empty data with ``st.info`` (not a blank chart).
Drill-down tables are placed inside ``st.expander`` beneath each chart.
"""

from __future__ import annotations

import duckdb
import streamlit as st

from flying_probe_copilot.ui import data as _data
from flying_probe_copilot.ui.charts import (
    build_anomaly_bar,
    build_pareto_chart,
    build_spc_chart,
    build_yield_bar,
)
from flying_probe_copilot.ui.data import (
    Filters,
    cached_anomaly,
    cached_pareto,
    cached_spc,
    cached_yield,
    distinct_boards,
    distinct_refdes,
    distinct_values,
    filter_df_by_key,
    overview_kpis,
)


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------


def render_overview(con: duckdb.DuckDBPyConnection, filters: Filters) -> None:
    """Render the Overview page: KPI cards + compact yield + mini Pareto."""
    st.header("Overview")

    db_path = _data.get_db_path()

    yield_df = cached_yield(
        con,
        db_path=db_path,
        window_days=filters.window_days,
        as_of=filters.as_of,
        group_by="board",
    )
    pareto_df = cached_pareto(
        con,
        db_path=db_path,
        window_days=filters.window_days,
        as_of=filters.as_of,
        by="record_type",
        top_n=5,
    )
    anomaly_df = cached_anomaly(
        con,
        db_path=db_path,
        window_days=filters.window_days,
        as_of=filters.as_of,
        by="shift",
        threshold=3.0,
    )

    kpis = overview_kpis(yield_df, pareto_df, anomaly_df)

    # --- KPI metric cards ---
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Overall Yield %", f"{kpis['overall_yield_pct']:.1f}%")
    c2.metric("Panels Tested", kpis["panels_tested"])
    c3.metric("Total Failures", kpis["total_failures"])
    c4.metric("Top Failure Mode", kpis["top_failure_mode"])
    c5.metric("Flagged Anomalies", kpis["flagged_anomalies"])

    st.divider()

    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Yield by board")
        if yield_df.empty:
            st.info("No yield data in the selected window.")
        else:
            st.plotly_chart(build_yield_bar(yield_df), use_container_width=True)

    with col_right:
        st.subheader("Failure Pareto (top 5)")
        if pareto_df.empty:
            st.info("No failure data in the selected window.")
        else:
            st.plotly_chart(build_pareto_chart(pareto_df), use_container_width=True)


# ---------------------------------------------------------------------------
# Yield
# ---------------------------------------------------------------------------


def render_yield(con: duckdb.DuckDBPyConnection, filters: Filters) -> None:
    """Render the Yield page: dimension selector + value multiselect + bar chart."""
    st.header("Yield")

    db_path = _data.get_db_path()

    dim = st.selectbox(
        "Group by",
        ["board", "shift", "line", "operator"],
        index=0,
    )

    yield_df = cached_yield(
        con,
        db_path=db_path,
        window_days=filters.window_days,
        as_of=filters.as_of,
        group_by=dim,
    )

    if yield_df.empty:
        st.info(
            f"No test runs in the selected window for dimension '{dim}'. "
            "Widen the date range."
        )
        return

    # Value multiselect (post-filter on grouped rows)
    all_vals = sorted(yield_df["group_key"].tolist())
    selected = st.multiselect(f"Filter {dim} values", all_vals, default=[])
    filtered_df = filter_df_by_key(yield_df, "group_key", selected)

    st.plotly_chart(build_yield_bar(filtered_df), use_container_width=True)

    with st.expander("Data table"):
        st.dataframe(filtered_df, use_container_width=True)


# ---------------------------------------------------------------------------
# Pareto
# ---------------------------------------------------------------------------


def render_pareto(con: duckdb.DuckDBPyConnection, filters: Filters) -> None:
    """Render the Failure Pareto page."""
    st.header("Failure Pareto")

    db_path = _data.get_db_path()

    by = st.selectbox("Group by", ["record_type", "refdes"], index=0)
    top_n = st.slider("Top N", min_value=3, max_value=20, value=10, step=1)

    pareto_df = cached_pareto(
        con,
        db_path=db_path,
        window_days=filters.window_days,
        as_of=filters.as_of,
        by=by,
        top_n=top_n,
    )

    if pareto_df.empty:
        st.info("No failures found in the selected window.")
        return

    st.plotly_chart(build_pareto_chart(pareto_df), use_container_width=True)

    with st.expander("Data table"):
        st.dataframe(pareto_df, use_container_width=True)


# ---------------------------------------------------------------------------
# SPC
# ---------------------------------------------------------------------------


def render_spc(con: duckdb.DuckDBPyConnection, filters: Filters) -> None:
    """Render the SPC Individuals Chart page."""
    st.header("SPC — Individuals Chart")

    db_path = _data.get_db_path()

    boards = distinct_boards(con)
    if not boards:
        st.info("No board profiles found in the database.")
        return

    board = st.selectbox("Board profile", boards, index=0)

    refdes_list = distinct_refdes(con, board)
    if not refdes_list:
        st.info(
            f"No components with measurements found for board '{board}'. "
            "Select a different board or widen the date range."
        )
        return

    refdes = st.selectbox("Component (refdes)", refdes_list, index=0)

    record_type = st.text_input("Filter by record_type (optional)", value="")
    rt = record_type.strip() if record_type.strip() else None

    rules = st.multiselect(
        "Alarm rules",
        ["rule_1", "rule_2", "rule_3", "rule_4"],
        default=["rule_1", "rule_4"],
    )
    rules_tuple = tuple(rules) if rules else ("rule_1", "rule_4")

    spc_df = cached_spc(
        con,
        db_path=db_path,
        window_days=filters.window_days,
        as_of=filters.as_of,
        board_profile_id=board,
        refdes=refdes,
        record_type=rt,
        rules=rules_tuple,
    )

    if spc_df.empty:
        st.info(
            f"No SPC data for {board}/{refdes} in the selected window."
        )
        return

    st.plotly_chart(build_spc_chart(spc_df), use_container_width=True)

    with st.expander("Data table"):
        st.dataframe(
            spc_df[["panel_serial", "start_ts", "value", "mean", "ucl", "lcl", "alarms"]],
            use_container_width=True,
        )


# ---------------------------------------------------------------------------
# Anomalies
# ---------------------------------------------------------------------------


def render_anomalies(con: duckdb.DuckDBPyConnection, filters: Filters) -> None:
    """Render the Anomaly Detection page (z-score by group)."""
    st.header("Anomaly Detection")

    db_path = _data.get_db_path()

    by = st.selectbox(
        "Group by",
        ["shift", "board", "line", "operator"],
        index=0,
    )
    threshold = st.slider(
        "Z-score threshold",
        min_value=1.0,
        max_value=5.0,
        value=3.0,
        step=0.5,
    )

    anomaly_df = cached_anomaly(
        con,
        db_path=db_path,
        window_days=filters.window_days,
        as_of=filters.as_of,
        by=by,
        threshold=threshold,
    )

    if anomaly_df.empty:
        st.info("No test runs in the selected window to analyze.")
        return

    st.plotly_chart(
        build_anomaly_bar(anomaly_df, threshold=threshold),
        use_container_width=True,
    )

    # Table with ⚠ flag label
    display_df = anomaly_df[
        ["group_key", "value", "z_score", "flagged", "flag_label"]
    ].copy()
    display_df.rename(
        columns={"group_key": "Group", "value": "Failure rate",
                 "z_score": "Z-score", "flagged": "Flagged", "flag_label": "Flag"},
        inplace=True,
    )

    with st.expander("Data table"):
        st.dataframe(display_df, use_container_width=True)
