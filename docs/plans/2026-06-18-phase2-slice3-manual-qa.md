# Manual QA — Phase 2 slice 3 (Streamlit dashboard)

> Owner-run hands-on script. ~10 min. Run from the worktree root.
> Branch: `claude/zen-roentgen-2818ce`. Prereq: `uv` environment synced (`python -m uv run pytest -q` once).

---

## §0 — Suite + coverage (automated gate)

```
python -m uv run pytest -q
```
**Expect:** `373 passed, 1 xfailed` (xfail = pre-existing BUG-011), **TOTAL coverage 97%**.
`ui/data.py` 100%, `ui/charts.py` 100%, `ui/views.py` ~87%, `ui/app.py` ~86%.

---

## §1 — Build / refresh the sample DB (if `data/db/sample.duckdb` is absent)

`data/db/*.duckdb` is gitignored — regenerate locally. Use disjoint date ranges so panel serials don't collide:
```
python -m uv run generator --board-profile=small  --count=30 --seed=42 --fault-profile=drift          --fault-rate=0.15 --start-date=2026-05-04 --end-date=2026-05-15 --operators=3 --lines=2 --out=data/synthetic/
python -m uv run generator --board-profile=medium --count=20 --seed=7  --fault-profile=cluster        --fault-rate=0.18 --start-date=2026-05-18 --end-date=2026-05-29 --operators=3 --lines=2 --out=data/synthetic/
python -m uv run generator --board-profile=small  --count=20 --seed=99 --fault-profile=process-change --fault-rate=0.25 --start-date=2026-06-01 --end-date=2026-06-12 --operators=3 --lines=2 --out=data/synthetic/
# then ingest each run dir into one DB:
#   python -m uv run parser --input=data/synthetic/<run_dir> --db=data/db/sample.duckdb
```
**Expect:** 3 "Ingested run ..." lines, 0 parse_errors, 2 boards / 70 panels total.

---

## §2 — Launch the dashboard

```
python -m uv run streamlit run src/flying_probe_copilot/ui/app.py
```
**Expect:** opens at http://localhost:8501; left sidebar shows **Filters** with **Start date** / **End date**,
and a nav list of 5 pages (Overview, Yield, Failure Pareto, SPC, Anomalies). Page loads in < 2 s.

---

## §3 — Page-by-page

| # | Page | Do | Expect |
|---|------|----|--------|
| 3.1 | **Overview** | (default) | 5 KPI cards (Overall Yield %, Panels Tested, Total Failures, Top Failure Mode, Flagged Anomalies); compact **Yield by board** bar (small ≈80%, medium ≈90%) + **Failure Pareto (top 5)** (A-RES tallest). |
| 3.2 | **Yield** | Switch **Group by** to `shift`, then `operator` | Bar of yield % per group, 0–100% axis, % labels; bars recolor (green ≥90 / amber ≥75 / red <75). Use **Filter values** multiselect → chart subsets to chosen groups. **Data table** expander shows rows. |
| 3.3 | **Failure Pareto** | Toggle **Group by** record_type↔refdes; move **Top N** slider | Bars descending by count + blue cumulative-% line on right axis + dashed 80% line. |
| 3.4 | **SPC** | Board=`small`, Component=`R4` (or any listed); toggle **Alarm rules** | Line+markers of measured value vs time; solid center, dashed red UCL/LCL; any out-of-control point shown as a red ✕ in the **alarms** legend series. Switch board=`medium` → refdes list changes. |
| 3.5 | **Anomalies** | **Group by**=`shift`; set **threshold** to 2.0 | z-score bar per group; shift **B** (or the elevated group) turns red with **⚠** in the table's Flag column; ±threshold dashed lines. Raise threshold to 5.0 → flags clear. |

---

## §4 — Filters + empty/edge

| # | Do | Expect |
|---|----|--------|
| 4.1 | Narrow the date range to a single day with no data | Pages show an `st.info` guidance message (not a blank/broken chart). |
| 4.2 | Widen the date range back to the full span | Charts repopulate. |
| 4.3 | Stop the app; `set FPC_DB_PATH` to a non-existent path; relaunch | App shows a red **"Database not found"** error with the generator+parser commands and stops cleanly (no traceback). |

---

## Sign-off

- [ ] §0 suite green @ 97%
- [ ] §2 launches < 2 s
- [ ] §3 all 5 pages render with correct charts
- [ ] §4 empty + missing-DB handled gracefully

Notes / issues: ____________________
