# Work instructions — using the multi-agent workflow

> Plain-English guide for the project owner (non-programmer).
> How to use the 10-step workflow, tiering, the context brief, and prompt caching together.
> Read at the start of any non-trivial session.

---

## The big picture in one paragraph

You have four things that work together:

- **10-step workflow** — the steps an AI agent follows to do a task safely.
- **Tiering** — deciding how many of those 10 steps actually run for a given task.
- **Context brief** — a short text block you write once per session so AI sub-agents don't waste time re-reading rules.
- **Prompt caching** — Anthropic's behind-the-scenes trick that makes the brief almost free to reuse.

Think of it like running a part through a manufacturing line:
- The 10 steps are the full sequence of stations.
- Tiering decides which stations the part actually visits.
- The brief is the job traveler that follows the part.
- Prompt caching is keeping the test fixtures set up between consecutive runs so the next part is faster.

---

## Part 1 — Pick a tier (1 minute, every session)

Before you tell Claude what to do, look at your task and ask, in order:

| Ask | If YES → tier is | Steps that run |
|---|---|---|
| Is this a typo, one-line config, or doc edit? | **Trivial** | 1 → 7 → 8 |
| Is this one file, one idea, tests are obvious? | **Small** | 1 → 3 → 5 → 7 → 8 |
| Does this touch 2–4 files, or introduce a new idea, but the path is clear? | **Medium** | 1 → 2 → 3 → 5 → 7 → 8 |
| Is this the parser, the schema, the RAG core, or anything where a bug ships bad data? | **Large** | All 10 |

If you genuinely can't decide in 5 minutes, default to **Medium**. It's the safest middle.

### Real examples from this project

- Fix a typo in CLAUDE.md → Trivial
- Add a `--seed` flag to the generator → Small
- Build the fault-injection module → Medium
- Build the parser → Large
- Add a column to the DuckDB schema → Large

For the full tier reference (including the mid-session escalation protocol), see [.claude/templates/tiering.md](tiering.md).

---

## Part 2 — Open the session the right way

When you start Claude Code, your **very first message** should look like this:

> "Today I want to [describe what you want done]. I think this is a [Trivial / Small / Medium / Large] task. Please start with Step 1 of the workflow."

That single sentence tells Claude (a) what you want and (b) how much rigor to apply. Claude will then write the Session Brief (Step 1) to `docs/plans/YYYY-MM-DD-brief.md`. You read it. If it doesn't match what you meant, correct it now — fixing a misunderstanding here costs minutes, fixing it later costs hours.

**Do not skip this** — even on Trivial tasks. The brief is the contract for the whole session.

---

## Part 3 — Fill the context brief (1 minute, once per session)

Right after Claude finishes the Session Brief, your next message is:

> "Now fill in the context brief block using the template at `.claude/templates/sub-agent-brief.md` for this session."

Claude will produce a filled-in block of text. It includes:

- Which phase (1a, 1b, etc.)
- Which tier
- Which branch
- The hard guardrails (no real customer data, no IPC verbatim, etc.)
- What's out of scope this session
- Any decisions in force from DECISION_LOG.md

**Read it once.** Does it look right? Does it correctly say what's out of scope? If yes, **lock it in** — you don't touch it again for the rest of the session.

### The most important rule about the brief

**Once filled, do not edit it during the session.** Not even small edits. Not adding a date. Not rewording a bullet. The brief is the text that gets cached, and any change breaks the savings.

If a decision changes mid-session — for example, the owner realizes the work needs to expand — that's the signal to **escalate the tier** (see Part 6), not to edit the brief mid-flight.

---

## Part 4 — How prompt caching saves you money (no buttons to push)

You don't turn caching on. It happens automatically. Whether it actually helps you depends on two simple habits.

### Habit 1 — Same brief, every sub-agent

When Claude sends out an Explore sub-agent, then a Plan-Reviewer sub-agent, then the `exec` sub-agent, then a Verifier sub-agent — each one should get the **exact same brief** pasted at the top. Word for word.

You don't have to type this yourself. Just say once, at the start:

> "For every sub-agent you dispatch this session, paste the filled context brief at the top of the prompt verbatim. Do not paraphrase or update it."

That instruction makes Claude do the work consistently.

### Habit 2 — Run the loop in one sitting (within ~5 minutes per step)

The cache forgets things after **5 minutes of not being used**. So if you start a Medium-tier session and walk away for 30 minutes mid-loop, the cache has expired and your next sub-agent will cost full price.

- **Fine:** Reading what Claude just produced (1–2 minutes between steps). Brief pauses to think.
- **Hurts:** Walking away for 20+ minutes. Switching to a different conversation and coming back. Spreading a Medium session across the entire afternoon.

Rule of thumb: **once you start a Medium or Large session, plan to stay with it for 20–45 minutes straight.** Don't start one if you only have 5 minutes.

For the full mechanics of prompt caching (and what secretly breaks it), see [.claude/templates/prompt-caching.md](prompt-caching.md).

---

## Part 5 — A full Medium-tier session, step by step

Here's exactly what it looks like to build the fault-injection module (a real upcoming Phase 1a task):

| # | Your message to Claude | What happens |
|---|------------------------|--------------|
| 1 | "Today I want to build the fault-injection module for the synthetic log generator. I think this is Medium tier. Please start with Step 1." | Claude writes Session Brief to `docs/plans/2026-06-14-brief.md`. You read it. |
| 2 | "Now fill in the context brief block from `.claude/templates/sub-agent-brief.md`. From now on, paste this brief verbatim at the top of every sub-agent dispatch." | Claude produces the filled brief. You skim it. Don't edit. |
| 3 | "Now do Step 2 — Explore." | Claude dispatches an Explore sub-agent (with brief on top). Returns a structured map of files to touch and fixtures available. You read it. |
| 4 | "Now do Step 3 — write the plan." | Claude (the parent itself, not a sub-agent) writes the plan to `docs/plans/2026-06-14-plan.md`. You read and approve. |
| 5 | "Now do Step 5 — dispatch the `exec` sub-agent." | The `exec` sub-agent (tool-restricted, sonnet-pinned) runs the plan TDD-first. Returns an execution log. You see what changed. |
| 6 | "Now do Step 7 — Triple Check." | Claude reads the code itself, compares to plan, gives you a comparison table. |
| 7 | "Now do Step 8 — update logs and commit to the feature branch. Don't push." | Claude updates SESSION_LOG, DECISION_LOG, CLAUDE.md, then commits. |
| 8 | "Push it." | Branch is on GitHub, ready for merge. |

**Total time:** 30–45 minutes. About 7–8 messages from you. Most of that time is you reading what Claude produced — not waiting for Claude.

---

## Part 6 — When things go wrong

### "I picked the wrong tier"

You started Small but realized it's actually Medium. Don't keep going. Say:

> "Stop the current sub-agent. We're escalating from Small to Medium. Log the escalation in the session brief, then restart from Step 2 — Explore."

That's the escalation protocol from [.claude/templates/tiering.md](tiering.md). Catching this early is cheap; ignoring it is expensive.

### "I got interrupted and came back 30 minutes later"

The cache has expired. Your work isn't lost — your files and your plan are still there. The next sub-agent just costs full price instead of cached price. Continue normally. Nothing to fix.

### "The brief doesn't match the work anymore"

That means either the work has drifted out of scope (a problem) or the brief was wrong from the start (also a problem). Stop. Don't keep going with a stale brief. Say:

> "The brief no longer matches what we're doing. Let's pause, review scope with me, and either rewrite the brief from scratch or end this session."

### "Claude wants to edit an approval-gated file"

Approval-gated files: `pyproject.toml`, `src/flying_probe_copilot/db/schema.py`, anything in `migrations/`, `.claude/settings.json`, `.env.example`. Claude is supposed to stop and ask you. If it does, decide:

- **Yes** — give explicit per-session sign-off, in writing in chat ("yes, you may edit pyproject.toml this session to add X")
- **No** — defer the work
- **Replan** — ask Claude to make a new plan that avoids this file

### "Claude pushed without asking"

Should not happen — the rule is owner-initiated push only. If it does, tell Claude to stop, then check `git log origin/<branch>` to see what landed. The push itself is not destructive (you can fix anything), but the discipline matters.

---

## Part 7 — The quick daily checklist

Print this. Stick it on your monitor.

### At session start

1. Read CLAUDE.md + last SESSION_LOG entry (2 minutes).
2. Pick a tier in your head.
3. Tell Claude the task + the tier in one message.
4. Have Claude write the Session Brief, read it.
5. Have Claude fill the context brief block, read it, lock it.
6. Tell Claude: "paste this brief at the top of every sub-agent this session."

### During the session

- Run the right steps for your tier (see Part 1 table).
- Don't edit the brief.
- Don't walk away mid-loop for >5 minutes if you can help it.
- If something feels off, stop and escalate — don't push through.

### At session end

- Step 7 (Triple Check) — Claude does, you read.
- Step 8 (Document + commit) — Claude does, on the feature branch.
- You say "push it" (or push manually).
- Add one line to CLAUDE.md session log.

---

## One last thing

You're not a programmer — that's fine. Your job in this system is to:

1. **Decide tier** at the start.
2. **Read what Claude produced** at each step.
3. **Approve or redirect.**

Claude does the typing. You do the judgment calls. That split is the whole point of the workflow — your manufacturing-engineer judgment is what catches the bugs an AI can't.

---

## Related files

- [.claude/templates/sub-agent-brief.md](sub-agent-brief.md) — the brief template you fill in once per session
- [.claude/templates/tiering.md](tiering.md) — full tier reference + escalation protocol
- [.claude/templates/prompt-caching.md](prompt-caching.md) — caching mechanics
- [.claude/agents/exec.md](../agents/exec.md) — the dedicated execution sub-agent
- [.claude/skills/session-workflow/SKILL.md](../skills/session-workflow/SKILL.md) — the full 10-step workflow definition
- [.claude/rules/session-workflow.md](../rules/session-workflow.md) — short quick-reference of the workflow
- [.claude/rules/agent-conduct.md](../rules/agent-conduct.md) — agent behavior rules
- [.claude/rules/testing.md](../rules/testing.md) — TDD rules
