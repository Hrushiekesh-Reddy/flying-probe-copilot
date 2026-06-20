# Plan — Phase 2 slice 2: SPC + anomaly detection

**Date:** 2026-06-18 · **Branch:** `feature/phase2-slice2-spc-anomaly` · **Tier:** Large
**Author:** parent (Step 3 — NOT delegated) · **Informed by:** `2026-06-18-phase2-slice2-explore` workflow (5-agent research+map+synthesis)

---

## Goal Contract

Ship two pure-library analytics functions over the existing DuckDB schema:

1. `individuals_chart(...) -> list[SPCPoint]` — a Shewhart **individuals (I-MR / XmR)** control
   chart over a chosen component's parametric reading, with Wheeler-doctrine alarm rules.
2. `z_score_anomalies(...) -> list[AnomalyRow]` — per-group failure-rate anomaly detection with a
   **leave-one-out** baseline.

Both mirror the slice-1 contracts exactly (naive-UTC `as_of`, `ValueError` on tz-aware / bad-enum /
`window_days < 1`, unrounded floats, `MAX(test_runs.start_ts)` anchor, inclusive `[anchor-d, anchor]`
window, `[]` on empty). No UI. No schema change. No new dependency. Pure-additive: extend
`analytics/models.py` + `analytics/__init__.py`; add `analytics/spc.py` + `analytics/anomaly.py`; do
not edit `yield_metrics.py` / `pareto.py` / `_window.py`.

**SUCCESS-WHEN:**
- S1. `spc.py` + `anomaly.py` implement the signatures in §Decisions, ≥80% coverage each.
- S2. Sigma is `MR̄ / 1.128` (NOT sample stdev). Verified in code review + a dedicated test.
- S3. Anomaly baseline excludes the evaluated group from its own mean & std (leave-one-out). Asserted.
- S4. Every implemented alarm rule has a positive (trips) AND negative (does-not-trip) test.
- S5. Every edge case in §Edge-cases has a test; none raises (all return `[]` / zero-width limits / no flag).
- S6. Full pytest suite green; repo coverage ≥97% (slice-1 baseline).
- S7. Notebook SPC + anomaly cells added and smoke-tested in-process.
- S8. Manual-QA script written. All doc updates landed. PR opened to `dev`.

**MUST-NOT:**
- Touch approval-gated files (`pyproject.toml`, `db/schema.py`, `migrations/*`, `.claude/settings.json`,
  `.env.example`) without owner sign-off.
- Reintroduce `placeholder_fields` markers (removed 2026-06-18).
- Use sample/global stdev for individuals control limits.
- Include the evaluated group in its own anomaly baseline.
- Implement X-bar/R or Isolation Forest in this slice (deferred — Decision Gate).
- Commit before Step 10; push without owner request.

---

## Locked decisions (L1–L18) — pending owner ratification at the Decision Gate (Step 6)

Items marked **[GATE]** are surfaced to the owner as explicit questions; the rest are parent
recommendations documented for ratification.

**SPC design**

- **L1 [GATE]** Alarm-rule family = **Wheeler / XmR doctrine** (Western-Electric-derived rules on an
  individuals chart, with Wheeler's "Rule 1 default, others in reserve" discipline). Default-on
  `('rule_1', 'rule_4')`; opt-in `('rule_2', 'rule_3')` via the `rules` parameter. **Rejected:**
  Nelson-all-8 (Rules N7/N8 require subgroups; full stack → ARL~38, 7–9× false alarms), X-bar/R
  (no rational subgroups), attribute charts (different surface). → DECISION_LOG.
  - rule_1: one point beyond 3-sigma (`value > ucl or value < lcl`). Distribution-robust headline flag.
  - rule_4: run of **8** consecutive points on the same side of the center line. Sign-only → robust
    to non-normality. (Wheeler/WECO use 8; Nelson uses 9 — **L2 [GATE]** picks 8.)
  - rule_2 (opt-in): 2 of 3 consecutive beyond 2-sigma, same side.
  - rule_3 (opt-in): 4 of 5 consecutive beyond 1-sigma, same side.
- **L2 [GATE]** Run length for rule_4 = **8** (Wheeler canonical), not 9 (Minitab/Nelson).
- **L3** Sigma estimator = **MR̄ / d2, d2 = 1.128** (moving range span 2). 3-sigma limits =
  `center ± 3·(MR̄/1.128)` = `center ± 2.66·MR̄`. **Never** sample/global stdev. (S2)
- **L4 [GATE]** Individuals-chart value = **per-panel `mean(measurements.measured_value)` filtered to
  one `(board_profile_id, refdes)`** (optionally `record_type`), time-ordered `start_ts ASC`.
  Rationale: `duration_s` is constant (=12, useless); `measured_value` is the only varying continuous
  metric but is per-component, so a refdes selector is required. **Rejected:** per-panel failure rate /
  measurement count (attribute data → wrong I-MR limits), `duration_s` (zero variance). → DECISION_LOG.
- **L5 [GATE]** Signature diverges from the handover's literal `individuals_chart(con, *,
  board_profile_id, window_days=30, as_of=None)` by adding required `refdes`, optional `record_type`,
  and a `rules` tuple:
  ```python
  def individuals_chart(
      con, *, board_profile_id: str, refdes: str,
      record_type: str | None = None, window_days: int = 30,
      rules: tuple[str, ...] = ("rule_1", "rule_4"),
      as_of: datetime | None = None,
  ) -> list[SPCPoint]
  ```
- **L6** `SPCPoint` (`@dataclass(frozen=True)`), key-first like slice-1, honoring the handover's named
  fields (`value, mean, ucl, lcl, alarm_flags`) plus `start_ts` (needed as the chart x-axis):
  ```python
  panel_serial: str
  start_ts: datetime
  value: float            # per-panel mean(measured_value) for the refdes (unrounded)
  mean: float             # center line = grand mean (same on every row, unrounded)
  ucl: float              # mean + 2.66·MR̄ (unrounded)
  lcl: float              # mean - 2.66·MR̄ (unrounded)
  alarm_flags: tuple[str, ...]   # subset of `rules` that fired on this point; () if none
  ```
- **L7** Empty filtered series (refdes has no rows in window) → `[]`. `< 2` points → return the
  point(s) with `sigma=0` ⇒ `ucl == lcl == mean`, `alarm_flags=()`; never raise. Constant series ⇒
  `MR̄=0` ⇒ zero-width limits, no flags; never divide by zero (rule logic compares, never divides by sigma).

**Anomaly design**

- **L8** `z_score_anomalies` signature (matches handover, `window_days=30`):
  ```python
  def z_score_anomalies(
      con, *, window_days: int = 30, threshold: float = 3.0,
      by: str = "board", as_of: datetime | None = None,
  ) -> list[AnomalyRow]
  ```
  `by ∈ {"board","shift","line","operator"}` — same vocabulary as slice-1 `yield_over_time`.
- **L9** `AnomalyRow` (`@dataclass(frozen=True)`), exactly the handover's fields:
  ```python
  group_key: str
  value: float            # per-group failure rate = failed/total (unrounded)
  baseline_mean: float    # leave-one-out mean of peer groups
  baseline_std: float     # leave-one-out sample std (ddof=1) of peer groups; 0.0 if <2 peers
  z_score: float          # (value - baseline_mean)/baseline_std; 0.0 when baseline_std==0
  flagged: bool           # baseline_std>0 and abs(z_score) >= threshold
  ```
- **L10 [GATE]** Anomaly metric = **per-group failure rate** `failed/total`, `failed = COUNT(btest_status
  != 0)`, `total = COUNT(*)` per group in window. **Rejected:** raw failure count (scales with volume),
  per-measurement out-of-spec count (double-counts), binary per-panel pass/fail (infinite-tail z). → DECISION_LOG.
- **L11 [GATE]** v1 z-scores the **raw proportion** (no logit/arcsin transform). Documented limitation:
  proportion z can violate normality at small group-N; revisit via transform if needed.
- **L12** **Leave-one-out** baseline (S3): for group `g`, `baseline_mean`/`baseline_std` are computed
  over the failure rates of **all other** groups in the window (g excluded from both). Python loop over
  explicit peer lists using stdlib `statistics` (`fmean`, `stdev` = ddof=1). Stdlib only — no new dep.
- **L13** **ddof = 1** (sample std) for the baseline. Documented (changes z magnitude vs population std).
- **L14** `flagged` predicate = **two-sided** `abs(z_score) >= threshold`.
- **L15** Return **one row per evaluable group** (group has total>0 and ≥1 peer), each labeled
  `flagged`. Single-group window → `[]`. Groups with total==0 excluded from candidates AND peers.
  `baseline_std==0` (≤1 peer, or identical peers) ⇒ `z_score=0.0`, `flagged=False` (no divide-by-zero).
- **L16 [GATE]** Anomaly ordering = **`abs(z_score) DESC, group_key ASC`** (severity-first). Diverges
  from slice-1's universal `group_key ASC` — anomaly lists are inherently severity-ranked. → DECISION_LOG.
- **L17** `threshold <= 0` → `ValueError(f"threshold must be > 0; received {threshold!r}")` (validated
  before the DB; non-positive threshold flags everything — caller error).

**Scope / shared**

- **L18 [GATE]** **Defer** X-bar/R (OQ3) and Isolation Forest/sklearn (OQ5 — new dep, approval-gated
  `pyproject.toml`). Slice 2 needs **no** schema change (OQ6). All three recorded in DECISION_LOG with
  revisit conditions. Both functions reuse `_resolve_anchor` + `_compute_window_bounds` from `_window.py`
  (no edits there). Validation order mirrors slice-1: enum/`window_days`/`threshold` → `_resolve_anchor`
  (tz check) → window bounds → SQL → build dataclasses. No `placeholder_fields`.

---

## Edge cases (each gets a test — S5)

| # | Function | Input | Expected |
|---|----------|-------|----------|
| EC1 | individuals | constant series (all values equal) | `MR̄=0` ⇒ `ucl==lcl==mean`; all `alarm_flags=()`; no crash |
| EC2 | individuals | single point in window | 1 SPCPoint, `ucl==lcl==mean`, `alarm_flags=()` |
| EC3 | individuals | `<2` points | available point(s), zero-width limits, no flags, no raise |
| EC4 | individuals | refdes with 0 matching measurements | `[]` |
| EC5 | individuals | series shorter than a rule window (e.g. 5 pts, rule_4 needs 8) | that rule cannot fire; no error |
| EC6 | individuals | empty DB (anchor None) | `[]` |
| EC7 | individuals | invalid rule name in `rules` | `ValueError` listing `'rule_1'..'rule_4'` |
| EC8 | individuals | tz-aware `as_of` | `ValueError` (via `_resolve_anchor`) |
| EC9 | individuals | `window_days < 1` | `ValueError` (slice-1 wording) |
| EC10 | anomaly | group with `total==0` | excluded from candidates and peers; no div-by-zero |
| EC11 | anomaly | all groups identical rate (zero between-group var) | `baseline_std=0` ⇒ all `z=0`, none flagged |
| EC12 | anomaly | single group in window | `[]` (no peers) |
| EC13 | anomaly | exactly two groups (1 peer each) | rows returned, `baseline_std=0`, `z=0`, `flagged=False` |
| EC14 | anomaly | all-fail group (rate=1.0) | valid; flags iff loo-z ≥ threshold; no NaN |
| EC15 | anomaly | empty DB (anchor None) | `[]` |
| EC16 | anomaly | `threshold <= 0` | `ValueError` |
| EC17 | anomaly | `window_days < 1` / bad `by` / tz-aware `as_of` | `ValueError` (slice-1 wording) |

---

## Ordered TDD steps (Step 7 Execute follows this; RED → GREEN → REFACTOR per step)

**E0 — Skeleton (enables import/collection).** Add `SPCPoint` + `AnomalyRow` to `analytics/models.py`;
create `analytics/spc.py` + `analytics/anomaly.py` with the signatures raising `NotImplementedError`;
add all four names to `analytics/__init__.py` `__all__`. (No behavior yet.)

**E1 — Fixtures (conftest additions, pure-additive).** In `tests/test_analytics/conftest.py` add:
- `spc_individuals_db` fixture: one board profile, ~18 panels over the window, each with one `R1`
  analog measurement, values ~N(10000, ~40) all inside limits, time-ordered; returns `(con, meta)`.
- `_make_spc_db` helper-fixture: builds an in-memory DB from an explicit ordered list of
  `(refdes, measured_value, start_ts)` rows (mirrors `_build_pareto_db` style) so each SPC test injects
  its own series (clean / single-outlier / run-shift / constant / single-point).
- `_make_anomaly_db` helper-fixture: builds groups with per-group `(total, failed)` specs across a
  chosen `by` dimension (board/shift/line/operator) so anomaly tests set exact rates.

**E2 — SPC tests RED → implement `individuals_chart` GREEN.** Write `tests/test_analytics/test_spc.py`
covering: canonical limits math (S2 — assert sigma == `MR̄/1.128`, `ucl/lcl == mean ± 2.66·MR̄`),
rule_1 +/−, rule_4 +/−, rule_2 +/− (opt-in gating: silent under default `rules`), rule_3 +/− (opt-in),
time-ordering, EC1–EC9. Then implement `spc.py`: SQL (join measurements→test_runs→panels, filter
board_profile_id+refdes[+record_type]+`measured_value IS NOT NULL`+window, `AVG` per
panel_serial+start_ts, `ORDER BY start_ts ASC, panel_serial ASC`), Python MR̄/limits/rule engine.

**E3 — Anomaly tests RED → implement `z_score_anomalies` GREEN.** Write
`tests/test_analytics/test_anomaly.py` covering: leave-one-out correctness (S3 — anomalous group's
`baseline_mean` reflects peers only, not pulled toward its own rate), positive (one bad group flagged)
+ negative (homogeneous → none flagged), each `by` value, ordering (L16), ddof=1, two-sided abs,
EC10–EC17. Then implement `anomaly.py`: per-group `total`/`failed` SQL (slice-1 group-by config shape),
Python leave-one-out loop with `statistics.fmean`/`statistics.stdev`, zero-variance guard.

**E4 — Public-API test.** Extend `tests/test_analytics/test_public_api.py` (or add a focused test):
import smoke for the 2 functions + 2 dataclasses; dataclass field-shape assertions for `SPCPoint` /
`AnomalyRow`.

**E5 — Notebook cells.** Append SPC + anomaly markdown+code cells to `notebooks/01-queries.ipynb`
(after Query 6, before cleanup); add the import to the setup cell. Smoke-test every new code cell
in-process against `data/db/sample.duckdb` (and assert `lcl <= mean <= ucl`). If `sample.duckdb` lacks
a refdes with enough points, note it in the cell + manual-QA (do not regenerate here — out of scope).

**E6 — Verify.** `uv run pytest -q` (full suite green) + `--cov=src --cov-report=term-missing`
(spc.py + anomaly.py ≥80%, repo ≥97%).

---

## What / Why / Where / When — file table (exec scope boundary)

| File | Action | Why |
|------|--------|-----|
| `src/flying_probe_copilot/analytics/models.py` | EDIT (additive) | add `SPCPoint`, `AnomalyRow` |
| `src/flying_probe_copilot/analytics/spc.py` | CREATE | `individuals_chart` |
| `src/flying_probe_copilot/analytics/anomaly.py` | CREATE | `z_score_anomalies` |
| `src/flying_probe_copilot/analytics/__init__.py` | EDIT (additive) | re-export 2 fns + 2 dataclasses |
| `tests/test_analytics/conftest.py` | EDIT (additive) | 3 new fixtures/helpers |
| `tests/test_analytics/test_spc.py` | CREATE | SPC tests |
| `tests/test_analytics/test_anomaly.py` | CREATE | anomaly tests |
| `tests/test_analytics/test_public_api.py` | EDIT (additive) | import + shape tests |
| `notebooks/01-queries.ipynb` | EDIT (additive) | SPC + anomaly cells |
| `docs/plans/2026-06-18-phase2-slice2-manual-qa.md` | CREATE | Step 11 QA |
| `docs/logs/{SESSION_LOG,DECISION_LOG,ROADMAP,BUG_LOG}.md`, `CLAUDE.md` | EDIT | Step 10 docs |

**Out of bounds for exec:** `yield_metrics.py`, `pareto.py`, `_window.py`, `db/schema.py`,
`pyproject.toml`, generator/parser code, `tests/test_parser/`, `tests/conftest.py`.

---

## Decision-Gate items (Step 6 — owner sign-off required before Execute)

G1 (L1/L2) Rule family Wheeler/XmR + default rules `{rule_1, rule_4}`, run length 8.
G2 (L4/L5) Individuals value = per-(board_profile_id, refdes) `mean(measured_value)`; signature gains `refdes`.
G3 (L10/L11/L16) Anomaly = per-group failure rate, raw proportion, leave-one-out, severity-first ordering.
G4 (L18) Defer X-bar/R **and** Isolation Forest/sklearn; confirm **no** schema change.
(Plus Step 5 red-team concerns folded in.)

---

## Revision 1 — resolutions of the Step 5 adversarial red-team (parent, binding on Execute)

Red-team verdict: **APPROVE_WITH_REVISIONS** (1 BLOCKER, 4 WARNING, 3 MINOR). Each resolved below;
these are binding refinements to the locked decisions and override any conflicting earlier text.

- **R1-B1 (BLOCKER — canonical sigma constant).** L3's two forms `3·(MR̄/1.128)` and `2.66·MR̄` differ
  by ~6.4e-4 and a `rel_tol=1e-9` test on the rounded form would fail a correct exact-division impl.
  **RESOLUTION:** the ONE canonical formula is `sigma_hat = MR̄ / 1.128` and
  `ucl = mean + 3*sigma_hat`, `lcl = mean - 3*sigma_hat` (exact division, NO literal `2.66` anywhere in
  code or test assertions). `2.66·MR̄` survives only as informal prose. Tests assert
  `ucl == mean + 3*(MR̄/1.128)` via `math.isclose(rel_tol=1e-9)` and the back-check
  `(ucl-mean)/3 == MR̄/1.128`. Keep the `NOT isclose(ucl, mean + 3*statistics.stdev(series))`
  assertion (defuses the real MR̄-vs-stdev landmine). SPC-01 series `[10,12,11,13,12]`: MR̄=1.5,
  mean=11.6, sigma=1.5/1.128=1.32979, ucl=15.58936…, lcl=7.61064…
- **R1-W1 (WARNING — SPC join path).** `refdes` is NOT on `measurements`; it lives on `components`
  keyed by `(board_profile_id, refdes) → component_id`, and `measurements.component_id` is the link.
  **RESOLUTION:** the SPC SQL is
  ```sql
  SELECT tr.panel_serial, tr.start_ts, AVG(m.measured_value) AS value
  FROM measurements m
  JOIN test_runs tr ON tr.test_run_id = m.test_run_id
  JOIN components c ON c.component_id = m.component_id
  WHERE c.board_profile_id = ? AND c.refdes = ?
    AND m.measured_value IS NOT NULL
    [AND m.record_type = ?]          -- only when record_type given
    AND tr.start_ts >= ? AND tr.start_ts <= ?
  GROUP BY tr.panel_serial, tr.start_ts
  ORDER BY tr.start_ts ASC, tr.panel_serial ASC
  ```
  `board_profile_id` comes from `components` (sufficient; no `panels` join needed). The `_make_spc_db`
  helper (E1) MUST insert matching `components` rows and set `measurements.component_id`, or every SPC
  test silently returns `[]`. A test must verify refdes isolation populates ≥2 distinct components.
- **R1-W2 (WARNING — float comparison).** **RESOLUTION:** every computed float
  (`value` when a ratio, `mean`, `ucl`, `lcl`, `baseline_mean`, `baseline_std`, `z_score`) is asserted
  with `math.isclose(rel_tol=1e-9)` (slice-1 Y-01 precedent). Reserve `==` only for exact-zero
  (`baseline_std == 0.0`, zero-width limits) and pass-through of exact-integer inputs.
- **R1-W3 (WARNING — flag placement convention).** **RESOLUTION (pinned):** a rule flags **every point
  whose trailing window satisfies the pattern.** Concretely, evaluating left-to-right in `start_ts`
  order: rule_1 flags any point with `value > ucl or value < lcl`; rule_4 flags every point that is the
  8th-or-later in an unbroken run of same-side points (so a 9-run flags points 8 and 9); rule_2 flags
  point `i` iff within the trailing 3-window ending at `i` there are ≥2 points beyond 2-sigma on the
  same side as a same-side majority and `i` is on that side; rule_3 flags point `i` iff its trailing
  5-window has ≥4 beyond 1-sigma on `i`'s side. Tests assert the EXACT flagged index set (incl. the
  9-run overlap case).
- **R1-W4 (WARNING — stdev guard).** **RESOLUTION:** `z_score_anomalies` computes
  `if len(peers) < 2: baseline_std = 0.0` (do NOT call `statistics.stdev` — it raises
  `StatisticsError` on a 1-element list); else `baseline_std = statistics.stdev(peers)` (ddof=1).
  Then `z = (value - baseline_mean)/baseline_std if baseline_std > 0 else 0.0`. Added to L12/L15.
- **R1-M1 (MINOR — rule_1 self-masking).** Keep the SPC-03 outlier comfortably above the
  with-outlier-recomputed `ucl`; comment the fixture so future edits don't shrink the margin.
- **R1-M2 (MINOR — ordering tiebreak).** Add an SPC test with two panels sharing one `start_ts`
  asserting the `panel_serial ASC` tiebreak drives a deterministic MR sequence.
- **R1-M3 (continuous-vs-count).** No change needed — SPC value test distinguishing `AVG` from
  `SUM`/`COUNT`/single-row already guards it.
- **Added tests folded in:** sigma exact-constant pin (R1-B1), colliding-`start_ts` tiebreak (R1-M2),
  rule_4 flag-index on a 9-run overlap (R1-W3), an anomaly case where one peer has `total==0` (excluded
  from a named group's baseline, exact `fmean` pinned), and a `record_type`-filter two-branch test
  (None aggregates both record_types on a refdes; explicit value isolates one).

**Behavior-level Test-Case Plan** (Step 4) is captured in `2026-06-18-phase2-slice2-test-plan.md`
(SPC-01…, ANOM-01…, API-01…); Execute (Step 7) implements each as RED→GREEN.
