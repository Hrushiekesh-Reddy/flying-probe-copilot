# Skill: architecture-refactor

> Invoke: `/architecture-refactor`
> Break up a god-file or shallow module into deep modules behind a clean interface,
> in small reviewable chunks. Orchestrator only — it routes the work, it does not
> write code itself. See /skill-sergeant for routing.

---

## When to use

- "Refactor this god-file", "break up X in chunks", "split this file"
- "Extract a module", "improve the architecture", "deep modules", "reorganize this file"
- Any request to restructure a large or widely-coupled file **without changing behavior**

You are the **orchestrator** for chunked, interface-first refactoring. Your value is the
*sequence and the guardrails*, not new logic — you compose the existing skills so a large
file is never refactored in one unreviewable diff.

**Refactor = behavior-preserving.** Each chunk must leave observable behavior identical.
If a chunk would change behavior, that is a feature change — stop and route it through
`/plan-architect` as a normal change, not a refactor.

---

## Before anything

1. Read `docs/logs/SESSION_LOG.md` (current state) and `docs/logs/DECISION_LOG.md`
   (decisions in force) so the refactor respects the project's history and direction.
2. Read `.claude/rules/agent-conduct.md` — the **critical / approval-gated files** live
   there (`pyproject.toml, src/flying_probe_copilot/db/schema.py, migrations/, .claude/settings.json, .env.example`). Editing any of them needs explicit owner approval first.
   A file can be widely coupled without being approval-gated; treat both with care.
3. Resolve any unclear domain terms against the project's glossary or domain docs (if one
   exists) before you start naming modules.

---

## Vocabulary & the deletion test (use these exactly)

Speak in one consistent vocabulary so every suggestion is comparable — don't drift
into "component / service / boundary":

- **Module** — anything with an interface and an implementation (function, class, file, package).
- **Interface** — everything a caller must know to use it: signatures, invariants, error
  modes, ordering, config. *Not* just the type signature.
- **Depth** — leverage at the interface: a lot of behaviour behind a small interface.
  **Deep** = high leverage; **shallow** = interface nearly as complex as the implementation.
- **Seam** — where an interface lives; a place behaviour can be swapped without editing in place.
- **Leverage** — what callers gain from depth. **Locality** — what maintainers gain:
  change, bugs, and knowledge concentrated in one place.

**The deletion test** (apply to anything you suspect is shallow): imagine deleting the
module and inlining it at every call site. If complexity *vanishes*, it was a
pass-through — the extraction was not earning its keep. If complexity *reappears across
N callers*, the module was doing real work — keep it and deepen it. A "yes, complexity
concentrates" is the signal that a deepening is worth proposing.

Corollary: **one adapter = a hypothetical seam; two adapters = a real seam.** Don't
build a seam for a single implementation.

---

## The chunked loop (one cohesive seam per pass)

Pick the **smallest, lowest-coupling cohesive seam first** to prove the workflow, then
repeat. Never batch multiple seams into one chunk.

### 1. Explore (read-only) — find the seam
Spawn an Explorer sub-agent (or run `/repo-doc` for a deep audit). Deliverables for the
target file: a section map (name, line range, responsibility), the coupling of each
section (shared globals/state, framework/runtime calls, DOM/IDs, imports), and a ranked
list of extraction candidates by coupling. Output the single safest next chunk with exact
line ranges and its full dependency list.

### 2. Plan — interface-first
Route to `/plan-architect`. The plan must:
- Confirm the seam and the desired module boundary with the owner.
- Define the new module's **public interface first** (signatures, inputs/outputs, error
  contract, what stays private) in the What/Why/Where table — the implementation body is
  delegated to execute-plan.
- Name every call site that must keep working and the exact wiring change (new file +
  load order / import).
- Flag critical-file touches for approval and confirm the change stays within the current
  milestone's scope (one feature per branch).
- Include a **behavior-preservation check** in the Manual QA / verification section (the
  chunk changes no observable behavior).

### 3. Decision gate
On plan approval, run the **Decision Gate** (session-workflow Step 6): Decision Index +
Coverage Check + per-decision detail. The `plan_approval_gate.py` hook fires its advisory
checklist on approval; the parent then runs the full gate. **Deleting the old code** that
the chunk replaces is its own decision — surface it explicitly (agent-conduct forbids
deleting code without approval).

### 4. Execute — delegated, behind the interface
Route to `/execute-plan`. The work sub-agent implements behind the planned signatures and
must mark any public-signature change as DEVIATED. For risky logic, use execute-plan's
TDD order (red → green → refactor). Recommended chunk order: create the new module and
wire it → **verify it works** → only then remove the old definition (per the gate's
deletion approval).

### 5. Verify — fresh perspective
Route to `/verify-execution` against the plan + the executor's report. Confirm: all call
sites resolve, behavior is unchanged, no orphaned code, tests and any contract/integrity
checks pass.

### 6. Test
Route to `/test-generator` for the new interface (or a behavior characterization test for
the seam). For pure UI moves with no test harness, a documented manual smoke is acceptable
— state it explicitly.

---

## Guardrails (refactor-specific)

- **One chunk per change.** Land it (or PR it) before starting the next seam.
- **Behavior-preserving only.** No "while I'm here" feature changes inside a refactor chunk.
- **Critical files** (`pyproject.toml, src/flying_probe_copilot/db/schema.py, migrations/, .claude/settings.json, .env.example`, per `.claude/rules/agent-conduct.md`): no edit
  without explicit owner approval.
- **No silent deletion.** Removing the replaced code requires its own approval at the gate.
- **Public API / exported endpoints:** never remove without confirming zero callers remain
  (run the project's contract/integrity check).
- **Schema / DB columns:** never drop or rename without a committed migration.
- **Docs sync:** update `docs/logs/SESSION_LOG.md` + `docs/logs/DECISION_LOG.md` (and the
  roadmap) in the same change set — the work is incomplete without docs.

---

## Verification commands

Use the project's own commands (see `.claude/rules/testing.md`). Typically:

```bash
# Run the full test suite
<project test command, e.g. pytest -q / npm test>

# Run any contract / integrity check whenever the public API surface could be affected
<project integrity check, if one exists>

# Scan for secrets before any commit the owner requests
<project secret scan, e.g. scripts/check-no-secrets.py>
```

Reference: `.claude/rules/agent-conduct.md`, `.claude/rules/session-workflow.md`,
`.claude/skills/session-workflow/SKILL.md` (the loop + Decision Gate), `CLAUDE.md`, `SKILLS.md`.
