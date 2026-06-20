# Decision Gate record — Phase 2 slice 2 (Step 6)

**Date:** 2026-06-18 · **Owner sign-off:** YES (all four recommendations ratified) · **Gate:** CLEARED → Execute unblocked.

## Decision Index

| # | Decision | Owner choice | Plan refs |
|---|----------|--------------|-----------|
| G1 | SPC alarm-rule family | **Wheeler/XmR** — default `('rule_1','rule_4')`, opt-in `('rule_2','rule_3')`, run length 8 | L1, L2 |
| G2 | Individuals-chart value / signature | **Add `refdes` selector** — chart per-panel `mean(measured_value)` for a `(board_profile_id, refdes)`; optional `record_type` | L4, L5 |
| G3 | Anomaly metric | **Per-group failure rate** (fail/total), leave-one-out baseline, raw proportion, severity-first ordering | L10, L11, L12, L16 |
| G4 | Stretch scope | **Defer both** X-bar/R and Isolation Forest → no `sklearn`, **no schema change**, no approval-gated file edits | L18 |

## Coverage check (every plan decision accounted for)

- L1/L2 ✅ G1 · L3 (MR̄/1.128 exact, R1-B1) parent-locked · L4/L5 ✅ G2 · L6/L7 SPCPoint shape parent-locked
- L8/L9 AnomalyRow shape parent-locked · L10/L11/L16 ✅ G3 · L12–L15/L17 parent-locked statistics policy
- L18 ✅ G4. Red-team Revision 1 (R1-B1, R1-W1..W4, R1-M1..M3) all binding on Execute.

## Approval-gated files — confirmed untouched

`pyproject.toml`, `db/schema.py`, `migrations/*`, `.claude/settings.json`, `.env.example` — **none edited.**
G4 (defer sklearn) removes the only reason slice 2 would have touched `pyproject.toml`. No schema change needed:
existing `measurements` / `components` / `test_runs` / `panels` columns are sufficient (R1-W1 join path confirmed).

## What the owner did NOT pick (recorded for DECISION_LOG)

- Nelson 8-rule set (N7/N8 need subgroups; full stack ~7–9× false alarms) — rejected.
- Rule-1-only (misses sustained shifts rule_4 catches) — rejected.
- `duration_s` as the I-MR value (constant=12, zero variance) — rejected.
- Isolation Forest / `sklearn`, X-bar/R — deferred (revisit conditions in DECISION_LOG).
- Raw failure count metric (scales with volume) — rejected.
