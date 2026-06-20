# Triple Check — Phase 2 slice 2 (Step 9, parent-only, independent)

**Date:** 2026-06-18 · **Verdict: CLEAN** · Found vs Planned vs Executed compared independently
(parent re-read every new file line-by-line and re-ran pytest; did not rely on the exec report alone).

## Independent re-run

`uv run pytest -q` (parent's own run): **292 passed, 1 xfailed, 0 failed**, 75s.
Coverage: `spc.py` **100%**, `anomaly.py` **100%**, `models.py` 100%, repo-wide **97%** (= slice-1 baseline).
spc.py + anomaly.py both clear the ≥80% target with margin.

## Found vs Planned vs Executed

| Plan item | Planned | Executed | Verdict |
|-----------|---------|----------|---------|
| Sigma estimator | `MR̄/1.128`, exact, no literal 2.66 (R1-B1) | `sigma_hat = mr_bar/1.128`, `ucl=center+3*sigma_hat` (spc.py:156-159); SPC-01 pins exact value AND asserts NOT-isclose to `3*statistics.stdev` | ✅ |
| SPC join path | `measurements→test_runs→components` on component_id (R1-W1) | exactly that join, `c.board_profile_id`+`c.refdes` filter, `measured_value IS NOT NULL`, optional `record_type` branch (spc.py:106-136); fixture inserts components+component_id | ✅ |
| Flag convention | flag every point whose trailing window satisfies (R1-W3) | run-tracking for rule_4 (8+), trailing-3/trailing-5 for rule_2/3; 9-run flags pts 8 & 9 (test_spc_rule4_9run) | ✅ |
| Opt-in gating | rule_2/rule_3 silent unless in `rules` | guarded by `in rules_set`; SPC-07/SPC-10 prove silence under default | ✅ |
| Leave-one-out | peers exclude self from mean AND std (S3) | per-group peer list excludes g (anomaly.py:161); ANOM-01 proves bm=peer-only (≠0.375), ANOM-02 proves per-group | ✅ |
| `<2 peers` guard | no `statistics.stdev` on 1 elem (R1-W4) | `if len(peers)<2: baseline_std=0.0` (anomaly.py:164-167); ANOM-13 two-group passes (no raise) | ✅ |
| ddof=1 | sample std | `statistics.stdev` (ddof=1); ANOM-06 pins vs pstdev | ✅ |
| Ordering | `abs(z) DESC, group_key ASC` (L16) | `result.sort(key=lambda r:(-abs(r.z_score),r.group_key))` (anomaly.py:188); ANOM-08 | ✅ |
| Contracts | naive UTC, ValueError wording, unrounded, empty→[] | `_resolve_anchor` reused; slice-1 wording verbatim; SPC-14/15/20, ANOM-15/16/17/18/19 | ✅ |
| Edge cases EC1–EC17 | all tested, none raises | SPC-16/17/18/19/20 + ANOM-10/11/12/13/14/15 all green | ✅ |
| Rule pos+neg | every rule both polarities | rule_1 SPC-03/04, rule_4 SPC-05/06, rule_2 SPC-08/09(+07 gate), rule_3 SPC-11/12(+10 gate) | ✅ |
| Dataclasses | SPCPoint/AnomalyRow per spec | match handover field names (`value,mean,ucl,lcl,alarm_flags` / `value,baseline_mean,baseline_std,z_score,flagged`); no placeholder_fields (API-03/04 guard) | ✅ |
| Scope | only the 8 allowed files + BUG_LOG | `git diff` = models.py, __init__.py, conftest.py, test_public_api.py, BUG_LOG.md; untracked spc.py, anomaly.py, test_spc.py, test_anomaly.py | ✅ |
| Approval-gated files | untouched | `git diff` over pyproject/schema/settings/.env = empty | ✅ |

## Deviations (from exec report — all benign, verified)

1. **E0 full-impl-not-stub.** Exec wrote implementations alongside tests rather than NotImplementedError
   stubs. RED state = "module did not exist yet". TDD intent preserved (tests authored first); every test
   asserts real behavior with hand-computed values, not tautologies — verified by reading all 50 tests.
   Accepted.
2. **SPC-05/06 fixture redesign.** Original step-function `[below×2, above×8]` mathematically forces
   rule_1 violations on the below-center points (the executor proved this). Switched to alternating
   baseline `[10000,10200,…]` giving wide limits so only rule_4 fires. Behavior asserted is unchanged
   (8-run trips, 7-run doesn't); fixture is side-agnostic (run can be above or below center — rule_4 is
   sign-only, so this is correct). Verified the test still pins the 8-vs-7 boundary. Accepted.

## Out-of-scope (logged, not fixed)

- **BUG-011** (`test_tokenize_balances_braces_returns_records` flaky under full suite) — pre-existing
  parser-test order dependency, confirmed by exec via `git stash`; **passed in the parent's full-suite
  run**, so it did not block. Logged P2/OPEN, chipped (task_1a493613). NOT this slice's code.
- BUG-010 (TestJetRecord collection warning) — still open, pre-existing.

## Conclusion

Implementation matches Plan + Revision 1 + the four owner-ratified Decision-Gate choices with no
unjustified divergence. All red-team BLOCKER/WARNING resolutions are present in the shipped code and
defended by tests. **CLEAN — proceed to notebook + docs + PR.**
