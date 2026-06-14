# Decision Log — Flying-Probe Co-Pilot

Architectural, design, and process decisions in reverse-chronological order.
Every non-obvious choice gets an entry here: what was decided, why, what was rejected, and when to revisit.

---

## 2026-06-14 — Dedicated `exec` sub-agent with hard tool restrictions

**Decision:** Step 5 of the 10-step session-workflow uses a dedicated `exec` sub-agent defined at `.claude/agents/exec.md`, with a tool allowlist enforced by the agent definition itself. Other sub-agent roles (Explore, Plan-Reviewer, Verifier) continue to use the built-in `Explore` agent type or the existing skills.

**Why:** Skills can *advise* a sub-agent on scope discipline; an agent definition can *enforce* it via tool restrictions. The executor is the highest-blast-radius role (it's the one writing files), so tool-level guardrails are most valuable there. Specifically, the `exec` agent cannot spawn further sub-agents (no recursion), cannot fetch the web, cannot control the browser or desktop, cannot enter/exit plan mode, and cannot invoke nested workflows — even if a misread plan instruction tries to make it.

**Rejected:**
- Custom agents for every role (Explore, Plan-Reviewer, Verifier, Exec). Diminishing returns — Explore is already well-served by the built-in `Explore` agent type, and the other roles benefit more from skill-level prompting than tool restriction.
- Continuing to rely on `execute-plan` skill alone. A skill is advisory; the executor could ignore it. Tool restrictions cannot be ignored.

**Revisit:** End of Phase 1b. If the executor's tool list turns out to be too restrictive (e.g. we discover legitimate need for `WebFetch`), expand the allowlist deliberately rather than dropping restrictions wholesale.

---

## 2026-06-14 — Tier-based step selection for the 10-step workflow

**Decision:** The 10-step loop is no longer uniformly applied. Sessions classify as Trivial (Steps 1, 7, 8), Small (1, 3, 5, 7, 8), Medium (1, 2, 3, 5, 7, 8), or Large (full 1–10). Tier is chosen at Step 1 using the five-minute decision rule in `.claude/templates/tiering.md`. Mid-session escalation is allowed via the escalation protocol (STOP → log → reset brief → restart at the new tier's correct step).

**Why:** Running the full loop on a typo fix or a 50-LOC helper is ~4–8x token overhead with near-zero quality gain. Step 6 (Verify Execution) in particular has the lowest yield-per-token in the loop because Step 7 (parent Triple Check) already catches what Step 6 would. Tiering preserves rigor where it matters (parser, schema, RAG core) and removes it where it doesn't (config tweaks, doc edits).

**Rejected:**
- Two-tier system (fast path vs full loop). Too coarse — most Phase 1a work falls between "typo" and "build the parser".
- Letting sub-agents self-select tier. Parent owns this — sub-agents see only their assigned tier's charter.

**Revisit:** After 5 full-loop sessions of real Phase 1a/1b work. If Step 6 catches something Step 7 missed, restore Step 6 to Medium tier.

---

## 2026-06-14 — Context-cache brief block for sub-agent prompts

**Decision:** Every sub-agent dispatch in a Medium or Large tier session is prefixed with a byte-for-byte identical "context brief" block, templated at `.claude/templates/sub-agent-brief.md`. The brief contains phase, tier, branch, guardrails-in-force, decisions-in-force, OUT-OF-SCOPE, fixtures-to-leave-alone, and resolved open questions.

**Why:** Two reasons:
1. **Direct context savings.** Without the brief, each sub-agent reads CLAUDE.md (~150 lines) + agent-conduct.md (~80 lines) + the relevant phase doc to learn the rules — ~3-5k input tokens per dispatch, or ~12-20k across a 4-sub-agent Large-tier loop.
2. **Prompt-cache prefix reuse.** Anthropic prompt caching keys on identical token prefix with a 5-minute TTL. An identical brief across the 4 sub-agents of one loop pays the prefix cost once and reads cache (~10x cheaper) on the other three. See `.claude/templates/prompt-caching.md` for the mechanics and timeline.

**Rejected:**
- Letting sub-agents read CLAUDE.md fresh each time. Wasteful; same content re-encoded each call.
- Including volatile content (diffs, test output) in the brief. Breaks the cache. Volatile content goes in the role-specific tail of the prompt, not the brief.

**Revisit:** After 3 Medium/Large sessions, measure `cache_read_input_tokens` vs `input_tokens` ratio. Target: >60% cache reads on dispatches 2–4 of a loop. If lower, the brief is drifting between calls — investigate and tighten.

---

## 2026-06-13 — Synthetic data `.gitignore` — samples-only allow-list

**Decision:** `.gitignore` excludes `data/synthetic/*` broadly and re-includes only `data/synthetic/samples/`. Bulk generator outputs (20–50 MB `results.csv` / `results.json` from 1k-panel runs) must go to `data/synthetic/<run_id>/` or any sibling of `samples/` — never into `samples/` itself. Only deliberately curated small example files belong in `samples/`.

**Why:** A `git add .` after a generator run would otherwise drop ~50 MB blobs into the index and blow past GitHub's 100 MB file limit (or at minimum bloat the repo). Guardrail #4 in CLAUDE.md ("all committed data is synthetic") does not mean all synthetic data should be committed — only small samples for documentation / parser fixtures.

**Implementation notes:**
- Used `data/synthetic/*` (not `data/synthetic/`) because the trailing-slash form blocks gitignore re-include rules for any subpath of the excluded directory. The `/*` form excludes one level of entries and lets `!data/synthetic/samples/` actually take effect.
- Also narrowed the existing `!data/synthetic/**/*.log` re-include to `!data/synthetic/samples/**/*.log` so a bulk run's `.log` files don't sneak back in via the broader `*.log` rule.
- `data/synthetic/samples/.gitkeep` committed so the samples dir exists in fresh clones.

**Rejected:** Per-extension exclude (`data/synthetic/**/*.csv`, `**/*.json`) — fragile; a new output format would silently slip through. Excluding by size — git doesn't natively support it.

**Revisit:** If the generator gains a "minimal demo" output mode that's small enough to commit alongside parser fixtures, place those under `samples/` and document the convention in the generator's spec.

---

## 2026-06-13 — Branching strategy: Option A (feature/* → dev → main)

**Decision:** Two permanent branches (`main`, `dev`). All work on short-lived `feature/[name]` branches. Merge feature → dev as tasks complete; dev → main at phase boundaries.

**Why:** Solo portfolio project. ROADMAP.md already tracks phase gates — git branches don't need to mirror them. Lowest overhead, cleanest history.

**Rejected:** Option B (phase/[name] branch layer between feature and dev). Adds merge ceremony without adding clarity for a solo project.

**Revisit:** After first contributor joins — may layer in phase branches then.

---

## 2026-06-13 — hrk-agent-starter as portable governance kit

**Decision:** All AI agent skills, hooks, rules, and log templates live in a separate repo (`-hrk-agent-starter` on GitHub). New projects are stamped via `stamp.ps1` or GitHub template. Skills are owned by the kit repo; project-specific adaptations live in the project.

**Why:** Owner wants to start any future project with the same governance discipline without rebuilding it from scratch each time. Single source of truth for skills means improvements propagate across all future projects.

**Rejected:** Keeping skills only in each project (no canonical source, diverges over time). Git submodule (too much overhead for a stamp-and-forget workflow).

**Revisit:** After 2-3 projects stamped — decide whether to version the kit with releases.

---

## 2026-06-13 — 10-step multi-agent loop as canonical workflow

**Decision:** The session-workflow skill defines a 10-step loop with specific agent roles. Steps 3 (Plan) and 7 (Triple Check) are parent-only and can never be delegated. Out-of-scope bugs are logged immediately and surfaced via spawn_task at step 8.

**Why:** The triple comparison (Found vs Planned vs Executed) catches executor drift, report inflation, and plan gaps — three failure modes that aren't caught by tests alone. The explicit handoff step ensures no context is lost between sessions.

**Rejected:** Simpler linear pipeline with no triple check. Catches fewer failure modes.

**Revisit:** After Phase 1b — tune step count and agent charters based on real usage.

---

## 2026-06-13 — Governance system adopted from my-assembly-hub

**Decision:** Use the same agent-governance pattern as `my-assembly-hub`:
hooks (block_dangerous_git, plan_approval_gate, doc_reminder_stop), rules (agent-conduct,
session-workflow, testing), skills (plan-architect, execute-plan, test-generator, session-workflow,
diagnose), and log files (BUG_LOG, DECISION_LOG, AGENT_HANDOFF_LOG, SESSION_LOG).

**Why:** Owner already runs assembly-hub this way successfully. Consistent pattern across projects
means zero ramp-up time. The governance layer enforces discipline without needing to re-explain it.

**Rejected:** A lighter-weight approach (just CLAUDE.md). Too easy to skip steps on a portfolio project
that no one else is reviewing.

**Revisit:** After Phase 2 — add skills for analytics-specific patterns if needed.

---

## 2026-06-13 — TDD as the default workflow

**Decision:** Tests are written before implementation in every phase. Red → Green → Refactor.
No implementation is committed without a corresponding test.

**Why:** Portfolio project — demonstrates software engineering discipline. Also prevents silent bugs
in the synthetic-data → parser → DuckDB pipeline where a wrong value produces wrong analytics silently.

**Rejected:** Build-then-test. Explicitly rejected by owner.

**Revisit:** Never. Standing rule.

---

## 2026-06-13 — Tech stack locked

**Decision:** Python 3.11+, uv, DuckDB, ChromaDB + sentence-transformers + rank-bm25,
Gemini API (primary LLM), Claude API (backup), Streamlit + Plotly.

**Why:** Full AI engineering stack on a portfolio-demonstrable footprint. DuckDB handles
analytical queries without a server process. ChromaDB + BM25 gives hybrid retrieval.
Streamlit keeps the UI fast to build. Gemini is free-tier friendly for portfolio work.

**Rejected:** PostgreSQL (overkill for local-only), React frontend (too much overhead for
a solo portfolio project), OpenAI as primary (cost + Gemini is sufficient).

**Revisit:** After Phase 3 — if Gemini quality disappoints, switch to Claude API.

---

## 2026-06-13 — HP3070 / Keysight i3070 log format as v1 target

**Decision:** Target HP3070-style flying-probe logs as the only supported format in v1.
Generic multi-format parser is deferred.

**Why:** Narrow scope = shippable within the timeline. HP3070 is the format the owner
encounters most in their professional context. Good enough for portfolio demonstration.

**Rejected:** Multi-format parser in v1 (too broad; makes Phase 1a unbounded).

**Revisit:** After Phase 1b — decide if Takaya format is worth adding for variety.

---

## Template

```
## YYYY-MM-DD — Short title

**Decision:** What was decided, in plain English.

**Why:** The reason — include constraints, tradeoffs, and stakeholder input.

**Rejected:** What alternatives were considered and why they were ruled out.

**Revisit:** When (phase boundary, date, condition) and what might change the decision.
```
