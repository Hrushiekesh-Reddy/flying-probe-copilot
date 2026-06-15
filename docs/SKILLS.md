# Skills Registry — flying-probe-copilot

Custom Claude Code skills available in this project.
Skills live in `.claude/skills/[skill-name]/SKILL.md`.
Invoke with `/skill-name` in Claude Code.

**Start here:** `/skill-sergeant` is the routing brain — use it when unsure which skill to invoke.

---

## Skill roster

| Skill | Invoke | When to use |
|-------|--------|-------------|
| `skill-sergeant` | `/skill-sergeant` | **Start here.** Routes to the right skill. Handles gray zones. Manages don't-use lists. |
| `plan-architect` | `/plan-architect` | Before any non-trivial implementation. Plan first, build second. |
| `execute-plan` | `/execute-plan` | After owner approves a plan. TDD-first implementation. |
| `test-generator` | `/test-generator` | Write failing test stubs before implementation (RED phase). |
| `session-workflow` | `/session-workflow` | Full 12-step pipeline for complex multi-file tasks. |
| `architecture-refactor` | `/architecture-refactor` | Break up a god-file / shallow module into deep modules behind a clean interface, one reviewable chunk at a time. |
| `diagnose` | `/diagnose` | Root-cause analysis when something is broken. Read evidence, trace cause. |
| `deep-research` | `/deep-research` | Research a library, API, or domain with adversarial verification. |
| `verify-execution` | `/verify-execution` | Post-implementation: confirm output meets plan's success criteria. |
| `repo-doc` | `/repo-doc` | Generate or update project documentation. |
| `frontend-design` | `/frontend-design` | UI/UX patterns, layout, accessibility, and design decisions. |
| `evidence-dialogue` | `/evidence-dialogue` | Structured Q&A where every claim needs cited evidence. |

---

## Standard flow for a new feature

```
/skill-sergeant          ← route the task (or skip if obvious)
       ↓
/plan-architect          ← design before building
       ↓
/test-generator          ← write failing tests (RED)
       ↓
[owner approval]
       ↓
/execute-plan            ← implement (GREEN)
       ↓
/verify-execution        ← confirm it meets the spec
       ↓
session-end ritual → commit
```

---

## Standard flow for a broken thing

```
/diagnose                ← trace the root cause first
       ↓
/execute-plan            ← apply the specific fix
       ↓
/verify-execution        ← confirm the fix worked and nothing regressed
```

---

## Notes

- Skills are in `.claude/skills/` — each has a `SKILL.md` with its full protocol.
- Mirror to `.cursor/skills/` if using Cursor as your editor.
- To add a skill: create `.claude/skills/[name]/SKILL.md`, add it to this table, add a DECISION_LOG entry.
