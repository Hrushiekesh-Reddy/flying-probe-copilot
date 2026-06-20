# Plan — Phase 2 slice 3: Streamlit dashboard

> Step 3 (Plan) artifact — parent-authored. Date 2026-06-18. Tier: Medium.
> Brief: `docs/plans/2026-06-18-phase2-slice3-brief.md`. Design contract: §B below.

---

## A. Goal Contract

```
OBJECTIVE:
  Ship src/flying_probe_copilot/ui/ — a 5-page Streamlit+Plotly dashboard (Overview,
  Yield, Failure Pareto, SPC, Anomalies) over the 4 existing pure analytics functions,
  with global date-range filtering, per-page controls, Plotly charts, and st.cache_data
  /st.cache_resource caching.

SUCCESS-WHEN:
  1. `uv run streamlit run src/flying_probe_copilot/ui/app.py` launches; all 5 pages
     render against data/db/sample.duckdb with no exception; load < 2 s.
  2. New tests under tests/test_ui/ pass: pure-helper unit tests, chart-builder unit
     tests, and AppTest headless smoke (per-view + app entry + empty-DB + missing-DB).
  3. Full `uv run pytest` green; repo coverage >= 97% (slice-2 baseline).
  4. Analytics layer (4 functions + dataclasses) UNCHANGED.

OUT-OF-SCOPE:
  - Editing the 4 analytics functions / dataclasses (real bug -> chip, don't fix).
  - True yield time-series line (group_by="day" deferred, DECISION_LOG 2026-06-16).
  - Analytics-layer value-subset filters (functions aggregate-by-dimension only).
  - New deps (none needed). Real data. RAG/LLM. X-bar/R + IsolationForest. Cloud deploy.

CONSTRAINTS:
  - Phase 2 only. TDD (RED->GREEN->REFACTOR) for all testable logic.
  - NO approval-gated file edits. streamlit+plotly already in pyproject.toml + uv.lock
    (verified) -> NO pyproject edit. db/schema.py / migrations / settings.json / .env.example
    untouched.
  - Branch != main/dev. Commit only at Step 10. Push only when owner asks. No force-push.
```

## B. Design contract (locked at frontend-design pass)

- Shell: `st.set_page_config(layout="wide")`; `st.navigation` over 5 pages; **sidebar global
  filter** = a date-range picker -> `(window_days, as_of)`, default = full data span. Page-specific
  controls render at the top of each page (progressive disclosure).
- Overview: KPI `st.metric` cards (overall yield %, panels tested, total failures, top failure mode,
  # flagged anomalies) + compact yield bar + mini Pareto.
- Yield: dimension selector {board,shift,line,operator} + value multiselect (post-filter on rows);
  vertical bar of yield % per group, 0–100% axis, count labels, semantic color (>=90 green / >=75 amber / else red).
- Pareto: `by` {record_type,refdes} + `top_n` slider; bars (count desc) + cumulative-% line on 2nd axis + 80% ref line.
- SPC: board picker + refdes picker (from DB, only refdes with measurements) + optional record_type +
  rules multiselect; individuals line+markers vs start_ts, solid center, dashed UCL/LCL, alarm points as
  red ✕ markers WITH a legend label (not color alone).
- Anomalies: `by` selector + threshold slider; z-score bar per group, flagged bars red + "⚠" in the
  table column (not color alone), ±threshold ref lines.
- Drill-down = `st.expander` data table under each chart + Plotly hover. NOT analytics value-subsetting.
- Empty data -> `st.info` guidance (not a blank chart). Missing DB -> `st.error` + `st.stop()`.
- Colors (charts.py constants): pass #2e7d32, warn #f9a825, fail #c62828, accent #1565c0, neutral #90a4ae.

## C. What / Why / Where table

| File | What | Why (deliverable) | Test file |
|------|------|-------------------|-----------|
| `src/flying_probe_copilot/ui/__init__.py` | New (package marker, short docstring) | ROADMAP P2 `ui/` module | — |
| `src/flying_probe_copilot/ui/data.py` | New: `get_db_path`, `get_connection`(cache_resource, read_only), `date_range_to_window`, `data_date_span`, `distinct_values`/`distinct_boards`/`distinct_refdes`, `*_rows_to_df`/`spc_points_to_df`, `filter_df_by_key`, `overview_kpis`, `Filters` dataclass, `cached_yield/pareto/spc/anomaly` (cache_data->DataFrame) | ROADMAP P2 caching + filters | `tests/test_ui/test_data.py` |
| `src/flying_probe_copilot/ui/charts.py` | New: color constants + `build_yield_bar`, `build_pareto_chart`, `build_spc_chart`, `build_anomaly_bar` (pure df->go.Figure) | ROADMAP P2 Plotly charts | `tests/test_ui/test_charts.py` |
| `src/flying_probe_copilot/ui/views.py` | New: `render_overview/yield/pareto/spc/anomalies(con, filters)` | ROADMAP P2 pages | `tests/test_ui/test_views_smoke.py` |
| `src/flying_probe_copilot/ui/app.py` | New: `main()` — page config, db-path guard, sidebar filters, st.navigation over 5 pages | ROADMAP P2 Streamlit entry | `tests/test_ui/test_app_smoke.py` |
| `tests/test_ui/__init__.py` + `tests/test_ui/conftest.py` | New: temp file-DB fixture (`ui_db_path`) built from schema + minimal multi-board/shift/line/operator rows incl. components+measurements (>=15 SPC pts) + flagged anomaly; clears cache_resource on teardown | test infra | — |

**Absolute imports only** in `app.py` (`from flying_probe_copilot.ui import data, views`) so `AppTest.from_file` and `streamlit run` both work (entry runs as `__main__`, relative imports would break).

## D. Key signatures (so exec doesn't guess)

```python
# data.py
DEFAULT_DB_PATH = "data/db/sample.duckdb"; DB_PATH_ENV = "FPC_DB_PATH"
def get_db_path() -> str
@st.cache_resource
def get_connection(db_path: str) -> duckdb.DuckDBPyConnection   # duckdb.connect(db_path, read_only=True)
def date_range_to_window(start: date, end: date) -> tuple[int, datetime]
    # end<start -> ValueError; as_of=datetime.combine(end, time(23,59,59));
    # window_days=max(1,(end-start).days+1)  [over-includes <=1 day on low end — safe direction; documented]
def data_date_span(con) -> tuple[date, date] | None
def distinct_values(con, dimension: str) -> list[str]   # board/shift/line/operator; bad -> ValueError
def distinct_boards(con) -> list[str]
def distinct_refdes(con, board_profile_id: str) -> list[str]   # only refdes with non-null measured_value
def yield_rows_to_df / pareto_rows_to_df / spc_points_to_df / anomaly_rows_to_df(rows) -> pd.DataFrame
    # empty input -> empty df WITH the declared columns; spc adds bool 'alarmed' + str 'alarms'; anomaly adds 'flag_label'
def filter_df_by_key(df, key_col, selected) -> pd.DataFrame   # falsy selected -> unchanged
def overview_kpis(yield_df, pareto_df, anomaly_df) -> dict
@dataclass class Filters: window_days: int; as_of: datetime
@st.cache_data(show_spinner=False) cached_yield/pareto/spc/anomaly(_con, *, db_path, ...params...) -> pd.DataFrame

# charts.py  (all return go.Figure; empty df -> figure with centered "No data" annotation)
build_yield_bar(df) ; build_pareto_chart(df) ; build_spc_chart(df) ; build_anomaly_bar(df, threshold)
```

## E. Ordered TDD steps

> RED -> GREEN per sub-step. Build pure logic first (no Streamlit runtime), then render/AppTest.

**Group 0 — scaffolding**
1. Create `ui/__init__.py`, empty `ui/data.py`/`charts.py`/`views.py`, `tests/test_ui/__init__.py`. Confirm `pytest` still collects/green.
2. `tests/test_ui/conftest.py`: `ui_db_path` fixture — write temp `.duckdb`, `init_database`, insert 2 boards (small+medium), panels across shifts A/B/C + lines LINE-A/LINE-B + operators OP-1/OP-2, test_runs (some btest_status!=0 incl. one shift with elevated rate for a flagged anomaly), components + >=15 measurements for one (board,refdes), and matching failures. Teardown: `data.get_connection.clear()` then drop file.

**Group 1 — data.py pure helpers (RED->GREEN each)**
3. `date_range_to_window`: normal range, single-day (start==end -> window_days 1), end<start -> ValueError, as_of=23:59:59 naive.
4. `*_rows_to_df` (yield/pareto/spc/anomaly): non-empty mapping incl. derived cols; empty -> empty df with declared columns.
5. `filter_df_by_key`: subset, empty-selection passthrough, no-match -> empty.
6. `overview_kpis`: known dfs -> known KPIs; all-empty -> zeros + "—".
7. `data_date_span`, `distinct_values`(+bad-dim ValueError), `distinct_boards`, `distinct_refdes` against `ui_db_path` con.

**Group 2 — charts.py builders (RED->GREEN each)**
8. `build_yield_bar`: returns go.Figure; 1 bar trace; y == yield_pct; marker colors follow thresholds; empty df -> "No data" annotation.
9. `build_pareto_chart`: 2 data traces (bar count + line cumulative on y2); 80% ref line present; bar y == counts.
10. `build_spc_chart`: traces for value + center + UCL + LCL + alarm; alarm trace point count == alarmed rows; empty -> annotation.
11. `build_anomaly_bar`: bar y == z_scores; per-bar color flags flagged rows; ±threshold ref lines.

**Group 3 — views + app (AppTest)**
12. Confirm AppTest API: `from streamlit.testing.v1 import AppTest`; verify `AppTest.from_function` runs a zero-arg closure (fallback: module-global injection). One spike test.
13. `test_views_smoke.py`: for each `render_X`, `AppTest.from_function(closure(con, filters)).run()` -> `not at.exception` + an expected element (header/plotly chart). Include an empty-data variant (wide-past window / empty DB) to hit `st.info` branches.
14. Implement `views.render_*` minimally to pass each smoke test (charts + controls + expander + empty guards).
15. `test_app_smoke.py`: `AppTest.from_file(APP_PATH)` with `FPC_DB_PATH=ui_db_path` -> `not at.exception` + sidebar date filter present (covers app wiring + default Overview). Add a **missing-DB** test (`FPC_DB_PATH`=nonexistent) -> app shows error and stops without raising.
16. Implement `app.py` `main()` to pass.

**Group 4 — integration + coverage**
17. `uv run pytest` full suite green; check `--cov` >= 97%; add targeted tests for any uncovered branch (empty/error paths).
18. Manual launch smoke (parent, Step 9): `uv run streamlit run ...` headless; or `AppTest` already proves render. Time the load.

## F. Guardrails block

```
GUARDRAILS:
- Branch: this worktree's claude/zen-roentgen-2818ce (feature-style; NOT dev/main).
  feature/phase2-slice3-streamlit is locked by another worktree — final PR branch confirmed at Decision Gate.
- Critical/approval-gated files touched: NONE. (streamlit+plotly already declared+locked -> no pyproject edit.)
- New dependencies: NONE.
- Phase discipline: Phase 2 slice 3 (UI) only. Analytics functions read-only/unchanged.
- Docs to update (Step 10): SESSION_LOG, DECISION_LOG (UI contracts: yield-bar-not-line, date-range mapping,
  read-only cache_resource conn, value-filter-as-postfilter), ROADMAP (5 UI boxes + status + Phase 2 done),
  CLAUDE.md session line, BUG_LOG (if surfaced), AGENT_HANDOFF_LOG, manual-QA script.
```
