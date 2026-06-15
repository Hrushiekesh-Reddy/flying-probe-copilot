# Skill: session-workflow

> Invoke: `/session-workflow`
> The full multi-agent loop for any non-trivial task.
> Parent agent orchestrates; sub-agents execute, verify, and report.
> See /skill-sergeant for routing. Use fast path for simple changes.

---

## When to use

- Task touches ≥3 files or has ≥5 steps
- Any new module being built from scratch
- Any task with unclear scope or multiple approaches
- Any task where independent verification matters

## When NOT to use

- Doc edits, typo fixes, single-file config changes → use fast path
- Conversational questions → just answer

---

## The Loop — 12 Steps

```
Step 1  Document        ← PARENT         Requirements capture, session brief
Step 2  Explore         ← SUB-AGENT      What/Why/Where/When structured map
Step 3  Plan            ← PARENT ONLY    Goal Contract + ordered steps (never delegated)
Step 4  Test-Case Plan  ← SUB-AGENT      Behavior-level test plan (test-generator role)
Step 5  Verify Plan     ← SUB-AGENT      Adversarial red-team of the plan + test plan
Step 6  Decision Gate   ← PARENT ONLY    Owner approval: Decision Index + Coverage Check + per-decision detail
Step 7  Execute         ← SUB-AGENT      TDD implementation, strict guardrails
Step 8  Verify Exec     ← SUB-AGENT      Execution report vs plan
Step 9  Triple Check    ← PARENT ONLY    Found vs Planned vs Executed (independent)
Step 10 Documentation   ← PARENT         Git ops, logs, out-of-scope bugs
Step 11 Manual QA       ← PARENT guided  Hands-on test with owner
Step 12 Feedback + Handoff ← PARENT      Collect feedback, write AGENT_HANDOFF_LOG
```

---

## Step 1 — Document (PARENT)

**Purpose:** Establish a clear, unambiguous goal before any work begins.

Do NOT paraphrase or assume. Ask if the requirement is unclear.

Produce a **Session Brief** and save it to `docs/plans/YYYY-MM-DD-brief.md`:

```markdown
## Session Brief — YYYY-MM-DD

### What the owner wants
[Verbatim or near-verbatim description of the request]

### Goal statement (one sentence)
[Restate in concrete, measurable terms]

### Success looks like
[Specific, observable outcomes — not vague. e.g. "test_x passes", "CLI produces output Y"]

### Out of scope (explicit)
[What will NOT be done this session — be specific]

### Phase / milestone
[Which roadmap item this maps to]

### Branch
feature/[short-name] — confirm before anything else
```

**Do not proceed to Step 2 until the goal is unambiguous. Ask the owner to clarify if needed.**

---

## Step 2 — Explore (SUB-AGENT: Explorer)

**Purpose:** Gather all facts needed for the plan. Parent should NOT do this directly.

Charter for Explorer sub-agent:
```
ROLE: Read-only context scout. No edits. No opinions. Facts only.

READ:
- CLAUDE.md (phase, guardrails)
- docs/ROADMAP.md or equivalent (exact deliverable)
- docs/logs/SESSION_LOG.md (last session state)
- docs/logs/DECISION_LOG.md (decisions in force)
- Any relevant spec in specs/
- Source files the task will touch
- Existing tests and fixtures in tests/

RETURN (structured — no prose):
WHAT: [files that will change and why]
WHY:  [which deliverable each change serves]
WHERE: [exact file paths, line ranges, function names]
WHEN: [dependencies — what must happen before what]
TESTS_EXIST: [yes/no per module + test file path]
FIXTURES_AVAILABLE: [list from conftest.py]
OPEN_QUESTIONS: [anything ambiguous that the parent must decide]
DO_NOT_TOUCH: [files that look relevant but must NOT change]
CRITICAL_FILES: [approval-gated files this task may need]

EXTERNAL RESEARCH / WEB DOWNLOAD POLICY (applies whenever this subagent — or
any general-purpose subagent — is given web/fetch tools to gather external
material):

- NEVER persist downloaded source material (PDFs, source files, archives,
  HTML dumps) at the repo root or anywhere inside the project working tree.
- Use the OS scratch location for any disk caching:
    Windows:  %TEMP%\agent-research\<session-id>\
    Unix:     ~/.cache/agent-research/<session-id>/
  Construct the path with the platform-correct join — never concatenate
  "<project-name>" + ".cache_research" + "<filename>". If a write path you
  are about to use does NOT start with the scratch root above, STOP and
  report the path-construction bug instead of retrying.
- The final report MUST contain only citations (URLs / DOIs) and short
  paraphrased extracts — NEVER copied source material, NEVER wholesale
  PDF-to-text dumps, NEVER copy-pasted source files.
- Third-party source code (especially LGPL / GPL / AGPL / proprietary) MUST
  be cited by repo URL + commit hash (or release tag + file path) only.
  Never copy it into the project working tree, even temporarily, even into
  a gitignored folder.
- Cached files MUST be deleted before this subagent returns. The report
  MUST include a "Cleanup:" line listing what was removed and from where
  ("Cleanup: 5 files removed from %TEMP%\agent-research\sess-2026-06-13\").
```

Parent reads the Explorer's full output before moving to Step 3.
If open questions exist: resolve them with the owner before planning.
If the Explorer was given web/fetch tools (i.e., the External Research /
Web Download Policy applied) and the report is missing a `Cleanup:` line —
or its Cleanup path is inside the repo — treat the explore output as
compromised and re-run before planning. A purely read-only Explorer that
never fetched external material is not expected to emit a Cleanup line.

---

## Step 3 — Plan (PARENT ONLY — NEVER DELEGATED)

**Purpose:** Parent synthesizes the Explorer's output into a concrete, executable plan.
Planning is always done by the parent agent. It cannot be delegated to a sub-agent.

Using `/plan-architect`, produce and save to `docs/plans/YYYY-MM-DD-plan.md`:

```markdown
## Plan — YYYY-MM-DD — [short name]

### Goal Contract
OBJECTIVE:    [one sentence]
SUCCESS-WHEN: [measurable — specific test names, CLI output, query results]
OUT-OF-SCOPE: [explicit list — things that look related but won't be done]
CONSTRAINTS:  [branch rule, TDD-first, critical file approvals, phase discipline]

### What / Why / Where / When
| # | File | What changes | Why (deliverable) | When (after what) | Test file |
|---|------|-------------|------------------|-------------------|-----------|
| 1 | src/x.py | new fn parse() | ROADMAP 1b — parser | after conftest fixture | tests/test_x.py |

### Ordered execution steps (TDD)
1. Write test: tests/test_x.py::test_parse_valid → RED
2. Implement: src/x.py::parse() — happy path
3. pytest → GREEN
4. Write test: test_parse_malformed → RED
5. Implement error path
6. pytest → GREEN
...

### Guardrails
- Branch: feature/[name]
- Critical files touched: [list or "none"]
- New dependencies: [none / list — each requires approval]
- Phase discipline: [confirm phase-N only]
```

**Rule: No execution starts until this document exists, has a Test-Case Plan (Step 4),
survives the adversarial review (Step 5), and clears the Decision Gate (Step 6).**

---

## Step 4 — Test-Case Plan (SUB-AGENT: Test Planner / test-generator role)

**Purpose:** Decide WHAT to test — by behavior, not implementation — before the plan is
locked. A fresh `test-generator`-role sub-agent reads the plan and lists the test cases
each deliverable must satisfy. This is the *design* of the test surface; the actual
RED-first stubs are still written during Execute (Step 7). Runs AFTER the plan exists
and BEFORE the adversarial plan review, so the reviewer can red-team both together.

Charter for Test Planner sub-agent:
```
MISSION:    From the plan's Goal Contract and What/Why/Where/When table, enumerate the
            test cases that prove each deliverable works — described by observable
            behavior (inputs → expected outputs/effects), never by implementation detail.

ALLOWED:    Read the plan (docs/plans/), existing tests, fixtures, and the target
            interface. Produce a behavior-level test-case list. Note coverage gaps.

PROHIBITED: No production code. No test implementation — no stubs, no asserts yet.
            No edits to source or the plan. Flag plan gaps; do not fix them yourself.

DELIVERABLE: A Test-Case Plan saved to docs/plans/YYYY-MM-DD-test-plan.md:
  - One row per behavior: case name | input / precondition | expected result | deliverable it proves
  - Happy paths, edge cases (empty / null / max / malformed), and error paths per unit
  - An explicit "untestable by automation" list (these become Manual QA cases in Step 11)
  - Coverage gaps or ambiguities the plan must resolve before approval
```

The parent attaches the Test-Case Plan to the plan so Step 5 red-teams BOTH, and Step 7
implements the cases RED-first (see `/test-generator`).

---

## Step 5 — Verify Plan (SUB-AGENT: Plan Reviewer, adversarial)

**Purpose:** A fresh agent with no attachment to the plan tries to break it — the plan
and the Test-Case Plan together.

Charter:
```
ROLE: Adversarial plan reviewer. Your job is to find problems, not validate.

READ:
- docs/plans/YYYY-MM-DD-plan.md
- docs/plans/YYYY-MM-DD-test-plan.md

LOOK FOR:
- Scope creep: does any step touch something outside OUT-OF-SCOPE?
- Missing edge cases: what inputs/states does the plan not cover?
- Test gaps: does the Test-Case Plan miss a behavior, edge case, or error path
  the plan introduces? Are any "expected results" vague or unobservable?
- Phase violations: does any step implement a future-phase deliverable?
- Wrong branch: would any step commit to a permanent branch?
- Missing fixtures: do the tests reference fixtures that don't exist yet?
- Ordering errors: are dependencies respected in the step sequence?
- Approval-gated files: does any step touch a critical file without noting it?
- TDD violations: does any step write implementation before its test?

RETURN:
CONCERNS: [numbered list — specific, not vague]
SEVERITY: [BLOCKER / WARNING / MINOR per concern]
VERDICT: APPROVE / APPROVE WITH CHANGES / BLOCK
```

Parent reads the reviewer's output and:
- For each BLOCKER: resolve in the plan / test-plan before proceeding
- For each WARNING: note the resolution or accepted risk
- For each MINOR: note and continue
- Update `docs/plans/YYYY-MM-DD-plan.md` and the test-plan with resolutions

**Resolve all BLOCKERs, then take the updated plan to the Decision Gate (Step 6).**

---

## Step 6 — Owner Approval + Decision Gate (PARENT ONLY — never delegated)

**Purpose:** No execution begins until the owner has seen *every* decision the plan
contains and had the chance to veto each one. A simple "go ahead" is not enough — a long
plan is easy to skim, so the parent must surface the decisions explicitly. This step is
the parent's job and is never delegated to a sub-agent.

The `plan_approval_gate.py` hook fires an advisory 5-point checklist (branch / TDD /
scope / decisions logged / critical-file sign-off) the moment the owner signals approval.
That hook is the *reminder*; this step is the *procedure* the parent then runs, in order.

> **Stop on approval.** When the owner says "go ahead / approved / proceed / build it",
> run no Shell, edits, commits, or sub-agents until this gate completes.

### 6a — Decision Index (first, required)
List EVERY decision in the plan, numbered, one line each, with its recommended option.
Do not omit a decision because it seems minor or because you have a strong default.
```
DECISION INDEX — N decisions across M sections
1. (Section <name>) <decision in plain English> — Recommended: <option>
2. (Section <name>) <decision in plain English> — Recommended: <option>
```
If the plan genuinely contains zero decisions, say so explicitly.

### 6b — Coverage Check (required)
Prove no plan section was skipped. Enumerate every section/phase and list the decision
numbers it holds — or the literal words "no decisions here".
```
COVERAGE CHECK
- <Section A>: decisions #1, #2
- <Section B>: no decisions here
- <Section C>: decision #3
```
A section that performs an irreversible action or touches a critical file but is absent
from the Index is a **gate failure** — fix the Index before continuing.

### 6c — Per-decision detail (required, for each indexed decision)
1. **Problem** — 2–4 sentences, plain English: what could go wrong and why it matters.
2. **Options** — only choices allowed by `.claude/rules/agent-conduct.md` and the
   critical-file rules (no auto-commit/push the owner didn't ask for; no critical-file
   edits without an approval path).
3. **Repercussions** — one line per option: what happens if they pick it.
4. **Recommendation** — mark **Recommended: <option>** with a plain reason (safety,
   gate, scope).

Wait for the owner's answers (or an explicit "use your recommendations") before Step 7.
Apply the answers; if scope changed, adjust the plan. Only then proceed to Execute.

---

## Step 7 — Execute (SUB-AGENT: Executor, strict guardrails)

**Purpose:** Build what the plan says. Nothing more, nothing less.

Charter:
```
ROLE: Executor. Implement the plan at docs/plans/YYYY-MM-DD-plan.md faithfully.

MANDATORY RULES:
1. TDD order: write test → confirm RED → implement → confirm GREEN → next step
2. Implement ONLY plan steps. No improvements, no cleanup, no "while I'm here".
3. If a step is impossible: STOP. Report the blocker. Do not improvise.
4. If you touch a file not in the plan: STOP. Report it. Do not commit.
5. Out-of-scope finding: LOG IT IMMEDIATELY (see below), then continue.
6. No new dependencies without owner approval (log the need, pause).
7. Match code style of surrounding files exactly.
8. No commented-out code. No TODOs without a BUG_LOG entry.

OUT-OF-SCOPE BUG LOGGING (mandatory, automatic):
When you find a bug that is NOT in scope for this session:
  1. Add entry to docs/logs/BUG_LOG.md immediately (do not wait for session end)
  2. Include: what you found, file:line, severity estimate
  3. Note it in your execution log
  4. Continue the plan — do NOT fix it

DEVIATION LOGGING:
If you deviate from any plan step for any reason:
  DEVIATION — step N:
    Planned:  [what the plan said]
    Actual:   [what you did]
    Reason:   [why]

PRODUCE at end:
- Execution log with each step: DONE / SKIPPED / DEVIATED / BLOCKED
- List of files changed (file → what changed)
- List of tests: passing / failing
- List of out-of-scope findings logged
- List of deviations from plan
```

---

## Step 8 — Verify Execution (SUB-AGENT: Verifier)

**Purpose:** Independent check that execution actually did what the executor claimed.

Charter:
```
ROLE: Execution verifier. You have not seen the execution — read the evidence.

READ:
- docs/plans/YYYY-MM-DD-plan.md (what was supposed to happen)
- The executor's execution log (what they claim happened)
- The actual changed files (what actually happened)

RUN:
- Full test suite (pytest / npm test / etc.)
- Coverage report

PRODUCE Execution Report:
---
## Execution Report — YYYY-MM-DD

### Test suite results
Passing: N  |  Failing: N  |  Coverage: X%

### Step-by-step verification
| Plan step | Executor claimed | Evidence found | Match? |
|-----------|-----------------|----------------|--------|
| 1. Write test X | DONE — RED confirmed | test exists, fails → ✓ | YES |
| 2. Implement parse() | DONE — GREEN | function exists, test passes → ✓ | YES |
| ... | | | |

### Out-of-scope bugs logged
[list from BUG_LOG, or "none"]

### Deviations detected
[any step where executor's claim ≠ evidence found]

### SUCCESS-WHEN check
[each criterion from plan → MET / NOT MET + evidence]

### Verdict
PASS — all steps verified, SUCCESS-WHEN met
  OR
FAIL — [specific items that don't match]
---
```

---

## Step 9 — Triple Check (PARENT ONLY — independent, never delegated)

**Purpose:** Parent reads everything independently and runs the triple comparison.
This step is what catches executor drift, report inflation, and plan gaps.
Parent does NOT re-read the execution log before checking the code — check code first.

**Do in this order:**

### 9a — Read the actual code/tests independently
```
Open each file that was supposed to change.
Read it. Note what you actually see.
Do NOT read the executor's log yet.
```

### 9b — Read the plan's SUCCESS-WHEN criteria
```
What did the plan say would be true when done?
```

### 9c — Read the executor's report + verifier's report
```
What did they claim was done?
```

### 9d — Triple Comparison

Produce this comparison table:

```markdown
## Parent Triple Comparison — YYYY-MM-DD

### What I FOUND (independent code read)
- File src/x.py: parse() exists, lines N-M, handles valid + malformed input
- tests/test_x.py: 4 tests, all passing
- [etc.]

### What was PLANNED (SUCCESS-WHEN from plan)
- parse() implemented
- test_parse_valid passing
- test_parse_malformed passing
- [etc.]

### What was EXECUTED (executor + verifier claim)
- Executor: all 6 steps done, 4 tests GREEN
- Verifier: PASS, all criteria met
- [etc.]

### Delta Analysis
FOUND vs PLANNED:   [match or gap — be specific]
FOUND vs EXECUTED:  [match or gap — did executor do what they claimed?]
EXECUTED vs PLANNED: [match or gap — did executor follow the plan?]

### Out-of-scope bugs (surfacing to owner)
[list bugs from BUG_LOG that were logged this session]

### Verdict
CLEAN — all three align. Proceed to documentation.
  OR
DRIFT — [specific delta]. Return to step 7 or 8 to resolve before documenting.
```

**If DRIFT: do not proceed. Resolve first. Document why in DECISION_LOG.**

---

## Step 10 — Documentation (PARENT)

**Purpose:** Lock in the record of what happened and surface anything the owner needs to know.

Do in this order:

1. **Session log** — add entry to `docs/logs/SESSION_LOG.md`
2. **Decision log** — add any architectural decisions made this session
3. **Bug log** — verify any out-of-scope bugs found in step 7 are in `docs/logs/BUG_LOG.md`
4. **Roadmap** — tick any deliverables completed
5. **CLAUDE.md** — update session log line

6. **Surface out-of-scope bugs to owner:**
   For EACH bug logged during execution, call `spawn_task`:
   ```
   Title: "Fix [BUG-XXX]: [short title]"
   Prompt: "Bug found during [session goal] session on [date]. 
            See docs/logs/BUG_LOG.md entry [BUG-XXX].
            File: [file:line]. Symptom: [symptom]. Not fixed this session (out of scope)."
   ```
   This surfaces a chip to the owner without interrupting the current session's work.

7. **Git operations:**
   ```bash
   git add [specific files — never git add .]
   git status          # confirm only expected files are staged
   git commit -m "..."
   ```
   Commit message format:
   ```
   [Phase/type]: [one-line summary]
   
   - [bullet: specific thing done]
   - [bullet: specific thing done]
   
   Tests: N passing | Coverage: X%
   Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
   ```
   
   **Never push unless owner explicitly requests it.**

---

## Step 11 — Manual QA (PARENT guided)

**Purpose:** Owner tests the actual running output. Code passing tests ≠ feature working.

Parent prepares a Manual QA script. Start from the "untestable by automation" list the
Test-Case Plan flagged in Step 4 — those cases land here.

```markdown
## Manual QA — YYYY-MM-DD

### Setup
[exactly how to run the thing being tested]

### Test cases to run manually
1. [Specific action] → Expected: [specific output]
2. [Specific action] → Expected: [specific output]
3. [Edge case action] → Expected: [specific behaviour]

### What to look for
[specific things that tests can't catch — UI, file output, timing, error messages]

### Pass/fail criteria
PASS: all N test cases produce expected output
FAIL: any test case deviates — note exactly what was seen
```

Owner runs the QA. Parent collects results.
If FAIL: log the failure in BUG_LOG.md and decide: fix now (new mini-loop) or log for later.

---

## Step 12 — Feedback + Agent Handoff (PARENT)

**Purpose:** Capture what happened so the next agent (or next session) starts fully informed.

### 12a — Collect feedback from owner

Ask:
1. "Did the output match what you expected?"
2. "Anything that felt wrong or could be better?"
3. "Priority for next session?"

Note the answers — they shape the next session's Step 1.

### 12b — Write Agent Handoff Log

Add entry to `docs/logs/AGENT_HANDOFF_LOG.md`:

```markdown
## Handoff: Session YYYY-MM-DD → Next session

**Branch:** feature/[name] [merged/not merged]
**Session goal:** [from Step 1 brief]
**Outcome:** Done / Partial / Blocked

### Completed
- [specific: file, function, test — not vague]

### In progress — needs pickup
- [item: exact file / function / state / what's left / watch-outs]

### Out-of-scope bugs logged (spawn_task chips created)
- BUG-XXX: [title] — [file:line] — chip created ✓

### Test suite status
Passing: N | Failing: N | Coverage: X%

### Owner feedback
- [what owner said]

### Next session should (ordered)
1. [specific first action]
2. [specific second action]

### Documents updated this session
- [ ] SESSION_LOG.md
- [ ] DECISION_LOG.md
- [ ] BUG_LOG.md
- [ ] Roadmap
- [ ] CLAUDE.md
```

---

## Subagent charter summary

| Role | Can read | Can write | Hard limits |
|------|----------|-----------|-------------|
| Explorer | All docs, source, specs | Nothing in repo; scratch only in `%TEMP%` / `~/.cache/agent-research/` | No edits ever; no downloads to repo; cleanup before return |
| External-research (general-purpose w/ web tools) | Public web; same scratch as above | Same scratch only | Citations + paraphrase only in report; no copied source / PDFs / LGPL-GPL code in repo |
| Test Planner | Plan, tests, fixtures, interface | Test-Case Plan doc | No code, no test impl, no plan edits |
| Plan Reviewer | Plan + test-plan docs | Nothing | No fixes, concerns only |
| Executor | Plan, tests, source | Source + tests | Plan steps ONLY, log out-of-scope |
| Verifier | Plan, changed files, test results | Execution report | No code edits |

**Parent agent owns:** Steps 1, 3, 6, 9, 10, 11, 12 — never delegated. (Step 6, the
Decision Gate, and Step 9, the Triple Check, are the two checkpoints the parent must
run itself.)

---

## Fast path (single-file, doc edits, typos)

Skip steps 2–8. Still mandatory: step 9 (read what you did), step 10 (log + commit), step 12 (handoff note if session continues).

---

## Out-of-scope bug rule (enforced at every step)

Any agent (parent or sub-agent) that finds a bug outside the current plan's scope MUST:
1. Add it to `docs/logs/BUG_LOG.md` immediately — not at session end
2. Note it in their output
3. Continue working — do NOT fix it
4. Parent surfaces it via `spawn_task` in Step 10

**Silent out-of-scope fixes are prohibited.** They expand blast radius without review.
