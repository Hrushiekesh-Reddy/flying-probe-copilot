# Bug Log — Flying-Probe Co-Pilot

Bugs that took >5 minutes to diagnose or resolve are logged here.
Add an entry here AND reference it from `SESSION_LOG.md` on the day it was found.

Severity:
- **P0** — Blocks all work. Must fix before anything else.
- **P1** — Important. Workaround exists. Fix this sprint.
- **P2** — Minor. Log and defer.

---

## Active / Open

<!-- Add new bugs below this line -->

## [BUG-010] `TestJetRecord` Pydantic model name causes PytestCollectionWarning on every test run (P3) — OPEN, deferred

**Discovered:** 2026-06-16
**Found during:** Phase 2 operator_id wiring session
**File:line:** `src/flying_probe_copilot/generator/models.py:327`
**Symptom:** pytest emits `PytestCollectionWarning: cannot collect test class 'TestJetRecord' because it has a __init__ constructor` for two test files (`test_log_parser.py`, `test_roundtrip.py`) that import from models. Not a test failure — just noise in every test run output.
**Root Cause:** Pydantic model class name `TestJetRecord` begins with `Test`, so pytest's default collection heuristic tries to gather it as a test class.
**Severity estimate:** P3 (cosmetic/noise — zero impact on correctness)
**Fix:** NOT DONE — out of scope this session. Rename to `TJetRecord` in models.py + all usages, or add `python_classes` conftest filter to exclude it. spawn_task chip created at Step 10.

## [BUG-009] `test_runs.operator_id` was always batch-level (per-panel operator-id lost in per-board logs) (P2) — RESOLVED 2026-06-16

**Discovered:** 2026-06-14 (during Phase 1b PR #9 review; the column was declared nullable as the v1 workaround per DECISION_LOG 2026-06-14).
**Phase:** Phase 2 — first task (per-panel operator-id repair), branch `feature/per-panel-operator`.
**File(s):** `src/flying_probe_copilot/generator/models.py`, `cli.py`, `renderers/log.py`, `grammar.py`, `src/flying_probe_copilot/parser/log_parser.py`, `ingest.py`, `src/flying_probe_copilot/db/schema.py` (+ matching test files).
**Symptom:** Per-board `.log` files carried `@BATCH.operator_id` once (one value per per-board log file, derived from `boards[0].panel.operator_id`). The parser sourced the per-panel operator from `@BATCH`, so every panel in a single run appeared under the same operator in `test_runs`. Per-operator yield queries (Notebook Query 4 and any Phase 2 dashboard depending on it) returned per-run-operator data, not true per-panel data.
**Root Cause:** The Keysight Log Record Format @BTEST record as originally modelled had no operator field — only `board_id`, `status`, timestamps, and `board_number`. The generator's per-board renderer therefore had nowhere to write `panel.operator_id`. The Phase 1b parser, having nothing better to read, fell back to `@BATCH.operator_id` for per-panel attribution and the schema declared the column nullable to convert the silent data degradation into an explicit "may be incomplete" contract.
**Fix:** Path A — generator extension. Added `operator_id: str = Field(min_length=1)` as a mandatory field at @BTEST positional index 12 (between `board_number` and the optional `parent_panel_id`). Wired through `BoardTestRecord`, the generator CLI builder (`cli._build_batch_log` now passes `operator_id=panel.operator_id`), the log renderer (`_render_btest` emits the new slot), the grammar regex (`_BTEST` accepts the 13/14-field form), the parser (`_parse_btest` extracts `fields[12]`; `_make_board_log` lost its `batch_rec` parameter and reads `btest.operator_id` directly), and the ingest layer (`ingest.py:287` reads `btest.operator_id`). Schema column flipped to `VARCHAR NOT NULL`. `@BATCH.operator_id` semantics unchanged — still set to `boards[0].panel.operator_id` for batch-level summary, but no longer the parser's source.
**Verification:** 11 new tests covering each layer of the contract, including `test_multi_operator_run_distinct_operators_per_panel` which constructs 4 boards with explicitly distinct operators (OP-001..OP-004), drives them through `render_log → ingest_run_directory`, asserts `COUNT(DISTINCT operator_id) == 4` in `test_runs` and that each `panel_serial`'s ingested operator matches its `PanelInstance.operator_id`. Full suite: 196 passing, 0 failing, 97% coverage (schema 100%, parser 97%, generator ≥90%). The previously batch-level @BATCH assertion in `test_log_parser.py:91` still passes for the right reason (single-operator small fixture has `boards[0].panel.operator_id == panel.operator_id` for every panel by construction).
**Time to resolve:** ~25 min exec sub-agent runtime + ~30 min parent review/triple-check. Closes the deferred decision in DECISION_LOG 2026-06-14 ("test_runs.operator_id nullable; per-panel operator recovery deferred to Phase 2").

## [BUG-008] Partial multi-file ingest failure left earlier files' fact rows committed, blocking retry with PK conflicts (P2) — RESOLVED 2026-06-14

**Discovered:** 2026-06-14
**Phase:** Phase 1b — PR #9 follow-up Bugbot review (comment id 3410321846, medium severity) on the BUG-006 fix
**File(s):** `src/flying_probe_copilot/parser/ingest.py:489-555` (post-BUG-006 / pre-BUG-008)
**Symptom:** After the BUG-006 fix (deferring the `runs` INSERT to after the loop), a mid-loop failure no longer left a stranded `runs` row — but earlier successful files' `panels` / `test_runs` / `measurements` / `failures` rows were still committed because each insert was an implicit autocommit. The CLI re-ingest guard then correctly allowed retry, but the retry hit PRIMARY KEY conflicts on `panels.panel_serial` (and the surrogate-PK fact tables, since counters were re-initialised from MAX+1 but earlier panel serials already existed).
**Root Cause:** No explicit transaction wrapping. DuckDB defaults to autocommit on each `con.execute(...)`, so partial state survived the function-level exception. The BUG-006 fix solved only the runs-row stickiness, not the broader atomicity gap.
**Fix:** Wrapped the entire ingest body (after manifest parse + counter init) in `con.execute("BEGIN TRANSACTION")` / `con.execute("COMMIT")` with a `try/except` that runs `con.execute("ROLLBACK"); raise` on any failure. The dim-table `INSERT OR IGNORE` calls roll back too, but that's safe — the next retry's `INSERT OR IGNORE` is idempotent. Surrogate-PK counters are re-derived from MAX+1 on each call, so retry-after-rollback starts fresh.
**Verification:** `tests/test_parser/test_cli.py::test_partial_multi_file_failure_rolls_back_earlier_panels` monkeypatches `_ingest_batch_log` to succeed on the first two calls and raise on the third, then asserts `SELECT COUNT(*) FROM panels / test_runs / measurements / runs` all return 0 after the failure. Then lifts the patch, retries, and asserts `panels` count equals the full board count (proving no PK conflicts on retry). 185/185 tests pass; ingest.py coverage held at 100%.
**Time to resolve:** ~15 min.

## [BUG-007] Parser-rebuilt PanelInstance hardcoded shift="A" and line_id="LINE-A" (P2) — FULLY RESOLVED 2026-06-17

**Update 2026-06-16:** The `operator_id` half of this bug-family was closed via Path A — see BUG-009.

**Update 2026-06-17 (FULL CLOSE):** Path A applied to the remaining two fields. `@BTEST` extended with mandatory `shift: Literal["A","B","C"]` at positional index 13 and `line_id: str = Field(min_length=1)` at index 14 (`parent_panel_id` shifted to optional index 15). `BoardTestRecord` carries both; the generator CLI passes `shift=panel.shift, line_id=panel.line_id`; the renderer emits them at the new positions; the grammar regex accepts `\|[ABC]\|{_FIELD}` between operator_id and the optional parent_panel_id; the parser's `_parse_btest` extracts `fields[13]` and `fields[14]`; `_make_board_log` reads `btest.shift` and `btest.line_id` instead of the placeholder literals. `panels.shift` and `panels.line_id` were already `NOT NULL` in the schema — no schema flip needed; the bug was silent-wrong-data, not nullability.

**Verification:** `tests/test_parser/test_ingest.py::test_multi_shift_multi_line_run_distinct_per_panel` constructs 4 panels with explicitly distinct `(shift, line_id)` tuples spanning all three shift letters and four different line_ids, runs them through `render_log → ingest_run_directory`, and asserts the `panels.shift` / `panels.line_id` values in DuckDB match the in-memory `PanelInstance` exactly for every panel_serial. Plus three model-layer tests: shift is required, shift rejects letters outside `Literal["A","B","C"]`, and `line_id` rejects empty string. 200 passing, 0 failing, 97% coverage.

**Notebook Query 3 (per-shift yield) caveat closed** alongside Query 4's earlier close — both per-shift and per-operator analytics now sit on real per-panel data.

**Discovered:** 2026-06-14
**Phase:** Phase 1b — PR #9 Bugbot review (comment id 3410306157, medium severity)
**File(s):** `src/flying_probe_copilot/parser/log_parser.py:619-628` (`_make_board_log`), `src/flying_probe_copilot/parser/ingest.py:268-283` (persists the placeholder into `panels`)
**Symptom:** Notebook Query 3 (per-shift yield) and any future per-line analytics return uniform data — every panel ingested through the parser ends up in `panels` with `shift='A'` and `line_id='LINE-A'`, regardless of what the generator's `PanelInstance.shift` / `line_id` actually was at schedule time.
**Root Cause:** The per-board `.log` file emitted by `src/flying_probe_copilot/generator/renderers/log.py` does not carry `shift` or `line_id` at any record level (`@BATCH` has neither field; `@BTEST` only has board_id + status + timestamps). When the parser rebuilds a `PanelInstance` in `_make_board_log`, the only legal source of truth is the log itself, which is silent. The parser writes the literals `"A"` / `"LINE-A"` rather than NULL, so DuckDB sees uniform values instead of missing-data.
**Why this is the same family as per-operator (DECISION_LOG 2026-06-14):** Same v1 limitation surface as `test_runs.operator_id`. The honest schema treatment is "nullable column populated where available, NULL where not; document in DECISION_LOG; defer enrichment to Phase 2."
**Workaround in this PR:** Notebook Query 3 markdown now carries the same caveat as Query 4 (per-operator), explicitly calling out "placeholder, until Phase 2 either (a) extends @BTEST to carry shift + line_id, or (b) ingests results.json as an authorised sidecar."
**Phase 2 fix paths (pick one in the spawned task):**
  - **A — Generator extension.** Add `shift` + `line_id` (and `operator_id`) to `@BTEST` or a sibling `@CTX` record; parser reads them; columns flip to `NOT NULL`. Touches generator, schema, parser, all three.
  - **B — Authorised sidecar.** Have the parser read `results.json` alongside the `.log` files (the original v1 brief excluded this; revisit). Generator stays unchanged.
  - **C — Schema nullability now, repair later.** Make `panels.shift` + `panels.line_id` nullable; parser writes NULL; downstream queries learn to skip NULLs. Closes the silent-wrong-data risk while we pick A vs B.
**Verification (when fixed):** A new round-trip test that builds a 3-shift × 2-line batch, runs through generator → parser → DB, asserts `SELECT DISTINCT shift FROM panels` returns `{'A','B','C'}` and the per-panel shift matches the in-memory `PanelInstance.shift`.

## [BUG-006] `runs` row inserted before parse loop blocks retry after mid-ingest failure (P2) — RESOLVED 2026-06-14

**Discovered:** 2026-06-14
**Phase:** Phase 1b — PR #9 Bugbot review (comment id 3410306158, medium severity)
**File(s):** `src/flying_probe_copilot/parser/ingest.py:489-507` (pre-fix)
**Symptom:** If `_ingest_batch_log` raised partway through the per-file loop (e.g. a DuckDB constraint hit), the `runs` row was already in the database. The CLI pre-flight check (`SELECT 1 FROM runs WHERE run_id = ?`) then exited code 2 on every retry, blocking re-ingest after the operator fixed the upstream cause. The DB was left with a `runs` row but partial / no fact rows.
**Root Cause:** Ordering. The `INSERT INTO runs` lived between `_ensure_board_dim` and the `for log_path in log_files:` loop, so it landed before any actual ingest happened.
**Fix:** Moved the `INSERT INTO runs` to AFTER the loop completes. An exception during the loop now propagates out of `ingest_run_directory` without persisting the runs row; the CLI catches it, returns exit 1, and a retry hits an empty `runs` table and proceeds normally. A completed (even zero-file) loop still writes the runs row, preserving the "this run was ingested" contract.
**Verification:** `tests/test_parser/test_cli.py::test_runs_row_not_persisted_when_ingest_raises_mid_loop` monkeypatches `_ingest_batch_log` to raise on the first call, asserts the runs row is absent and that a follow-up retry (patch lifted) succeeds with exit code 0 and persists exactly one runs row. 184/184 tests pass; ingest.py coverage held at 100%.
**Time to resolve:** ~10 min.

## [BUG-005] Parser CLI `--encoding` flag parsed but never threaded into parse_log_file (P2) — RESOLVED 2026-06-14

**Discovered:** 2026-06-14
**Phase:** Phase 1b — PR #9 Bugbot review (comment id 3410306154, medium severity)
**File(s):** `src/flying_probe_copilot/parser/cli.py:106-108` and `src/flying_probe_copilot/parser/ingest.py:512-515` (pre-fix)
**Symptom:** The CLI exposed `--encoding={auto,utf-8,cp1252}` and the manual QA Test 8 documented strict-encoding behaviour, but `cli.py` called `ingest_run_directory(run_dir, con)` without forwarding `args.encoding`, and `ingest.py` called `parse_log_file(log_path)` without an `encoding` argument. Every ingest silently fell through to `parse_log_file`'s default `encoding="auto"`, so `--encoding=utf-8` did NOT fail on a cp1252-encoded log (auto-detect rescued it) — the operator's strict choice was discarded.
**Root Cause:** Missing plumbing on a 2-hop boundary (CLI → ingest → parse_log_file). The acceptance tests covered `--encoding=auto` only; nothing exercised a non-default value end-to-end.
**Fix:** `ingest_run_directory(run_dir, con, encoding="auto")` now accepts an `encoding` parameter and forwards it to `parse_log_file(log_path, encoding=encoding)`. The CLI passes `args.encoding` through. The default stays `"auto"` so library callers and existing tests are unaffected.
**Verification:** `tests/test_parser/test_cli.py::test_cli_encoding_utf8_fails_on_cp1252_log` writes cp1252 logs with an injected cp1252-only byte (0x92), invokes the CLI with `--encoding=utf-8`, and asserts that fewer panels land in the DB than the input contained (proving strict-utf-8 actually fails to decode, instead of silently auto-detecting cp1252). 184/184 tests pass.
**Time to resolve:** ~5 min.

## [BUG-004] Shift letter drawn randomly per panel; shift-C wrap snap dropped raw_ts onto wrong overnight window (P2) — RESOLVED 2026-06-14

**Discovered:** 2026-06-14
**Phase:** Phase 1a — post-merge (PR #3 Bugbot review, comment id 3409766436, low severity)
**File(s):** `src/flying_probe_copilot/generator/schedule.py:105-128` (pre-fix)
**Symptom:** `generate_panel_schedule` drew a shift letter (A/B/C) uniformly at random per panel, then snapped to that shift's start hour on the *raw draw's* calendar day. The wrap-correction block for shift C was a literal `pass` — a no-op. Result: a raw timestamp at e.g. 02:00 on day X randomly assigned to shift C was snapped to (day X, 22:00) + 0–8 h, ~20 hours away from the raw draw and inside a *different* shift-C instance than the one that physically contained the raw timestamp. The shift-letter assignment was effectively decoupled from the raw chronology.
**Root Cause:** Two compounding problems. (a) The shift letter was drawn from `rng.choices(...)` rather than derived from `ts.hour`, so the assigned label had no physical relationship to the raw draw's time-of-day. (b) The shift-C wrap correction was implemented as a commented-out intent (`pass`) — i.e. never implemented.
**Fix:** Adopted option A from the PR thread. New module-level helpers `_shift_for_hour(hour)` and `_shift_window_start(ts, shift)`; `generate_panel_schedule` now derives `shift = _shift_for_hour(ts.hour)` and anchors the snap to `_shift_window_start(ts, shift)`, which steps back one calendar day when `shift == "C"` and `ts.hour < 6`. The unused `_shift_start_for` helper and the now-unreferenced `time` import were removed. Docstring updated to drop the weekday-shift weighting language (which was implicit and lost when we stopped drawing the shift randomly).
**Verification:** Three new regression tests in `tests/test_generator/test_schedule.py`:
  - `test_panel_shift_is_derived_from_raw_timestamp_hour` — narrow 02:00–03:00 window must produce only shift-C panels. RED-confirmed under the bug, passes after fix.
  - `test_snapped_timestamp_lies_within_assigned_shift_window` — contract: each panel's hour-of-day must lie in its shift's window.
  - `test_shift_C_panel_in_early_morning_anchors_to_previous_day_window` — for every shift-C panel with `hour < 6`, the (previous-day 22:00, +8h) window must contain it.
  Full suite: 101/101 pass; total coverage 95% (schedule.py 91%, up from 85%).
**Time to resolve:** ~35 min (RED → GREEN → cleanup).

## [BUG-002] Generator hardcodes 4 test records per board regardless of profile (P0) — RESOLVED 2026-06-13

**Discovered:** 2026-06-13
**Phase:** Phase 1a — Step 9 (Manual QA)
**File(s):** `src/flying_probe_copilot/generator/cli.py:94-142` (`_build_blocks`)
**Symptom:** Generated `.log` files for small/medium/large board profiles are all ~410 bytes. Each panel has exactly 4 test records: `shorts`, `R12` (A-RES), `D1` (A-DIO), `U7` (D-T) — the same 4 every time, regardless of `--board-profile`. CSV inspection (Test 8 of manual QA) confirmed: 4 rows per panel × N panels, identical component identifiers. Spec lines 100-104 require small=~120 tests, medium=~450 tests, large=~1600 tests per board.
**Root Cause:** `_build_blocks` docstring says "Build the representative four-block test set for one board." The function hardcodes the 4-block list as a representative sample, never expanding to use `profile.component_count` or `profile.component_mix`. Manual QA caught this; automated tests did NOT because (a) `test_profiles` validates profile DEFINITIONS only, not output scale; (b) `test_lexical_compliance` only checks lexical validity; (c) CLI tests only assert file presence and YAML round-trip, not realistic content scale.
**Fix:** Replace `_build_blocks(outcome)` with `generate_blocks(profile, outcome, seed)` that (a) uses `profile.component_count` to size the block count, (b) apportions blocks across component types per `profile.component_mix`, (c) generates realistic refdes (R1..R80, C1..C40, U1..U12, etc.), (d) maps component-type prefixes to record types (R→A-RES, C→A-CAP, L→A-IND, D→A-DIO, Q→A-NPN, U→D-T), (e) randomizes the component that fails (not always R12), and (f) keeps one shorts test as the first block per panel. Add tests asserting per-panel block count matches profile within ±10%, type mix matches `component_mix` within ±10%, refdes diversity, and failure can occur on any component family.
**Verification:** Manual QA Test 5 reruns produce small/medium/large with file sizes scaling ~5KB / 20KB / 80KB. Automated `test_panel_block_count_scales_with_profile` and `test_panel_block_mix_matches_profile_component_mix` pass.
**Time to resolve:** in progress (estimated 45-60 min, this session).

## [BUG-003] `available_profiles()` returns sorted-set order ('large, medium, small') not size order (P3) — RESOLVED 2026-06-13

**Discovered:** 2026-06-13
**Phase:** Phase 1a — Step 9 (Manual QA)
**File(s):** `src/flying_probe_copilot/generator/profiles.py`
**Symptom:** CLI error for unknown profile reads "valid: large, medium, small" — alphabetical, not the size-ascending order the spec implies and the docs everywhere quote ("small | medium | large").
**Root Cause:** Likely `set(...)` or `sorted(...)` returns alphabetical.
**Fix:** Return the list in size-ascending order explicitly.
**Verification:** `test_available_profiles_returns_size_ascending_order` passes; manual QA Test 6 shows ordered list.
**Time to resolve:** in progress (estimated 5 min, this session).

## [BUG-001] Web-research subagent cached proprietary Keysight PDF + Virinco LGPL source in `.cache_research/` (P1) — RESOLVED 2026-06-13

**Discovered:** 2026-06-13
**Phase:** Phase 1a — Step 2 (Explore)
**File(s):** `.cache_research/LogRecordFormat.pdf`, `.cache_research/LogRecordFormat.txt`, `.cache_research/Importer.cs`, `.cache_research/UnitMapper.cs`, `.cache_research/README.md`, plus stray `flying-probe-copilot.cache_researchImporter.cs` (malformed path concatenation)
**Symptom:** Step 2's external-research subagent (general-purpose, web-enabled) downloaded the Keysight "i3070 Log Record Format" PDF and its extracted text, plus three files from the Virinco WATS-Client-Converter repo (LGPL-3.0), into a working `.cache_research/` directory at the repo root. A separate `flying-probe-copilot.cache_researchImporter.cs` artifact also appeared, evidence of a path-concatenation bug in the subagent's file-saving code. None of these files were in `.gitignore` at the time; a `git add .` could have committed proprietary Keysight content into the repo, violating CLAUDE.md hard guardrail #3 ("No proprietary Keysight documentation copied wholesale").
**Root Cause:** The subagent was instructed to do public-sources research with citations. It correctly fetched material to read it, but persisted the raw downloads at the repo root instead of in `~/.cache/` or `%TEMP%`. The guardrail was not part of its charter. The stray artifact additionally indicates the subagent built file paths by string-concatenating "<project-name>" + ".cache_research" + "<filename>" instead of a platform-correct path join.
**Fix:**
  In-session (2026-06-13):
    (a) Added `.cache_research/` to `.gitignore`;
    (b) deleted `.cache_research/` and the stray `flying-probe-copilot.cache_researchImporter.cs` artifact;
    (c) noted the issue in DECISION_LOG.
  Process improvement (2026-06-13, this entry's resolution):
    (d) Added an "External Research / Web Download Policy" block to the Explorer charter in `.claude/skills/session-workflow/SKILL.md` (Step 2) requiring `%TEMP%\agent-research\<session>\` (Win) or `~/.cache/agent-research/<session>/` (Unix) for any caching, citation-only reports, no copying of LGPL/GPL/proprietary source, mandatory cleanup with a `Cleanup:` line in the report, and an explicit STOP-on-bad-path rule that catches the path-concatenation bug pattern.
    (e) Added a matching charter block to `.claude/skills/deep-research/SKILL.md` Step 2 ("Charter for every fan-out search agent") and reinforced in the Research quality rules.
    (f) Added a one-line summary to `.claude/rules/session-workflow.md` Hard rules.
    (g) Added matching rows to the Subagent charter summary table.
    (h) Source of truth for these edits is `E:\hrk-agent-starter\` (the portable kit) — all three files updated there and propagated here, so future stamps of new projects inherit the policy automatically.
**Verification:**
  - `.cache_research/` and stray artifact removed from working tree (in-session, 2026-06-13).
  - `.cache_research/` present in `.gitignore`: verified.
  - Charter updated in both `E:\hrk-agent-starter\` (source of truth) and `E:\flying-probe-copilot\` (this project), files:
    `.claude\skills\session-workflow\SKILL.md` (Step 2 + summary table),
    `.claude\skills\deep-research\SKILL.md` (Step 2 + quality rules),
    `.claude\rules\session-workflow.md` (Hard rules).
  - Behavioural verification deferred to next external-research session: confirm the spawned subagent (i) writes only to `%TEMP%\agent-research\<session>\`, (ii) returns a `Cleanup:` line, (iii) the post-session `git status` shows no new files under the repo root and no path-mangled artifacts.
**Time to resolve:** ~5 min (in-session mitigation, 2026-06-13) + ~30 min (process improvement: charter language drafted, applied to starter + project, 2026-06-13).

---

## Resolved

<!-- Move bugs here when fixed. Include resolution date and verification note. -->

---

## Template

```
## [BUG-XXX] Short title (P0 / P1 / P2) — OPEN | RESOLVED YYYY-MM-DD

**Discovered:** YYYY-MM-DD
**Phase:** Phase X — name
**File(s):** `src/flying_probe_copilot/...`
**Symptom:** What you saw or what failed.
**Root Cause:** Why it happened.
**Fix:** What was changed to resolve it.
**Verification:** How you confirmed the fix (test name, manual check, etc.)
**Time to resolve:** X min / X hr
```
