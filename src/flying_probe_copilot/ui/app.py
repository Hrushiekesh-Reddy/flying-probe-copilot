"""app.py — Streamlit entry-point for the Flying-Probe Co-Pilot dashboard.

Run with:
    streamlit run src/flying_probe_copilot/ui/app.py

Design
------
- ``st.set_page_config(layout='wide')``
- Sidebar: global date-range picker → ``Filters(window_days, as_of)``
- ``st.navigation`` over 6 pages (Overview, Yield, Pareto, SPC, Anomalies, Co-Pilot)
- Missing-DB guard: ``st.error`` + ``st.stop()``

Absolute imports are mandatory here so that both ``streamlit run`` (which runs
this file as ``__main__``) and ``AppTest.from_file`` both resolve the package.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import streamlit as st

from flying_probe_copilot.ui import data as _data
from flying_probe_copilot.ui import views as _views
from flying_probe_copilot.ui.data import Filters, data_date_span, date_range_to_window

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Configure and run the 6-page Streamlit dashboard."""
    st.set_page_config(
        page_title="Flying-Probe Co-Pilot",
        layout="wide",
        page_icon="🔬",
    )

    # --- DB path & missing-DB guard ---
    db_path = _data.get_db_path()
    if not os.path.exists(db_path):
        st.error(
            f"Database not found at **{db_path}**. "
            "Set the `FPC_DB_PATH` environment variable to a valid DuckDB path, "
            "or generate a sample DB with the generator + parser CLIs:\n\n"
            "```\n"
            "uv run generator --board-profile=small --count=30 --out=data/synthetic/\n"
            "uv run parser --input=data/synthetic/<run_dir> --db=data/db/sample.duckdb\n"
            "```"
        )
        st.stop()
        return  # defensive (st.stop() raises ScriptRunner.StopException)

    con = _data.get_connection(db_path)

    # --- Sidebar: global date-range filter ---
    with st.sidebar:
        st.title("Filters")

        # Determine sensible defaults from the DB span
        span = data_date_span(con)
        if span is not None:
            default_start, default_end = span
        else:
            default_end = date.today()
            default_start = default_end - timedelta(days=30)

        start_date = st.date_input("Start date", value=default_start)
        end_date = st.date_input("End date", value=default_end)

        # Clamp end >= start
        if end_date < start_date:
            end_date = start_date

        window_days, as_of = date_range_to_window(start_date, end_date)
        filters = Filters(window_days=window_days, as_of=as_of)

    # --- 5 pages via st.navigation ---
    def _overview():
        _views.render_overview(con, filters)

    def _yield():
        _views.render_yield(con, filters)

    def _pareto():
        _views.render_pareto(con, filters)

    def _spc():
        _views.render_spc(con, filters)

    def _anomalies():
        _views.render_anomalies(con, filters)

    def _chat():
        from flying_probe_copilot.ui import chat as _chat_mod

        _chat_mod.render_chat()

    pages = [
        st.Page(_overview, title="Overview", icon="📊", default=True),
        st.Page(_yield, title="Yield", icon="📈"),
        st.Page(_pareto, title="Failure Pareto", icon="📉"),
        st.Page(_spc, title="SPC", icon="🎯"),
        st.Page(_anomalies, title="Anomalies", icon="⚠️"),
        st.Page(_chat, title="Co-Pilot", icon="🤖"),
    ]
    pg = st.navigation(pages)
    pg.run()


if __name__ == "__main__":
    main()
