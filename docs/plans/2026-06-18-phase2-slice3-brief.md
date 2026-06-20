# Session Brief — Phase 2 slice 3: Streamlit dashboard

> Step 1 (Document) artifact. Written before any exploration/planning.
> Date: 2026-06-18 · Phase: 2 (Analytics) · Slice: 3 of 3 (final Phase 2 deliverable)

---

## Goal (one sentence)

Build the Streamlit + Plotly UI layer (`src/flying_probe_copilot/ui/`) over the four existing,
already-tested pure analytics functions — 5 pages (Overview, Yield, Failure Pareto, SPC, Anomalies)
with filter controls and `st.cache_data` caching — so a manufacturing engineer can explore yield,
failure Pareto, SPC control charts, and anomaly flags against a synthetic DuckDB locally.

## Tier decision (five-minute rule, `.claude/templates/tiering.md`)

- One file? No. ≥3 files + a new `ui/` abstraction. → not Trivial/Small.
- Schema/migration/parser-core/real-data? **No** — read-only over DuckDB, zero schema change,
  synthetic data only. → not Large.
- ≥3 files OR new abstraction OR milestone boundary? **Yes** (all three). → **Medium**.
- Risk bump? The only risk vector (approval-gated `pyproject.toml` dep add) **evaporated** — see
  Discoveries. No irreversible/public/real-data risk remains. → stays **Medium**.

**TIER = MEDIUM.** Steps that run: Document → Explore → Plan → Decision Gate → Execute →
Triple Check → Documentation. Per handover, also write a manual-QA script and verify the app
actually launches (parent Triple Check).

## Discoveries that change the handover's assumptions

1. **`streamlit>=1.40` + `plotly>=5.24` are ALREADY in `pyproject.toml` (lines 13-14) and `uv.lock`.**
   Verified: `uv run` built the venv and imported `streamlit 1.58.0` / `plotly 6.8.0` with no error.
   → The approval-gated `pyproject.toml` edit the handover flagged as "the one thing that needs the
   Decision Gate" is **moot**. **No approval-gated file will be touched.** (They were almost certainly
   added at Phase 0 `uv init` when the whole locked stack was declared up front.)
2. **`feature/phase2-slice3-streamlit` already exists but is empty** (identical to `dev`, 0 commits)
   and is **checked out in another worktree** (`xenodochial-black-3cc4d9`). Git forbids checking the
   same branch out twice → I cannot use that branch name here. The `beautiful-beaver-e50f90` worktree
   is on an unrelated BUG-011 task. **No `ui/` code exists on any branch.** I will work on THIS
   worktree's branch (`claude/zen-roentgen-2818ce`, currently at `dev` tip `e61ee24`) and surface the
   final branch/PR naming at the Decision Gate. No commit lands on `main`/`dev`.

## Scope — IN

- `src/flying_probe_copilot/ui/` package: `app.py` (entry), `data.py` (connection + cached query
  wrappers + pure filter/transform helpers), `charts.py` (pure Plotly figure builders), `views.py`
  (5 page render functions). Plus `ui/__init__.py`.
- 5 pages wired 1:1 to: `yield_over_time`, `failure_pareto`, `individuals_chart`,
  `z_score_anomalies` (+ an Overview that composes them).
- Plotly charts: yield bar-per-group, Pareto bar+cumulative line, SPC individuals line w/ center+UCL+LCL
  + alarm markers, anomaly bar w/ flagged groups highlighted.
- Filter controls: date range (→ `window_days` + `as_of`), and a group-by **dimension** selector
  {board, shift, line, operator} + value multiselect (post-filter); SPC gets board+refdes(+record_type)
  pickers; Pareto gets a `by` selector.
- `st.cache_data` on query-result wrappers; connection via `st.cache_resource` (read-only).
- Tests: `tests/test_ui/` — unit tests on pure helpers + chart builders; `AppTest` headless smoke.
- Docs: SESSION_LOG, DECISION_LOG (UI contracts), ROADMAP tick-off, CLAUDE.md session line,
  BUG_LOG if anything surfaces, manual-QA script, AGENT_HANDOFF_LOG entry.

## Scope — OUT (chip it, do not fix)

- **Do NOT modify the four analytics functions or their dataclasses** (unless a real bug → chip it).
- Real-data ingestion (Guardrail #1). RAG / LLM (Phase 3). X-bar/R + Isolation Forest (deferred at
  slice-2 gate, DECISION_LOG 2026-06-18). Cloud deploy (Phase 4).
- No new dependencies (none needed). No `pyproject.toml` / `db/schema.py` / migration / settings.json
  / `.env.example` edits.
- No analytics-layer value-subset filters (the functions group-and-aggregate; they do not filter to a
  single board/operator value) — UI does value-subsetting by post-filtering returned rows.

## Key constraint discovered (drives a Decision-Gate question)

The analytics functions **aggregate by a dimension over a rolling window**; they do **not** return a
time series and do **not** accept a "show only board X" subset filter. Consequences:
- `yield_over_time` returns one row PER GROUP for the window (not yield-vs-time). "day" grouping was
  explicitly deferred (DECISION_LOG 2026-06-16). → Honest v1 Yield chart = **bar of yield% per group**,
  not a time-series line. (Decision-Gate item.)
- "Drill-down" / per-value filters are realized as UI post-filters on grouped rows + data-table
  expanders + hover, not as analytics-layer subsetting.

## Success criteria (Definition of Done)

- `uv run streamlit run src/flying_probe_copilot/ui/app.py` launches; all 5 pages render against
  `data/db/sample.duckdb` without error; loads < 2 s.
- Full `uv run pytest` green; repo coverage ≥ 97% baseline; UI helpers + chart builders unit-tested;
  `AppTest` smoke passes.
- Plan + gate + triple-check + manual-QA artifacts under `docs/plans/2026-06-18-phase2-slice3-*.md`.
- ROADMAP Phase 2 UI boxes ticked; Phase 2 complete. PR opened to `dev` (push owner-initiated).

## Guardrails in force

TDD mandatory (RED→GREEN→REFACTOR for testable logic). Branch ≠ main/dev. Commit only at Step 10;
push only when owner asks. Never force-push. Synthetic data only. Approval-gated files untouched.
