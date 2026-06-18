# Plan — Phase 2 first task: per-panel operator-id repair
**Date:** 2026-06-14
**Brief:** `docs/plans/2026-06-14-phase2-operator-brief.md`
**Tier:** Medium — full 10-step loop
**Branch:** `feature/per-panel-operator` (from `dev` @ `ac13c7e` + BUG-008 wrap)
**Author:** parent — Claude Opus 4.7 (1M context)

---

## 0. Goal Contract

**Goal:** add a mandatory `operator_id` field to the `@BTEST` Keysight log record so that each per-board log file carries its own panel's operator, wire it through generator/grammar/renderer/parser/ingest, and flip `test_runs.operator_id` to `VARCHAR NOT NULL` — with a regression test proving multi-operator runs ingest with per-panel-distinct operators.

**Hard constraints (immutable for this session):**
1. **Field position locked:** `operator_id` is the new mandatory field 12 (zero-indexed within the @BTEST positional sequence, AFTER `board_number` at index 11, BEFORE the optional `parent_panel_id`). @BTEST goes from 12-or-13 fields to 13-or-14 fields.
2. **Mandatory, not optional:** no default value, no `None`, no empty string. Pydantic `extra="forbid"` semantics preserved.
3. **Parser sources operator from `@BTEST.operator_id`, NOT `@BATCH.operator_id`.** The "operator_id is batch-level" parser note is removed.
4. **Ingest sources operator from `btest.operator_id`, NOT `batch_log.batch.operator_id`.** Single edit at `ingest.py:287`.
5. **Schema flip lands AFTER ingest is producing non-NULL values** — see step ordering below to avoid red intermediate states.
6. **No new dependencies.** No `uv add`. No new modules. No new CLIs.
7. **`@BATCH.operator_id` semantics unchanged** — still set to `boards[0].panel.operator_id` for batch-level summary. Parser does not use it for panel-operator anymore.
8. **Single coherent commit at Step 8.** No mid-session commits.

**Files in scope (What/Why/Where/When table):**

| File | What changes | Why | When (step) |
|------|--------------|-----|-------------|
| `src/flying_probe_copilot/generator/models.py` | Add `operator_id: str` (no default) to `BoardTestRecord` between `board_number` and `parent_panel_id` | Single source of truth for the new field | Step 5.1 |
| `src/flying_probe_copilot/generator/cli.py` | Pass `operator_id=panel.operator_id` when constructing `BoardTestRecord` (~L123-130) | Wire generator output to the new field | Step 5.2 |
| `src/flying_probe_copilot/generator/renderers/log.py` | Insert `btr.operator_id` between `str(btr.board_number)` and the `parent_panel_id` append in `_render_btest` | Emit the new field at the locked positional slot | Step 5.3 |
| `src/flying_probe_copilot/generator/grammar.py` | Update `_BTEST` regex: append `\|{_FIELD}` for mandatory operator_id BEFORE the optional `parent_panel_id` group | Grammar must accept the renderer's output | Step 5.4 |
| `src/flying_probe_copilot/parser/log_parser.py` | `_parse_btest`: bump min-field check from 12→13; extract `operator_id=fields[12]`; shift `parent_panel_id` from `fields[12]` to `fields[13]`; build `BoardTestRecord(operator_id=...)`. `_make_board_log`: use `btest.operator_id` not `batch_rec.operator_id`. Remove the "operator_id is batch-level" `report.notes.append(...)` | Parser must read the new field and stop using @BATCH as the per-panel source | Step 5.5 |
| `src/flying_probe_copilot/parser/ingest.py` | Change `operator_id = batch_log.batch.operator_id` → `operator_id = btest.operator_id` (L287) | Ingest must write per-panel operator, not batch-level | Step 5.6 |
| `src/flying_probe_copilot/db/schema.py` | Flip `test_runs.operator_id VARCHAR` → `test_runs.operator_id VARCHAR NOT NULL` (L91). **Approval-gated.** | Make the data contract strict now that data is correct | Step 5.7 |
| `tests/test_generator/test_models.py` | Add `operator_id="OP-001"` kwarg to the `BoardTestRecord(...)` literal at L113-122 | Tests must construct the new mandatory field | Step 5.1 (RED) |
| `tests/test_generator/test_renderers.py` | Add `operator_id="OP-001"` kwarg to fixture L251-259; update any positional index assertion that depends on field count after board_number | Renderer test must use the new field | Step 5.3 (RED) |
| `tests/test_generator/test_grammar.py` | Update hardcoded `@BTEST` string literals (L22-27, ~L80, ~L111, ~L128, ~L131) to include the new operator_id field | Grammar test must use the new format | Step 5.4 (RED) |
| `tests/test_generator/test_lexical_compliance.py` | Add `operator_id` to the `BoardTestRecord(...)` call in `_build_batch_log_via_cli_path` (L79-86) — but only if it's not built via the actual CLI helper (cross-check) | Lexical compliance must pass against generator output | Step 5.4 (RED) |
| `tests/test_parser/test_log_parser.py` | Add `operator_id="OP-001"` kwarg to the 3 `BoardTestRecord(...)` literals at L287-297, L353-368, L424-439 | Parser unit tests must use the new field | Step 5.5 (RED) |
| `tests/test_parser/test_ingest.py` | Add `operator_id="OP-001"` kwarg to L401-405, L473-477. **NEW:** add `test_multi_operator_run_distinct_operators_per_panel` covering Success-8 (multi-op generate → ingest → query DISTINCT). | Ingest tests must use the new field; new regression test for the actual contract | Step 5.5 (RED) + Step 5.6 (RED) |
| `tests/test_parser/test_malformed.py` | Update hardcoded `@BTEST` literal at ~L27 to include operator_id | Malformed-line test must use valid base format | Step 5.4 (RED) |
| `notebooks/01-queries.ipynb` | Update preamble cell + Query 4 markdown to drop the "batch-level operator" caveat. Code unchanged. | Doc accuracy — caveat is now stale | Step 8 (docs) |
| `docs/logs/DECISION_LOG.md` | Append **Resolved 2026-06-14** footnote to the L42-60 entry, with commit ref | Close the deferred decision | Step 8 (docs) |
| `docs/logs/SESSION_LOG.md` | New entry at top documenting this session | Audit trail | Step 8 (docs) |
| `docs/logs/BUG_LOG.md` | New entry: closing data-degradation note for the per-panel operator gap | Trace deferred-bug closure | Step 8 (docs) |
| `docs/ROADMAP.md` | Phase 2 status block: add "Per-panel operator-id repair landed" sub-item | Roadmap reflects what shipped | Step 8 (docs) |
| `CLAUDE.md` | Append session-log line and update phase table if needed | CLAUDE.md memory bridge | Step 8 (docs) |

**Files NOT in scope (do NOT touch this session):**
- `pyproject.toml` (no new deps, no new scripts).
- `.claude/settings.json`, `.env.example`, `migrations/`.
- `src/flying_probe_copilot/generator/renderers/csv.py`, `renderers/json.py` — these already use `PanelInstance.operator_id` directly.
- `src/flying_probe_copilot/generator/faults.py`, `schedule.py` — unrelated.
- `notebooks/01-queries.ipynb` code cells (markdown only updates).
- `data/db/sample.duckdb` (gitignored; owner regenerates if needed; manual-QA script will document the command).

---

## 1. Step-by-step ordered plan (TDD: Red → Green → Refactor)

### Step 5.1 — Add `operator_id` to `BoardTestRecord`

**Red:**
- Update `tests/test_generator/test_models.py:113-122` `test_btest_record_status_uses_intenum`: add `operator_id="OP-001"` kwarg.
- Add a NEW test `test_btest_record_requires_operator_id`: `BoardTestRecord(...)` without `operator_id` raises Pydantic ValidationError.
- Run `uv run pytest tests/test_generator/test_models.py -v` → expect the new test to FAIL (no field yet) and the updated test to FAIL until the model accepts the kwarg.

**Green:**
- Edit `src/flying_probe_copilot/generator/models.py` `BoardTestRecord` — insert `operator_id: str` between `board_number: int` (L208) and `parent_panel_id: str | None = None` (L209). NO default.
- Re-run → both tests pass.

**Refactor:** none expected — single-field addition.

### Step 5.2 — Wire generator CLI

**Red:**
- Add NEW test `tests/test_generator/test_cli_builder.py::test_build_batch_log_each_btest_uses_panel_operator` (or use existing file). Build a multi-panel batch via `cli._build_batch_log` (or whatever the public entry is), assert `batch_log.boards[i].btest.operator_id == batch_log.boards[i].panel.operator_id` for every i.
- If a CLI-builder test module doesn't exist, put the test in `tests/test_generator/test_cli_smoke.py` if it exists; otherwise create `tests/test_generator/test_cli_builder.py` with one focused test.
- Run → FAIL (cli.py builds BoardTestRecord without operator_id kwarg, will raise ValidationError after Step 5.1).

**Green:**
- Edit `src/flying_probe_copilot/generator/cli.py:123-130` `BoardTestRecord(...)` block — add `operator_id=panel.operator_id`.
- Re-run → pass.

**Refactor:**
- Leave `@BATCH.operator_id` assignment at L140 unchanged (`boards[0].panel.operator_id if boards else "OP-001"`). It is intentionally a batch-level summary; the parser no longer reads it.

### Step 5.3 — Renderer emits the new field

**Red:**
- Update `tests/test_generator/test_renderers.py:251-259` `sample_batch_log` fixture: add `operator_id="OP-001"` to the `BoardTestRecord(...)` literal.
- Add NEW test `test_btest_renders_operator_id_at_position_12`: render the BTEST, split on `|`, assert `split[13] == "OP-001"` (index = 0 for "@BTEST" prefix + 12 fields). Confirms locked positional slot.
- Verify existing `test_btest_rendered_status_field_matches_model` (L277-283) — `fields[2]` is status. operator_id at position 12 does NOT shift status. Test should still pass after the fixture update.
- Run → new test FAILS; existing test passes after fixture update.

**Green:**
- Edit `src/flying_probe_copilot/generator/renderers/log.py:88-105` `_render_btest`: insert `btr.operator_id` between `str(btr.board_number)` and the `if btr.parent_panel_id is not None:` block.
- Re-run → all green.

**Refactor:** none.

### Step 5.4 — Grammar regex accepts the new field

**Red:**
- Update `tests/test_generator/test_grammar.py` hardcoded `@BTEST` literals (L22-27 and any others at ~L80, ~L111, ~L128, ~L131) to include the new operator_id field at the locked position. Use literal `OP-001` for clarity.
- Update `tests/test_parser/test_malformed.py:~L27` hardcoded literal similarly.
- Update `tests/test_generator/test_lexical_compliance.py:79-86` and any sibling helpers — add `operator_id="OP-001"` kwarg if they manually construct `BoardTestRecord`. Cross-check: if `_build_batch_log_via_cli_path` calls the real CLI helper (`cli._build_batch_log`), no edit is needed there — the generator change handles it. (Explore noted L79-86 is a literal construction.)
- Add NEW test `test_grammar_btest_requires_operator_id_field`: a 12-field @BTEST string (the OLD format) fails grammar validation.
- Run → existing grammar tests pass against OLD format (because we haven't updated the regex yet) → they will FAIL after updating literals to NEW format; new test FAILS.

**Green:**
- Edit `src/flying_probe_copilot/generator/grammar.py:62-78` `_BTEST` regex: between the `board_number` line (`rf"\|\d+"`) and the optional parent_panel_id (`rf"(?:\|{_FIELD})?"`), insert one mandatory field: `rf"\|{_FIELD}"  # operator_id`.
- Re-run → grammar tests + new test green.

**Refactor:** none. Field-order is locked; regex shape is minimal.

### Step 5.5 — Parser extracts operator_id from @BTEST

**Red:**
- Update `tests/test_parser/test_log_parser.py:287-297, 353-368, 424-439` `BoardTestRecord(...)` literals to include `operator_id="OP-001"` kwarg.
- Add NEW test `test_parse_btest_extracts_operator_id_from_field_12`: build a synthetic @BTEST line with `OP-XYZ` at position 12, parse, assert `BoardTestRecord.operator_id == "OP-XYZ"` AND `BoardLog.panel.operator_id == "OP-XYZ"` (per-panel propagation through `_make_board_log`).
- Add NEW test `test_make_board_log_uses_btest_operator_not_batch_operator`: build a BatchLog where `@BATCH.operator_id == "OP-BATCH"` but `@BTEST.operator_id == "OP-PANEL"`, parse, assert `panel.operator_id == "OP-PANEL"`.
- Add NEW test `test_parser_emits_no_batch_level_operator_note`: parse any valid log, assert `"operator_id is batch-level" not in any(report.notes)`.
- Run → all 4 new tests FAIL.

**Green:**
- Edit `src/flying_probe_copilot/parser/log_parser.py:207-228` `_parse_btest`:
  - Change `if len(fields) < 12` → `if len(fields) < 13`.
  - Extract `operator_id = fields[12]`.
  - Shift `status_qualifier` extraction: still `fields[10]`.
  - Shift `board_number` extraction: still `fields[11]`.
  - Change `parent_panel_id=fields[12] if len(fields) > 12 else None` → `parent_panel_id=fields[13] if len(fields) > 13 else None`.
  - Pass `operator_id=operator_id` to `BoardTestRecord(...)` constructor.
- Edit `_make_board_log` (L611-629): change `op_id = batch_rec.operator_id if batch_rec else "OP-001"` → `op_id = btest.operator_id`. Drop the `batch_rec` defensive fallback because BTEST is now the authoritative source (BTEST is always passed in — it's a positional arg).
- Edit L436-440: remove the `report.notes.append(...)` call about "operator_id is batch-level".
- Re-run → all 4 new tests + existing parser tests green.

**Refactor:** the `op_id` local in `_make_board_log` is now a single line. Inline if clearer.

### Step 5.6 — Ingest reads from `btest.operator_id`

**Red:**
- Update `tests/test_parser/test_ingest.py:401-405, 473-477` `BoardTestRecord(...)` literals to include `operator_id="OP-001"` kwarg.
- Add NEW test `test_multi_operator_run_distinct_operators_per_panel`:
  - Use `cli._build_batch_log` (or equivalent) to generate a 4-panel run with deterministic per-panel operators (`OP-001`, `OP-002`, `OP-003`, `OP-004`).
  - Write the run to a tmp_path (per existing conftest pattern).
  - Ingest via `ingest_run_directory`.
  - Query `SELECT panel_serial, operator_id FROM test_runs ORDER BY panel_serial`.
  - Assert `COUNT(DISTINCT operator_id) == 4`.
  - Assert each row's `operator_id` matches the generator's `PanelInstance.operator_id` for that serial.
  - Also assert `operators` dimension has 4 rows.
- Run → existing tests fail with ValidationError until literals updated; new test fails on the distinct-count assert (parser already returns per-panel after Step 5.5, but ingest still reads from `batch_log.batch.operator_id`).

**Green:**
- Edit `src/flying_probe_copilot/parser/ingest.py:287` — change `operator_id = batch_log.batch.operator_id` to `operator_id = btest.operator_id`.
- Re-run → all green.

**Refactor:** none.

### Step 5.7 — Schema flip + integrity test

**Red:**
- Add NEW test `tests/test_parser/test_schema.py::test_test_runs_operator_id_is_not_null`: introspect `test_runs` column metadata via `DESCRIBE test_runs` or `PRAGMA table_info`, assert the `operator_id` column has `NOT NULL` (or equivalent in DuckDB introspection — likely `null` column = false).
- Run → FAIL (column is currently nullable).

**Green:**
- Edit `src/flying_probe_copilot/db/schema.py:91` `_DDL_TEST_RUNS`: change `operator_id        VARCHAR,` → `operator_id        VARCHAR NOT NULL,`.
- Re-run schema test → pass.
- Run FULL parser+ingest suite → must remain green (operator_id is now non-NULL everywhere because of Step 5.6).

**Refactor:** Remove the `Per #WARNING-5: test_runs.operator_id is nullable...` comment at L13-14 of schema.py. Replace with a one-line note: `# test_runs.operator_id is NOT NULL — sourced per-panel from @BTEST.operator_id (Phase 2 2026-06-14).`

### Step 5.8 — Full-suite green gate

Run `uv run pytest -v` and `uv run pytest --cov=src --cov-report=term-missing`. Required:
- All tests pass (no skips, no xfail).
- Coverage on `src/flying_probe_copilot/generator/` ≥ 90%.
- Coverage on `src/flying_probe_copilot/parser/` ≥ 95%.
- Coverage on `src/flying_probe_copilot/db/schema.py` = 100%.

If coverage drops on a touched file, ADD the missing-line test before considering Step 5 done.

---

## 2. Test-naming standards (per `.claude/rules/testing.md`)

All new tests:
- `test_btest_record_requires_operator_id` (test_models.py)
- `test_build_batch_log_each_btest_uses_panel_operator` (test_cli_builder.py — new module)
- `test_btest_renders_operator_id_at_position_12` (test_renderers.py)
- `test_grammar_btest_requires_operator_id_field` (test_grammar.py)
- `test_parse_btest_extracts_operator_id_from_field_12` (test_log_parser.py)
- `test_make_board_log_uses_btest_operator_not_batch_operator` (test_log_parser.py)
- `test_parser_emits_no_batch_level_operator_note` (test_log_parser.py)
- `test_multi_operator_run_distinct_operators_per_panel` (test_ingest.py)
- `test_test_runs_operator_id_is_not_null` (test_schema.py)

Total: 9 new tests.

---

## 3. Verification checklist for Step 6 (Verify Execution sub-agent)

The verify sub-agent must answer YES/NO with file:line evidence:

- [ ] `models.py` `BoardTestRecord` has `operator_id: str` with no default, between `board_number` and `parent_panel_id`.
- [ ] `cli.py` BoardTestRecord construction uses `operator_id=panel.operator_id`.
- [ ] `log.py::_render_btest` inserts `btr.operator_id` BETWEEN `str(btr.board_number)` and the parent_panel_id append.
- [ ] `grammar.py::_BTEST` regex has exactly one `\|{_FIELD}` between board_number and the optional parent_panel_id group.
- [ ] `log_parser.py::_parse_btest` extracts `operator_id` from `fields[12]`, has min-field check `< 13`, and shifts `parent_panel_id` to `fields[13]`.
- [ ] `log_parser.py::_make_board_log` uses `btest.operator_id`, NOT `batch_rec.operator_id`.
- [ ] `log_parser.py` no longer appends the "operator_id is batch-level" note.
- [ ] `ingest.py:287` reads `btest.operator_id`, NOT `batch_log.batch.operator_id`.
- [ ] `schema.py:91` declares `operator_id VARCHAR NOT NULL`.
- [ ] All 9 new tests exist and pass.
- [ ] All pre-existing tests in `tests/test_generator/`, `tests/test_parser/` pass.
- [ ] Coverage gates hold.
- [ ] No edits to `pyproject.toml`, `.claude/settings.json`, `.env.example`, `migrations/`.
- [ ] No new dependencies in `pyproject.toml`.
- [ ] No mid-session commits in `git log`.

---

## 4. Risks / pre-mitigations

- **Risk:** test_renderers.py `fields[2] == "4"` positional assertion. **Mitigation:** locked field position is AFTER status (index 1 in @BTEST positional), so `fields[2]` (which is start_ts) is unaffected. No edit needed beyond the fixture kwarg.
- **Risk:** test_lexical_compliance.py manual BoardTestRecord construction. **Mitigation:** Step 5.4 RED includes the kwarg update; lexical compliance runs the grammar over real CLI output → will exercise the renderer + grammar update.
- **Risk:** schema flip lands while ingest still produces NULLs. **Mitigation:** ordering — Step 5.6 (ingest fix) lands BEFORE Step 5.7 (schema flip). Step 5.7's full-suite green gate verifies no test produces a NULL operator_id under the new schema.
- **Risk:** existing `data/db/sample.duckdb` was ingested under old nullable schema. **Mitigation:** out-of-scope per the brief; manual-QA script documents the regenerate command.
- **Risk:** Bugbot or PR review catches an existing helper that emits hardcoded 12-field @BTEST. **Mitigation:** explore subagent surfaced the touchpoints; Step 5.4 RED enumerates each one.

---

## 5. Owner go-ahead gate

**This plan must receive owner sign-off before Step 5 (execution) starts.** The Step 4 red-team sub-agent will run next; any BLOCKERs become a Revision 1 section; then the owner reviews + says "go ahead" (or "stop / change X").

Until then, no edits to `src/` or `data/`.

---

## 6. Revision 1 — Red-team findings resolved (2026-06-14)

Red-team sub-agent surfaced **3 BLOCKERs / 4 WARNINGs / 6 MINORs**. Resolutions below; the plan stays Medium-tier; final test count rises from 9 → **11 new tests** plus a bulk-update step.

### BLOCKER B1 — 17+ hardcoded `@BTEST` string literals in `tests/test_parser/test_log_parser.py`

Step 5.5 RED expands: BEFORE updating the `BoardTestRecord(...)` constructor literals at L287/L353/L424, ALSO update every raw `"{@BTEST|..."` string literal in `tests/test_parser/test_log_parser.py`, `tests/test_parser/test_malformed.py`, and `tests/test_parser/test_yield_query.py`. Mandatory commands the exec sub-agent must run:

```bash
uv run python -c "import pathlib, re; \
  files = pathlib.Path('tests/test_parser').rglob('*.py'); \
  hits = [(str(p), i+1, l.rstrip()) for p in files for i, l in enumerate(p.read_text().splitlines()) if '@BTEST|' in l]; \
  [print(f'{p}:{ln} {l}') for p, ln, l in hits]"
```

Output is the working set. Each line must be updated to the 13-field form, inserting the new `operator_id` value between the `board_number` field (currently the last mandatory field) and the optional `parent_panel_id` field. The literal value used in test strings is `OP-001` unless the test specifically needs a distinct operator.

### BLOCKER B2 — `test_parse_btest_too_few_fields_produces_error` is now a false-positive

`tests/test_parser/test_log_parser.py:833-844` asserts on the OLD 12-field boundary. After the min-field check flips to `< 13`, the existing 2-field test still passes but does NOT exercise the new boundary. Plan Step 5.5 RED adds a NEW test:

- `test_parse_btest_12_field_old_format_is_rejected` — feed a 12-field @BTEST (the OLD valid format, no operator_id) to `_parse_btest`, assert `ParseError` is recorded in `ParseReport.errors`.

Plus the existing test's docstring updates from "fewer than 12 fields" → "fewer than 13 fields". The 2-field test stays as a defence-in-depth gate.

**Test count update:** +1 → 10 new tests.

### BLOCKER B3 — `tests/test_parser/test_yield_query.py:185-188` writes `operator_id=NULL` directly

Direct `INSERT INTO test_runs (..., operator_id, ...) VALUES (..., NULL, ...)`. After Step 5.7 schema flip, this fixture raises on insert and kills the canonical yield-query exit-criterion test from Phase 1b.

Add `tests/test_parser/test_yield_query.py` to the in-scope files (Section 0 table). Step 5.5 RED bulk-update step extends to it: replace `NULL` with `'OP-001'` in the fixture INSERT. If the fixture deliberately exercises NULL semantics (it doesn't — yield query doesn't read operator_id), keep the constant.

### WARNING W1 — `batch_rec` becomes an unused parameter in `_make_board_log`

Step 5.5 GREEN extends: after switching to `btest.operator_id`, drop `batch_rec` from `_make_board_log`'s signature AND from both call sites in `log_parser.py` (the in-loop flush at L451-456 and the trailing flush at L584-588). Lint clean, no `# noqa` band-aid.

### WARNING W2 — `DESCRIBE test_runs` introspection must be locked

Step 5.7 RED test `test_test_runs_operator_id_is_not_null` is locked to this exact query:

```python
rows = con.execute("DESCRIBE test_runs").fetchall()
operator_row = next(r for r in rows if r[0] == "operator_id")
# DuckDB DESCRIBE columns: (column_name, column_type, null, key, default, extra)
assert operator_row[2] == "NO", f"operator_id must be NOT NULL, got null={operator_row[2]!r}"
```

No `PRAGMA table_info` fallback. The 6-column DESCRIBE layout (index 2 = null) is the contract.

### WARNING W3 — `test_log_parser.py:91` stale `batch.operator_id` assertion

This test asserts `parsed.batch.operator_id == small_batch_log.batch.operator_id`. After the change, `@BATCH.operator_id` is still `boards[0].panel.operator_id` (unchanged generator behaviour), so the assertion still passes for single-operator fixtures. Leave the assertion. ADD a docstring line above it:

```python
# @BATCH.operator_id is a batch-level summary, not per-panel — per-panel
# operator is sourced from @BTEST.operator_id; see DECISION_LOG 2026-06-14.
```

No new test required; no semantic change.

### WARNING W4 — `_FIELD` regex accepts empty string; mandatory `operator_id` could pass grammar with empty value

Step 5.1 GREEN extends: `BoardTestRecord.operator_id` is declared as `operator_id: str = Field(min_length=1)` (Pydantic v2). Imports: add `Field` to the `from pydantic import ...` line at `models.py:17`.

Step 5.1 RED adds a NEW test:
- `test_btest_record_operator_id_rejects_empty_string` — `BoardTestRecord(..., operator_id="")` raises `pydantic.ValidationError`.

Grammar (`_FIELD` = `[^|{}\r\n]*`) stays as-is — defence-in-depth lives at the model layer; updating the regex would also break the renderer's empty-`status_qualifier` slot.

**Test count update:** +1 → 11 new tests.

### MINOR M2 — `test_lexical_compliance.py:79-86` wording

Plan Section 0 row for `test_lexical_compliance.py` updates: drop the conditional "but only if it's not built via the actual CLI helper (cross-check)". The literal is direct — definitive instruction: ADD `operator_id="OP-001"` kwarg.

### MINOR M3 — BUG_LOG has no existing entry to close

Plan Section 0 row for `BUG_LOG.md` updates: instead of "closing entry", create a NEW entry `BUG-009: test_runs.operator_id was always batch-level (per-panel operator-id lost in per-board logs)` with status "Resolved 2026-06-14 — fixed in `feature/per-panel-operator`". Captures the deferred-from-Phase-1b data-degradation as a historical bug record.

### MINOR M1 / M4 / M5 / M6 — already resolved by the original plan

No further action.

---

## 7. Final verification checklist (supersedes Section 3)

The verify sub-agent at Step 6 must answer YES/NO with file:line evidence:

- [ ] `models.py` `BoardTestRecord` has `operator_id: str = Field(min_length=1)` between `board_number` and `parent_panel_id`, with `Field` imported.
- [ ] `cli.py` BoardTestRecord construction uses `operator_id=panel.operator_id`.
- [ ] `log.py::_render_btest` inserts `btr.operator_id` BETWEEN `str(btr.board_number)` and the parent_panel_id append.
- [ ] `grammar.py::_BTEST` regex has exactly one `\|{_FIELD}` between board_number and the optional parent_panel_id group.
- [ ] `log_parser.py::_parse_btest` extracts `operator_id` from `fields[12]`, has min-field check `< 13`, shifts `parent_panel_id` to `fields[13]`, passes `operator_id=...` to `BoardTestRecord(...)`.
- [ ] `log_parser.py::_make_board_log` uses `btest.operator_id`, has **no `batch_rec` parameter**, no `OP-001` fallback. Both call-sites updated.
- [ ] `log_parser.py` no longer appends the "operator_id is batch-level" note.
- [ ] `ingest.py:287` reads `btest.operator_id`, NOT `batch_log.batch.operator_id`.
- [ ] `schema.py:91` declares `operator_id VARCHAR NOT NULL`; the `#WARNING-5: nullable` comment is gone.
- [ ] All 11 new tests exist and pass:
  - `test_btest_record_requires_operator_id`
  - `test_btest_record_operator_id_rejects_empty_string`
  - `test_build_batch_log_each_btest_uses_panel_operator`
  - `test_btest_renders_operator_id_at_position_12`
  - `test_grammar_btest_requires_operator_id_field`
  - `test_parse_btest_extracts_operator_id_from_field_12`
  - `test_parse_btest_12_field_old_format_is_rejected`
  - `test_make_board_log_uses_btest_operator_not_batch_operator`
  - `test_parser_emits_no_batch_level_operator_note`
  - `test_multi_operator_run_distinct_operators_per_panel`
  - `test_test_runs_operator_id_is_not_null`
- [ ] Every pre-existing `@BTEST|` literal in `tests/test_parser/` updated to 13/14-field form (script-verified zero remaining 12-field literals).
- [ ] `tests/test_parser/test_yield_query.py:185-188` writes `'OP-001'`, not `NULL`.
- [ ] All pre-existing tests in `tests/test_generator/`, `tests/test_parser/` pass.
- [ ] Coverage gates hold (generator ≥90%, parser ≥95%, schema = 100%).
- [ ] No edits to `pyproject.toml`, `.claude/settings.json`, `.env.example`, `migrations/`.
- [ ] No mid-session commits in `git log feature/per-panel-operator`.

---

## 8. Owner go-ahead gate (Revision 1)

Plan is ready. Awaiting owner explicit "go ahead" before Step 5 execution kicks off.

Per session-workflow Step 4b: until owner says "go", no edits land in `src/` or `tests/`.
