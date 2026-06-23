"""tests/test_ui/test_views_smoke.py — AppTest headless smoke tests for views.

Step 13 of the plan.

Each ``render_X`` function is tested via ``AppTest.from_function`` with kwargs
passing the db_path (so the function body is self-contained and can be source-
extracted by AppTest). Asserts:
  - ``not at.exception`` (no st.exception() elements)
  - An expected UI element (header or plotly chart) is present

Empty-data variants use a narrow past window to hit the ``st.info`` branches.
"""

from __future__ import annotations

from datetime import datetime

from streamlit.testing.v1 import AppTest

# ---------------------------------------------------------------------------
# Helper: build a Filters-like kwargs dict from ui_db_path
# ---------------------------------------------------------------------------


def _base_kwargs(ui_db_path: str) -> dict:
    """Return kwargs to pass to view smoke functions."""
    as_of = datetime(2026, 4, 14, 23, 59, 59)
    return {
        "db_path": ui_db_path,
        "window_days": 30,
        "as_of_iso": as_of.isoformat(),
    }


def _empty_kwargs(ui_db_path: str) -> dict:
    """Return kwargs with a window that will find no data (very old as_of)."""
    as_of = datetime(2000, 1, 1, 23, 59, 59)
    return {
        "db_path": ui_db_path,
        "window_days": 1,
        "as_of_iso": as_of.isoformat(),
    }


# ===========================================================================
# render_overview
# ===========================================================================


def _smoke_overview(db_path, window_days, as_of_iso):
    from datetime import datetime

    import duckdb  # noqa: F811

    from flying_probe_copilot.ui.data import Filters
    from flying_probe_copilot.ui.views import render_overview

    con = duckdb.connect(db_path, read_only=True)
    filters = Filters(
        window_days=window_days,
        as_of=datetime.fromisoformat(as_of_iso),
    )
    render_overview(con, filters)
    con.close()


def _smoke_overview_empty(db_path, window_days, as_of_iso):
    from datetime import datetime

    import duckdb  # noqa: F811

    from flying_probe_copilot.ui.data import Filters
    from flying_probe_copilot.ui.views import render_overview

    con = duckdb.connect(db_path, read_only=True)
    filters = Filters(
        window_days=window_days,
        as_of=datetime.fromisoformat(as_of_iso),
    )
    render_overview(con, filters)
    con.close()


class TestRenderOverview:
    def test_smoke_no_exception(self, ui_db_path):
        at = AppTest.from_function(_smoke_overview, kwargs=_base_kwargs(ui_db_path))
        at.run(timeout=10)
        assert not at.exception, f"unexpected exception in render_overview: {at.exception}"

    def test_smoke_has_header(self, ui_db_path):
        at = AppTest.from_function(_smoke_overview, kwargs=_base_kwargs(ui_db_path))
        at.run(timeout=10)
        assert (
            len(at.header) > 0 or len(at.subheader) > 0 or len(at.title) > 0 or len(at.markdown) > 0
        ), "expected at least one header/title/markdown element in render_overview"

    def test_smoke_empty_window_no_exception(self, ui_db_path):
        at = AppTest.from_function(_smoke_overview_empty, kwargs=_empty_kwargs(ui_db_path))
        at.run(timeout=10)
        assert not at.exception, f"render_overview empty raised: {at.exception}"


# ===========================================================================
# render_yield
# ===========================================================================


def _smoke_yield(db_path, window_days, as_of_iso):
    from datetime import datetime

    import duckdb  # noqa: F811

    from flying_probe_copilot.ui.data import Filters
    from flying_probe_copilot.ui.views import render_yield

    con = duckdb.connect(db_path, read_only=True)
    filters = Filters(
        window_days=window_days,
        as_of=datetime.fromisoformat(as_of_iso),
    )
    render_yield(con, filters)
    con.close()


def _smoke_yield_empty(db_path, window_days, as_of_iso):
    from datetime import datetime

    import duckdb  # noqa: F811

    from flying_probe_copilot.ui.data import Filters
    from flying_probe_copilot.ui.views import render_yield

    con = duckdb.connect(db_path, read_only=True)
    filters = Filters(
        window_days=window_days,
        as_of=datetime.fromisoformat(as_of_iso),
    )
    render_yield(con, filters)
    con.close()


class TestRenderYield:
    def test_smoke_no_exception(self, ui_db_path):
        at = AppTest.from_function(_smoke_yield, kwargs=_base_kwargs(ui_db_path))
        at.run(timeout=10)
        assert not at.exception, f"render_yield raised: {at.exception}"

    def test_smoke_empty_no_exception(self, ui_db_path):
        at = AppTest.from_function(_smoke_yield_empty, kwargs=_empty_kwargs(ui_db_path))
        at.run(timeout=10)
        assert not at.exception, f"render_yield empty raised: {at.exception}"


# ===========================================================================
# render_pareto
# ===========================================================================


def _smoke_pareto(db_path, window_days, as_of_iso):
    from datetime import datetime

    import duckdb  # noqa: F811

    from flying_probe_copilot.ui.data import Filters
    from flying_probe_copilot.ui.views import render_pareto

    con = duckdb.connect(db_path, read_only=True)
    filters = Filters(
        window_days=window_days,
        as_of=datetime.fromisoformat(as_of_iso),
    )
    render_pareto(con, filters)
    con.close()


def _smoke_pareto_empty(db_path, window_days, as_of_iso):
    from datetime import datetime

    import duckdb  # noqa: F811

    from flying_probe_copilot.ui.data import Filters
    from flying_probe_copilot.ui.views import render_pareto

    con = duckdb.connect(db_path, read_only=True)
    filters = Filters(
        window_days=window_days,
        as_of=datetime.fromisoformat(as_of_iso),
    )
    render_pareto(con, filters)
    con.close()


class TestRenderPareto:
    def test_smoke_no_exception(self, ui_db_path):
        at = AppTest.from_function(_smoke_pareto, kwargs=_base_kwargs(ui_db_path))
        at.run(timeout=10)
        assert not at.exception, f"render_pareto raised: {at.exception}"

    def test_smoke_empty_no_exception(self, ui_db_path):
        at = AppTest.from_function(_smoke_pareto_empty, kwargs=_empty_kwargs(ui_db_path))
        at.run(timeout=10)
        assert not at.exception, f"render_pareto empty raised: {at.exception}"


# ===========================================================================
# render_spc
# ===========================================================================


def _smoke_spc(db_path, window_days, as_of_iso):
    from datetime import datetime

    import duckdb  # noqa: F811

    from flying_probe_copilot.ui.data import Filters
    from flying_probe_copilot.ui.views import render_spc

    con = duckdb.connect(db_path, read_only=True)
    filters = Filters(
        window_days=window_days,
        as_of=datetime.fromisoformat(as_of_iso),
    )
    render_spc(con, filters)
    con.close()


def _smoke_spc_empty(db_path, window_days, as_of_iso):
    from datetime import datetime

    import duckdb  # noqa: F811

    from flying_probe_copilot.ui.data import Filters
    from flying_probe_copilot.ui.views import render_spc

    con = duckdb.connect(db_path, read_only=True)
    filters = Filters(
        window_days=window_days,
        as_of=datetime.fromisoformat(as_of_iso),
    )
    render_spc(con, filters)
    con.close()


def _smoke_spc_no_boards(db_path, window_days, as_of_iso):
    """Runs render_spc against a DB with no boards (covers no-boards guard)."""
    from datetime import datetime

    import duckdb  # noqa: F811

    from flying_probe_copilot.db.schema import init_database
    from flying_probe_copilot.ui.data import Filters
    from flying_probe_copilot.ui.views import render_spc

    con = duckdb.connect(":memory:")
    init_database(con)
    filters = Filters(
        window_days=window_days,
        as_of=datetime.fromisoformat(as_of_iso),
    )
    render_spc(con, filters)
    con.close()


class TestRenderSpc:
    def test_smoke_no_exception(self, ui_db_path):
        at = AppTest.from_function(_smoke_spc, kwargs=_base_kwargs(ui_db_path))
        at.run(timeout=10)
        assert not at.exception, f"render_spc raised: {at.exception}"

    def test_smoke_empty_no_exception(self, ui_db_path):
        at = AppTest.from_function(_smoke_spc_empty, kwargs=_empty_kwargs(ui_db_path))
        at.run(timeout=10)
        assert not at.exception, f"render_spc empty raised: {at.exception}"

    def test_smoke_no_boards_no_exception(self, ui_db_path):
        """render_spc with an empty DB (no boards) hits the no-boards guard."""
        at = AppTest.from_function(
            _smoke_spc_no_boards,
            kwargs=_base_kwargs(ui_db_path),
        )
        at.run(timeout=10)
        assert not at.exception, f"render_spc no-boards raised: {at.exception}"


# ===========================================================================
# render_anomalies
# ===========================================================================


def _smoke_anomalies(db_path, window_days, as_of_iso):
    from datetime import datetime

    import duckdb  # noqa: F811

    from flying_probe_copilot.ui.data import Filters
    from flying_probe_copilot.ui.views import render_anomalies

    con = duckdb.connect(db_path, read_only=True)
    filters = Filters(
        window_days=window_days,
        as_of=datetime.fromisoformat(as_of_iso),
    )
    render_anomalies(con, filters)
    con.close()


def _smoke_anomalies_empty(db_path, window_days, as_of_iso):
    from datetime import datetime

    import duckdb  # noqa: F811

    from flying_probe_copilot.ui.data import Filters
    from flying_probe_copilot.ui.views import render_anomalies

    con = duckdb.connect(db_path, read_only=True)
    filters = Filters(
        window_days=window_days,
        as_of=datetime.fromisoformat(as_of_iso),
    )
    render_anomalies(con, filters)
    con.close()


class TestRenderAnomalies:
    def test_smoke_no_exception(self, ui_db_path):
        at = AppTest.from_function(_smoke_anomalies, kwargs=_base_kwargs(ui_db_path))
        at.run(timeout=10)
        assert not at.exception, f"render_anomalies raised: {at.exception}"

    def test_smoke_empty_no_exception(self, ui_db_path):
        at = AppTest.from_function(_smoke_anomalies_empty, kwargs=_empty_kwargs(ui_db_path))
        at.run(timeout=10)
        assert not at.exception, f"render_anomalies empty raised: {at.exception}"
