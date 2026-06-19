# Manual QA — Phase 2 per-panel operator-id repair
**Date:** 2026-06-16
**Branch:** `feature/per-panel-operator`
**Related:** brief `docs/plans/2026-06-14-phase2-operator-brief.md`, plan `docs/plans/2026-06-14-phase2-operator-plan.md`, BUG_LOG BUG-009 (RESOLVED), BUG-007 (PARTIAL).

This script is for the owner to run hands-on before signing off the PR. It exercises the new `@BTEST.operator_id` field end-to-end (generator → log file → parser → DuckDB) and confirms the contract holds against a freshly-generated multi-operator run, not just the in-suite fixtures.

Expected time: ~10 minutes.

---

## Pre-flight

```bash
git status
# expect: on feature/per-panel-operator, working tree clean (after Step 10 commit lands)

uv run pytest -q 2>&1 | tail -3
# expect: 196 passed
```

If either fails, STOP and surface to the parent — do not proceed.

---

## QA-1 — Round-trip on a fresh multi-operator small-profile run

```bash
# Generate 20 panels, small profile, deterministic seed so the operator distribution is reproducible.
uv run generator --board-profile=small --count=20 --seed=42 \
    --out=data/synthetic/ --start-date=2026-04-01 --end-date=2026-04-15

# Find the run directory the generator just emitted (most recent under data/synthetic/).
ls -1t data/synthetic/ | head -3
```

Note the run directory name (e.g. `run-20260401T...`). Then:

```bash
# Wipe any old sample DB so this run is the only one in it.
rm -f data/db/qa-operator.duckdb

# Parse the run into a fresh DuckDB.
uv run parser --input=data/synthetic/<RUN_DIR>/ --db=data/db/qa-operator.duckdb
```

Expect ingest report:
- `panels=20`
- `test_runs=20`
- `measurements` ≥ 1000 (varies by fault rate; small profile baseline ~1020)
- `failures` ≥ 0
- `parse_errors=0`

---

## QA-2 — Schema introspection

```bash
uv run python -c "
import duckdb
con = duckdb.connect('data/db/qa-operator.duckdb')
rows = con.execute('DESCRIBE test_runs').fetchall()
op = next(r for r in rows if r[0] == 'operator_id')
print(f'column={op[0]} type={op[1]} null={op[2]}')
assert op[2] == 'NO', f'operator_id must be NOT NULL on a fresh DB, got null={op[2]!r}'
print('OK: test_runs.operator_id is NOT NULL')
"
```

Expect: `column=operator_id type=VARCHAR null=NO` then `OK: test_runs.operator_id is NOT NULL`.

---

## QA-3 — Distinct operators per panel

```bash
uv run python -c "
import duckdb
con = duckdb.connect('data/db/qa-operator.duckdb')
rows = con.execute('''
    SELECT operator_id, COUNT(*) AS panel_count
    FROM test_runs
    GROUP BY operator_id
    ORDER BY operator_id
''').fetchall()
print('operator_id | panel_count')
for op, n in rows:
    print(f'  {op:>10} | {n}')
distinct = len(rows)
print(f'distinct operators = {distinct}')
assert distinct >= 2, f'Expected at least 2 distinct operators in a 20-panel small-profile run, got {distinct}. Operator rotation in schedule.py is rng.randint(60,200) — with seed=42 a 20-panel run should still cross one boundary.'
print('OK: per-panel operator attribution is real (not a single batch-level value)')
"
```

Expect: ≥2 rows in the table, each with a count < 20 (i.e. no operator owns the whole run). The exact distribution is seed-dependent but the assertion is the contract.

---

## QA-4 — Per-panel operator matches the generator's intent

```bash
uv run python -c "
import duckdb, json
con = duckdb.connect('data/db/qa-operator.duckdb')

# Pull the per-panel operators that ingest wrote.
ingested = dict(con.execute('SELECT panel_serial, operator_id FROM test_runs ORDER BY panel_serial').fetchall())
print(f'ingested {len(ingested)} test_runs rows')

# Re-derive the expected per-panel operators by re-parsing the log files.
# The log files are the single source of truth — if they say OP-XYZ at field 12
# of @BTEST, that is the contract for what ingest must write.
from flying_probe_copilot.parser.log_parser import parse_log_file
from pathlib import Path

run_dir = sorted(Path('data/synthetic').iterdir(), key=lambda p: p.stat().st_mtime)[-1]
log_files = sorted((run_dir / 'logs').glob('*.log'))
print(f'parsing {len(log_files)} log files from {run_dir.name}')

mismatches = []
for lp in log_files:
    bl, _ = parse_log_file(lp)
    for board in bl.boards:
        serial = board.panel.serial
        log_op = board.btest.operator_id
        ingested_op = ingested.get(serial)
        if log_op != ingested_op:
            mismatches.append((serial, log_op, ingested_op))

if mismatches:
    print(f'FAIL: {len(mismatches)} mismatches:')
    for s, lo, io in mismatches[:5]:
        print(f'  {s}: log says {lo!r}, ingest says {io!r}')
    raise SystemExit(1)
print('OK: every panel_serial in test_runs matches the @BTEST.operator_id in its log file')
"
```

Expect: `OK: every panel_serial in test_runs matches the @BTEST.operator_id in its log file`.

---

## QA-5 — Notebook Query 4 returns real per-operator yield

Open `notebooks/01-queries.ipynb` in VS Code or Cursor. Update the setup cell's DB path from `data/db/sample.duckdb` to `data/db/qa-operator.duckdb`, then run Cell 10 (Query 4 — Per-operator yield).

Expect: at least 2 rows (one per operator the seed=42 run produced), with realistic per-operator pass-rate percentages. The "Caveat" text above the query should be the new Phase 2 footnote, NOT the old DECISION_LOG batch-level caveat.

If the notebook still shows the old caveat, the cell 9 markdown wasn't updated — flag back to parent.

---

## QA-6 — Old sample.duckdb is gracefully tolerated

```bash
# data/db/sample.duckdb (from Phase 1b notebook session) is gitignored; it may or may not exist.
ls -la data/db/sample.duckdb 2>/dev/null || echo 'no old sample.duckdb — skip this step'
```

If it does exist, the notebook should still run against it without crashing — `CREATE TABLE IF NOT EXISTS` preserves the old nullable column on an existing DB. Queries 1–3 should work; Query 4 may show a single batch-level operator-id (because the file was ingested under the old code). This is expected and not a bug: the file is owner-recreatable. Optionally:

```bash
rm -f data/db/sample.duckdb
# Re-run the Phase 1b sample DB regen if you want it fresh:
uv run parser --input=data/synthetic/<RUN_DIR>/ --db=data/db/sample.duckdb
```

---

## Sign-off

If QA-1 through QA-5 all pass:
- Reply to the session with "Manual QA pass — ready to PR".
- The parent will open `feature/per-panel-operator` → `dev`.

If any step fails:
- Capture the failing command's output verbatim.
- Reply with "Manual QA fail at QA-N: <one-line symptom>".
- The parent triages (re-open the loop or spawn a fix branch).

---

## Cleanup (optional)

```bash
rm -f data/db/qa-operator.duckdb
# data/synthetic/ runs accumulate — see GUARDRAILS.md for the samples-only allow-list rule.
```

End of script.
