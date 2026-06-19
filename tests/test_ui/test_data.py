"""tests/test_ui/test_data.py — unit tests for flying_probe_copilot.ui.data.

Group 1 (steps 3-7 of the plan):
  - date_range_to_window
  - *_rows_to_df helpers
  - filter_df_by_key
  - overview_kpis
  - data_date_span, distinct_values, distinct_boards, distinct_refdes

All tests follow RED->GREEN discipline.  DB-query tests use the ``ui_db_path``
session-scoped fixture from conftest.py and open a new read-only connection
per test function.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

import duckdb
import pandas as pd
import pytest

from flying_probe_copilot.analytics.models import (
    AnomalyRow,
    ParetoRow,
    SPCPoint,
    YieldRow,
)
from flying_probe_copilot.ui.data import (
    Filters,
    anomaly_rows_to_df,
    cached_anomaly,
    cached_pareto,
    cached_spc,
    cached_yield,
    data_date_span,
    date_range_to_window,
    distinct_boards,
    distinct_refdes,
    distinct_values,
    filter_df_by_key,
    get_connection,
    overview_kpis,
    pareto_rows_to_df,
    spc_points_to_df,
    yield_rows_to_df,
)


# ===========================================================================
# Step 3 — date_range_to_window
# ===========================================================================


class TestDateRangeToWindow:
    def test_normal_range_window_days(self):
        """Multi-day range: window_days = (end - start).days + 1."""
        start = date(2026, 4, 7)
        end = date(2026, 4, 14)
        window_days, as_of = date_range_to_window(start, end)
        assert window_days == 8, f"expected 8, got {window_days}"

    def test_normal_range_as_of_time(self):
        """as_of should be naive datetime at 23:59:59 on end date."""
        start = date(2026, 4, 7)
        end = date(2026, 4, 14)
        _, as_of = date_range_to_window(start, end)
        assert as_of == datetime(2026, 4, 14, 23, 59, 59), f"unexpected as_of: {as_of}"
        assert as_of.tzinfo is None, "as_of must be naive"

    def test_single_day_range(self):
        """start == end → window_days == 1."""
        d = date(2026, 6, 18)
        window_days, as_of = date_range_to_window(d, d)
        assert window_days == 1, f"expected 1, got {window_days}"
        assert as_of == datetime(2026, 6, 18, 23, 59, 59)

    def test_end_before_start_raises(self):
        """end < start → ValueError."""
        with pytest.raises(ValueError, match="end.*before.*start|start.*after.*end|end < start"):
            date_range_to_window(date(2026, 4, 14), date(2026, 4, 7))

    def test_as_of_is_naive(self):
        """Returned as_of carries no tzinfo."""
        _, as_of = date_range_to_window(date(2026, 1, 1), date(2026, 1, 31))
        assert as_of.tzinfo is None


# ===========================================================================
# Step 4 — *_rows_to_df helpers
# ===========================================================================


class TestYieldRowsDf:
    def test_non_empty_returns_correct_df(self):
        rows = [
            YieldRow(group_key="small", total=5, passed=4, yield_pct=80.0),
            YieldRow(group_key="medium", total=3, passed=2, yield_pct=66.666),
        ]
        df = yield_rows_to_df(rows)
        assert list(df.columns) == ["group_key", "total", "passed", "yield_pct"]
        assert len(df) == 2
        assert df.loc[0, "group_key"] == "small"
        assert df.loc[0, "yield_pct"] == 80.0

    def test_empty_returns_empty_with_columns(self):
        df = yield_rows_to_df([])
        assert list(df.columns) == ["group_key", "total", "passed", "yield_pct"]
        assert len(df) == 0


class TestParetoRowsDf:
    def test_non_empty(self):
        rows = [
            ParetoRow(key="A-RES", count=10, pct_of_total=50.0, cumulative_pct=50.0),
            ParetoRow(key="D-SHO", count=5, pct_of_total=25.0, cumulative_pct=75.0),
        ]
        df = pareto_rows_to_df(rows)
        assert list(df.columns) == ["key", "count", "pct_of_total", "cumulative_pct"]
        assert len(df) == 2
        assert df.loc[0, "key"] == "A-RES"
        assert df.loc[0, "count"] == 10

    def test_empty_returns_columns(self):
        df = pareto_rows_to_df([])
        assert list(df.columns) == ["key", "count", "pct_of_total", "cumulative_pct"]
        assert len(df) == 0


class TestSpcPointsDf:
    def test_non_empty_adds_derived_columns(self):
        pts = [
            SPCPoint(
                panel_serial="P-001",
                start_ts=datetime(2026, 4, 1, 10, 0, 0),
                value=10.1,
                mean=10.0,
                ucl=10.5,
                lcl=9.5,
                alarm_flags=(),
            ),
            SPCPoint(
                panel_serial="P-002",
                start_ts=datetime(2026, 4, 2, 10, 0, 0),
                value=10.8,
                mean=10.0,
                ucl=10.5,
                lcl=9.5,
                alarm_flags=("rule_1",),
            ),
        ]
        df = spc_points_to_df(pts)
        assert "alarmed" in df.columns, "derived 'alarmed' column missing"
        assert "alarms" in df.columns, "derived 'alarms' column missing"
        assert df.loc[0, "alarmed"] is False or df.loc[0, "alarmed"] == False
        assert df.loc[1, "alarmed"] is True or df.loc[1, "alarmed"] == True
        assert df.loc[1, "alarms"] == "rule_1"
        assert df.loc[0, "alarms"] == ""

    def test_empty_returns_columns_with_derived(self):
        df = spc_points_to_df([])
        assert "alarmed" in df.columns
        assert "alarms" in df.columns
        assert len(df) == 0


class TestAnomalyRowsDf:
    def test_non_empty_adds_flag_label(self):
        rows = [
            AnomalyRow(
                group_key="C",
                value=0.75,
                baseline_mean=0.1,
                baseline_std=0.05,
                z_score=13.0,
                flagged=True,
            ),
            AnomalyRow(
                group_key="A",
                value=0.0,
                baseline_mean=0.1,
                baseline_std=0.05,
                z_score=-2.0,
                flagged=False,
            ),
        ]
        df = anomaly_rows_to_df(rows)
        assert "flag_label" in df.columns
        flagged_row = df[df["group_key"] == "C"].iloc[0]
        normal_row = df[df["group_key"] == "A"].iloc[0]
        assert flagged_row["flag_label"] != "", "flagged row should have non-empty flag_label"
        assert normal_row["flag_label"] == "", "non-flagged row should have empty flag_label"

    def test_empty_returns_columns_with_flag_label(self):
        df = anomaly_rows_to_df([])
        assert "flag_label" in df.columns
        assert len(df) == 0


# ===========================================================================
# Step 5 — filter_df_by_key
# ===========================================================================


class TestFilterDfByKey:
    def setup_method(self):
        self.df = pd.DataFrame(
            {"group_key": ["A", "B", "C", "A"], "val": [1, 2, 3, 4]}
        )

    def test_subset_filter(self):
        result = filter_df_by_key(self.df, "group_key", ["A"])
        assert set(result["group_key"].tolist()) == {"A"}
        assert len(result) == 2

    def test_falsy_selected_returns_unchanged(self):
        result = filter_df_by_key(self.df, "group_key", [])
        assert len(result) == len(self.df)

    def test_none_selected_returns_unchanged(self):
        result = filter_df_by_key(self.df, "group_key", None)
        assert len(result) == len(self.df)

    def test_no_match_returns_empty(self):
        result = filter_df_by_key(self.df, "group_key", ["Z"])
        assert len(result) == 0

    def test_multiple_values(self):
        result = filter_df_by_key(self.df, "group_key", ["A", "B"])
        assert set(result["group_key"].tolist()) == {"A", "B"}


# ===========================================================================
# Step 6 — overview_kpis
# ===========================================================================


class TestOverviewKpis:
    def test_known_inputs(self):
        yield_df = pd.DataFrame({
            "group_key": ["small", "medium"],
            "total": [10, 5],
            "passed": [8, 4],
            "yield_pct": [80.0, 80.0],
        })
        pareto_df = pd.DataFrame({
            "key": ["A-RES", "D-SHO"],
            "count": [10, 5],
            "pct_of_total": [66.7, 33.3],
            "cumulative_pct": [66.7, 100.0],
        })
        anomaly_df = pd.DataFrame({
            "group_key": ["C", "A", "B"],
            "value": [0.75, 0.0, 0.0],
            "baseline_mean": [0.1, 0.1, 0.1],
            "baseline_std": [0.05, 0.05, 0.05],
            "z_score": [13.0, -2.0, -2.0],
            "flagged": [True, False, False],
            "flag_label": ["⚠", "", ""],
        })
        kpis = overview_kpis(yield_df, pareto_df, anomaly_df)
        assert kpis["panels_tested"] == 15
        assert kpis["total_failures"] == 15
        assert kpis["top_failure_mode"] == "A-RES"
        assert kpis["flagged_anomalies"] == 1
        assert abs(kpis["overall_yield_pct"] - 80.0) < 0.01

    def test_all_empty_returns_zeros_and_dash(self):
        yield_df = pd.DataFrame({"group_key": [], "total": [], "passed": [], "yield_pct": []})
        pareto_df = pd.DataFrame({"key": [], "count": [], "pct_of_total": [], "cumulative_pct": []})
        anomaly_df = pd.DataFrame({
            "group_key": [], "value": [], "baseline_mean": [],
            "baseline_std": [], "z_score": [], "flagged": [], "flag_label": [],
        })
        kpis = overview_kpis(yield_df, pareto_df, anomaly_df)
        assert kpis["panels_tested"] == 0
        assert kpis["total_failures"] == 0
        assert kpis["top_failure_mode"] == "—"
        assert kpis["flagged_anomalies"] == 0
        assert kpis["overall_yield_pct"] == 0.0


# ===========================================================================
# Step 7 — DB-query helpers (use ui_db_path fixture)
# ===========================================================================


@pytest.fixture
def ui_con(ui_db_path):
    """Open a fresh read-only connection for each test function."""
    con = duckdb.connect(ui_db_path, read_only=True)
    yield con
    con.close()


class TestDataDateSpan:
    def test_returns_min_max_dates(self, ui_con):
        result = data_date_span(ui_con)
        assert result is not None, "expected (min_date, max_date) tuple"
        min_date, max_date = result
        assert isinstance(min_date, date), f"min_date not a date: {type(min_date)}"
        assert isinstance(max_date, date), f"max_date not a date: {type(max_date)}"
        assert min_date <= max_date

    def test_empty_db_returns_none(self):
        con = duckdb.connect(":memory:")
        from flying_probe_copilot.db.schema import init_database
        init_database(con)
        result = data_date_span(con)
        assert result is None
        con.close()


class TestDistinctValues:
    def test_board_dimension(self, ui_con):
        vals = distinct_values(ui_con, "board")
        assert "small" in vals
        assert "medium" in vals

    def test_shift_dimension(self, ui_con):
        vals = distinct_values(ui_con, "shift")
        assert set(vals) == {"A", "B", "C"}

    def test_line_dimension(self, ui_con):
        vals = distinct_values(ui_con, "line")
        assert "LINE-A" in vals
        assert "LINE-B" in vals

    def test_operator_dimension(self, ui_con):
        vals = distinct_values(ui_con, "operator")
        assert "OP-1" in vals
        assert "OP-2" in vals

    def test_bad_dimension_raises(self, ui_con):
        with pytest.raises(ValueError, match="dimension"):
            distinct_values(ui_con, "bad_dim")


class TestDistinctBoards:
    def test_returns_board_ids(self, ui_con):
        boards = distinct_boards(ui_con)
        assert "small" in boards
        assert "medium" in boards


class TestDistinctRefdes:
    def test_returns_only_refdes_with_measurements(self, ui_con):
        """Only refdes that have non-null measured_value should be returned."""
        refdes = distinct_refdes(ui_con, "small")
        # R1 has >=15 non-null measurements; C1 has 1 non-null measurement
        assert "R1" in refdes, f"R1 not in {refdes}"

    def test_no_refdes_for_unknown_board(self, ui_con):
        refdes = distinct_refdes(ui_con, "nonexistent_board")
        assert refdes == []


# ===========================================================================
# Step 7b — Filters dataclass
# ===========================================================================


class TestFilters:
    def test_dataclass_fields(self):
        f = Filters(window_days=7, as_of=datetime(2026, 4, 14, 23, 59, 59))
        assert f.window_days == 7
        assert f.as_of == datetime(2026, 4, 14, 23, 59, 59)


# ===========================================================================
# Step 7c — get_connection (basic import check; full cache tested via fixture)
# ===========================================================================


class TestGetConnection:
    def test_read_only_connection_works(self, ui_db_path):
        con = get_connection(ui_db_path)
        # Should return a working read-only connection
        rows = con.execute("SELECT 1").fetchall()
        assert rows == [(1,)]


# ===========================================================================
# Step 17 — targeted coverage tests for cached_spc / cached_anomaly
# ===========================================================================


class TestCachedYield:
    def test_returns_dataframe(self, ui_db_path):
        """cached_yield returns a DataFrame; covers the function body."""
        con = duckdb.connect(ui_db_path, read_only=True)
        as_of = datetime(2026, 4, 14, 23, 59, 59)
        df = cached_yield(
            con,
            db_path=ui_db_path,
            window_days=30,
            as_of=as_of,
            group_by="board",
        )
        assert isinstance(df, pd.DataFrame)
        assert "group_key" in df.columns
        con.close()


class TestCachedPareto:
    def test_returns_dataframe(self, ui_db_path):
        """cached_pareto returns a DataFrame; covers the function body."""
        con = duckdb.connect(ui_db_path, read_only=True)
        as_of = datetime(2026, 4, 14, 23, 59, 59)
        df = cached_pareto(
            con,
            db_path=ui_db_path,
            window_days=30,
            as_of=as_of,
            by="record_type",
            top_n=10,
        )
        assert isinstance(df, pd.DataFrame)
        assert "key" in df.columns
        con.close()


class TestGetDbPath:
    def test_returns_default_when_env_not_set(self, monkeypatch):
        """get_db_path returns DEFAULT_DB_PATH when FPC_DB_PATH is not set."""
        monkeypatch.delenv("FPC_DB_PATH", raising=False)
        from flying_probe_copilot.ui.data import get_db_path, DEFAULT_DB_PATH
        assert get_db_path() == DEFAULT_DB_PATH

    def test_returns_env_when_set(self, monkeypatch):
        """get_db_path returns the FPC_DB_PATH env var when set."""
        monkeypatch.setenv("FPC_DB_PATH", "/tmp/custom.duckdb")
        from flying_probe_copilot.ui.data import get_db_path
        assert get_db_path() == "/tmp/custom.duckdb"


class TestCachedSpc:
    def test_returns_dataframe(self, ui_db_path):
        """cached_spc returns a DataFrame (not None); covers the function body."""
        con = duckdb.connect(ui_db_path, read_only=True)
        as_of = datetime(2026, 4, 14, 23, 59, 59)
        df = cached_spc(
            con,
            db_path=ui_db_path,
            window_days=30,
            as_of=as_of,
            board_profile_id="small",
            refdes="R1",
        )
        assert isinstance(df, pd.DataFrame), f"expected DataFrame, got {type(df)}"
        assert "value" in df.columns
        con.close()

    def test_empty_result_for_unknown_refdes(self, ui_db_path):
        """cached_spc returns empty DataFrame when refdes has no measurements."""
        con = duckdb.connect(ui_db_path, read_only=True)
        as_of = datetime(2026, 4, 14, 23, 59, 59)
        df = cached_spc(
            con,
            db_path=ui_db_path,
            window_days=30,
            as_of=as_of,
            board_profile_id="small",
            refdes="ZZZZ_NONEXISTENT",
        )
        assert df.empty
        con.close()


class TestCachedAnomaly:
    def test_returns_dataframe(self, ui_db_path):
        """cached_anomaly returns a DataFrame; covers the function body."""
        con = duckdb.connect(ui_db_path, read_only=True)
        as_of = datetime(2026, 4, 14, 23, 59, 59)
        df = cached_anomaly(
            con,
            db_path=ui_db_path,
            window_days=30,
            as_of=as_of,
            by="shift",
            threshold=3.0,
        )
        assert isinstance(df, pd.DataFrame)
        assert "group_key" in df.columns
        con.close()
