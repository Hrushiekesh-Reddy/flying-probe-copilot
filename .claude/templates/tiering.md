# Session tiering — choosing a task class

> Read at the start of every session AFTER the Step 1 brief is written.
> The tier you pick determines which of the 10 workflow steps run.
> Wrong tier = wasted tokens (over-engineered) or wasted time (under-engineered).

---

## The four tiers

| Tier | Run these steps | Typical signal |
|------|-----------------|----------------|
| **Trivial**  | 1 → 7 → 8 | Typo, single-line config, doc edit, README tweak |
| **Small**    | 1 → 3 → 5 → 7 → 8 | One file, ≤200 LOC, one module, one concept |
| **Medium**   | 1 → 2 → 3 → 5 → 7 → 8 | New feature, 2–4 files, cross-module, but mechanism is clear |
| **Large**    | Full 1–10 | New subsystem, schema change, RAG core, parser core, anything irreversible |

`/session-workflow Steps 4 (Verify Plan), 6 (Verify Exec), 9 (Manual QA), 10 (Handoff) — appear only in Large.`

---

## Five-minute tier decision (run at start of session)

Ask yourself, in order:

1. **Is the change one file, ≤30 lines, no logic?** → Trivial.
2. **Is the change one module, one concept, with tests already obvious?** → Small.
3. **Will the change touch ≥3 files OR introduce a new abstraction OR cross a phase deliverable boundary?** → Medium.
4. **Is the change to a schema, migration, parser core, RAG retriever, or anything where a bug ships data corruption?** → Large.
5. **Is the change RISKY for any reason (irreversible, public-facing, runs on real data)?** → Bump one tier up.

If you can't pick in 5 minutes, default to **Medium** — it's the highest-value tier per token spent.

---

## Worked examples (flying-probe-copilot)

| Task | Tier | Why |
|------|------|-----|
| Fix typo in CLAUDE.md | Trivial | Doc edit, no code |
| Add `--seed` flag to generator CLI | Small | One file, obvious tests |
| Add a new board profile (medium-double-sided) | Small | Config-shaped, fixture-shaped |
| Build the fault-injection module | Medium | New abstraction, multiple files, but mechanism is clear |
| Build the HP3070 log writer | Medium | Cross-file but bounded by output spec |
| Build the parser | **Large** | Phase 1b core; bugs corrupt the DB downstream |
| Add a column to DuckDB schema | **Large** | Schema = approval-gated, requires migration |
| Wire up Gemini API for the RAG co-pilot | **Large** | New external dependency, secret handling, Phase 3 core |

---

## What each tier skips, and why

### Trivial — skips Explore, Plan, Verify-Plan, Execute-as-sub-agent, Verify-Exec, Manual-QA, Handoff
The parent can do the whole thing inline. Step 7 (Triple Check) is still run — even a typo deserves a read-back before commit. Step 8 (Docs/git) is still run because everything goes through the same logging discipline.

### Small — adds Plan and Execute (as sub-agent)
You skip Explore because the parent already knows the touch points. You skip Verify-Plan because the plan is small enough that the parent can self-review. You skip Verify-Exec because Step 7 catches anything Verify-Exec would. The Execute sub-agent IS used so tool restrictions still apply.

### Medium — adds Explore
Explore returns when the parent can't enumerate touch points from memory. Verify-Plan is still skipped — the plan is large enough that the parent's own Step 7 read is what catches errors.

### Large — full loop
Verify-Plan + Verify-Exec come back. The token cost is justified by the blast radius — a bug in the parser corrupts every downstream query.

---

## Mid-session escalation (Q3 — what if the tier was wrong?)

If you started Trivial/Small/Medium and discover the work actually needs a higher tier (e.g. the "small" CLI flag turns out to require a schema column), DO NOT keep going at the current tier. Escalate explicitly:

### Escalation protocol

1. **STOP the current sub-agent immediately.** Do not let it keep working with the wrong tier's guardrails.
2. **Log the escalation** in the session brief under a `### Tier escalation` section:
   ```
   ### Tier escalation — [timestamp]
   Original tier: Small
   New tier:      Medium
   Trigger:       Found that --seed flag requires a new column in the run_metadata table
   Cost so far:   ~3k tokens, no commits, no edits to gated files
   ```
3. **Reset the session brief.** The OUT-OF-SCOPE block and SUCCESS-WHEN criteria may now be wrong — rewrite them.
4. **Restart from the appropriate step of the new tier.**
   - Trivial → Small: restart at Step 3 (Plan), because you now need one.
   - Small → Medium: restart at Step 2 (Explore), because you need touch-point mapping.
   - Medium → Large: restart at Step 4 (Verify Plan), because the blast radius now justifies adversarial review.
5. **Tell the owner.** Escalations are informative — owner may decide to defer the work to a separate session instead of expanding the current one.

### Anti-pattern (do not do this)

- "I started this as Small but I'll just add an Explore step and keep going." → No. The current sub-agent has stale context. Stop, reset, restart cleanly.
- "I'll quietly add the schema column inline since the parent will catch it." → No. Approval-gated files require an explicit pause regardless of tier.
- Treating escalation as failure → it's not. Catching a wrong tier 5k tokens in is a feature; catching it 50k tokens in is a bug.

---

## Anti-tier (when to DECLINE to start)

If you can't pick a tier even after the 5-minute decision, the request is under-specified. STOP at Step 1. Ask the owner to clarify. Bad tier choice on a vague request burns 10x the tokens of a clarifying question.
