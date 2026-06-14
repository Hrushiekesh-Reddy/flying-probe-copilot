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
- [ ] `src/flying_probe_copilot/parser/` module
- [ ] DuckDB schema: dimension tables (boards, panels, operators, components, tests) + fact tables (test_runs, measurements, failures)
- [ ] Parser ingests generator output reliably
- [ ] CLI: `uv run parser --input=data/synthetic/ --db=data/db/flying-probe.duckdb`
- [ ] Sample SQL queries documented in `notebooks/01-queries.ipynb`
- [ ] Parser tests: round-trip integrity (generator → parser → DB → match)
- [ ] Error handling for malformed lines (log + skip, don't crash)

### Exit criteria
"Yield by board over last week" query returns correct result. Round-trip test passes for ≥99% of generator output.

---

## Phase 2 — Analytics & Dashboard (Week 5-6)

**Goal:** A working Streamlit dashboard over the data.

### Deliverables
- [ ] `src/flying_probe_copilot/analytics/` module
  - Yield-over-time function
  - Failure Pareto function
  - SPC chart helpers (X-bar, R, individual)
  - Anomaly detection (z-score baseline; Isolation Forest stretch)
- [ ] `src/flying_probe_copilot/ui/` Streamlit app
- [ ] Pages: Overview, Yield, Failure Pareto, SPC, Anomalies
- [ ] Plotly charts with drill-down
- [ ] Filter controls: date range, board, operator, line, shift
- [ ] Caching with `st.cache_data` for query results

### Exit criteria
Dashboard runs locally with `uv run streamlit run src/.../ui/app.py`. Loads in <2s on 100k records.

---

## Phase 3 — RAG Co-Pilot Layer (Week 7-8)

**Goal:** Natural-language Q&A grounded in the data.

### Deliverables
- [ ] `src/flying_probe_copilot/rag/` module
- [ ] Failure-mode knowledge base in `docs/knowledge-base/` (markdown, owner-authored)
- [ ] Hybrid retrieval: ChromaDB (vector) + rank_bm25 (lexical) + reciprocal rank fusion
- [ ] LLM integration via Gemini API
- [ ] Structured-output prompt template that forces citation of retrieved evidence
- [ ] Chat interface integrated into Streamlit dashboard
- [ ] Tests: 10 representative questions with expected citation patterns
- [ ] Anti-hallucination test: questions with no supporting data must be refused

### Exit criteria
Co-pilot correctly answers ≥8 of 10 representative root-cause questions with citations. Refuses ungrounded questions.

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
