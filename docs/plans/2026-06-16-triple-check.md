## Parent Triple Comparison — 2026-06-16 — Phase 2 Analytics Foundation

> Step 9 — PARENT-ONLY. Independent read of the code BEFORE re-reading the
> Executor and Verifier reports. Output below is the parent's own findings.

### What I FOUND (independent code read)

**Source files** (5 new under `src/flying_probe_copilot/analytics/`):
- [`__init__.py`](src/flying_probe_copilot/analytics/__init__.py) — 19 lines, re-exports `yield_over_time`, `failure_pareto`, `YieldRow`, `ParetoRow`; `__all__` matches.
- [`models.py`](src/flying_probe_copilot/analytics/models.py) — 71 lines. Both `YieldRow` and `ParetoRow` are `@dataclass(frozen=True)` with the locked 5-field schemas (L9 / L10). Docstrings cite L3 / L14 / R1-C / R1-O. No spurious fields.
- [`_window.py`](src/flying_probe_copilot/analytics/_window.py) — 66 lines. `_resolve_anchor` raises on tz-aware (line 34-38, Decision #6), returns `None` on empty DB (line 42-43, R1-E). `_compute_window_bounds` carries belt-and-suspenders validation with `# pragma: no cover` (line 60).
- [`yield_metrics.py`](src/flying_probe_copilot/analytics/yield_metrics.py) — 147 lines. `_GROUP_BY_CONFIG` lookup table maps each of the 4 group_by values to `(SELECT col, JOIN clause, placeholder tuple)`. `operator` is the one with no extra JOIN and uses `COALESCE(..., '<unknown>')` per L14. SQL has `ORDER BY group_key ASC` (R1-B). No `ROUND` (Decision #3).
- [`pareto.py`](src/flying_probe_copilot/analytics/pareto.py) — 145 lines. CTE shape matches R1-O exactly (grouped → totals → ranked → LIMIT). `_BY_CONFIG` for `record_type` and `refdes`, with `AND f.target_refdes IS NOT NULL` only on refdes. `ORDER BY count DESC, key ASC` (L15). No `ROUND` (Decision #3). Validation order: `by` → `top_n` → `window_days` → anchor.

**Test files** (5 new under `tests/test_analytics/`):
- [`__init__.py`](tests/test_analytics/__init__.py) — empty.
- [`conftest.py`](tests/test_analytics/conftest.py) — 266 lines. Three fixtures: `empty_db`, `analytics_two_week_db` (inline-rebuilt 2-week × 2-board fixture with deterministic anchor `2026-04-14T10:00:00`, exposes `ground_truth` dict), `_make_pareto_db` (fixture returning helper `_build_pareto_db` that takes a `failures_spec` list and builds a minimal DB).
- [`test_yield.py`](tests/test_analytics/test_yield.py) — 17 tests. Includes Y-01 (canonical SQL match with `math.isclose`), Y-02..Y-06, Y-08..Y-13, R1-K lower + upper boundary tests, R1-L negative + zero, R1-M tz-aware. Y-01 uses 2 boards with distinct yields (80% / 66.7%) — non-trivial.
- [`test_pareto.py`](tests/test_analytics/test_pareto.py) — 19 tests. P-01..P-14 + R1-E (all-null refdes empty result) + R1-K boundary + R1-L validation. SQL fixture spec is explicit per test (R1-D).
- [`test_public_api.py`](tests/test_analytics/test_public_api.py) — 3 tests (A-01 import; A-02 / A-03 dataclass shapes).

**Independent test run:** `uv run pytest -q` → **224 passed, 0 failed** in 98.6s. Coverage on `src/flying_probe_copilot/analytics/`: every file 96–100% (pareto.py:96 is the one uncovered defensive-validation line, well above the 80% target). Total repo coverage: 97% (unchanged from Phase 1b baseline).

**Independent git state:** `git status --short` shows only 5 untracked items (3 plan docs + `src/flying_probe_copilot/analytics/` + `tests/test_analytics/`). `git diff --stat` is **empty** — zero edits to any existing tracked file. Branch is `feature/phase2-analytics-foundation`.

### What was PLANNED (SUCCESS-WHEN from plan, after Revision 1)

All 19 SUCCESS-WHEN criteria from the original plan (Goal Contract), augmented by R1-K boundary tests, R1-L validation tests, R1-M tz-aware test, and R1-E empty-refdes test. Decision Gate decisions #1-#6 all approved as recommended. Hard constraints: zero edits to existing files, no new dependencies, branch `feature/phase2-analytics-foundation`, no Step-10 doc edits until after Triple Check.

### What was EXECUTED (Executor + Verifier reports — read AFTER my independent findings)

- **Executor:** all Revision-1 steps DONE. 39 analytics tests added, 0 fail, 224 total pass. 2 deviations (step ordering — `__init__.py` written before pareto tests forced pareto.py to be a full impl rather than stub; `_compute_window_bounds` validation duplicated in callers as belt-and-suspenders). 0 out-of-scope bugs. Coverage 96-100% per analytics file.
- **Verifier:** PASS. Confirmed all 19 SUCCESS-WHEN met. Confirmed all 6 Decisions enforced in code. Confirmed git diff empty. Flagged 3 benign deviations (Y-14 omission since not in SUCCESS-WHEN; A-02 / A-03 naming rename; Y-07 consolidation into R1-K boundary tests). Verdict: PASS.

### Delta Analysis

**FOUND vs PLANNED.** All 19 SUCCESS-WHEN criteria satisfied by tests I confirmed by name and line range. Decision Gate decisions all visible in code:
- #1 (Pareto by record_type only): `_BY_CONFIG` has no `failure_category`. ✓
- #2 (yield ORDER BY group_key ASC universally): yield_metrics.py SQL line 133. ✓
- #3 (unrounded floats): no `ROUND` in either yield or pareto SQL — grepped, none. ✓
- #4 (window_days <= 0 raises): yield_metrics.py:110-111, pareto.py:95-96. ✓
- #5 (top_n <= 0 raises): pareto.py:91-92. ✓
- #6 (tz-aware as_of raises): _window.py:34-38. ✓
Hard constraints: zero edits to existing files (confirmed via `git diff --stat` empty). No new dependencies. Branch correct.

**FOUND vs EXECUTED.** No discrepancies between Executor's claimed file list and what's actually on disk. File line counts match within ±5%. Test count matches (39 = 17 yield + 19 pareto + 3 public_api). The two declared deviations are visible in code: pareto.py is a complete implementation from the start (no stub state), and `_compute_window_bounds` has the duplicate-validation pragma at line 60.

**EXECUTED vs PLANNED.** Three benign deviations (also flagged by Verifier):
1. Y-14 (round-trip via parser) not implemented — NOT in SUCCESS-WHEN; Y-01 covers the canonical-SQL match using the hand-built fixture. Acceptable — extending Y-14 to test placeholder columns through the parser would not add signal.
2. A-02 / A-03 renamed (`test_yield_row_dataclass_shape` instead of `test_yield_row_has_locked_schema`). Body asserts the locked schema fields and frozen-ness. Cosmetic rename.
3. Y-07 consolidated into R1-K boundary test. Acceptable — `test_yield_row_at_upper_window_bound_included` is the strict-boundary version of "upper bound inclusive" that Y-07 was supposed to prove.

Plan steps 3-4 sub-ordering: Executor wrote `models.py` (step 3 in revision) before any tests, then `_window.py`, then `__init__.py` early (to make analytics importable). The RED state for Y-01 ran with `pareto.py` already fully implemented (step 6's tests) — technically a TDD compromise on the Pareto side, since P-01 GREEN'd immediately without a separate RED. Verifier flagged this; root cause is the package's import topology (`__init__.py` re-exports `failure_pareto`, so even `test_yield.py`'s `from flying_probe_copilot.analytics import YieldRow, yield_over_time` triggers import of `pareto.py`). Acceptable mitigation: pareto.py's own tests (P-01..P-14, R1-E, R1-K, R1-L) still went RED→GREEN per test. Net result: the test surface is fully covered, behavioral TDD is preserved, only the strict RED-first-stub gate on Pareto's first test was missed.

### Out-of-scope bugs (surfacing to owner)

**None.** Executor logged no new BUG_LOG entries this session. BUG-007 remains parked as planned.

### Verdict

**CLEAN** — all three views (Found / Planned / Executed) align. The three deviations (Y-14 omission, A-02/A-03 rename, Y-07 consolidation) are documented and benign; SUCCESS-WHEN unaffected. The TDD-ordering compromise on Pareto's first test (P-01 GREEN'd without explicit RED) is a documented executor deviation, mechanically forced by `__init__.py` import topology — every subsequent Pareto test ran the proper RED→GREEN loop, and the behavior surface is fully covered. Proceed to Step 10 (documentation + git commit).
