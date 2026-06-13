# Skill: repo-doc

> Invoke: `/repo-doc`
> Generate or update project documentation.
> Use for README, CLAUDE.md, specs, API docs, module docs — not for code changes.
> See /skill-sergeant for routing.

---

## When to use

- "Update the README"
- "Document this module"
- "Write a spec for Phase X"
- "Update CLAUDE.md after this session"
- "Generate API documentation"
- "Add a section to the roadmap"

## When NOT to use

- Code changes (use /execute-plan)
- Research (use /deep-research)
- Session-end log updates (those are part of the session-end ritual, not this skill)

---

## Types of documentation this skill handles

| Doc type | File | When to update |
|----------|------|----------------|
| Project identity | `CLAUDE.md` | Start of each phase, major decisions |
| README | `README.md` | At phase boundaries or public-facing milestones |
| Roadmap | `docs/ROADMAP.md` | At phase start and when deliverables complete |
| Phase spec | `specs/[phase]-[name].md` | Before starting a new phase |
| Module doc | `src/[module]/README.md` | When module API stabilizes |
| API doc | `docs/api-[name].md` | When public interface is finalized |
| Decision log | `docs/logs/DECISION_LOG.md` | Every architectural decision |
| Skills registry | `docs/SKILLS.md` | When skills are added or removed |

---

## Step 1 — Read before writing

Before generating any documentation:
1. Read the existing file (if it exists) to understand the current state.
2. Read `CLAUDE.md` for project context.
3. Read the relevant source code or spec.
4. Read `docs/logs/SESSION_LOG.md` and `DECISION_LOG.md` for recent changes.

Do not generate documentation from memory — read the current state of the code.

---

## Step 2 — Scope the update

State:
```
DOC FILE:   [which file is being updated]
PURPOSE:    [why this doc needs updating now]
SECTIONS:   [which sections will change — don't touch unrelated sections]
AUDIENCE:   [who reads this: owner, recruiter, other dev, AI agent]
```

---

## Step 3 — Generate with the audience in mind

| Audience | Tone | Detail level |
|----------|------|-------------|
| AI agent (CLAUDE.md) | Direct, structured, no ambiguity | High — include constraints and rules |
| Owner (SESSION_LOG) | Personal, conversational | Medium — what matters for continuity |
| Recruiter (README) | Professional, compelling | Low — show value, not internals |
| Future dev (module doc) | Technical, precise | High — why decisions were made |

---

## Step 4 — Show diff before writing

For any file >50 lines, show the owner:
1. Which sections will change
2. A preview of the new content

Get confirmation before writing to existing documentation.

---

## Step 5 — Cross-check for consistency

After updating, verify:
- Does the new doc contradict anything in `DECISION_LOG.md`?
- Does it reference files that exist? (Check with Glob)
- Does it mention version numbers or dates that are accurate?
- If it's CLAUDE.md, does it accurately reflect the current phase status?

---

## CLAUDE.md update checklist

When updating CLAUDE.md specifically:

- [ ] Phase table status column is accurate
- [ ] Session log line added for today
- [ ] Open questions list is current (close resolved ones)
- [ ] Tech stack is still accurate (no new additions without updating this)
- [ ] Guardrails list is complete
