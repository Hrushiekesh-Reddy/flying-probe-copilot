# Case Study — Flying-Probe / ICT Test-Log Intelligence Co-Pilot

> A Python system that ingests PCBA flying-probe / ICT test logs, runs the standard yield / Pareto / SPC / anomaly analytics, and answers natural-language root-cause questions with strictly-grounded citations — built over 8 weeks of evenings and weekends as a Manufacturing Engineer's portfolio project for landing an AI-augmented role in EMS.

**Author:** Hrushiekesh Reddy Kanjula · Manufacturing Engineer, ~4 years PCBA · Dallas, TX
**Repo:** [flying-probe-copilot](https://github.com/Hrushiekesh-Reddy/flying-probe-copilot) · **Status:** Phase 3 complete; Phase 4 polish in progress
**Headline metrics:** 519 passing tests · 97% line coverage · 10/10 live RAG eval in 37.13s · ~1 s to synthesize 1,000 panels

---

## 1. The problem

Every printed-circuit-board-assembly (PCBA) line that runs flying-probe or in-circuit testers (ICT) emits structured test logs — record-by-record measurements of analog tolerances, opens / shorts checks, boundary-scan steps, and final board verdicts. On a busy line that's millions of records per shift. The data is there. The analytics layer is not.

Today, factories have two real choices: pay for a commercial test-data-analytics suite (Nick's Software NS-HPDCA is the well-known one), or do it in Excel and rely on tribal knowledge. Most do the latter — and most root-cause investigations come down to a senior engineer remembering "we saw something like this on lot 2024-W18, check the solder paste viscosity." That works until the senior engineer takes a week off, and it doesn't scale to a multi-line operation.

The technical gaps that matter:

- **No queryable spine.** Logs sit in flat files; correlating a specific shift's yield drop against a specific component family takes hours.
- **No statistical-process-control automation.** Run-of-8, beyond-3-σ, and zone rules are well-known but rarely automated against PCBA test data.
- **No anomaly detection.** Per-component failure-rate outliers ("Q15 is suddenly failing 4× as often as the line average") fall through.
- **No grounded root-cause Q&A.** "Why are we seeing tombstoning on these 0402s?" is a Slack message to a senior engineer — when it should be a query that returns a citation-backed answer in seconds.

This project closes those four gaps for the open-source, local-first, single-engineer case.

## 2. Scope decisions

Building this as a 1-person, 8-week portfolio project means saying no to a lot of plausible features. The decisions that did the most to keep the project tractable:

- **Synthetic data only, in this repo.** Real customer logs are confidential. The synthetic generator (Phase 1a) produces Keysight Log Record Format logs — the public format spec — with three board profiles, configurable fault-correlation, and shift-physics-aware timestamps. Every test and every demo uses synthetic data. Real-data validation happens only on the work network, and never enters this repo.
- **Local-first, no cloud.** DuckDB as the SQL spine, ChromaDB for vectors, file-based everything. The whole stack runs against a single `.duckdb` file on a laptop. No service to deploy, no auth, no cost-per-query.
- **Streamlit over a real frontend.** The portfolio audience needs to see the analytics; they do not need React. Streamlit was the fastest path to a working 6-page dashboard.
- **Hybrid retrieval (BM25 + vector + Reciprocal Rank Fusion) over a vector-only approach.** PCBA failure modes have a lot of specific component names and refdes patterns; lexical retrieval catches those reliably. Vector retrieval catches semantic phrasing. RRF combines both without tuning a weighted score.
- **KB-grounded RAG only, not DuckDB-grounded.** The co-pilot grounds on an 8-document failure-mode knowledge base — not on live SQL query results. SQL-grounded RAG ("answer this from the test_runs table") would have been a much bigger surface; the KB approach keeps the eval set tight and the anti-hallucination contract enforceable.
- **No IPC-A-610 / J-STD-001 verbatim text in this repo.** The standards are copyrighted. The KB cites them by section number only; the verbatim text lives in the standards themselves.

Every one of those decisions is logged in [docs/DECISIONS.md](DECISIONS.md) with the date it was made and why.

## 3. Architecture

The system splits cleanly into two independent pipelines that meet in the dashboard.

**The analytics pipeline:**

1. The synthetic generator emits HP3070-style logs to disk under `data/synthetic/run_<timestamp>/`.
2. The parser walks each run directory, validates against the Keysight record-format grammar, and ingests into a 9-table DuckDB schema (5 dimension tables, 1 `runs` table, 3 fact tables).
3. The analytics library is four pure Python functions over a DuckDB connection: `yield_over_time`, `failure_pareto`, `individuals_chart` (Wheeler XmR with optional zone rules), and `z_score_anomalies` (leave-one-out per-group failure-rate, severity-first).
4. The Streamlit dashboard renders four pages over those four functions, plus an Overview page.

**The RAG pipeline:**

1. The knowledge base (`docs/knowledge-base/failure-modes/`) is 8 markdown documents covering the failure modes that matter on a flying-probe line: opens, shorts, cold solder joints, missing components, misorientation, tombstoning, out-of-tolerance analog, insufficient solder. Each cites the relevant IPC / J-STD section without quoting it.
2. Documents are chunked by heading (fence-aware), embedded with `all-MiniLM-L6-v2`, indexed in ChromaDB (cosine HNSW) and rank-bm25.
3. The hybrid retriever takes a question, runs both indices, fuses results with Reciprocal Rank Fusion (k=60), and returns the top chunks.
4. The `answer()` function builds a strict JSON-mode prompt for Gemini, validates the response against a four-rule anti-hallucination contract, and either returns a cited answer or a refusal.
5. The dashboard's Co-Pilot page calls `answer()` and renders citations in an expandable panel.

The Streamlit dashboard is the single user-facing surface. Everything else is a library function.

## 4. Three engineering stories

These three bugs (one from each major phase) are the ones I learned the most from. Each surfaced a class of error I now actively look for.

### 4a. BUG-004 — shift-snap overnight (Phase 1a)

The synthetic generator schedules panel arrivals across three shifts. Shift C runs 22:00 to 05:59, which means a `raw_ts` of 02:00 on March 5 belongs in shift C's window that **starts** at 22:00 on March 4. The original code drew a shift letter uniformly per panel and then "snapped" the timestamp into that shift's window — but the shift-C wrap correction was a literal `pass`. So a 02:00 raw draw randomly assigned to shift C would silently jump to 22:00 on the same day's window.

The fix wasn't to patch the wrap correction — it was to derive shift from physics. The new `_shift_for_hour(hour)` looks up which shift's window the raw hour falls into; `_shift_window_start(ts, shift)` snaps to the *correct* window-start (previous day's 22:00 for early-morning shift C). That made the broken `pass` unreachable: shift assignment now comes from time-of-day, not random draw, so the snap can only land in a window the timestamp already physically belongs to.

The class of bug: any time you have two correlated parameters (shift letter + timestamp) and one is being drawn independently from the other, you have to think hard about the "snap" step. The right pattern is to derive one from the other rather than draw both and reconcile. SPC trend analysis on a synthetic dataset with the original bug would have showed completely fictitious shift-vs-shift yield deltas. Logged as BUG-004 (P2 — RESOLVED 2026-06-14); the [BUG_LOG entry](logs/BUG_LOG.md) has the full diff.

### 4b. BUG-013 — Gemini model retirement (Phase 3 exit)

The Phase 3 exit criterion was a live ≥8/10 evaluation against the real Gemini API on a frozen 10-question dataset. First attempt: the test ran for 2 minutes 31 seconds and failed with `google.api_core.exceptions.NotFound: 404 This model models/gemini-2.0-flash is no longer available`. Google had retired the model — the entire 2:31 wall-clock was the gRPC client's 600-second retry deadline timing out, not real API work.

The fix was three lines (`DEFAULT_GEMINI_MODEL` constant + a test-side string for accuracy + the `.env.example` doc). The model id bumped to `gemini-3.5-flash`. The re-run passed 10/10 in 37.13 seconds — a 4× speedup over the failing run, all of it explained by not retrying a dead endpoint.

The class of bug: **vendor model IDs are versioned external state, not constants in your code.** A "constant" in `src/.../llm.py` is a contract with a remote API that can be revoked unilaterally. The lesson I took: any external model ID should be paired with a fast-failing health check, and the SDK should be the current one. The follow-up — migrating from the deprecated `google-generativeai` SDK to the successor `google-genai` — was queued at the time and landed the same day on a separate branch ([PR #30](https://github.com/Hrushiekesh-Reddy/flying-probe-copilot/pull/30)); the live ≥8/10 eval re-ran green on the new SDK without changing the model id. Logged as BUG-013 (P0 — RESOLVED 2026-06-21).

### 4c. BUG-011 — flaky test under parallel load (Phase 2)

A parser test passed in isolation and failed intermittently in the full suite — about a 60% flake rate. The symptom was either a partial-read `AssertionError` or a Windows `PermissionError [WinError 32]`.

The test helper `_render_to_text` wrote to a fixed path at the repo root: `tmp_test_render.log`. Two tests called the helper. Run them in isolation: no contention. Run them inside the full suite: Windows file-watchers + antivirus + parallel pytest workers all hit the same path, sometimes mid-write. Locks. Partial reads. Failure.

The fix was to thread pytest's `tmp_path` fixture through the helper so every test invocation got a unique OS-temp path. I verified the fix with a two-thread stress harness: shared-path version failed 484 out of 800 times; isolated version passed 800 out of 800.

The class of bug: **shared mutable state in tests is the same anti-pattern as shared mutable state in production — flakiness is its visible failure mode.** What made this one stick is that the test was *correct* in isolation. The bug only existed under concurrency. I now grep for repo-root file writes in test helpers as part of every review. Logged as BUG-011 (P2 — RESOLVED 2026-06-18).

## 5. RAG design choices

The Phase 3 co-pilot is the most opinionated part of the project. Three choices drove most of the design:

**Hybrid retrieval over vector-only.** Vector retrieval alone misses exact-match queries like "Q15" or "0402". rank-bm25 catches those. ChromaDB with `hnsw:space=cosine` catches semantic phrasing like "lifted leads" matching "open joints". Reciprocal Rank Fusion (k=60) combines both rankings without tuning a weighted blend.

**Strict anti-hallucination grounding.** The `answer()` function refuses unless all four conditions hold: (1) retrieval returned at least one hit, (2) the LLM emitted valid JSON, (3) the JSON's `sufficient` field is `true`, and (4) at least one cited `chunk_id` is in the retrieved set. Hallucinated citations are dropped; the LLM is never called when retrieval is empty. The refusal text is fixed, not LLM-generated. A failing retrieval costs zero tokens.

**Eval as code, not vibe.** The Phase 3 exit criterion was a frozen 10-question dataset (`tests/test_rag/eval_dataset.py`), one question per failure-mode document. Two layers of eval: an offline citation-pattern test that proves the pipeline wiring with a stubbed retriever + stubbed LLM, and an env-gated live test (`RAG_RUN_LLM_EVAL=1`) that calls the real Gemini API and asserts ≥8/10 questions cite the expected source document. Offline tests run in CI; the live test runs by hand when a real API key is available. The live test passed 10/10 in 37.13s on first green run with `gemini-3.5-flash`.

## 6. Results

| Metric | Value | Source |
|---|---|---|
| Passing tests | 519 | `uv run pytest -q` |
| Coverage | 97% | `pytest --cov` |
| Live RAG eval | 10/10 correct citations | `RAG_RUN_LLM_EVAL=1 pytest tests/test_rag/test_eval.py` |
| Live eval latency | 37.13s for 10 sequential calls | Phase 3 exit run, 2026-06-21 |
| Synthetic-data throughput | ~1 second per 1,000 panels | Phase 1a benchmark |
| Knowledge-base coverage | 8 failure-mode documents | `docs/knowledge-base/failure-modes/` |
| Dashboard pages | 6 (Overview / Yield / Pareto / SPC / Anomalies / Co-Pilot) | `src/flying_probe_copilot/ui/app.py` |
| Commits to date | 78 | `git log --oneline | wc -l` |
| Merged PRs | 29 | `gh pr list --state all` |
| Hard guardrail violations | 0 | code review + grep audits in every PR |

Every passing test runs offline (no network, no API key). The live RAG eval is the only test that touches a remote service, and it is opt-in by environment variable. There are no real customer logs in the repo; every dataset under `data/` is gitignored unless it lives under `data/synthetic/samples/`.

## 7. What I'd do differently

Three things, honestly:

**Migrate the Gemini SDK earlier.** BUG-013 surfaced because `google-generativeai` is the legacy SDK; the successor (`google-genai`) was already the recommended path when I wrote Phase 3 slice 2. I deferred the migration to stay focused. The model-retirement 404 forced the issue anyway. Lesson: when a vendor SDK is end-of-support at the time you adopt it, the cost of migrating later is rarely smaller than the cost of migrating now. The migration shipped the same day on a follow-up PR; the live ≥8/10 eval re-ran green on the new SDK without changing the model id.

**Capture screenshots from CI, not by hand.** Phase 4 slice 1 (this writeup) needed six dashboard screenshots. I captured them by launching Streamlit locally and snipping the browser. A CI-driven headless Playwright run would have been a one-time setup that paid off every time the dashboard's visual design changes. *[Resolved 2026-06-21 — slice 2 shipped automated capture; see [`scripts/capture_screenshots.py`](../scripts/capture_screenshots.py) and [`docs/plans/2026-06-21-phase4-slice2-brief.md`](plans/2026-06-21-phase4-slice2-brief.md).]*

**Bench real-data validation earlier in the schedule.** The hard guardrail is that real customer logs only get tested on the work network, not at home. That's correct. But it pushes the real-data validation moment all the way to the end. Earlier sketch-and-confirm cycles with synthetic-but-realistic edge cases would have caught (for example) the BUG-007 line that hardcoded `shift="A"` and `line_id="LINE-A"` in the parser at the start of Phase 2 rather than mid-phase.

---

*Built with [Claude Code](https://claude.com/claude-code) in the IDE loop, with every plan, decision, and bug logged under [docs/logs/](logs/).*
