# Learning Log & Lessons Learned

Full session log lives in `CLAUDE.md` (session log section). This file captures the *insights* and *patterns* worth keeping, not the raw timeline.

---

## Multi-IDE Workflow Pattern

**What it is**: Claude Code (explore/plan/debug/doc) + Cursor (primary builder) sharing `CLAUDE.md` as a memory bridge.

**Why it works**: Each tool plays to its strength. Claude Code's 10-step workflow loop catches design flaws before Cursor writes code. Cursor's autocomplete accelerates mechanical implementation.

**Key insight**: Always start a session by pointing your IDE at `CLAUDE.md` — without it, context drifts and you redo design work.

---

## The 12-Step Session Workflow

Sessions run as a structured loop:
1. Read `CLAUDE.md` + relevant phase doc
2. Explore (spawn 2-5 subagents for research)
3. Plan (subagent returns step-by-step)
4. Generate test cases (before writing code)
5. Verify plan (adversarial red-team, 2-3 skeptics)
6. Decision gate (owner ratifies key choices)
7. Execute (write code against failing tests)
8. Independent verify (subagent reads output cold)
9. Triple-check (CLEAN = ship, FAIL = loop back)
10. Docs + commit

**Why it matters**: Step 5 adversarial review caught 7 BLOCKERs in Phase 2 slice 1 before any code was written. Prevented notebook-canonical-SQL divergences that would have produced wrong-data analytics.

---

## Lessons by Session

### 2026-06-13 — Synthetic Generator
- **Hook path bug**: `.claude/settings.json` with relative paths for hooks breaks when cwd drifts into a subdirectory (e.g., `cd notebooks/`). Always use absolute paths via `${CLAUDE_PROJECT_DIR}/.claude/hooks/<file>.py`.
- **Format research**: Don't assume log format — research public sources first. The Virinco public mirror had the authoritative Keysight Log Record Format, which was more detailed than expected.

### 2026-06-14 — Parser & DuckDB
- **Generator → parser contract**: The `@BTEST` record's field positions were brittle. Adding `operator_id` at field 12 later (BUG-007) required a mechanical mirror through models → CLI → renderer → grammar → parser → ingest. Document field positions explicitly.
- **BUG-007 lesson**: Silent wrong data (placeholder `"A"` for shift, `"LINE-A"` for line) is worse than null — nullability checks wouldn't have caught it. The placeholder-fields marker pattern was added to make it visible.
- **Notebook smoke-testing**: Always run notebook cells against a real (even tiny) DB, not mocked data. Query 3 and Query 4 had caveat notes that were only closed after BUG-007 was fixed.

### 2026-06-16 — Analytics Foundation
- **SPC sigma formula**: Use `MR̄ / 1.128`, **never** sample stdev (`std(ddof=1)`). Western Electric/Nelson rules were designed for X-bar charts, not individuals charts. Using them on individual measurements produces excessive false positives. See [[ADRs#ADR-007]].
- **Leave-one-out z-score**: When computing anomaly z-scores, exclude the group being scored from the baseline mean+std. Otherwise a large anomalous group pulls the baseline toward itself and hides the anomaly.
- **Ordering contract matters**: `yield_over_time` returns `group_key ASC` universally. This diverges from notebook Q4 ordering. Document the divergence explicitly (it was a BLOCKER caught in Step 5 review).

### 2026-06-18 — SPC + Anomaly
- **refdes lives on `components` not `measurements`**: The SPC `individuals_chart` function groups by `(board_profile_id, refdes)`. `refdes` is on the `components` dimension table, not on `measurements`. Query requires a JOIN. A subagent caught this before execution.
- **1 peer edge case in z-score**: When a group has only 1 other group in the baseline, `std(ddof=1)` raises (can't compute std with 0 degrees of freedom). Guard this case explicitly.

---

## Common Gotchas

1. **Hook paths**: Always absolute (`${CLAUDE_PROJECT_DIR}/...`), never relative
2. **SPC sigma**: `MR̄ / 1.128` only — sample stdev is wrong for XmR
3. **DuckDB `*.duckdb` files**: These are gitignored — don't rely on them being present in fresh clones, regenerate from synthetic data
4. **BUG-011 flaky test**: Pre-existing flaky parser test — if a test run shows 1 unexpected failure, check this first before panicking
5. **`@BTEST` field positions**: Fields are positional (pipe-delimited). If you add a field, update models → CLI → renderer → grammar → parser → ingest — all 6 layers
6. **Session scope rule**: One phase per session. If you're in Phase 2, do not start writing RAG code — park ideas in `docs/DECISIONS.md`

---

## Architecture Evolution

### BUG-007: From placeholder to real data
- **Original**: `shift = "A"`, `line_id = "LINE-A"` were hardcoded placeholders in `_make_board_log`
- **Problem**: All per-shift and per-line analytics were silently computing against wrong data
- **Fix (Path A)**: Extend `@BTEST` with mandatory `shift` (field 13) and `line_id` (field 14); read from `btest.shift` / `btest.line_id` in the log builder
- **Prevention**: The placeholder-fields marker pattern (since cleaned up after BUG-007 closed)

### placeholder_fields marker pattern (ADDED then REMOVED)
- Added in Phase 2 slice 1: `placeholder_fields: tuple[str, ...]` on dataclasses to make BUG-007-affected columns visible
- Removed in 2026-06-18 after BUG-007 fully closed — it served its purpose and became dead weight
- **Lesson**: Temporary scaffolding is fine if you clean it up promptly with a proper DECISION_LOG entry

---

**Tags:** #learning #lessons #decisions #spc #gotchas
