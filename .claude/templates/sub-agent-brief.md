# Sub-agent context brief — template

> The PARENT fills this in ONCE at the start of a session (after Step 1).
> Then pastes the filled brief at the top of EVERY sub-agent dispatch (Explore, Verify Plan, Exec, Verify Exec).
> Goal: sub-agents skip reading CLAUDE.md, agent-conduct, and phase docs from cold — saves ~3-5k tokens per dispatch
> AND the identical prefix benefits from Anthropic prompt caching across sub-agents in the same 5-minute window.

---

## Template (copy into the session brief, then reuse verbatim)

```
=== FLYING-PROBE CONTEXT BRIEF — fill once, reuse per sub-agent ===

PHASE:          [0 / 1a / 1b / 2 / 3 / 4]
PHASE GOAL:     [one-line from ROADMAP.md, e.g. "HP3070 synthetic log generator"]
SESSION TIER:   [trivial / small / medium / large]  ← see .claude/templates/tiering.md
BRANCH:         feature/[short-name]
SESSION BRIEF:  docs/plans/YYYY-MM-DD-brief.md
PLAN:           docs/plans/YYYY-MM-DD-plan.md   (omit if pre-Step-3)

HARD GUARDRAILS IN FORCE (do not violate, do not ask):
- No real customer log data in this repo, ever.
- No IPC / J-STD / Keysight verbatim text. Summaries + citations only.
- All test data is synthetic.
- API keys never committed.
- Approval-gated files (no edit without explicit owner sign-off this session):
  pyproject.toml, src/flying_probe_copilot/db/schema.py, migrations/*,
  .claude/settings.json, .env.example
- Branch rule: never commit to main or dev. Feature branches only.
- TDD mandatory: red → green → refactor. No implementation without a failing test.

DECISIONS IN FORCE (relevant to this session):
- [paste 1-3 lines from DECISION_LOG.md that bound this work]
- e.g. "Generator targets HP3070 i3070 format first; other ATE formats deferred."
- e.g. "DuckDB schema column names use snake_case."

OUT OF SCOPE THIS SESSION:
- [verbatim list from the session brief OUT-OF-SCOPE block]

FIXTURES / FILES TO LEAVE ALONE:
- [paths the sub-agent should NOT touch even if tempted]

OPEN QUESTIONS (resolved by owner — do not re-ask):
- [Q + answer, if any were resolved during Step 1]

=== END BRIEF — your sub-agent role instructions follow below ===
```

---

## Why this works

1. **Context savings.** Each sub-agent would otherwise read CLAUDE.md (~150 lines) + agent-conduct.md (~80 lines) + the relevant phase doc to learn the rules. With this brief at the top, they skip those reads unless they need a specific detail. Estimated savings: 3-5k input tokens per dispatch, or 12-20k across a full 4-sub-agent loop.

2. **Prompt-cache friendly.** Anthropic prompt caching keys on identical token prefixes. If the brief is *byte-for-byte the same* across the Explore / Verify-Plan / Exec / Verify-Exec calls within a 5-minute window, the prefix hits cache and only the role-specific tail is freshly billed. (See `.claude/templates/prompt-caching.md` for the full mechanics.)

3. **Single source of truth.** When the parent updates the brief (e.g. an open question is resolved), every subsequent sub-agent sees the updated state. No more "Explore returned with answer X but Exec didn't know."

---

## Usage in the parent's sub-agent dispatch

Compose every sub-agent prompt like this:

```
[paste filled CONTEXT BRIEF verbatim]

[then the role-specific charter for this sub-agent, e.g. for Explore:]
ROLE: Read-only context scout. Return What/Why/Where/When/Tests-Exist/...
TASK: For the plan in docs/plans/YYYY-MM-DD-brief.md, map the codebase touch points.
RETURN: [structured fields per session-workflow Step 2]
```

Keep the brief block IDENTICAL across the four sub-agent calls in one session. Edits to the brief between calls break the cache hit.

---

## What NOT to put in the brief

- Recent file edits or diffs (they change between sub-agent calls → cache miss)
- Test output (varies → cache miss)
- Long verbatim copies of CLAUDE.md (defeats the savings)
- Anything the sub-agent will need to re-derive anyway (just point to the file)

The brief is **stable** session-scoped context. Anything volatile lives in the role-specific tail.
