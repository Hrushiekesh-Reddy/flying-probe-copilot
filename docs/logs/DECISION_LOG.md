# Decision Log — Flying-Probe Co-Pilot

Architectural, design, and process decisions in reverse-chronological order.
Every non-obvious choice gets an entry here: what was decided, why, what was rejected, and when to revisit.

---

## 2026-06-14 — Phase 1b: DuckDB schema shape (boards + panels split, global components, persisted limits, ParseReport, runs metadata)

**Decision:** The Phase 1b DuckDB schema uses 9 tables organised as 5 dimension + 1 metadata + 3 fact:

- **Dimensions:** `boards` (board profiles only — small/medium/large + their BOM metadata; ~3 rows ever), `panels` (per-serial unit-under-test instances; one row per panel ever produced), `operators` (per `operator_id` seen in `@BATCH`), `components` (global per `(board_profile_id, refdes)` — N=~120 for small, ~450 for medium, ~1600 for large — looked up at ingest with `INSERT OR IGNORE` on the `UNIQUE` index), `tests` (per `(board_profile_id, block_designator, record_type)`).
- **Metadata:** `runs` (one row per generator run-directory ingested; columns sourced from `manifest.json` plus the directory basename as `run_id` and `ingested_at` defaulted to `CURRENT_TIMESTAMP`).
- **Facts:** `test_runs` (one per `@BTEST` record per panel), `measurements` (one per `@A-*` / `@D-T` / `@TS` / `@TJET` / `@PF` record, with type-specific nullable columns including `limit_high`/`limit_low`/`limit_nominal` from `@LIM2`/`@LIM3`), `failures` (denormalized convenience table: one row per non-PASS measurement, with `panel_serial` + `board_profile_id` carried for fast Pareto without joins).

The parser returns a structured `ParseReport` (errors + notes + record_count) rather than logging silently — testable, audit-friendly.

**Why:** All four decisions came from the Phase 1b brief's Step 2 explore + the owner's pre-plan answers:

1. *boards (profile) vs panels (instance) split:* "yield by board over last week" reads naturally as per-profile aggregation for a manufacturing engineer (small profile = X% yield); per-serial yield would be 100%/0% noise. The split keeps the semantic clean and lets the same `panels` table back per-serial drill-downs in Phase 2 dashboards.
2. *Components global per (profile, refdes):* per-panel rows would explode the components table 100–1000× and make cross-panel "how does R12 behave?" queries expensive. Global per (profile, refdes) keeps the dim stable.
3. *Limits persisted as nullable columns:* +3 nullable floats per measurement row is cheap. Without them, Phase 2 "which measurements failed because spec tightened" queries would have to re-parse logs or re-derive from the spec — both lossy.
4. *ParseReport object:* testable assertions on error counts + line numbers; matches the brief's "captured in a `parse_report` or logged" success criterion line.
5. *runs metadata table from manifest:* free during ingest; enables cross-run comparison queries ("compare fault rates across runs") and is the natural anchor for the re-ingest guard (#WARNING-13 below).

**Rejected:**
- *Single `boards` table conflating profile + instance* — wrong semantics for the named exit query; would have forced per-serial yield aggregation.
- *Per-panel `components` rows* — table size explosion + duplicate-key handling pain on every ingest.
- *Skip limits* — irrecoverable for downstream Pareto analysis.
- *Silent error logging instead of ParseReport* — untestable.
- *Skip manifest ingest* — single-run-only parser, no cross-run comparison.

**Test contracts pinned:**
- `tests/test_parser/test_schema.py::test_init_database_creates_all_9_tables` — `TABLES` constant length == 9; `SHOW TABLES` set-equals constant.
- `tests/test_parser/test_schema.py::test_each_table_has_expected_columns` — per-table column shape audit.
- `tests/test_parser/test_ingest.py::test_ingest_components_global_per_profile_refdes` — re-ingesting the same panel twice leaves `components` row-count unchanged for that profile.

**Revisit:** End of Phase 2. If the failures denormalization shows drift symptoms (e.g. `failures.board_profile_id` differs from the joined `panels.board_profile_id`), add a constraint or a periodic reconciliation query. If the surrogate-PK Python counter approach proves slow on >1M-row ingests, swap to DuckDB sequences.

---

## 2026-06-14 — Phase 1b: `test_runs.operator_id` nullable; per-panel operator recovery deferred to Phase 2

**Decision:** `test_runs.operator_id` is declared `VARCHAR` (nullable), not `VARCHAR NOT NULL`. The parser populates it from the single `@BATCH.operator_id` field on the per-board log file. Per-panel operator recovery (which the generator currently does NOT preserve in per-board logs) is deferred to Phase 2.

**Why:** Per-board `.log` files contain `@BATCH.operator_id` once. The generator's `cli.py:140` uses `boards[0].panel.operator_id` for that field — so every per-board file in a run inherits the first panel's operator. The actual per-panel `PanelInstance.operator_id` is preserved only in `results.json` / `results.csv`, which the brief explicitly excluded from ingest. Three repair options were considered:
- Edit the generator to add `operator_id` to `@BTEST` — out of Phase 1b scope (generator edits prohibited).
- Read `results.json` as a sidecar during ingest — violates the brief's "log files only" promise.
- Use `@BATCH.operator_id` and document the degradation — chosen.

Making the column nullable converts a silent-degraded-data risk into an explicit "this column may be incomplete" contract, which downstream analytics + dashboards can opt into respecting.

**Rejected:**
- *`NOT NULL` constraint:* would have crashed ingest on the first panel of any run that didn't expose an operator anywhere — and silently degraded data on every run that did, since every panel in a run gets the same operator.
- *Generator change in Phase 1b:* out of scope, scope-creep risk.
- *`results.json` sidecar read:* violates the brief's CSV/JSON-not-ingested commitment.

**Test contract:** No specific test for nullability today; the schema's column declaration + `init_database` idempotency tests verify the column is `VARCHAR` without a `NOT NULL` modifier. Phase 2's operator-id repair will need a dedicated test.

**Revisit:** Phase 2 first session. Decide whether to extend `@BTEST` (generator change) or to ingest `results.json` as an authorized sidecar. Either path lets the column flip to `NOT NULL` if we want strict integrity.

---

## 2026-06-14 — Phase 1b: re-ingest guarded at CLI, not at schema (single-run idempotency contract)

**Decision:** The parser CLI does a pre-flight `SELECT 1 FROM runs WHERE run_id = ?` before any insert. If the run is already present, the CLI exits with code 2 and a stderr message. The schema itself is NOT idempotent on fact tables (`panels`, `test_runs`, `measurements`, `failures` would all PK-conflict or duplicate on re-insert). Dimension tables use `INSERT OR IGNORE` semantics (`boards`, `operators`, `components`, `tests` — shared across runs).

**Why:** Two options were on the table — make the entire ingest idempotent (UPSERT everywhere) or guard at the CLI. The guard approach is simpler for v1: it surfaces a clear error to the operator ("this run is already ingested; use --overwrite in Phase 2"), prevents accidental double-counting in yield/Pareto queries, and avoids the complexity of teaching every fact table how to dedup against an in-progress ingest. UPSERT-everywhere would also have masked partial-ingest failures (half a run already in, second attempt silently completes the other half).

**Rejected:**
- *UPSERT every table:* hides partial failures and over-promises idempotency on facts that genuinely shouldn't double-count.
- *Silently allow duplicates and let Phase 2 dedup at query time:* poisons analytics until the dedup layer ships.
- *No re-ingest support at all (exit code 0 + skip):* hides operator intent — the operator may have wanted to re-ingest to refresh after a parser bug fix.

**Test contracts:**
- `tests/test_parser/test_cli.py::test_cli_exits_with_code_2_when_run_already_ingested` — pin the CLI behaviour.

**Revisit:** Phase 2. Add `--overwrite` flag that performs `DELETE FROM <table> WHERE run_id = ?` across fact tables before re-inserting. Or add `--append` that ignores the guard and lets duplicates accumulate (useful for stress testing).

---

## 2026-06-14 — Fault correlation wired through `generate_blocks` (addendum to 2026-06-13)

**Decision:** The refdes-numerical clustering heuristic documented in the 2026-06-13 entry below now actually fires during panel generation. `generate_blocks` (in `src/flying_probe_copilot/generator/blocks.py`) picks the primary failing component as before, then calls a new `_pick_correlated_failures(primary, profile, rng)` helper that performs per-candidate Bernoulli secondary-failure draws against same-family components. The candidate draw uses `rate = BASELINE_SECONDARY_RATE * correlation_multiplier(primary, candidate)` with `BASELINE_SECONDARY_RATE = 0.3`, and the draw is **only performed when `correlation_multiplier > 1.0`** (i.e., for ±3 refdes neighbors). Far candidates and cross-family candidates get no secondary draw.

**Why:** PR #1 landed `correlation_multiplier` and `correlated_failure_rate` in `faults.py` with unit tests, but they were never invoked from the CLI output path. `_pick_failing_component` marked exactly one component as failing per panel, so the realistic clustered-failure Pareto curves the heuristic was designed to produce never appeared in real generator output. Bugbot caught this in PR #3 review (comment id 3409766432, medium severity). The fix wires the existing heuristic into the panel-construction pipeline so it actually does its job.

The "multiplier > 1.0 only" gate matters: applying the baseline to every same-family component (multiplier == 1.0 for far candidates) would produce uniform secondary noise across the whole family and visually dilute the ±3 cluster around the primary. Gating on multiplier > 1.0 keeps far candidates clean and lets the Pareto curve show real clustering. `correlation_multiplier`'s contract is unchanged; only the *integration interprets* a 1.0 return as "no secondary draw."

**Rejected:**
- **Apply baseline to all same-family candidates** (uniform secondary rate, neighbors only get a multiplicative bump). Produces no visible aggregate Pareto signal — far candidates outnumber near ones and their cumulative secondary fails wash out the cluster.
- **Bias the primary draw with the multiplier instead of doing secondary Bernoulli draws.** Changes what `_pick_failing_component` *means* (no longer uniform across the family) and complicates seed-reproducibility tests. Per-panel secondary draws keep the primary draw clean and add clustering as a separate orthogonal layer.
- **Higher baseline (e.g. 0.5).** Empirically reaches the same Pareto target but makes failing panels dominated by 3–5 simultaneous component fails, which over-states realistic FP/ICT failure patterns. 0.3 was chosen as the lowest value that comfortably meets the test thresholds in `tests/test_generator/test_blocks.py` while keeping per-failing-panel fail counts in the 1–4 range.

**Test contracts pinned (`tests/test_generator/test_blocks.py`):**
- `test_neighbor_fail_rate_elevated_vs_far_when_primary_pinned` — 500 seeded panels with primary monkeypatched to R50: combined R49+R51 fail counts ≥ 3× R10 fail count.
- `test_failure_pareto_clusters_around_primary_under_correlation` — 1000 seeded panels with primary monkeypatched to R50: top-3 failing refdes account for >30% of all failures (and the top-3 must include R50 plus at least one ±1 neighbor).
- `test_correlation_secondary_fails_stay_within_same_family` — 500 seeded DIGITAL panels with primary pinned to U8: zero cross-family secondary fails.

**Revisit:** When Phase 2 analytics surface the failure Pareto. If clustering looks too tight (always exactly R50 ±1) or too loose (per-panel fail counts ≥5), retune `BASELINE_SECONDARY_RATE` rather than the multiplier table — the multiplier is the heuristic's public contract.

---

## 2026-06-14 — Dedicated `exec` sub-agent with hard tool restrictions

**Decision:** Step 5 of the 10-step session-workflow uses a dedicated `exec` sub-agent defined at `.claude/agents/exec.md`, with a tool allowlist enforced by the agent definition itself. Other sub-agent roles (Explore, Plan-Reviewer, Verifier) continue to use the built-in `Explore` agent type or the existing skills.

**Why:** Skills can *advise* a sub-agent on scope discipline; an agent definition can *enforce* it via tool restrictions. The executor is the highest-blast-radius role (it's the one writing files), so tool-level guardrails are most valuable there. Specifically, the `exec` agent cannot spawn further sub-agents (no recursion), cannot fetch the web, cannot control the browser or desktop, cannot enter/exit plan mode, and cannot invoke nested workflows — even if a misread plan instruction tries to make it.

**Rejected:**
- Custom agents for every role (Explore, Plan-Reviewer, Verifier, Exec). Diminishing returns — Explore is already well-served by the built-in `Explore` agent type, and the other roles benefit more from skill-level prompting than tool restriction.
- Continuing to rely on `execute-plan` skill alone. A skill is advisory; the executor could ignore it. Tool restrictions cannot be ignored.

**Revisit:** End of Phase 1b. If the executor's tool list turns out to be too restrictive (e.g. we discover legitimate need for `WebFetch`), expand the allowlist deliberately rather than dropping restrictions wholesale.

---

## 2026-06-14 — Tier-based step selection for the 10-step workflow

**Decision:** The 10-step loop is no longer uniformly applied. Sessions classify as Trivial (Steps 1, 7, 8), Small (1, 3, 5, 7, 8), Medium (1, 2, 3, 5, 7, 8), or Large (full 1–10). Tier is chosen at Step 1 using the five-minute decision rule in `.claude/templates/tiering.md`. Mid-session escalation is allowed via the escalation protocol (STOP → log → reset brief → restart at the new tier's correct step).

**Why:** Running the full loop on a typo fix or a 50-LOC helper is ~4–8x token overhead with near-zero quality gain. Step 6 (Verify Execution) in particular has the lowest yield-per-token in the loop because Step 7 (parent Triple Check) already catches what Step 6 would. Tiering preserves rigor where it matters (parser, schema, RAG core) and removes it where it doesn't (config tweaks, doc edits).

**Rejected:**
- Two-tier system (fast path vs full loop). Too coarse — most Phase 1a work falls between "typo" and "build the parser".
- Letting sub-agents self-select tier. Parent owns this — sub-agents see only their assigned tier's charter.

**Revisit:** After 5 full-loop sessions of real Phase 1a/1b work. If Step 6 catches something Step 7 missed, restore Step 6 to Medium tier.

---

## 2026-06-14 — Context-cache brief block for sub-agent prompts

**Decision:** Every sub-agent dispatch in a Medium or Large tier session is prefixed with a byte-for-byte identical "context brief" block, templated at `.claude/templates/sub-agent-brief.md`. The brief contains phase, tier, branch, guardrails-in-force, decisions-in-force, OUT-OF-SCOPE, fixtures-to-leave-alone, and resolved open questions.

**Why:** Two reasons:
1. **Direct context savings.** Without the brief, each sub-agent reads CLAUDE.md (~150 lines) + agent-conduct.md (~80 lines) + the relevant phase doc to learn the rules — ~3-5k input tokens per dispatch, or ~12-20k across a 4-sub-agent Large-tier loop.
2. **Prompt-cache prefix reuse.** Anthropic prompt caching keys on identical token prefix with a 5-minute TTL. An identical brief across the 4 sub-agents of one loop pays the prefix cost once and reads cache (~10x cheaper) on the other three. See `.claude/templates/prompt-caching.md` for the mechanics and timeline.

**Rejected:**
- Letting sub-agents read CLAUDE.md fresh each time. Wasteful; same content re-encoded each call.
- Including volatile content (diffs, test output) in the brief. Breaks the cache. Volatile content goes in the role-specific tail of the prompt, not the brief.

**Revisit:** After 3 Medium/Large sessions, measure `cache_read_input_tokens` vs `input_tokens` ratio. Target: >60% cache reads on dispatches 2–4 of a loop. If lower, the brief is drifting between calls — investigate and tighten.

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
