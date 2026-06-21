# ROADMAP.md

8-10 calendar weeks. Evenings + weekends. ~70-90 total hours.

---

## Phase 0 — Setup & Documentation (Days 1-3)

**Goal:** Repo, docs, and tools ready. No code yet.

### Deliverables
- [x] Project decision locked (flagship flying-probe co-pilot)
- [x] SKILLS.md and RESOURCES.md authored
- [x] GitHub repo `flying-probe-copilot` created (private)
- [x] Doc skeleton committed (README, CLAUDE.md, GUARDRAILS, SCOPE, ROADMAP, DECISIONS, REQUIREMENTS)
- [x] `.cursor/rules/project.mdc` committed
- [x] `.env.example` committed; `.env` ignored
- [x] `pyproject.toml` initialized with `uv init`
- [ ] Keysight i3070 manuals downloaded locally (kept off git)
- [x] First session log entry in CLAUDE.md

### Exit criteria
All boxes checked. Owner can describe project goals, scope, and guardrails from memory.

---

## Phase 1a — Synthetic HP3070 Log Generator (Week 1-2)

**Goal:** Generate realistic HP3070-style test reports from configurable parameters.

### Deliverables
- [x] `src/flying_probe_copilot/generator/` module
- [x] Data models for: Board, Panel, TestRun, Test, Measurement (pydantic v2 + 6 IntEnums + tagged-union validator)
- [x] Configurable parameters: board profile, panel count, fault injection rate, drift rate, operator IDs, line ID
- [x] At least 3 board profiles (small / medium / large component counts)
- [x] Output formats: `.log` (real Keysight Log Record Format), `.csv` (flat), `.json` (structured)
- [x] Fault injection covering: opens, shorts, out-of-tolerance analog, missing components, digital failures (4 profiles: random / drift / cluster / process-change)
- [x] CLI entry point: `uv run generator --board-profile=medium --count=100 --out=data/synthetic/`
- [x] Unit tests: 81 tests covering schema, fault distribution (±2pp / 10K panels), lexical compliance, seed reproducibility, BTEST derivation, sentinel-string guardrail; 94% line coverage
- [ ] README section in generator module documenting the format (deferred — small standalone doc task)

### Exit criteria
Generator produces 1,000 logs in <30 seconds; output passes parseability test; visual inspection of a sample log by an experienced engineer would not immediately flag it as fake.

**Status (2026-06-13):** 8/9 deliverables complete. 1000 small-profile panels generated in ~1 s (well under target). Output passes `grammar.validate()` lexical-compliance check across small/medium/drift runs. Visual-inspection criterion deferred to Step 9 manual QA. README documentation deliverable deferred to a follow-up doc-only session.

See `specs/synthetic-log-generator.md` for the full spec (revised 2026-06-13 to target the real Keysight Log Record Format).

---

## Phase 1b — Parser & DuckDB Schema (Week 3-4)

**Goal:** Logs become queryable rows.

### Deliverables
- [x] `src/flying_probe_copilot/parser/` module
- [x] DuckDB schema: dimension tables (boards, panels, operators, components, tests) + fact tables (test_runs, measurements, failures) + runs metadata table (9 tables total)
- [x] Parser ingests generator output reliably
- [x] CLI: `uv run parser --input=data/synthetic/<run_dir>/ --db=data/db/flying-probe.duckdb`
- [x] Sample SQL queries documented in `notebooks/01-queries.ipynb` (canonical yield-by-board-last-7-days exit query + 5 representative analytics queries: failure Pareto by record_type, per-shift yield, per-operator yield, top-10 failing refdes, btest_status distribution)
- [x] Parser tests: round-trip integrity (generator → parser → DB → match)
- [x] Error handling for malformed lines (log + skip, don't crash)

### Exit criteria
"Yield by board over last week" query returns correct result. Round-trip test passes for ≥99% of generator output.

**Status (2026-06-14):** 7/7 deliverables complete. 179 tests passing / 0 failing / 97% total coverage; parser 97%, db 100%. Round-trip test asserts count + per-panel start_ts equality. Yield query test passes with a deterministic 2-week × 2-profile fixture (last-week window with `>=` boundary semantics). Notebook `notebooks/01-queries.ipynb` authored against a 20-panel small-profile sample DB (`data/db/sample.duckdb`, gitignored via `*.duckdb`); every code cell smoke-tested in-process against the live DB. 10-step session-workflow loop ran end-to-end.

---

## Phase 2 — Analytics & Dashboard (Week 5-6)

**Goal:** A working Streamlit dashboard over the data.

### Deliverables
- [x] `src/flying_probe_copilot/analytics/` module
  - [x] Yield-over-time function (`yield_over_time`, 2026-06-16)
  - [x] Failure Pareto function (`failure_pareto`, 2026-06-16)
  - [x] SPC chart helpers — individuals (XmR) chart (`individuals_chart`, 2026-06-18; X-bar/R deferred — no rational subgroups)
  - [x] Anomaly detection — z-score leave-one-out baseline (`z_score_anomalies`, 2026-06-18; Isolation Forest deferred — would add `sklearn`)
- [x] `src/flying_probe_copilot/ui/` Streamlit app (`app.py`, `data.py`, `charts.py`, `views.py`; 2026-06-18)
- [x] Pages: Overview, Yield, Failure Pareto, SPC, Anomalies (`st.navigation`; 2026-06-18)
- [x] Plotly charts with drill-down (data-table expanders + hover; yield bar, Pareto bar+cumulative, SPC individuals w/ limits+alarms, anomaly z-score bar; 2026-06-18)
- [x] Filter controls: date range (→ window_days/as_of) + group-by dimension {board, operator, line, shift} + value multiselect; SPC board/refdes/record_type/rules pickers (2026-06-18)
- [x] Caching with `st.cache_data` for query results (+ `st.cache_resource` read-only connection; 2026-06-18)

### Exit criteria
Dashboard runs locally with `uv run streamlit run src/.../ui/app.py`. Loads in <2s on 100k records.
**Met (2026-06-18):** launches headless, health OK ~1 s, default page renders in **0.23 s** on the sample DB.

**Status (2026-06-16):** Phase 2 kicked off with a pre-analytics data-quality task. Per-panel operator-id repair landed (BUG-009 resolved, BUG-007 operator half closed). `@BTEST` now carries mandatory per-panel `operator_id` at field 12; `test_runs.operator_id` flipped to `VARCHAR NOT NULL`; per-operator analytics now sit on real data, not the batch-level placeholder. 196 tests passing, 97% coverage. Branch: `feature/per-panel-operator`. Shift + line_id half of BUG-007 still open — pick path next session. Analytics module / Streamlit not yet started.

**Status (2026-06-16):** Slice 1 of Phase 2 also complete — analytics module foundation. `yield_over_time(con, *, window_days=7, group_by="board", as_of=None) → list[YieldRow]` and `failure_pareto(con, *, window_days=7, by="record_type", top_n=10, as_of=None) → list[ParetoRow]` shipped as pure stdlib + duckdb library calls. 39 new tests (17 yield + 19 pareto + 3 public API), 224 total passing, 0 failing. Analytics package coverage 96-100% per file (target was ≥80%). Every code path that groups by BUG-007-affected columns (`shift`, `line_id`, `operator_id`) marks results via per-row `placeholder_fields: tuple[str, ...]`. Zero edits to existing files; pure additive. Six v1 contract decisions documented in `docs/logs/DECISION_LOG.md` (Pareto record-type-only, yield ordering `group_key ASC`, unrounded floats, strict `window_days >= 1` / `top_n >= 1` / naive UTC validation). Notebook Q4 (per-operator) ordering NOT matched — documented divergence.

**Status (2026-06-17):** BUG-007 **FULLY RESOLVED**. Path A applied to the remaining two fields: `@BTEST` gains mandatory `shift: Literal["A","B","C"]` at field 13 and `line_id: str` at field 14; `_make_board_log` reads `btest.shift` / `btest.line_id`. Schema already `NOT NULL` for both — no flip needed. 200 tests passing, 97% coverage. Per-shift + per-operator + per-line analytics now all sit on real per-panel data. PR `feature/per-panel-operator` → `dev` closes both halves of BUG-007 in one feature PR. Analytics slice 2 (SPC + anomaly) and slice 3 (Streamlit dashboard) still pending — pick those up next.

**Status (2026-06-18):** Slice 2 (SPC + anomaly) **complete**. `analytics/spc.py::individuals_chart` (Shewhart XmR chart, Wheeler rule_1/rule_4 default + rule_2/rule_3 opt-in, MR̄/1.128 sigma, per-(board,refdes) `measured_value`) and `analytics/anomaly.py::z_score_anomalies` (per-group failure-rate, leave-one-out baseline, severity-first) shipped as pure library functions. 57 new tests, 292 passing / 1 xfailed, `spc.py`+`anomaly.py` 100% coverage, repo 97%. Notebook Query 7 + Query 8 added. X-bar/R + Isolation Forest deferred at owner Decision Gate (no new dep, no schema change). Branch: `feature/phase2-slice2-spc-anomaly`. **Remaining Phase 2: slice 3 — Streamlit dashboard** (`ui/`, pages, Plotly, filters, caching).

---

## Phase 3 — RAG Co-Pilot Layer (Week 7-8)

**Goal:** Natural-language Q&A grounded in the data.

### Deliverables
- [x] `src/flying_probe_copilot/rag/` module (slice 1, 2026-06-20)
- [x] Failure-mode knowledge base in `docs/knowledge-base/` (markdown scaffold seeded with 8 synthetic docs; owner expands — slice 1, 2026-06-20)
- [x] Hybrid retrieval: ChromaDB (vector) + rank_bm25 (lexical) + reciprocal rank fusion (slice 1, 2026-06-20)
- [ ] LLM integration via Gemini API (slice 2)
- [ ] Structured-output prompt template that forces citation of retrieved evidence (slice 2)
- [ ] Chat interface integrated into Streamlit dashboard (slice 3)
- [ ] Tests: 10 representative questions with expected citation patterns (slice 3)
- [ ] Anti-hallucination test: questions with no supporting data must be refused (slice 2/3)

### Exit criteria
Co-pilot correctly answers ≥8 of 10 representative root-cause questions with citations. Refuses ungrounded questions.

**Status (2026-06-20):** Phase 3 **slice 1 complete** — offline hybrid-retrieval core shipped.
`rag/` (6 files: models, kb_loader, lexical_index, vector_index, retriever, __init__) does
ChromaDB-cosine vector + rank_bm25 lexical + reciprocal-rank fusion over a seeded
`docs/knowledge-base/` (README + index + 8 synthetic failure-mode docs). 80 new tests,
**454 passing / 1 xfailed / 97% coverage** (rag package 99–100% per file). Fully offline +
deterministic (injected fake embedder; real all-MiniLM-L6-v2 env-gated). Full 12-step loop ran
clean; Step 5 red-team caught 3 BLOCKERs (chroma L2-vs-cosine, RRF non-universal both>one claim,
BM25 ≤0-score match test) resolved in Plan Revision 1 before Execute. Branch:
`feature/phase3-slice1-rag-retrieval`. **Remaining Phase 3: slice 2 (Gemini LLM + citation prompt +
anti-hallucination — needs owner's Gemini API key) and slice 3 (chat UI + 10-Q eval).**

---

## Phase 4 — Polish & Portfolio (Week 9-10)

**Goal:** Hireable artifact.

### Deliverables
- [ ] README polished with architecture diagram (Mermaid), screenshots, demo gif
- [ ] Case-study writeup on portfolio site (hrushiekeshreddykanjula.com)
- [ ] Blog post: "Building an AI co-pilot for PCBA test analytics"
- [ ] `docs/DEMO.md` walkthrough script
- [ ] GitHub Actions workflow: lint + tests on PR
- [ ] Repo flipped to public after guardrails checklist passes
- [ ] LinkedIn post with screenshots
- [ ] Resume bullet drafted (see SKILLS.md for template)

### Exit criteria
A recruiter can land on the repo, watch the demo gif, read the case study, and understand the project in <5 minutes.

---

## Decision points / parking lot

(Decisions to revisit at phase boundaries. Don't act on them mid-phase.)

- After Phase 1a: do we need a second log format (Takaya) for variety?
- After Phase 2: do we add real-time ingest (file watcher)?
- After Phase 3: do we switch to Claude API if Gemini quality disappoints?
- After Phase 4: do we open-source the generator separately as its own package?

---

## Status log (update at each phase boundary)

- 2026-06-13 — Phase 0 started.
- 2026-06-13 — Phase 0: 8/9 deliverables done. Keysight manuals not yet downloaded. Log format will be researched from public sources in Phase 1a Step 2 (Explore).
- 2026-06-13 — Phase 1a: 8/9 deliverables done in a single session. Synthetic HP3070 / Keysight i3070 ICT log generator complete. Format target revised mid-session to real Keysight Log Record Format (authoritative reference found via Virinco public mirror). 81 tests passing, 94% coverage, 1000 panels in ~1 s. README deliverable deferred to a follow-up doc session.
- 2026-06-14 — Phase 1b: 6/7 deliverables done in a single Large-tier session. Parser module + DuckDB 9-table schema + ingest CLI + round-trip integrity tests + named yield-query test all green. 179 tests passing, 0 failing, 97% total coverage. Notebook deliverable deferred. 10-step loop completed end-to-end with Step 4 red-team Revision 1 catching 2 BLOCKERs + 5 WARNINGs that would have produced wrong-data round-trips.
- 2026-06-20 — Phase 3 started, slice 1 (offline RAG retrieval core + KB scaffold) complete. ChromaDB-cosine + rank_bm25 + RRF over a seeded 8-doc failure-mode KB. 80 new tests, 454 passing / 1 xfailed / 97% coverage. Red-team caught 3 BLOCKERs (cosine space, RRF non-universal claim, BM25 token-overlap match) resolved pre-Execute. Slice 2 (Gemini LLM + citations) needs owner's API key; slice 3 (chat UI + 10-Q eval) follows.
- 2026-06-16 — Phase 2 started, slice 1 (analytics foundation) complete. `yield_over_time` + `failure_pareto` shipped in a Medium-tier session. 39 new tests, 224 total passing, 0 failing. Analytics package coverage 96-100% per file. Per-row `placeholder_fields` marker keeps BUG-007-affected fields visible. 12-step session-workflow loop ran end-to-end; Step 5 adversarial review caught 7 BLOCKERs around notebook-canonical-SQL divergences that Plan Revision 1 resolved before Execute. Six v1 contract decisions documented in DECISION_LOG. Slice 2 (SPC + anomaly) and slice 3 (Streamlit dashboard) deferred to follow-up sessions.
