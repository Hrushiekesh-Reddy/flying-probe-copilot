# Project Dashboard

Real-time overview of project status, timelines, and priorities.

## Current Phase: Phase 2 — Analytics & Dashboard

**Phase Goal**: Working Streamlit dashboard over DuckDB data  
**Phase Status**: Slice 3 of 3 — Streamlit dashboard (NEXT)  
**Target Completion**: 8-10 weeks total from start (evenings + weekends)

### Phase 2 Task Breakdown

| Slice | Deliverable | Status |
|-------|-------------|--------|
| Slice 1 | `yield_over_time` + `failure_pareto` | ✅ 2026-06-16 |
| Slice 2 | `individuals_chart` (SPC/XmR) + `z_score_anomalies` | ✅ 2026-06-18 |
| Slice 3 | Streamlit dashboard (`ui/`) with Plotly charts + filters | 🔵 NEXT |

### Next Steps (Slice 3)
- [ ] Create `src/flying_probe_copilot/ui/` module
- [ ] Yield-over-time page with Plotly time series
- [ ] Failure Pareto chart (interactive bar chart)
- [ ] SPC individuals chart (with control limit lines)
- [ ] Anomaly flag table
- [ ] Board/date range filters
- [ ] Wire to real DuckDB file via Streamlit `@st.cache_data`

---

## All Phases Overview

| Phase | Goal | Status | Coverage |
|-------|------|--------|----------|
| Phase 0 | Setup & docs | ✅ Complete | — |
| Phase 1a | Synthetic HP3070 generator | ✅ Complete | 94% |
| Phase 1b | Parser + DuckDB schema | ✅ Complete | 97% |
| Phase 2 | Analytics + Streamlit dashboard | 🟡 Slice 3 next | 97% |
| Phase 3 | Hybrid RAG co-pilot | ⬜ Not started | — |
| Phase 4 | Polish + portfolio launch | ⬜ Not started | — |

---

## Key Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Test Coverage | ≥97% | 97% | 🟢 |
| Tests Passing | All green | 292 / 1 xfail | 🟢 |
| Phase 2 Slices | 3 | 2 done | 🟡 |
| Phases Complete | 4 | 3 (0, 1a, 1b) | 🟡 |
| Modules Shipped | 5 (gen, parser, db, analytics, ui) | 4 | 🟡 |
| RAG Q&A Correct | ≥8/10 | Not started | 🔵 |

---

## Open Bugs

| Bug | Description | Status |
|-----|-------------|--------|
| BUG-010 | TestJetRecord pytest collection warning | 🟡 Open |
| BUG-011 | Pre-existing flaky parser test | 🟡 Open |

*(Closed: BUG-001, BUG-002, BUG-004, BUG-007, BUG-009)*

---

## Open Questions

- [ ] Whether to include digital test patterns or only analog/shorts in v1
- [ ] Whether to ship an "import real logs" tool (Phase 4 consideration)
- [ ] After Phase 2: do we add real-time ingest (file watcher)?
- [ ] After Phase 3: swap to Claude API if Gemini quality disappoints?

---

## Related Notes

- [[Roadmap|Product Roadmap]] — Full phased plan with deliverables
- [[02-Features/Features-Index|Features Index]] — Feature-level detail
- [[05-Learning/Learning-Log|Learning Log]] — Session notes and lessons

---

**Tags:** #project-planning #dashboard #status
