# Manual QA — Phase 2 slice 2 (SPC + anomaly)

**For:** owner · **When:** after Step 9 Triple Check passes, before PR merge · **Time:** ~10 min
**Branch:** `feature/phase2-slice2-spc-anomaly`

These are hands-on checks the automated tests can't fully stand in for: that the two new
functions run against a *real* ingested DuckDB (not just hand-built fixtures), return sensible
shapes, and that the control limits + anomaly flags are ordered and bounded the way a manufacturing
engineer would expect. Run each block from the repo root in PowerShell.

---

## 0. Pre-flight: full test suite + coverage

```powershell
uv run pytest --cov=src --cov-report=term-missing
```
**PASS when:** the **full** suite is green — `292 passed, 1 xfailed, 0 failed`
(the `1 xfailed` is the pre-existing slice-1 Y-12 marker, an *expected* failure — `x`, not `F` —
not a real failure); in the per-file coverage table `spc.py` and `anomaly.py` are each ≥80%
(they are 100%) and the `TOTAL` row is ≥97%.

> Run the suite **without a path filter** for the coverage numbers. Scoping to
> `tests/test_analytics/` runs only the analytics subset, so the `TOTAL` coverage row drops to
> ~16% (generator/parser code isn't exercised) — that is expected and is **not** a failure
> (there is no `--cov-fail-under` gate).

---

## 1. Make sure a sample DB exists

If `data/db/sample.duckdb` is missing or you want a fresh one with real per-panel shift/line/operator
data (BUG-007 fully closed), regenerate (≈20 small-profile panels over two weeks so the window has data):

```powershell
uv run generator --board-profile=small --count=20 --seed=42 --out=data/synthetic/ --start-date=2026-04-01 --end-date=2026-04-15
# note the printed run directory, then:
uv run parser --input=data/synthetic/<run_dir> --db=data/db/sample.duckdb
```
(Both artifacts are gitignored. Skip if `data/db/sample.duckdb` already exists and you just want a smoke check.)

---

## 2. SPC individuals chart — runs, ordered, limits bracket the mean

```powershell
uv run python -c @"
import duckdb
from flying_probe_copilot.analytics import individuals_chart

con = duckdb.connect('data/db/sample.duckdb', read_only=True)

# Pick a refdes that actually has data on the small profile:
refdes = con.execute(
    \"SELECT refdes FROM components WHERE board_profile_id='small' \"
    \"AND refdes LIKE 'R%' ORDER BY refdes LIMIT 1\"
).fetchone()[0]
print('charting refdes:', refdes)

pts = individuals_chart(con, board_profile_id='small', refdes=refdes, window_days=30)
print('points:', len(pts))
for p in pts[:5]:
    print(f'  {p.panel_serial} {p.start_ts} value={p.value:.3f} '
          f'lcl={p.lcl:.3f} mean={p.mean:.3f} ucl={p.ucl:.3f} flags={p.alarm_flags}')

# Invariants:
assert all(p.lcl <= p.mean <= p.ucl for p in pts), 'control limits must bracket the mean'
assert [p.start_ts for p in pts] == sorted(p.start_ts for p in pts), 'must be time-ordered'
assert all(isinstance(p.alarm_flags, tuple) for p in pts)
# sigma is MR-bar/1.128, i.e. (ucl-mean) == 3*(ucl-mean)/3 — just confirm symmetry:
assert all(abs((p.ucl - p.mean) - (p.mean - p.lcl)) < 1e-6 for p in pts), 'limits symmetric about mean'
print('SPC invariants OK')
con.close()
"@
```
**PASS when:** prints ≥15 points, all time-ordered, `lcl ≤ mean ≤ ucl` on every row, limits symmetric
about the mean, `alarm_flags` is a tuple (usually empty on clean synthetic data). On clean data few or no
rule_1/rule_4 flags is expected and correct — the chart is in control.

**Optional — see a rule trip:** opt into the zone rules and confirm they only appear when enabled:
```powershell
uv run python -c "import duckdb; from flying_probe_copilot.analytics import individuals_chart; con=duckdb.connect('data/db/sample.duckdb',read_only=True); r=con.execute(\"SELECT refdes FROM components WHERE board_profile_id='small' AND refdes LIKE 'R%' ORDER BY refdes LIMIT 1\").fetchone()[0]; d=individuals_chart(con,board_profile_id='small',refdes=r,window_days=30); o=individuals_chart(con,board_profile_id='small',refdes=r,window_days=30,rules=('rule_1','rule_2','rule_3','rule_4')); print('default flags:',sum(len(p.alarm_flags) for p in d),'all-rules flags:',sum(len(p.alarm_flags) for p in o)); con.close()"
```
**PASS when:** the all-rules count is ≥ the default count (opt-in rules can only add flags, never remove).

---

## 3. z-score anomalies — every `by` runs, severity-ordered, flag is bounded

```powershell
uv run python -c @"
import duckdb
from flying_probe_copilot.analytics import z_score_anomalies

con = duckdb.connect('data/db/sample.duckdb', read_only=True)
for by in ('board', 'shift', 'line', 'operator'):
    rows = z_score_anomalies(con, by=by, window_days=30, threshold=3.0)
    print(f'by={by}: {len(rows)} groups')
    for r in rows:
        print(f'  {r.group_key}: rate={r.value:.3f} base_mean={r.baseline_mean:.3f} '
              f'base_std={r.baseline_std:.3f} z={r.z_score:.2f} flagged={r.flagged}')
    # severity-first ordering:
    zs = [abs(r.z_score) for r in rows]
    assert zs == sorted(zs, reverse=True), f'{by} not ordered by |z| DESC'
    # leave-one-out + zero-std guard sanity:
    assert all(r.flagged == (r.baseline_std > 0 and abs(r.z_score) >= 3.0) for r in rows)
print('anomaly invariants OK')
con.close()
"@
```
**PASS when:** each `by` returns rows (or `[]` if <2 groups — e.g. the small sample may have a single
board/line, which correctly yields `[]`), rows are ordered by `|z|` descending, and `flagged` agrees with
the `baseline_std>0 and |z|≥threshold` rule. On a uniform small sample, **zero flags is the correct result**
(homogeneous groups → no anomaly).

---

## 4. Contract guards (should raise)

```powershell
uv run python -c @"
import duckdb
from datetime import datetime, timezone
from flying_probe_copilot.analytics import individuals_chart, z_score_anomalies
con = duckdb.connect('data/db/sample.duckdb', read_only=True)
def expect_valueerror(fn, label):
    try:
        fn(); print('NO RAISE (BAD):', label)
    except ValueError as e:
        print('ok ValueError:', label, '->', str(e)[:60])
expect_valueerror(lambda: individuals_chart(con, board_profile_id='small', refdes='R1', window_days=0), 'window_days=0')
expect_valueerror(lambda: individuals_chart(con, board_profile_id='small', refdes='R1', rules=('rule_1','rule_9')), 'bad rule')
expect_valueerror(lambda: z_score_anomalies(con, by='nonsense'), 'bad by')
expect_valueerror(lambda: z_score_anomalies(con, threshold=0), 'threshold=0')
expect_valueerror(lambda: z_score_anomalies(con, as_of=datetime(2026,5,1,tzinfo=timezone.utc)), 'tz-aware as_of')
con.close()
"@
```
**PASS when:** all five print `ok ValueError` (none prints `NO RAISE (BAD)`).

---

## 5. Notebook smoke (optional)

Open `notebooks/01-queries.ipynb` in VS Code / Cursor and run the new SPC + anomaly cells (after Query 6).
**PASS when:** both cells execute without error and render a small table; the SPC cell asserts
`lcl ≤ mean ≤ ucl`.

---

## Sign-off

- [ ] §0 suite green + coverage targets met
- [ ] §2 SPC runs, ordered, limits bracket mean
- [ ] §3 anomalies run for all `by`, severity-ordered
- [ ] §4 all guards raise
- [ ] §5 notebook cells run (optional)

Any FAIL → note it on the PR and hand back before merge.
