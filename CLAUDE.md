# CLAUDE.md — Memory Bridge for Flying-Probe Co-Pilot

> Read this file at the start of every Claude Code session. It captures persistent project context so sessions stay focused and the context window stays clean.

## Project identity

- **Name:** Flying-Probe / ICT Test-Log Intelligence Co-Pilot
- **One-liner:** Parses PCBA flying-probe / ICT test logs into a SQL database, runs yield + anomaly analytics, and answers natural-language root-cause questions via hybrid RAG.
- **Owner:** Hrushiekesh Reddy Kanjula (Manufacturing Engineer, ~4 yrs PCBA, Dallas TX)
- **Why it exists:** Flagship AI portfolio project to land a Manufacturing/Process Engineer with AI role.
- **Status:** Phase 1a — Synthetic HP3070 Log Generator

## Hard guardrails (NEVER violate)

1. **No real customer log data ever enters this repo or any home machine.** Real-data validation happens only on the work network. See `docs/GUARDRAILS.md`.
2. **No IPC-A-610 / J-STD-001 verbatim text in the repo.** Copyrighted. Use summaries and citations only.
3. **No proprietary Keysight documentation copied wholesale.** Reference public manual sections by name; don't redistribute.
4. **All committed data is synthetic.** The synthetic generator is the single source of test data for the repo.
5. **API keys never committed.** Use `.env` + `python-dotenv`. `.env` is gitignored.

## Phase-based workflow

This project ships in 4 phases. Each phase has its own focus, deliverable, and ends with a written status update in `docs/ROADMAP.md`.

| Phase | Goal | Status |
|---|---|---|
| 0 — Setup | Docs, scope, guardrails, repo skeleton | ✅ Complete |
| 1a — Synthetic data | HP3070-style log generator | 🟡 In progress |
| 1b — Parser & DB | Log parser + DuckDB schema | ⬜ |
| 2 — Analytics | SPC, Pareto, anomaly detection, dashboard v1 | ⬜ |
| 3 — RAG co-pilot | Hybrid RAG over results + failure-mode KB | ⬜ |
| 4 — Polish | Tests, docs, portfolio writeup, demo gif | ⬜ |

**Rule: One phase per session.** If you're in Phase 1a, do not start writing parser code. Park ideas in `docs/DECISIONS.md` or a phase note.

## Tech stack (locked)

- Python 3.11+
- `uv` for dependency management
- DuckDB for SQL spine
- ChromaDB + sentence-transformers + rank-bm25 for hybrid RAG
- Google Gemini API (primary LLM); Claude API (backup)
- Streamlit + Plotly for UI
- pytest for tests

## Workflow conventions

- **Multi-IDE:** Claude Code = explore/plan/debug/doc. Cursor = primary builder. Both read this file.
- **Subagents:** For exploration spanning >3 queries, spawn an Explore subagent. For non-trivial implementation, spawn a Plan subagent first. Default to pipeline over parallel.
- **Adversarial verification:** Before acting on any finding, spawn 2-3 skeptic subagents to refute it.
- **Pre-fanout check:** Always read this file + the relevant phase's spec/doc before any multi-agent work.
- **Trust but verify:** Subagent summaries describe intent, not always what landed. Spot-check.
- **Use Context7 MCP** for live documentation lookup of DuckDB, Streamlit, ChromaDB, sentence-transformers, Gemini SDK.

## Reference paths

- Local repo: `E:\flying-probe-copilot\` (to be created)
- Personal Assistant home base: `E:\Personal Assistant\`
- Related projects: `E:\Portfolio\`, `E:\my-assembly-hub\`
- Cross-project findings → surface via `spawn_task` chips, don't silently scope-creep.

## Don't-do list (project-specific)

- ❌ Don't train a custom model. Use pre-trained embeddings + LLM API.
- ❌ Don't build a generic test-log parser. Target HP3070 / Keysight i3070 format first; expand later.
- ❌ Don't add MCPs beyond Context7 in Phase 0-2. Reassess in Phase 3.
- ❌ Don't write production-grade error handling in Phase 1. Get the happy path working first.
- ❌ Don't optimize prematurely. DuckDB on synthetic data is fast enough for any v1 query.
- ❌ Don't add a real frontend (React/Next). Streamlit only.
- ❌ Don't deploy to cloud in v1. Local + GitHub repo is the deliverable.

## Definition of "done" for each phase

- Phase 0: Every doc in `/docs` exists and is reviewed. Repo initialized on GitHub.
- Phase 1a: Generator produces ≥3 realistic HP3070-style log variants from configurable parameters; unit tests pass.
- Phase 1b: Parser ingests all generator output into DuckDB; query "yield by board over last week" returns correct results.
- Phase 2: Streamlit dashboard shows yield-over-time, failure Pareto, and anomaly flags on synthetic data.
- Phase 3: Co-pilot answers ≥10 representative root-cause questions correctly with citations to retrieved rows.
- Phase 4: Public GitHub repo with README, demo gif, case-study writeup on portfolio site.

## Open questions (update as we go)

- [ ] Exact field set for HP3070 log format — refine in Phase 1a spec
- [ ] Whether to include digital test patterns or only analog/shorts in v1
- [ ] Whether to ship an "import real logs" tool alongside the synthetic generator (Phase 4)

## Session log

Add a line each session: `YYYY-MM-DD — <phase> — <what was done>`

- 2026-06-13 — Phase 0 — Repo on GitHub; full .claude/ governance layer (10 skills incl. skill-sergeant, 3 hooks, rules); 10-step multi-agent loop finalized; hrk-agent-starter portable kit built and pushed; branching confirmed (feature/* → dev → main). Remaining: pyproject.toml + Keysight manuals.
- 2026-06-13 — Phase 0 complete — pyproject.toml committed (feature/pyproject-init → dev → main); Keysight manuals confirmed downloaded locally. All 9/9 Phase 0 deliverables done. Phase 1a begins next session.
