"""charts.py — Pure Plotly figure builders for the dashboard.

All functions accept a DataFrame (produced by the data.*_to_df helpers) and
return a ``plotly.graph_objects.Figure``.  They have no Streamlit dependency
and no side effects, making them straightforward to unit-test.

Color constants (plan §B):
    COLOR_PASS    — green  — yield >= 90%
    COLOR_WARN    — amber  — yield >= 75% and < 90%
    COLOR_FAIL    — red    — yield < 75% / flagged anomaly / alarm points
    COLOR_ACCENT  — blue   — secondary series
    COLOR_NEUTRAL — grey   — non-flagged anomaly bars

Empty-df contract:
    Every builder returns a Figure with a centered "No data" annotation when
    the input DataFrame is empty (instead of crashing or producing blank axes).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Color constants
# ---------------------------------------------------------------------------

COLOR_PASS = "#2e7d32"
COLOR_WARN = "#f9a825"
COLOR_FAIL = "#c62828"
COLOR_ACCENT = "#1565c0"
COLOR_NEUTRAL = "#90a4ae"

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _no_data_figure(title: str = "") -> go.Figure:
    """Return a blank Figure with a centered 'No data' annotation."""
    fig = go.Figure()
    fig.update_layout(
        title=title,
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[
            {
                "text": "No data",
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "showarrow": False,
                "font": {"size": 18, "color": COLOR_NEUTRAL},
            }
        ],
    )
    return fig


def _yield_color(pct: float) -> str:
    """Map a yield percentage to a semantic color."""
    if pct >= 90.0:
        return COLOR_PASS
    if pct >= 75.0:
        return COLOR_WARN
    return COLOR_FAIL


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------


def build_yield_bar(df: pd.DataFrame) -> go.Figure:
    """Build a vertical bar chart of yield % per group.

    Parameters
    ----------
    df:
        DataFrame from ``data.yield_rows_to_df``.  Must have columns
        ``group_key``, ``total``, ``passed``, ``yield_pct``.

    Returns
    -------
    go.Figure
        Bar chart with semantic per-bar colors and text labels.
        Returns a "No data" figure when ``df`` is empty.
    """
    if df.empty:
        return _no_data_figure("Yield by group")

    colors = [_yield_color(float(p)) for p in df["yield_pct"]]
    text_labels = [f"{float(p):.1f}%" for p in df["yield_pct"]]

    fig = go.Figure(
        go.Bar(
            x=list(df["group_key"]),
            y=list(df["yield_pct"]),
            marker={"color": colors},
            text=text_labels,
            textposition="outside",
            name="yield %",
        )
    )
    fig.update_layout(
        title="Yield % by group",
        yaxis={"title": "Yield %", "range": [0, 110]},
        xaxis={"title": "Group"},
        showlegend=False,
    )
    return fig


def build_pareto_chart(df: pd.DataFrame) -> go.Figure:
    """Build a Pareto chart: bar (count, primary y) + cumulative % line (secondary y).

    The 80% cumulative reference line is added as a layout shape.

    Parameters
    ----------
    df:
        DataFrame from ``data.pareto_rows_to_df``.  Columns: ``key``,
        ``count``, ``pct_of_total``, ``cumulative_pct``.

    Returns
    -------
    go.Figure with ``yaxis`` (count) and ``yaxis2`` (cumulative %).
    """
    if df.empty:
        return _no_data_figure("Failure Pareto")

    bar_trace = go.Bar(
        x=list(df["key"]),
        y=list(df["count"]),
        name="Count",
        marker={"color": COLOR_FAIL},
        yaxis="y",
    )
    line_trace = go.Scatter(
        x=list(df["key"]),
        y=list(df["cumulative_pct"]),
        name="Cumulative %",
        mode="lines+markers",
        marker={"color": COLOR_ACCENT},
        line={"color": COLOR_ACCENT},
        yaxis="y2",
    )

    fig = go.Figure(data=[bar_trace, line_trace])
    fig.update_layout(
        title="Failure Pareto",
        yaxis={"title": "Count"},
        yaxis2={
            "title": "Cumulative %",
            "overlaying": "y",
            "side": "right",
            "range": [0, 110],
            "showgrid": False,
        },
        xaxis={"title": "Failure type"},
        legend={"orientation": "h"},
    )
    # 80% reference line
    fig.add_hline(
        y=80,
        line_dash="dash",
        line_color=COLOR_WARN,
        annotation_text="80%",
        yref="y2",
    )
    return fig


def build_spc_chart(df: pd.DataFrame) -> go.Figure:
    """Build a Shewhart individuals (XmR) chart.

    Traces (all named so tests can assert by name):
        "value"  — per-panel value as line + markers
        "center" — horizontal center line (mean)
        "UCL"    — upper control limit (dashed)
        "LCL"    — lower control limit (dashed)
        "alarms" — alarm points as red X markers (only rows where alarmed=True)

    Parameters
    ----------
    df:
        DataFrame from ``data.spc_points_to_df``.  Must include columns
        ``start_ts``, ``value``, ``mean``, ``ucl``, ``lcl``, ``alarmed``.

    Returns
    -------
    go.Figure
        Empty → "No data" annotation.
    """
    if df.empty:
        return _no_data_figure("SPC Individuals Chart")

    center_val = float(df["mean"].iloc[0])
    ucl_val = float(df["ucl"].iloc[0])
    lcl_val = float(df["lcl"].iloc[0])
    x_vals = list(df["start_ts"])

    alarmed_df = df[df["alarmed"] == True]  # noqa: E712

    value_trace = go.Scatter(
        x=x_vals,
        y=list(df["value"]),
        mode="lines+markers",
        name="value",
        line={"color": COLOR_ACCENT},
        marker={"color": COLOR_ACCENT, "size": 6},
    )
    center_trace = go.Scatter(
        x=[x_vals[0], x_vals[-1]],
        y=[center_val, center_val],
        mode="lines",
        name="center",
        line={"color": COLOR_NEUTRAL, "dash": "solid"},
    )
    ucl_trace = go.Scatter(
        x=[x_vals[0], x_vals[-1]],
        y=[ucl_val, ucl_val],
        mode="lines",
        name="UCL",
        line={"color": COLOR_FAIL, "dash": "dash"},
    )
    lcl_trace = go.Scatter(
        x=[x_vals[0], x_vals[-1]],
        y=[lcl_val, lcl_val],
        mode="lines",
        name="LCL",
        line={"color": COLOR_FAIL, "dash": "dash"},
    )
    alarm_trace = go.Scatter(
        x=list(alarmed_df["start_ts"]),
        y=list(alarmed_df["value"]),
        mode="markers",
        name="alarms",
        marker={
            "color": COLOR_FAIL,
            "symbol": "x",
            "size": 12,
        },
    )

    fig = go.Figure(data=[value_trace, center_trace, ucl_trace, lcl_trace, alarm_trace])
    fig.update_layout(
        title="SPC Individuals Chart",
        xaxis={"title": "Test timestamp"},
        yaxis={"title": "Measured value"},
    )
    return fig


def build_anomaly_bar(df: pd.DataFrame, threshold: float) -> go.Figure:
    """Build a z-score bar chart for anomaly detection.

    Flagged bars use ``COLOR_FAIL``; non-flagged bars use ``COLOR_NEUTRAL``.
    ±threshold reference lines are added as layout shapes.

    Parameters
    ----------
    df:
        DataFrame from ``data.anomaly_rows_to_df``.  Columns: ``group_key``,
        ``z_score``, ``flagged``.
    threshold:
        Absolute z-score threshold; used for ±threshold reference lines.

    Returns
    -------
    go.Figure
        Empty → "No data" annotation.
    """
    if df.empty:
        return _no_data_figure("Anomaly Detection (Z-score)")

    colors = [COLOR_FAIL if f else COLOR_NEUTRAL for f in df["flagged"]]

    fig = go.Figure(
        go.Bar(
            x=list(df["group_key"]),
            y=list(df["z_score"]),
            marker={"color": colors},
            name="z-score",
        )
    )
    fig.update_layout(
        title="Anomaly Detection — Z-score by group",
        xaxis={"title": "Group"},
        yaxis={"title": "Z-score"},
    )
    # ±threshold reference lines
    fig.add_hline(
        y=threshold,
        line_dash="dash",
        line_color=COLOR_FAIL,
        annotation_text=f"+{threshold}σ",
    )
    fig.add_hline(
        y=-threshold,
        line_dash="dash",
        line_color=COLOR_FAIL,
        annotation_text=f"-{threshold}σ",
    )
    return fig
