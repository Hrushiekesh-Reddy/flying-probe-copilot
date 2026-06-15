## Session Brief — 2026-06-14 (Phase 2 kickoff — per-panel operator-id repair)

### What the owner wants
> "Phase 1b shipped on 2026-06-14 with `test_runs.operator_id` declared NULLABLE because per-panel operator recovery is currently impossible from per-board .log files alone. … Recommendation: OPTION A — pick this up as the first Phase 2 task before any analytics work, since per-operator-yield queries are a likely Phase 2 dashboard requirement."

First Phase 2 task. Repair the per-panel operator-id round-trip end-to-end (generator → log file → parser → DuckDB) by adding `operator_id` to the `@BTEST` record, then flip the schema column to `VARCHAR NOT NULL`. Phase 2 analytics, Streamlit, and any new dashboards stay out of this session.

### Goal statement (one sentence)
Extend the `@BTEST` record schema with a mandatory per-panel `operator_id` field so that each per-board `.log` file carries its panel's true operator (not the batch's first-panel operator), wire it end-to-end through the generator, grammar, renderer, parser, and ingest layer, and flip `test_runs.operator_id` to `VARCHAR NOT NULL` with a regression test proving multi-operator runs ingest with per-panel-distinct operators.

### Success looks like
Measurable, observable outcomes that must all be true at end of session:

1. **`BoardTestRecord` carries `operator_id`** — `src/flying_probe_copilot/generator/models.py` adds a mandatory `operator_id: str` field to `BoardTestRecord`. No default; no `None`. Pydantic v2 `extra="forbid"` semantics preserved.
2. **Generator wires it correctly** — `src/flying_probe_copilot/generator/cli.py` constructs each `BoardTestRecord` with `operator_id=panel.operator_id` (the panel's true operator, not `boards[0].panel.operator_id`). The line-140 `boards[0]` hack disappears from the `@BATCH.operator_id` site as well (we set @BATCH operator_id to a fixed batch operator or to `boards[0]` if needed — but `@BTEST.operator_id` is now the source of truth for per-panel operator recovery).
3. **Renderer emits the new field** — `src/flying_probe_copilot/generator/renderers/log.py::_render_btest` emits `operator_id` at its fixed positional slot. Field is never empty (mandatory).
4. **Grammar regex accepts and validates the new field** — `src/flying_probe_copilot/generator/grammar.py::_BTEST` updated. Lexical-compliance tests still pass for all three profiles.
5. **Parser recovers it from `@BTEST`** — `src/flying_probe_copilot/parser/log_parser.py::_parse_btest` extracts `operator_id` from the `@BTEST` field positions; `_make_board_log` builds `PanelInstance.operator_id` from the BTEST value, NOT from `batch_rec.operator_id`. The "operator_id is batch-level" note in the parser is removed.
6. **Schema flip** — `src/flying_probe_copilot/db/schema.py` declares `test_runs.operator_id VARCHAR NOT NULL`. This file is approval-gated; brief assumes go-ahead.
7. **Ingest enforces it** — `src/flying_probe_copilot/parser/ingest.py` writes the per-panel operator into each `test_runs` row. Each `operator_id` seen lands in the `operators` dimension (unchanged behaviour, but data now varies per row).
8. **Multi-operator regression test** — `tests/test_parser/test_ingest.py` (or a new module) adds a test that generates a multi-panel run with distinct operators, ingests it, queries `test_runs.operator_id`, and asserts `COUNT(DISTINCT operator_id) > 1` and each panel's `operator_id` matches the generator's `PanelInstance.operator_id`.
9. **Round-trip stays green** — every existing parser/generator/grammar/renderer test passes. The roundtrip test passes (counts + key sums unchanged).
10. **Test suite gates** — full `uv run pytest -v` passes; coverage on touched files holds at ≥95% (parser) / ≥90% (generator) — no coverage regression on `src/flying_probe_copilot/generator/` or `src/flying_probe_copilot/parser/`.
11. **DECISION_LOG closed** — the 2026-06-14 "test_runs.operator_id nullable; per-panel operator recovery deferred to Phase 2" entry gets a "**Resolved 2026-06-14:** Option A landed via `feature/per-panel-operator`" footnote linked to the new commit and this brief.
12. **Docs ticked** — ROADMAP.md gets a new Phase 2 line entry capturing this as the first task; SESSION_LOG entry added; CLAUDE.md session-log line updated; BUG_LOG.md gets a closing entry for the deferred-data degradation.

### Out of scope (explicit — do NOT do this session)
- **Analytics functions** (yield-over-time helper, Pareto, SPC, anomaly detection). Later Phase 2.
- **Streamlit UI** of any kind. Later Phase 2.
- **`notebooks/01-queries.ipynb`** edits beyond fixing the per-operator-yield caveat note. The notebook's `data/db/sample.duckdb` will need re-ingestion under the new schema, but the notebook code itself shouldn't need structural changes.
- **`@BATCH.operator_id` semantics change** — keep `@BATCH.operator_id` as-is (batch-level summary; can remain the first-board panel's operator or be set to a constant batch operator). The source of truth for per-panel operator is `@BTEST.operator_id`; `@BATCH.operator_id` is no longer the parser's source.
- **Migration framework** — no migration files. Phase 1b's `CREATE TABLE IF NOT EXISTS` strategy continues; the schema flip is a one-shot change that requires re-ingesting any existing DuckDB file.
- **CSV / JSON renderer changes** — these output formats already carry per-panel `operator_id` via `PanelInstance`; no edit required.
- **ChromaDB / sentence-transformers / BM25 / Gemini.** Phase 3.
- **Re-ingesting `data/db/sample.duckdb`** under the new schema — the file is gitignored, owner-recreatable; we'll document the regenerate command in the manual-QA script but won't ship a new sample.duckdb.
- **`uv add` / new dependencies.** None required.
- **`@BTEST` `parent_panel_id` reordering or removal.** Stays optional, stays at the trailing position.

### Phase / milestone
ROADMAP Phase 2 — Analytics & Dashboard (lines 71-88). First sub-task: clear the per-panel operator-id data-degradation blocker before any analytics depends on it. The DECISION_LOG entry "2026-06-14 — Phase 1b: test_runs.operator_id nullable; per-panel operator recovery deferred to Phase 2" (lines 42-60) names this exact decision and explicitly says "Revisit: Phase 2 first session. Decide whether to extend `@BTEST` (generator change) or to ingest `results.json` as an authorized sidecar." Owner picks Option A.

### Branch
`feature/per-panel-operator` — created from `dev` at the top of this session (per agent-conduct.md "never commit directly to dev/main"). Working tree confirmed clean before branching. `dev` tip is `ac13c7e Merge pull request #9` plus the BUG-008 transaction wrap.

### Tier
**Medium** — touches generator (models, cli, renderer, grammar) + parser (log_parser, ingest) + approval-gated schema (`db/schema.py`) + new tests on both sides. Justifies the full 10-step loop. Not Large because no new top-level module and no new CLI — every edit is within existing files.

### Critical / approval-gated files this session may touch
Per `.claude/rules/agent-conduct.md`:

| File | Status | Action |
|------|--------|--------|
| `src/flying_probe_copilot/db/schema.py` | approval-gated | Flip `test_runs.operator_id` to `VARCHAR NOT NULL`. **Owner sign-off granted via the brief.** |
| `pyproject.toml` | approval-gated | Not touched — no new dependencies, no script changes. |
| `migrations/` | approval-gated | Not touched. |
| `.claude/settings.json` | approval-gated | Not touched. |
| `.env.example` | approval-gated | Not touched. |

### Guardrails reaffirmed for this session
- TDD: Red → Green → Refactor per test, no implementation without a failing test first (`.claude/rules/testing.md`).
- Phase 2 + Phase 1b in the same session ONLY because this task closes a deferred-from-Phase-1b decision; new Phase 2 analytics work goes in a separate session.
- One coherent commit at Step 8 (not mid-session).
- Out-of-scope bugs → `BUG_LOG.md` + spawn_task chip at Step 8, never silently fixed.
- No push without explicit owner request.
- @BTEST field positional contract: `operator_id` insertion point will be locked in Step 3 (plan). Default working assumption: insert as a new mandatory field between `board_number` (current field 12) and `parent_panel_id` (currently optional 13th). Final position is a Step 3 decision.

### Risks called out for the red-team
- **Field-positional vs named risk:** inserting `operator_id` in the middle of `@BTEST` field positions shifts `parent_panel_id`'s index. Any test that hand-asserts byte content of an @BTEST line will break unless updated.
- **Lexical compliance tests:** `tests/test_generator/test_lexical_compliance.py` runs the grammar over real CLI block-generation output. Both grammar regex AND renderer must agree on the new field count.
- **Roundtrip integrity test:** `tests/test_parser/test_roundtrip.py` asserts counts + key sums. The `operator_id` round-trip is a new assertion; existing assertions should hold (count + ts).
- **Existing `data/db/sample.duckdb`:** under the OLD schema. Re-running the notebook's setup cell against it would fail (operator_id column allows NULL there; new code expects NOT NULL). Phase 2 dashboard work depends on a re-ingested DB. Document the regen command in manual-QA.
- **Schema flip vs ingest order:** schema flip must land BEFORE the ingest code that produces non-NULL `operator_id`, OR ingest must be updated first to produce non-NULL values BEFORE the flip — pick an order that avoids any in-between state where tests fail.
- **`@BATCH.operator_id` ambiguity:** keep emitting per the existing rule (`boards[0].panel.operator_id` is fine — but call it out in code, not just a code comment). Or set it to a fixed batch operator. Either way, the parser MUST stop using `batch_rec.operator_id` as the panel operator source.

End of brief.
