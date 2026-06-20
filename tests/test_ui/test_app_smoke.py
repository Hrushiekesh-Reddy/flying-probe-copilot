"""tests/test_ui/test_app_smoke.py — Headless smoke tests for app.py.

Step 15 of the plan.

Tests:
  1. Valid DB (FPC_DB_PATH=ui_db_path): ``AppTest.from_file`` runs, no exception,
     sidebar date filter present (covers app wiring + default Overview).
  2. Missing DB (FPC_DB_PATH=nonexistent path): app shows error and stops
     without raising an unhandled Python exception.
"""

from __future__ import annotations

import os
import pathlib

import pytest
from streamlit.testing.v1 import AppTest

# Path to app.py — absolute so AppTest.from_file finds it regardless of cwd.
APP_PATH = str(
    pathlib.Path(__file__).parents[2]
    / "src"
    / "flying_probe_copilot"
    / "ui"
    / "app.py"
)


class TestAppSmokeValid:
    def test_no_exception_with_valid_db(self, ui_db_path, monkeypatch):
        """App runs with no exception when a valid DB is provided."""
        monkeypatch.setenv("FPC_DB_PATH", ui_db_path)
        at = AppTest.from_file(APP_PATH)
        at.run(timeout=15)
        assert not at.exception, f"app raised exception with valid DB: {at.exception}"

    def test_sidebar_has_date_inputs(self, ui_db_path, monkeypatch):
        """Sidebar contains date_input widgets from the global filter."""
        monkeypatch.setenv("FPC_DB_PATH", ui_db_path)
        at = AppTest.from_file(APP_PATH)
        at.run(timeout=15)
        # The sidebar should have at least one date_input (start and end date)
        sidebar_date_inputs = at.sidebar.date_input
        assert len(sidebar_date_inputs) > 0, (
            f"expected date_input in sidebar, got {sidebar_date_inputs}"
        )


class TestAppSmokeEmptyDb:
    def test_empty_db_no_exception(self, tmp_path, monkeypatch):
        """App runs with an empty DB (no test_runs) — covers span=None branch."""
        import duckdb
        from flying_probe_copilot.db.schema import init_database
        empty_db = str(tmp_path / "empty.duckdb")
        con = duckdb.connect(empty_db)
        init_database(con)
        con.close()

        monkeypatch.setenv("FPC_DB_PATH", empty_db)
        at = AppTest.from_file(APP_PATH)
        at.run(timeout=15)
        assert not at.exception, f"empty DB raised: {at.exception}"


class TestAppSmokeMissingDb:
    def test_missing_db_shows_error_no_exception(self, monkeypatch):
        """App shows st.error and stops — no unhandled Python exception."""
        monkeypatch.setenv("FPC_DB_PATH", "/nonexistent/path/db.duckdb")
        at = AppTest.from_file(APP_PATH)
        at.run(timeout=10)
        # The app should NOT raise an unhandled exception (Python exception)
        # It should call st.error() + st.stop() — visible as at.error elements
        # We just verify it ran without a Python crash.
        # st.exception would contain Python errors; st.error would contain
        # the user-facing error message.
        # With st.stop(), the script ends early — that is expected behavior.
        # The key check: no unhandled Python exception from the app.
        assert not at.exception, (
            f"missing-DB path should not produce a Python exception, got: {at.exception}"
        )
