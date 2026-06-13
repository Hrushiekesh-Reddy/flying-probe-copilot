# Decision Log — Flying-Probe Co-Pilot

Architectural, design, and process decisions in reverse-chronological order.
Every non-obvious choice gets an entry here: what was decided, why, what was rejected, and when to revisit.

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
