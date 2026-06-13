# Decision Log — Flying-Probe Co-Pilot

Architectural, design, and process decisions in reverse-chronological order.
Every non-obvious choice gets an entry here: what was decided, why, what was rejected, and when to revisit.

---

## 2026-06-13 — Phase 1a: log format target = real Keysight Log Record Format (not simplified text report)

**Decision:** The synthetic generator emits files in the **real Keysight i3070 Log Record Format** — a record-oriented format with `{@PREFIX|field|...}` syntax, numeric status codes (no literal `"PASS"`/`"FAIL"` strings), scientific-notation floats (`+1.246700E+01`), CRLF Windows-1252 encoding by default, `@LIM2`/`@LIM3` limit subrecords following analog records, and full `@BTEST` status-code vocabulary. NOT the originally-drafted simplified human-readable text-report format.

**Why:** The spec drafted at Phase 0 described a sectioned text report (Header / Shorts / Analog / Digital / Summary) because the owner did not have Keysight manuals locally. Phase 1a Step 2 external-research subagent found the authoritative format chapter (Keysight "i3070 Log Record Format") publicly mirrored in the Virinco WATS-Client-Converter GitHub repo, with the format chapter as a PDF + an independent regex grammar in a C# parser (LGPL-3.0). With the real format in hand, generating the simplified format would have produced output that any manufacturing engineer who has used an i3070 would immediately recognize as fake — defeating the portfolio purpose. The real format raises renderer complexity from ~150 LOC to ~400 LOC, but every test, sample, and downstream phase becomes a precise simulation of real ICT output. The Phase 1b parser will be a defensible Python equivalent of the Virinco C# parser.

**Rejected:**
- **Simplified format as written** — easier and faster but loses portfolio credibility; Phase 1b parser would target a custom format with no real-world consumers.
- **Dual-format support** (real + simplified) — too much scope for v1; the simplified format has no consumer.

**Revisit:** After Phase 1b — if the parser confirms the format is correct against the generator output. If owner ever regains access to real i3070 logs at work, cross-check the real-vs-synthetic output for the remaining unknowns listed in `specs/synthetic-log-generator.md` "Open items".

**Guardrail compliance:** No verbatim Keysight or Virinco text copied into source. Grammar regexes derived from format-chapter field descriptions in the spec; Virinco repo cited only as cross-validation reference in `grammar.py` module docstring. Cached PDF + LGPL source files were deleted from `.cache_research/` and from repo root before Step 5 execution.

---

## 2026-06-13 — Phase 1a: @BTEST status derivation = categorical precedence rule

**Decision:** `models.derive_btest_status(blocks)` derives the overall `@BTEST` status from contained subtest statuses using **categorical precedence**: scan failing subtest records in this order, first match wins:

1. `FAIL_SHORTS` (4) — `@TS` shorts records
2. `FAIL_ANALOG` (6) — `@A-*` analog records (any of 14 types)
3. `FAIL_DIGITAL` (8) — `@D-T` digital records
4. `FAIL_PIN` (2) — `@PF` pins-failed records
5. `FAIL_TJET` (14) — `@TJET` VTEP records
6. `FAIL_POLARITY` (15) — `@PCHK` records (deferred Phase 5; placeholder in code)
7. `FAIL_CCHK` (16) — `@CCHK` connect-check records (deferred Phase 5; placeholder)
8. `FAIL_FUNCTIONAL` (9) — functional records (deferred; placeholder)
9. `FAIL_POWER` (7) — power-supply records (deferred; placeholder)
10. `FAIL_UNCATEGORIZED` (1) — catch-all (placeholder)

If no failures, return `PASS` (0). Environmental codes (`FAIL_HANDLER=11`, `FAIL_BARCODE=12`, `XD_OUT=13`, `RUNTIME_ERROR=80`, `ABORTED_STOP=81`, `ABORTED_BREAK=82`) are NEVER returned by this function — set externally by the orchestrator.

**Why:** Keysight's format chapter does not document an explicit precedence ordering for `@BTEST` status — only the categorical meaning of each code. Conventional ICT test ordering runs shorts → analog → digital → functional, and if shorts fails, the board is invariably reported as a shorts-failure regardless of what else fails downstream (shorts tests run first and gate the rest). The chosen precedence matches that operational logic and is defensible to a manufacturing engineer.

**Rejected:**
- **"First non-PASS encountered, in record order"** — simplest but semantically wrong. A board that has an analog test fail before the shorts test runs would be reported as analog-fail, which is wrong.
- **"Numerically smallest non-zero status code"** — would happen to match this ordering in most cases (4 < 6 < 8 < 14 < 15 < 16), but is a coincidence not a contract; doesn't gracefully extend if new codes are added.

**Revisit:** If the Phase 1b parser, when fed real customer logs (if owner ever gains access), reveals a different precedence is used in practice. Until then, the chosen ordering is the project's canonical synthesis convention.

**Forward extensibility:** The `_PRECEDENCE` list in `models.py` includes all 10 categories. The 5 deferred ones (POLARITY, CCHK, FUNCTIONAL, POWER, UNCATEGORIZED) have `lambda r: False` predicates today; a Phase 5 addition only needs to swap the predicate.

---

## 2026-06-13 — Phase 1a session: branch merge fast-path (one-time exception)

**Decision:** During Phase 0 cleanup at the start of the Phase 1a session, three in-flight feature branches (`fix/commit-uv-lock`, `feature/gitignore-data-synthetic-v2`, `feature/pyproject-dependency-groups`) were merged **directly to `main`** with `--no-ff`, instead of the canonical `feature/* → dev → main` flow specified in the branching-strategy decision. `dev` was then fast-forwarded from `main` to keep the two permanent branches in sync.

**Why:** Solo portfolio project. The three branches each contained small, isolated, non-conflicting changes (uv.lock commit, gitignore broadening, PEP 735 migration). Routing each through `dev` first would have meant 6 merge commits + 3 fast-forwards for content already owner-approved. The fast-path takes 4 merges total with no loss of history or attribution.

**Rejected:**
- **Canonical `feature/* → dev → main`** — correct per the branching-strategy decision but adds ceremony without adding clarity for a solo project. Original strategy decision explicitly says "Lowest overhead, cleanest history" as the rationale — fast-path is more consistent with that intent for this specific case.

**Scope of exception:** This applies ONLY to the 3 branches landed during Phase 0 cleanup at the start of the 2026-06-13 Phase 1a session. The canonical flow remains the default for all subsequent work.

**Revisit:** Never. One-time exception for one specific cleanup. Phase 1b and later sessions use the canonical flow.

---

## 2026-06-13 — Phase 1a: fault correlation = refdes-numerical clustering heuristic

**Decision:** Within-panel fault correlation in `faults.py` uses a **refdes-numerical clustering heuristic** rather than an explicit net-graph. When a component fails, components whose refdes differs by ±1 in the same family (R12 ↔ R13) receive a `1.5×` failure-rate multiplier; ±3 receives `1.2×`; further gets baseline `1.0×`. No `BoardProfile.net_adjacency` field is added in v1.

**Why:** The spec requires fault correlation to produce realistic Pareto curves (clustering rather than flat noise). A faithful net-graph would require either modeling actual board topology (out of scope) or synthesizing a random adjacency matrix per panel (extra state + reproducibility complications). Refdes-numerical clustering exploits the real-world tendency for adjacent reference designators to share routing concerns — it's a synthesis convenience that produces visibly clustered failure patterns without inflating the data model.

**Rejected:**
- **Explicit net-graph in `BoardProfile`** — out of v1 scope; would require generating a topology that doesn't currently inform anything else.
- **Per-panel random adjacency matrix** — adds state, complicates seed-reproducibility tests, and provides no realism benefit over a clustering heuristic.
- **No correlation at all** — produces unrealistic flat-noise Pareto curves; defeats the realism rule in the spec.

**Documented as a heuristic, not a physical claim:** `faults.py` module docstring states this is "a synthesis convenience, not a physical claim." If the project ever needs to claim physical realism (e.g., for a published paper), the heuristic would need to be replaced.

**Revisit:** When Phase 2 analytics surface (failure Pareto + SPC). If clustering looks "too clean" or "too noisy", retune the multipliers or move to a sparse adjacency model.

---

## 2026-06-13 — Synthetic data `.gitignore` — samples-only allow-list

**Decision:** `.gitignore` excludes `data/synthetic/*` broadly and re-includes only `data/synthetic/samples/`. Bulk generator outputs (20–50 MB `results.csv` / `results.json` from 1k-panel runs) must go to `data/synthetic/<run_id>/` or any sibling of `samples/` — never into `samples/` itself. Only deliberately curated small example files belong in `samples/`.

**Why:** A `git add .` after a generator run would otherwise drop ~50 MB blobs into the index and blow past GitHub's 100 MB file limit (or at minimum bloat the repo). Guardrail #4 in CLAUDE.md ("all committed data is synthetic") does not mean all synthetic data should be committed — only small samples for documentation / parser fixtures.

**Implementation notes:**
- Used `data/synthetic/*` (not `data/synthetic/`) because the trailing-slash form blocks gitignore re-include rules for any subpath of the excluded directory. The `/*` form excludes one level of entries and lets `!data/synthetic/samples/` actually take effect.
- Also narrowed the existing `!data/synthetic/**/*.log` re-include to `!data/synthetic/samples/**/*.log` so a bulk run's `.log` files don't sneak back in via the broader `*.log` rule.
- `data/synthetic/samples/.gitkeep` committed so the samples dir exists in fresh clones.

**Rejected:** Per-extension exclude (`data/synthetic/**/*.csv`, `**/*.json`) — fragile; a new output format would silently slip through. Excluding by size — git doesn't natively support it.

**Revisit:** If the generator gains a "minimal demo" output mode that's small enough to commit alongside parser fixtures, place those under `samples/` and document the convention in the generator's spec.

---

## 2026-06-13 — Branching strategy: Option A (feature/* → dev → main)

**Decision:** Two permanent branches (`main`, `dev`). All work on short-lived `feature/[name]` branches. Merge feature → dev as tasks complete; dev → main at phase boundaries.

**Why:** Solo portfolio project. ROADMAP.md already tracks phase gates — git branches don't need to mirror them. Lowest overhead, cleanest history.

**Rejected:** Option B (phase/[name] branch layer between feature and dev). Adds merge ceremony without adding clarity for a solo project.

**Revisit:** After first contributor joins — may layer in phase branches then.

---

## 2026-06-13 — hrk-agent-starter as portable governance kit

**Decision:** All AI agent skills, hooks, rules, and log templates live in a separate repo (`-hrk-agent-starter` on GitHub). New projects are stamped via `stamp.ps1` or GitHub template. Skills are owned by the kit repo; project-specific adaptations live in the project.

**Why:** Owner wants to start any future project with the same governance discipline without rebuilding it from scratch each time. Single source of truth for skills means improvements propagate across all future projects.

**Rejected:** Keeping skills only in each project (no canonical source, diverges over time). Git submodule (too much overhead for a stamp-and-forget workflow).

**Revisit:** After 2-3 projects stamped — decide whether to version the kit with releases.

---

## 2026-06-13 — 10-step multi-agent loop as canonical workflow

**Decision:** The session-workflow skill defines a 10-step loop with specific agent roles. Steps 3 (Plan) and 7 (Triple Check) are parent-only and can never be delegated. Out-of-scope bugs are logged immediately and surfaced via spawn_task at step 8.

**Why:** The triple comparison (Found vs Planned vs Executed) catches executor drift, report inflation, and plan gaps — three failure modes that aren't caught by tests alone. The explicit handoff step ensures no context is lost between sessions.

**Rejected:** Simpler linear pipeline with no triple check. Catches fewer failure modes.

**Revisit:** After Phase 1b — tune step count and agent charters based on real usage.

---

## 2026-06-13 — Governance system adopted from my-assembly-hub

**Decision:** Use the same agent-governance pattern as `my-assembly-hub`:
hooks (block_dangerous_git, plan_approval_gate, doc_reminder_stop), rules (agent-conduct,
session-workflow, testing), skills (plan-architect, execute-plan, test-generator, session-workflow,
diagnose), and log files (BUG_LOG, DECISION_LOG, AGENT_HANDOFF_LOG, SESSION_LOG).

**Why:** Owner already runs assembly-hub this way successfully. Consistent pattern across projects
means zero ramp-up time. The governance layer enforces discipline without needing to re-explain it.

**Rejected:** A lighter-weight approach (just CLAUDE.md). Too easy to skip steps on a portfolio project
that no one else is reviewing.

**Revisit:** After Phase 2 — add skills for analytics-specific patterns if needed.

---

## 2026-06-13 — TDD as the default workflow

**Decision:** Tests are written before implementation in every phase. Red → Green → Refactor.
No implementation is committed without a corresponding test.

**Why:** Portfolio project — demonstrates software engineering discipline. Also prevents silent bugs
in the synthetic-data → parser → DuckDB pipeline where a wrong value produces wrong analytics silently.

**Rejected:** Build-then-test. Explicitly rejected by owner.

**Revisit:** Never. Standing rule.

---

## 2026-06-13 — Tech stack locked

**Decision:** Python 3.11+, uv, DuckDB, ChromaDB + sentence-transformers + rank-bm25,
Gemini API (primary LLM), Claude API (backup), Streamlit + Plotly.

**Why:** Full AI engineering stack on a portfolio-demonstrable footprint. DuckDB handles
analytical queries without a server process. ChromaDB + BM25 gives hybrid retrieval.
Streamlit keeps the UI fast to build. Gemini is free-tier friendly for portfolio work.

**Rejected:** PostgreSQL (overkill for local-only), React frontend (too much overhead for
a solo portfolio project), OpenAI as primary (cost + Gemini is sufficient).

**Revisit:** After Phase 3 — if Gemini quality disappoints, switch to Claude API.

---

## 2026-06-13 — HP3070 / Keysight i3070 log format as v1 target

**Decision:** Target HP3070-style flying-probe logs as the only supported format in v1.
Generic multi-format parser is deferred.

**Why:** Narrow scope = shippable within the timeline. HP3070 is the format the owner
encounters most in their professional context. Good enough for portfolio demonstration.

**Rejected:** Multi-format parser in v1 (too broad; makes Phase 1a unbounded).

**Revisit:** After Phase 1b — decide if Takaya format is worth adding for variety.

---

## Template

```
## YYYY-MM-DD — Short title

**Decision:** What was decided, in plain English.

**Why:** The reason — include constraints, tradeoffs, and stakeholder input.

**Rejected:** What alternatives were considered and why they were ruled out.

**Revisit:** When (phase boundary, date, condition) and what might change the decision.
```
