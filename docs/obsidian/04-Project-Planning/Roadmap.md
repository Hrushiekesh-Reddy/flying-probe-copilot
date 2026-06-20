# Product Roadmap

8-10 calendar weeks. Evenings + weekends. ~70-90 total hours.  
Full source of truth: `docs/ROADMAP.md`

---

## Phase 0 — Setup & Documentation ✅
**Completed**: 2026-06-13

- [x] Project decision locked (flagship flying-probe co-pilot)
- [x] GitHub repo created (private)
- [x] Full doc skeleton committed (README, CLAUDE.md, GUARDRAILS, SCOPE, ROADMAP, DECISIONS, REQUIREMENTS)
- [x] `.env.example` committed; `.env` gitignored
- [x] `pyproject.toml` initialized with `uv init`
- [x] Multi-IDE workflow configured (Claude Code + Cursor)
- [ ] Keysight i3070 manuals downloaded locally *(off-git owner task — still pending)*

---

## Phase 1a — Synthetic HP3070 Log Generator ✅
**Completed**: 2026-06-13

- [x] `src/flying_probe_copilot/generator/` module (9 source files)
- [x] Pydantic v2 data models (Board, Panel, TestRun, Test, Measurement)
- [x] 3 board profiles: small / medium / large
- [x] Fault injection: opens, shorts, OOT analog, missing components, digital failures
- [x] 4 fault profiles: random / drift / cluster / process-change
- [x] Output formats: `.log` (real Keysight format), `.csv` (flat), `.json` (structured)
- [x] CLI: `uv run generator --board-profile=medium --count=100 --out=data/synthetic/`
- [x] 81 tests, 94% coverage — 1000 panels in ~1 second

---

## Phase 1b — Parser & DuckDB Schema ✅
**Completed**: 2026-06-14

- [x] `src/flying_probe_copilot/parser/` (log_parser, ingest, cli)
- [x] `src/flying_probe_copilot/db/schema.py` (9 tables, idempotent CREATE)
- [x] Round-trip integrity test (generator → parser → DuckDB → query)
- [x] CLI: `uv run parser --input=<dir>/ --db=data/db/flying-probe.duckdb`
- [x] `notebooks/01-queries.ipynb` — canonical queries + 5 analytics queries
- [x] 179 tests, 97% coverage

---

## Phase 2 — Analytics & Dashboard 🟡
**Started**: 2026-06-16 | **Remaining**: Slice 3

### Slice 1 ✅ (2026-06-16)
- [x] `yield_over_time(con, *, window_days=7, group_by="board", as_of=None)`
- [x] `failure_pareto(con, *, window_days=7, by="record_type", top_n=10, as_of=None)`

### Slice 2 ✅ (2026-06-18)
- [x] `individuals_chart` — Shewhart XmR (Wheeler rule_1/rule_4 default)
- [x] `z_score_anomalies` — per-group failure-rate, leave-one-out baseline

### Slice 3 — Streamlit Dashboard 🔵 NEXT
- [ ] `src/flying_probe_copilot/ui/` module
- [ ] Yield-over-time Plotly chart + board filter
- [ ] Failure Pareto Plotly bar chart
- [ ] SPC individuals chart with control limits
- [ ] Anomaly flag table
- [ ] Date range and board filters
- [ ] Exit criterion: dashboard renders all 4 analytics on synthetic data

---

## Phase 3 — RAG Co-Pilot Layer ⬜
**Target**: Weeks 7-8

- [ ] `src/flying_probe_copilot/rag/` module
- [ ] Failure-mode knowledge base in `docs/knowledge-base/`
- [ ] Hybrid retrieval: ChromaDB + rank_bm25 + RRF
- [ ] Gemini API integration with structured-output prompt
- [ ] Chat interface in Streamlit
- [ ] 10 representative Q&A tests + anti-hallucination test
- [ ] Exit criterion: ≥8/10 root-cause questions answered correctly with citations

---

## Phase 4 — Polish & Portfolio ⬜
**Target**: Weeks 9-10

- [ ] README with Mermaid architecture diagram + screenshots + demo gif
- [ ] Case-study writeup on portfolio site (hrushiekeshreddykanjula.com)
- [ ] Blog post: "Building an AI co-pilot for PCBA test analytics"
- [ ] GitHub Actions CI: lint + tests on PR
- [ ] Repo flipped to public (after guardrails checklist passes)
- [ ] LinkedIn post with screenshots
- [ ] Resume bullet drafted

---

## Decision Points (Phase Boundaries)

- **After Phase 2**: Add real-time ingest (file watcher)?
- **After Phase 3**: Swap to Claude API if Gemini quality disappoints?
- **After Phase 4**: Open-source the generator separately?
- **After Phase 1a**: Add Takaya format for variety? *(Deferred to Phase 5)*

---

**Tags:** #roadmap #planning #strategy
