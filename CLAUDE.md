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
| 1a — Synthetic data | HP3070-style log generator | ✅ Complete (8/9 — README deferred) |
| 1b — Parser & DB | Log parser + DuckDB schema | ✅ Complete (notebook deferred) |
| 2 — Analytics | SPC, Pareto, anomaly detection, dashboard v1 | 🟡 Up next |
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
- 2026-06-13 — Phase 0: 8/9 done — pyproject.toml committed. Keysight manuals NOT downloaded (off-git owner task, still pending). HP3070 log format will be researched from public sources in Phase 1a Explore step instead.
- 2026-06-13 — Phase 1a — synthetic HP3070 generator complete in single session. Format target revised mid-session to real Keysight Log Record Format (authoritative reference via Virinco public mirror). 9 source modules + 11 test files + conftest = 81 tests, 94% coverage, ~1 s for 1000 panels. 10-step workflow loop (brief → 2-explore → plan → red-team → execute → verify → triple-check → docs/commit) ran clean. Parent Step 7 corrected 2 contract drifts found by Step 6. uv installed standalone. BUG-001 logged for cache-research subagent process improvement. Next: Phase 1b parser + DuckDB schema.
- 2026-06-13 — Phase 1a prep — broadened `data/synthetic/` `.gitignore` to a samples-only allow-list so bulk generator outputs (20–50 MB results.csv/json from 1k-panel runs) can't accidentally be committed; added `data/synthetic/samples/.gitkeep`. Branch: feature/gitignore-data-synthetic-v2. (`uv.lock` un-ignore is a separate concern, already landed on branch fix/commit-uv-lock.)
- 2026-06-14 — Phase 1a meta — added dedicated `exec` sub-agent (`.claude/agents/exec.md`, sonnet, tool-restricted) + 3 workflow templates (`sub-agent-brief.md`, `tiering.md`, `prompt-caching.md`). Formalizes tier-based step selection (Trivial / Small / Medium / Large) and context-cache brief reuse to cut ~30–50% input tokens on Medium/Large loops. No source code touched. Branch: feature/exec-agent-and-templates.
- 2026-06-14 — Phase 1a fix — wired `correlation_multiplier` into `generate_blocks`. Bugbot caught (PR #3 review, medium severity) that the refdes-numerical clustering heuristic existed in `faults.py` but was never invoked from the CLI output path — `_pick_failing_component` marked exactly one component per panel. Added `_pick_correlated_failures` helper with multiplier-gated Bernoulli draws (`BASELINE_SECONDARY_RATE=0.3`, applied only when multiplier > 1.0) + 3 new tests (within-panel, aggregate Pareto, cross-family). All 97 tests pass. Branch: feature/wire-fault-correlation.
- 2026-06-14 — Phase 1a test fix — closed the coverage gap Bugbot flagged in PR #3 (comment 3409766434). `tests/test_generator/test_lexical_compliance.py` built panels with a hardcoded 4-block fixture (the pre-BUG-002 shape), so after the BUG-002 fix it never exercised the real CLI block-generation path (`generate_blocks`, 51 / 201 / 801 blocks per panel). Rewrote the test to mirror `cli._build_batch_log` exactly, added a `large`-profile case + a regression guard requiring ≥`component_count + 1` blocks per board. Lexical assertion now spans ~2,376 emitted blocks (was ~152). 98/98 tests pass, 94% coverage held. Branch: feature/lexical-test-via-generate-blocks.
- 2026-06-14 — Phase 1b — Parser & DuckDB schema complete in single Large-tier session (full 10-step loop). New: `src/flying_probe_copilot/parser/` (4 files: `__init__.py`, `log_parser.py`, `ingest.py`, `cli.py`) + `src/flying_probe_copilot/db/schema.py` (9 tables: 5 dim + runs + 3 fact, idempotent `CREATE TABLE IF NOT EXISTS`) + 7 new test modules under `tests/test_parser/`. Single-line `pyproject.toml` edit re-added `parser` script. **179 tests passing** (98 generator baseline + 81 parser), 0 failing, **97% total coverage** (parser 97%, db 100%, generator baseline preserved). Round-trip integrity test (generator → parser → DuckDB → query) confirms count + timestamp equality at byte/IEEE-754 precision. "Yield by board over last week" query passes the 2-week × 2-profile fixture exit-criterion test. Loop ran clean: brief → explore → plan (v1 + Revision 1 resolving 2 BLOCKERs + 5 WARNINGs + 6 MINORs from Step 4 red-team) → exec → independent verify (PASS) → triple-check (CLEAN). Notebook deliverable (`notebooks/01-queries.ipynb`) and per-panel operator-ID recovery deferred to follow-up sessions (chips at Step 8). Branch: feature/phase1b-parser.
- 2026-06-14 — Phase 1a fix — closed the shift-snap overnight bug Bugbot flagged in PR #3 (comment 3409766436, low severity). `generate_panel_schedule` drew a shift letter uniformly per panel and snapped to the raw draw's calendar day; the shift-C wrap correction was a literal `pass`, so a raw_ts at 02:00 randomly assigned to shift C jumped to the same day's 22:00–05:59 window. Adopted option A: derive `shift` from `ts.hour`, snap inside the window-start that physically contains the raw draw (previous-day 22:00 for early-morning shift C). New helpers `_shift_for_hour` + `_shift_window_start`; old `_shift_start_for` deleted as dead code. Logged BUG-004. 3 new tests (RED-first targeted regression + 2 contract checks). 101/101 tests pass, 95% total coverage. Branch: feature/fix-shift-snap-overnight.
- 2026-06-14 — Phase 1b — Notebook deliverable closed (`notebooks/01-queries.ipynb`, nbformat 4.5, 17 cells = 9 markdown + 8 code) — canonical yield-by-board-last-7-days query (CTE anchored to `MAX(panels.scheduled_ts)` for deterministic replay) + 5 analytics queries: failure Pareto by record_type, per-shift yield, per-operator yield, top-10 failing refdes, btest_status distribution. Sample DB `data/db/sample.duckdb` ingested from a 20-panel small-profile run (gitignored via `*.duckdb`). Every code cell smoke-tested in-process against the live DB. ROADMAP Phase 1b now 7/7. Tier: Small (doc-only). Branch: feature/phase1b-notebook. Side note: mid-session `cd notebooks/` exposed a hook-config sharp edge — `.claude/settings.json` registers `python .claude/hooks/block_dangerous_git.py` with a relative path, which hard-blocks every shell command when the cwd drifts into a subdir. Surfaced as a `spawn_task` chip for a separate owner-approved settings.json edit.
- 2026-06-14 — Governance fix — flipped all three hook commands in `.claude/settings.json` from relative paths to `python ${CLAUDE_PROJECT_DIR}/.claude/hooks/<file>.py` (Option A — portable, owner-approved over hard-coded path Option B). Same fix stamped upstream into `E:\hrk-agent-starter\.claude\settings.json` so every future stamped project gets it. Smoke-tested in-session: `cd notebooks && pwd && cd ..` succeeded immediately after the edit, proving the harness substitutes `${CLAUDE_PROJECT_DIR}` on this Windows machine. DECISION_LOG entry documents A-vs-B rationale, what was rejected, and revisit condition. Branch: feature/abs-hook-paths. Tier: Small (config + docs only).
- 2026-06-16 — Phase 2 first task — per-panel operator-id repair (Path A) landed on `feature/per-panel-operator`. `@BTEST` extended with mandatory `operator_id` at field 12; wired end-to-end through models → CLI → renderer → grammar → parser → ingest; `test_runs.operator_id` flipped to `VARCHAR NOT NULL`. 11 new tests, 196 passing total, 0 failing, 97% coverage (schema 100%, parser 97%, generator ≥90%). BUG-009 resolved; BUG-007 operator half closed (shift + line_id remain open); BUG-010 logged for TestJetRecord pytest collection warning. DECISION_LOG 2026-06-14 nullable-operator entry footnoted "Resolved 2026-06-16 — Path A landed". Notebook Query 4 caveat closed. Tier: Medium. 12-step workflow loop ran clean — plan was authored under prior 10-step workflow and migrated cleanly (red-team Revision 1 = new Step 5 Verify Plan; embedded per-step RED test cases covered new Step 4 Test-Case Plan).
- 2026-06-17 — Phase 2 — BUG-007 fully closed in a fast follow-up commit on `feature/per-panel-operator`. Path A applied to the remaining two fields: `@BTEST` gains mandatory `shift: Literal["A","B","C"]` at field 13 and `line_id: str = Field(min_length=1)` at field 14; wired through models → CLI → renderer → grammar → parser; `_make_board_log` reads `btest.shift` / `btest.line_id` instead of the `"A"` / `"LINE-A"` placeholder literals. Schema was already `NOT NULL` for both columns so no schema flip — the bug was silent-wrong-data, not nullability. 4 new tests (3 model-layer guards + multi-shift/multi-line end-to-end ingest); 200 passing total, 0 failing, 97% coverage. Bulk-patch of 12 `BoardTestRecord(...)` blocks + 30 hardcoded `@BTEST|` literals. Notebook Query 3 caveat closed. Per-shift + per-operator + per-line analytics now all sit on real per-panel data. Tier: Small (mechanical mirror of operator_id pattern, no separate brief/plan — TDD discipline preserved). PR `feature/per-panel-operator` → `dev` now closes both halves of BUG-007 in one PR.
