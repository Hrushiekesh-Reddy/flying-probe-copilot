# Skill: skill-sergeant

> Invoke: `/skill-sergeant`
> The routing brain for this project's skill toolkit.
> Use when you're unsure which skill to invoke, or to manage skill preferences.
> Also activates automatically when a request falls in a gray zone between two skills.

---

## Activate when

- "Which skill should I use for X?"
- "What skill handles X?"
- "Is there a skill for X?"
- "What's the right skill to handle this?"
- "Never use X skill for Y" / "Don't use X for this" / "Add X to the don't-use list"
- Any request that could plausibly belong to two different skills

---

## Skill registry — all available skills

| Skill | Invoke | Purpose | Primary triggers |
|-------|--------|---------|-----------------|
| `/plan-architect` | `/plan-architect` | Plan any non-trivial task before writing code. Produces Goal Contract, What/Why/Where table, ordered steps. | "Plan this", "how should I approach", "design X", "I need a plan" |
| `/execute-plan` | `/execute-plan` | Implement an approved plan, TDD-first. Never skips tests. | "Build it", "implement the plan", "go ahead", "execute" |
| `/test-generator` | `/test-generator` | Write failing test stubs (RED phase) before implementation starts. | "Write tests for X", "create test stubs", "TDD setup" |
| `/session-workflow` | `/session-workflow` | Orchestrate the full 12-step pipeline for complex multi-file tasks. | "Run the full workflow", "complex task", "end-to-end" |
| `/architecture-refactor` | `/architecture-refactor` | Break up a god-file / shallow module into deep modules behind a clean interface, one reviewable chunk at a time. Behavior-preserving. | "Refactor this god-file", "split this file", "extract a module", "deep modules", "reorganize without changing behavior" |
| `/diagnose` | `/diagnose` | Root-cause analysis when something is broken. Read evidence, trace cause, propose fix. | "This test is failing", "something is wrong", "debug X", "why is X happening" |
| `/deep-research` | `/deep-research` | Multi-source research with adversarial verification and cited output. | "Research X", "how does X library work", "find documentation for", "I need to understand X deeply" |
| `/verify-execution` | `/verify-execution` | Post-implementation verification that output meets the plan's success criteria. | "Is this correct?", "verify the implementation", "does this meet the spec?" |
| `/repo-doc` | `/repo-doc` | Generate or update project documentation (README, CLAUDE.md, specs, API docs). | "Update the docs", "write a README", "document this module", "update CLAUDE.md" |
| `/frontend-design` | `/frontend-design` | UI/UX patterns, layout, accessibility, and design decisions. Primary question is how it should look/feel/behave. | "Design this component", "how should this look", "improve the UX", "accessibility audit", "responsive layout" |
| `/evidence-dialogue` | `/evidence-dialogue` | Structured Q&A where every claim requires cited evidence. Prevents hallucination on architectural questions. | "Walk me through X with evidence", "is X true?", "justify this decision", "challenge this assumption" |

---

## Routing decision tree

```
User has a task
       │
       ├─ "I don't know how to approach this"
       │  "What should I build?" / "Design X"
       │       → /plan-architect
       │
       ├─ "I have an approved plan, now build it"
       │       → /test-generator FIRST → then /execute-plan
       │
       ├─ "Something is broken / a test is failing"
       │       → /diagnose
       │
       ├─ "Is the implementation correct?"
       │  "Does this meet the spec?"
       │       → /verify-execution
       │
       ├─ "This task is complex, multi-file, multi-step"
       │       → /session-workflow  (orchestrates all sub-skills automatically)
       │
       ├─ "I need to understand a library / API / framework"
       │  "Research X"
       │       → /deep-research
       │
       ├─ "Write / update documentation"
       │       → /repo-doc
       │
       ├─ "Break up a god-file / split a big module" (no behavior change)
       │       → /architecture-refactor
       │
       ├─ "How should this look / design this UI / improve the UX"
       │       → /frontend-design
       │
       └─ "Walk me through this decision with evidence"
          "Challenge this assumption"
                → /evidence-dialogue
```

---

## Gray zones — where two skills overlap

| Situation | Pick this | Not that | Why |
|-----------|-----------|----------|-----|
| "Write tests for this existing function" | `/test-generator` if doing TDD-first; `/diagnose` if tests already fail | Don't use `/execute-plan` for test-writing alone | execute-plan implements; test-generator writes the stubs |
| "Fix this failing test" | `/diagnose` first, then `/execute-plan` for the fix | Don't jump to `/execute-plan` without diagnosing | Skipping diagnosis leads to random trial-and-error |
| "Is this plan correct?" | `/plan-architect` (Step 5: pre-build review) | Not `/verify-execution` (that's post-implementation) | Verification needs an implementation to verify |
| "Refactor this module" | `/architecture-refactor` for a god-file / module split (behavior-preserving); `/plan-architect` → `/execute-plan` for a feature-changing rework | Not jumping straight to `/execute-plan` | architecture-refactor enforces chunked, interface-first, no-behavior-change; a plan covers reworks that change behavior |
| "Explain how X library works" | `/deep-research` if it's an external library; `/evidence-dialogue` if it's your own architecture | Don't use `/repo-doc` (that generates docs, doesn't explain) | research vs explanation vs generation are different tasks |
| "Review this code" | `/verify-execution` if checking against a spec; `/evidence-dialogue` if open-ended | Not `/diagnose` (that's for failures, not reviews) | diagnose traces an error; verify checks a spec; evidence-dialogue debates |
| "I need comprehensive tests AND implementation" | `/session-workflow` (it orchestrates both) | Don't chain skills manually for complex tasks | session-workflow handles the full pipeline including gates |
| "Update CLAUDE.md and docs after this session" | `/repo-doc` | Not `/execute-plan` (that's for code) | doc updates are a different skill |

---

## Don't-use list management

When the user says "never use X for Y" or "add X to the don't-use list for Y":

1. Acknowledge the rule clearly.
2. Save it to memory: `Skill [x] is NOT to be used for [task type]. Reason: [user's reason]`.
3. Apply it in all future routing decisions in this session and future sessions.
4. When that situation arises again, route to the next-best skill and explain why you're skipping the preferred one.

Format for saved rules:
```
DONT-USE RULE: /skill-name — not for [task-type]
REASON: [what the user said]
ALTERNATIVE: /other-skill
```

---

## Output format when routing

When you invoke skill-sergeant, respond with:

```
RECOMMENDED: /skill-name
WHY: [one sentence — what this skill does that fits the task]
FIRST STEP: [what the user does immediately after invoking it]
NOT:  /other-skill — [one sentence why this one doesn't fit]
NOT:  /another-skill — [one sentence why]
```

If the task is clearly complex and multi-step:
```
RECOMMENDED: /session-workflow
WHY: This task spans [N] files and [N] steps — the full pipeline handles the gates.
SKILLS IT WILL INVOKE: plan-architect → test-generator → execute-plan → verify-execution
```

---

## Proactive activation

Do NOT wait for the user to type `/skill-sergeant`. Activate automatically when:
- A request could map to 2+ skills and the wrong choice would waste a session
- The user says "just do it" without specifying a skill (scope is unclear)
- The user's request mixes planning + execution + testing in one ask

In those cases, output the routing recommendation BEFORE starting any work.
