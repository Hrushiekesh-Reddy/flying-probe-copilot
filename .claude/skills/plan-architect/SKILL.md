# Skill: plan-architect

> Invoke: `/plan-architect`
> Use before any non-trivial implementation. Produces a complete plan so execute-plan never has to guess.

---

## When to use

- Before writing any new module or function
- Before modifying a file that touches multiple downstream consumers
- Any task that touches >2 files or >5 steps
- When the approach is unclear

## When NOT to use

- Doc-only edits, typo fixes, single-line changes
- When a plan already exists and was approved this session

---

## Step 1 — Context scout (spawn Explore subagent)

Before designing anything, read:
- `CLAUDE.md` — current phase and guardrails
- `docs/ROADMAP.md` — exact deliverable you're implementing
- `docs/logs/DECISION_LOG.md` — decisions that constrain the design
- `docs/logs/SESSION_LOG.md` — what was done last session
- `specs/` — relevant spec file for this phase
- Any existing source files in the module being extended

Scout output (internal — not shown to owner unless asked):
- List of files to create or modify
- Existing patterns to match
- Existing tests to not break
- Open questions that need design decisions

---

## Step 2 — Define Goal Contract

State these four things explicitly:

```
OBJECTIVE:    One sentence — what this plan delivers.
SUCCESS-WHEN: Measurable exit criteria (test names, CLI outputs, query results).
OUT-OF-SCOPE: What this plan explicitly does NOT do.
CONSTRAINTS:  Phase rule, critical files, test-first, no new deps without approval.
```

---

## Step 3 — What / Why / Where table

For every file that will change:

| File | What changes | Why (which deliverable) | Test file |
|------|-------------|------------------------|-----------|
| `src/.../module.py` | New function `parse_header()` | ROADMAP Phase 1b — parser ingests generator output | `tests/test_parser/test_log_parser.py` |

---

## Step 4 — Ordered execution steps

Number every step. One action per step (one file, one function, one test).

```
1. Write test: tests/test_parser/test_log_parser.py::test_parse_header_valid_input
2. Run pytest — confirm RED
3. Implement: src/flying_probe_copilot/parser/log_parser.py::parse_header()
4. Run pytest — confirm GREEN
5. Write test: test_parse_header_malformed_input_raises_ParseError
6. Run pytest — confirm RED
7. Implement error path in parse_header()
8. Run pytest — confirm GREEN
...
```

Steps must be TDD-ordered: test → red → implement → green → next test.

---

## Step 5 — Guardrails block

Every plan must end with:

```
GUARDRAILS:
- Branch: feature/[name] (not dev, not main)
- Critical file check: [list any approval-gated files this plan touches]
- New dependencies: [none / list + require owner approval]
- Phase discipline: [confirm this is Phase X work only]
- Docs to update: SESSION_LOG, DECISION_LOG (if decisions), ROADMAP (if deliverable done)
```

---

## Step 6 — Present to owner

Show the owner:
1. Goal Contract (4 items)
2. What/Why/Where table
3. Ordered steps (numbered)
4. Guardrails block

**Do not start executing until the owner says "go ahead" or equivalent.**

---

## Output artifact

Save the plan as `docs/plans/YYYY-MM-DD-[short-name].md` before executing.
Reference this file from `AGENT_HANDOFF_LOG.md` if handing off mid-session.
