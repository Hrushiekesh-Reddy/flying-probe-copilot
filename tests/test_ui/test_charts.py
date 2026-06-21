"""tests/test_ui/test_charts.py — unit tests for flying_probe_copilot.ui.charts.

Group 2 (steps 8-11 of the plan):
  - build_yield_bar     (step 8)
  - build_pareto_chart  (step 9)
  - build_spc_chart     (step 10)
  - build_anomaly_bar   (step 11)

All chart builders are pure df → go.Figure functions; tests never launch Streamlit.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import pytest

from flying_probe_copilot.ui.charts import (
    COLOR_FAIL,
    COLOR_PASS,
    COLOR_WARN,
    build_anomaly_bar,
    build_pareto_chart,
    build_spc_chart,
    build_yield_bar,
)
from flying_probe_copilot.ui.data import (
    _ANOMALY_COLS,
    _PARETO_COLS,
    _SPC_COLS,
    _YIELD_COLS,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _empty_yield_df():
    return pd.DataFrame(columns=_YIELD_COLS)


def _yield_df():
    return pd.DataFrame(
        {
            "group_key": ["high_yield", "mid_yield", "low_yield"],
            "total": [10, 10, 10],
            "passed": [9, 8, 5],
            "yield_pct": [90.0, 80.0, 50.0],
        }
    )


def _empty_pareto_df():
    return pd.DataFrame(columns=_PARETO_COLS)


def _pareto_df():
    return pd.DataFrame(
        {
            "key": ["A-RES", "D-SHO", "D-OPN"],
            "count": [10, 6, 4],
            "pct_of_total": [50.0, 30.0, 20.0],
            "cumulative_pct": [50.0, 80.0, 100.0],
        }
    )


def _empty_spc_df():
    return pd.DataFrame(columns=_SPC_COLS)


def _spc_df():
    rows = []
    for i in range(20):
        alarmed = i == 15  # one alarm point
        rows.append(
            {
                "panel_serial": f"P-{i:04d}",
                "start_ts": datetime(2026, 4, i + 1, 10, 0, 0),
                "value": 10.0 + (0.5 if alarmed else 0.0),
                "mean": 10.0,
                "ucl": 10.4,
                "lcl": 9.6,
                "alarm_flags": ("rule_1",) if alarmed else (),
                "alarmed": alarmed,
                "alarms": "rule_1" if alarmed else "",
            }
        )
    return pd.DataFrame(rows, columns=_SPC_COLS)


def _empty_anomaly_df():
    return pd.DataFrame(columns=_ANOMALY_COLS)


def _anomaly_df():
    return pd.DataFrame(
        {
            "group_key": ["C", "A", "B"],
            "value": [0.75, 0.0, 0.05],
            "baseline_mean": [0.05, 0.05, 0.05],
            "baseline_std": [0.02, 0.02, 0.02],
            "z_score": [13.0, -2.5, 0.0],
            "flagged": [True, False, False],
            "flag_label": ["⚠", "", ""],
        }
    )


# ===========================================================================
# Step 8 — build_yield_bar
# ===========================================================================


class TestBuildYieldBar:
    def test_returns_figure(self):
        fig = build_yield_bar(_yield_df())
        assert isinstance(fig, go.Figure)

    def test_has_bar_trace(self):
        fig = build_yield_bar(_yield_df())
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        assert len(bar_traces) >= 1, "expected at least one Bar trace"

    def test_bar_y_values_are_yield_pct(self):
        df = _yield_df()
        fig = build_yield_bar(df)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        y_vals = list(bar_traces[0].y)
        expected = list(df["yield_pct"])
        assert y_vals == pytest.approx(expected, abs=0.01), (
            f"bar y values {y_vals} != yield_pct {expected}"
        )

    def test_high_yield_bar_color_is_pass(self):
        """Bars >= 90% should use COLOR_PASS."""
        df = _yield_df()
        fig = build_yield_bar(df)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        colors = list(bar_traces[0].marker.color)
        # high_yield row has yield_pct=90.0 → pass color
        assert colors[0] == COLOR_PASS, f"expected {COLOR_PASS}, got {colors[0]}"

    def test_mid_yield_bar_color_is_warn(self):
        """Bars >= 75% and < 90% should use COLOR_WARN."""
        df = _yield_df()
        fig = build_yield_bar(df)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        colors = list(bar_traces[0].marker.color)
        # mid_yield row has yield_pct=80.0 → warn color
        assert colors[1] == COLOR_WARN, f"expected {COLOR_WARN}, got {colors[1]}"

    def test_low_yield_bar_color_is_fail(self):
        """Bars < 75% should use COLOR_FAIL."""
        df = _yield_df()
        fig = build_yield_bar(df)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        colors = list(bar_traces[0].marker.color)
        # low_yield row has yield_pct=50.0 → fail color
        assert colors[2] == COLOR_FAIL, f"expected {COLOR_FAIL}, got {colors[2]}"

    def test_empty_df_returns_no_data_annotation(self):
        fig = build_yield_bar(_empty_yield_df())
        assert isinstance(fig, go.Figure)
        annotations = fig.layout.annotations
        texts = [a.text for a in annotations]
        assert any("No data" in t for t in texts), f"expected 'No data' annotation, got {texts}"


# ===========================================================================
# Step 9 — build_pareto_chart
# ===========================================================================


class TestBuildParetoChart:
    def test_returns_figure(self):
        fig = build_pareto_chart(_pareto_df())
        assert isinstance(fig, go.Figure)

    def test_has_two_data_traces(self):
        """Bar (count) + Line (cumulative_pct) — both required."""
        fig = build_pareto_chart(_pareto_df())
        assert len(fig.data) >= 2, f"expected >= 2 traces, got {len(fig.data)}"

    def test_bar_trace_y_is_count(self):
        fig = build_pareto_chart(_pareto_df())
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        assert len(bar_traces) >= 1
        y_vals = list(bar_traces[0].y)
        assert y_vals == [10, 6, 4], f"bar y != counts: {y_vals}"

    def test_line_trace_is_on_y2(self):
        """Cumulative-pct line must be on secondary y-axis (y2)."""
        fig = build_pareto_chart(_pareto_df())
        line_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        assert len(line_traces) >= 1, "no Scatter trace found"
        assert line_traces[0].yaxis == "y2", (
            f"cumulative line not on y2, got {line_traces[0].yaxis}"
        )

    def test_80_percent_ref_line_present(self):
        """80% reference line must appear as a layout shape."""
        fig = build_pareto_chart(_pareto_df())
        assert len(fig.layout.shapes) >= 1, "expected at least 1 layout shape (80% ref)"

    def test_empty_df_returns_no_data_annotation(self):
        fig = build_pareto_chart(_empty_pareto_df())
        texts = [a.text for a in fig.layout.annotations]
        assert any("No data" in t for t in texts)


# ===========================================================================
# Step 10 — build_spc_chart
# ===========================================================================


class TestBuildSpcChart:
    def test_returns_figure(self):
        fig = build_spc_chart(_spc_df())
        assert isinstance(fig, go.Figure)

    def test_has_value_trace(self):
        fig = build_spc_chart(_spc_df())
        names = [t.name for t in fig.data]
        assert "value" in names, f"'value' trace not found in {names}"

    def test_has_center_line_trace(self):
        fig = build_spc_chart(_spc_df())
        names = [t.name for t in fig.data]
        assert any("center" in n.lower() or "mean" in n.lower() for n in names), (
            f"center/mean trace not found in {names}"
        )

    def test_has_ucl_trace(self):
        fig = build_spc_chart(_spc_df())
        names = [t.name for t in fig.data]
        assert any("ucl" in n.lower() for n in names), f"UCL trace not found in {names}"

    def test_has_lcl_trace(self):
        fig = build_spc_chart(_spc_df())
        names = [t.name for t in fig.data]
        assert any("lcl" in n.lower() for n in names), f"LCL trace not found in {names}"

    def test_alarm_trace_present(self):
        fig = build_spc_chart(_spc_df())
        names = [t.name for t in fig.data]
        assert any("alarm" in n.lower() for n in names), f"alarm trace not found in {names}"

    def test_alarm_trace_point_count_matches_alarmed_rows(self):
        """Alarm trace should have exactly as many points as alarmed rows."""
        df = _spc_df()
        fig = build_spc_chart(df)
        alarm_traces = [t for t in fig.data if t.name and "alarm" in t.name.lower()]
        assert len(alarm_traces) >= 1
        # 1 alarmed row in our fixture
        n_alarmed = int(df["alarmed"].sum())
        assert len(alarm_traces[0].x) == n_alarmed, (
            f"alarm trace has {len(alarm_traces[0].x)} points, expected {n_alarmed}"
        )

    def test_empty_df_returns_no_data_annotation(self):
        fig = build_spc_chart(_empty_spc_df())
        texts = [a.text for a in fig.layout.annotations]
        assert any("No data" in t for t in texts)


# ===========================================================================
# Step 11 — build_anomaly_bar
# ===========================================================================


class TestBuildAnomalyBar:
    def test_returns_figure(self):
        fig = build_anomaly_bar(_anomaly_df(), threshold=3.0)
        assert isinstance(fig, go.Figure)

    def test_bar_y_is_z_score(self):
        df = _anomaly_df()
        fig = build_anomaly_bar(df, threshold=3.0)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        assert len(bar_traces) >= 1
        y_vals = list(bar_traces[0].y)
        assert y_vals == pytest.approx(list(df["z_score"]), abs=0.001)

    def test_flagged_bar_uses_fail_color(self):
        """First row (flagged=True) should have COLOR_FAIL marker."""
        df = _anomaly_df()
        fig = build_anomaly_bar(df, threshold=3.0)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        colors = list(bar_traces[0].marker.color)
        # First row in our df is "C" which has flagged=True
        assert colors[0] == COLOR_FAIL, f"expected {COLOR_FAIL} for flagged bar, got {colors[0]}"

    def test_threshold_ref_lines_present(self):
        """±threshold reference lines must appear as layout shapes."""
        fig = build_anomaly_bar(_anomaly_df(), threshold=3.0)
        assert len(fig.layout.shapes) >= 2, (
            f"expected >= 2 shapes for ±threshold, got {len(fig.layout.shapes)}"
        )

    def test_empty_df_returns_no_data_annotation(self):
        fig = build_anomaly_bar(_empty_anomaly_df(), threshold=3.0)
        texts = [a.text for a in fig.layout.annotations]
        assert any("No data" in t for t in texts)
