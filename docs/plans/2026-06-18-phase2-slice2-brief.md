# Session Brief — Phase 2 slice 2: SPC + anomaly detection

**Date:** 2026-06-18
**Phase:** 2 (Analytics & Dashboard)
**Slice:** 2 of ~3 (SPC chart helpers + anomaly detection; slice 3 = Streamlit dashboard)
**Branch:** `feature/phase2-slice2-spc-anomaly` (renamed from worktree `claude/xenodochial-black-3cc4d9`)
**Tier:** Large (full 12-step session-workflow loop; statistics-heavy, high silent-wrong-data risk)

---

## 1. Goal (one sentence)

Ship the next analytics slice as **pure library functions** — an SPC individuals chart
helper and a z-score anomaly detector — over the existing DuckDB schema, matching the
slice-1 analytics contracts, with adversarially-generated tests at ≥80% coverage, notebook
cells, and a manual-QA script. **No UI** (that is slice 3).

## 2. Why this slice exists

ROADMAP Phase 2 lists four analytics deliverables under `analytics/`:
- [x] `yield_over_time` (slice 1, 2026-06-16)
- [x] `failure_pareto` (slice 1, 2026-06-16)
- [ ] **SPC chart helpers (X-bar, R, individual)** ← this slice
- [ ] **Anomaly detection (z-score baseline; Isolation Forest stretch)** ← this slice

These are the statistical core the slice-3 Streamlit SPC and Anomalies pages will render.
Getting the statistics *correct* now (right chart for the data, right sigma estimator,
leave-one-out baseline) prevents a dashboard that renders confident-but-wrong control limits.

## 3. Deliverables (target shape — refined in the Plan, confirmed at the Decision Gate)

| # | Deliverable | Notes |
|---|-------------|-------|
| D1 | `src/flying_probe_copilot/analytics/spc.py` | `individuals_chart(...) -> list[SPCPoint]`. Per-panel individuals (I-MR) chart. Signature may gain a metric selector — see §6 Open Q. |
| D2 | `src/flying_probe_copilot/analytics/anomaly.py` | `z_score_anomalies(con, *, window_days=30, threshold=3.0, by="board") -> list[AnomalyRow]`. Leave-one-out baseline. |
| D3 | `SPCPoint` + `AnomalyRow` dataclasses | In `analytics/models.py` (extend existing file) — `@dataclass(frozen=True)` like `YieldRow`/`ParetoRow`. |
| D4 | `analytics/__init__.py` re-exports | Add the 2 functions + 2 dataclasses to `__all__`. |
| D5 | `tests/test_analytics/test_spc.py` | ≥80% coverage of `spc.py`. Adversarial cases (§5). |
| D6 | `tests/test_analytics/test_anomaly.py` | ≥80% coverage of `anomaly.py`. Adversarial cases (§5). |
| D7 | `notebooks/01-queries.ipynb` SPC + anomaly cells | Appended after the existing 6 queries. Smoke-test in-process before commit. |
| D8 | `docs/plans/2026-06-18-phase2-slice2-manual-qa.md` | Step 11 owner QA script. |
| D9 | Doc updates | SESSION_LOG, DECISION_LOG, ROADMAP tick-off, CLAUDE.md session-log line, BUG_LOG (if anything surfaces). |

## 4. Hard constraints (from `.claude/rules/` + handover)

- **Full 12-step loop.** Plan (3), Decision Gate (6), Triple Check (9) are **parent-only** —
  never delegated. No execution before Step 5 (adversarial review) + Step 6 (owner sign-off).
- **TDD strict.** RED → GREEN → REFACTOR per step. No implementation without a failing test first.
- **Approval-gated files** (NO edit without explicit owner sign-off): `pyproject.toml`,
  `db/schema.py`, `migrations/*`, `.claude/settings.json`, `.env.example`.
  **Slice 2 must NOT need a schema change.** Any need = Decision Gate item.
- **Match slice-1 contracts (DECISION_LOG 2026-06-16):**
  - Unrounded floats (caller rounds at presentation).
  - Naive UTC `as_of`; tz-aware raises `ValueError`.
  - `window_days <= 0` raises `ValueError`; bad enum (`group_by` / `by`) raises `ValueError`.
  - `group_key ASC` ordering unless a divergence is justified in DECISION_LOG.
  - Window anchor = `MAX(test_runs.start_ts)`, inclusive `[anchor - window_days, anchor]`.
  - Empty DB / empty window → `[]` (no exception).
- **Per-row `placeholder_fields` markers are GONE** (removed 2026-06-18). Do not reintroduce.
- **Pure additive** preferred: extend `models.py` and `__init__.py`; do not edit
  `yield_metrics.py` / `pareto.py` / `_window.py` unless a shared helper genuinely belongs there
  (and then only additively).
- **No new dependencies** without owner sign-off. Isolation Forest needs `sklearn` → Decision Gate.
- **Branch policy:** `feature/*` → `dev`. Never force-push. No direct main/dev commits.
  Commit only at Step 10. Push only if owner requests.

## 5. What makes this hard (the statistics landmines)

1. **Right chart for the data.** Individuals (I-MR) charts assume **continuous** data with
   rational subgroups of size 1. Using them on **count/attribute** data (failures per panel)
   is a classic error — count data wants a c-/u-chart. The charted value must be continuous.
2. **`duration_s` is a constant.** `generator/cli.py:127` hardcodes `duration_s=12`, so the
   per-panel test-cycle-time metric has **zero variance** in synthetic data → useless as an
   I-MR series (zero-sigma is the *normal* case, not an edge case). The only per-panel
   continuous metric that varies is `measurements.measured_value` (analog readings), which is
   **per-component**, not per-panel. → The given signature has no metric selector; this needs
   a Plan refinement (likely add `refdes` / `record_type`). **Open Q for the Gate.**
3. **Sigma estimator.** For individuals charts the standard estimator is **MR-bar / 1.128**
   (average moving range / d2 for n=2), **NOT** the sample standard deviation. The plan
   red-team (Step 5) must explicitly verify which estimator each function uses and why.
4. **Leave-one-out baseline.** `z_score_anomalies` must NOT include the row being evaluated
   in its own baseline mean/std. State the rule in the Plan; assert it in tests.
5. **Alarm-rule family choice.** Western Electric vs Nelson vs Wheeler (and others). Pick one
   set in the Plan, justify it, document rejected alternatives in DECISION_LOG. Do not silently
   implement Nelson "because it's popular." Each implemented rule ships with a **positive**
   (trips) AND a **negative** (does not trip) test.

## 6. Open questions → routed to the Decision Gate (Step 6, owner sign-off)

- **OQ1 — SPC value / signature.** Add a metric selector (`refdes` + optional `record_type`)
  so the individuals chart tracks a real varying parametric measurement? Recommended yes.
  Alternative (chart `duration_s`) is useless (constant). Confirm the refined signature.
- **OQ2 — Alarm-rule family.** Which family (WE / Nelson / Wheeler / subset)? Parent recommends
  one after Step 2 research; owner confirms.
- **OQ3 — X-bar / R charts.** Implement now or defer? Rational subgroups of size >1 are
  contrived in this synthetic per-panel dataset. Parent leans **defer** (document why);
  owner confirms scope.
- **OQ4 — Anomaly metric.** What per-group scalar does `z_score_anomalies` z-score
  (per-group failure rate vs raw fail count vs volume)? Parent recommends after research.
- **OQ5 — Isolation Forest stretch.** Requires `sklearn` (new dep). Owner decides:
  add the dep, or defer the stretch. Parent leans **defer** (keep zero-new-dep streak).
- **OQ6 — Schema.** Confirm slice 2 needs NO schema change (expected: none).

## 7. Out of scope (chip it, don't fix it)

- Streamlit / UI / Plotly (slice 3).
- Real-data ingestion. Any RAG / LLM work.
- `data/db/sample.duckdb` regeneration with richer variance (notebook will note if needed).
- BUG-010 (TestJetRecord PytestCollectionWarning) — still open; not this slice.

## 8. Done when

- All 12 steps complete with artifacts under `docs/plans/2026-06-18-*.md`.
- Full pytest suite green; coverage ≥ slice-1 baseline (97% repo-wide); spc.py + anomaly.py ≥80%.
- Notebook SPC + anomaly cells smoke-tested in-process.
- PR opened `feature/phase2-slice2-spc-anomaly` → `dev` with auto-generated description.
- Manual-QA script ready for owner.
- AGENT_HANDOFF_LOG entry written at Step 12.
