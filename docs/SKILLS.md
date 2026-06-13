# Skills Registry — Flying-Probe Co-Pilot

Custom Claude Code skills available in this project.
Skills live in `.claude/skills/[skill-name]/SKILL.md`.
Invoke with `/skill-name` in Claude Code.

---

## Available skills

| Skill | Invoke | When to use |
|-------|--------|-------------|
| `skill-sergeant` | `/skill-sergeant` | **Start here.** Routes to the right skill. Handles gray zones. Manages don't-use lists. |
| `plan-architect` | `/plan-architect` | Before any non-trivial implementation. Produces a What/Why/Where plan with test cases. |
| `execute-plan` | `/execute-plan` | After owner approves a plan. Implements faithfully in TDD order (Red → Green → Refactor). |
| `test-generator` | `/test-generator` | Write failing test stubs (TDD RED phase) before implementation starts. |
| `session-workflow` | `/session-workflow` | Full 10-step pipeline for complex multi-file tasks. Orchestrates all sub-skills. |
| `diagnose` | `/diagnose` | Root-cause analysis when tests fail or behavior is wrong. Read evidence, trace cause. |
| `deep-research` | `/deep-research` | Multi-source research on a library, API, or domain with adversarial verification. |
| `verify-execution` | `/verify-execution` | Post-implementation: confirm output meets the plan's SUCCESS-WHEN criteria. |
| `repo-doc` | `/repo-doc` | Generate or update project documentation (README, CLAUDE.md, specs). |
| `evidence-dialogue` | `/evidence-dialogue` | Structured Q&A — every claim requires cited evidence. Prevents hallucination. |

---

## Skill interaction map

```
New feature task
       │
       ▼
 /plan-architect ──────────────────────────────────────────────────┐
       │                                                           │
       │  produces: plan document + What/Why/Where table          │
       ▼                                                           │
 /test-generator                                                   │
       │                                                           │
       │  produces: failing tests (RED)                           │
       ▼                                                           │
 [owner approval gate]                                             │
       │                                                           │
       ▼                                                           │
 /execute-plan                                                     │
       │                                                           │
       │  produces: implementation (GREEN)                        │
       ▼                                                           │
 uv run pytest ─── FAIL ──→  /diagnose ──→ back to /execute-plan ┘
       │
       │  all green
       ▼
 session-end ritual → commit
```

---

## Skill guardrails

- **Never skip plan-architect for a new module.** Jumping straight to code without a plan produces scope creep and untestable designs.
- **test-generator always runs before execute-plan.** Tests must exist and fail before implementation starts.
- **diagnose is for root-cause analysis, not guessing.** It reads failing test output and traces back to the source — don't just retry fixes randomly.

---

## Adding a new skill

1. Create `.claude/skills/[skill-name]/SKILL.md`
2. Add an entry to the table above
3. Mirror to `.cursor/skills/[skill-name]/SKILL.md` if using Cursor
4. Add a `DECISION_LOG.md` entry explaining why the skill was added
