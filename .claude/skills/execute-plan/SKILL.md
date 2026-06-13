# Skill: execute-plan

> Invoke: `/execute-plan`
> Use AFTER owner has approved a plan from `/plan-architect`.
> Implements faithfully, TDD-first, with no scope drift.

---

## Before starting

1. Confirm a plan document exists in `docs/plans/` for this session.
2. Confirm you are on the correct feature branch (not `dev` or `main`).
3. Read the plan's Goal Contract — especially OUT-OF-SCOPE.
4. Check the Guardrails block — any approval-gated files? Any new deps?
5. Confirm tests are written (from `/test-generator`) and currently RED.

If tests are not yet written: STOP. Run `/test-generator` first.

---

## Execution rules

### TDD order — mandatory

For every step in the plan:
1. Run `uv run pytest [specific test]` — confirm it is RED.
2. Write the minimum implementation to make it GREEN.
3. Run `uv run pytest [specific test]` — confirm GREEN.
4. Refactor if needed — confirm still GREEN.
5. Move to next step.

**Never write implementation code without a failing test to justify it.**

### Scope discipline

- Implement ONLY what the plan says.
- If you discover something out-of-scope that needs fixing: `spawn_task` chip. Do not fix silently.
- If a plan step is blocked or impossible: STOP. Report to owner with specific reason.

### Code quality

- Match the style of surrounding code.
- No commented-out code.
- No TODO comments without a `BUG_LOG.md` entry.
- No new dependencies without explicit owner approval.

### Critical file gate

If any step touches an approval-gated file (`pyproject.toml`, schema files, migration files,
`.claude/settings.json`, `.env.example`) — STOP and ask for explicit sign-off before proceeding.

---

## Tracking deviations

If you deviate from the plan (even slightly), log it:
```
DEVIATION from plan step N:
  Planned: ...
  Actual: ...
  Reason: ...
```
Include this in the implementation report.

---

## Implementation report (Step 8 of session workflow)

After all steps are done, produce a brief report:

```
## Implementation Report — YYYY-MM-DD

### What changed
- File: src/.../module.py — Added function parse_header() (lines 45-72)
- File: tests/test_parser/test_log_parser.py — 4 new tests (all GREEN)

### What was NOT changed (and why)
- src/.../other_module.py — Out of scope for this plan

### Test results
- Tests passing: 4 new + N existing
- Tests failing: 0
- Coverage delta: +3.2%

### Deviations from plan
- None / [list if any]

### Docs to update (session-end ritual)
- [ ] SESSION_LOG.md
- [ ] DECISION_LOG.md (if decisions were made)
- [ ] ROADMAP.md (tick deliverable if done)
```

---

## If a step fails

1. Do not skip to the next step.
2. Do not change the test to make it pass.
3. Diagnose: read the error output carefully. Check: wrong import? Wrong return type? Wrong fixture?
4. If stuck >15 min: invoke `/diagnose` before trying another approach.
5. If the plan itself is wrong: STOP. Report to owner. Do not improvise a new design mid-execution.
