# SPEC: Synthetic HP3070 / i3070 Log Generator

**Owning phase:** 1a
**Module path:** `src/flying_probe_copilot/generator/`
**Status:** Spec drafted, ready to implement

---

## Purpose

Generate realistic HP3070 / Keysight i3070 in-circuit test (ICT) report logs from configurable parameters. Output is the **single source of test data** for the repo. Every committed test, sample, and demo uses generator output.

This spec is intentionally tight — refine the format details against real Keysight i3070 manuals (kept locally, not committed) and your knowledge of real logs (kept in your head, not committed).

---

## Output format overview

The HP3070 / i3070 generates plain-text reports that follow a sectioned structure. The generator should produce reports approximating this structure. Sections typically include:

1. **Header** — board identifier, panel, operator, timestamp, fixture, test program version, line/station
2. **Shorts test** — node-to-node continuity scan, list of unexpected shorts
3. **Analog tests** — resistance, capacitance, inductance, diode, BJT, FET measurements with expected values and tolerances
4. **Digital / functional tests** — IC validation, vector tests, boundary scan summaries
5. **Summary** — pass/fail counts, total test time, overall result

⚠️ **You will need to refine each section's exact lexical format** against an actual Keysight i3070 report you have access to (at work). Do not copy real log content into this repo. Describe the format in your own words, in code comments.

---

## Data model

Implement these as `dataclasses` or `pydantic` models in `src/flying_probe_copilot/generator/models.py`:

```
BoardProfile
  - id: str
  - name: str
  - component_count: int
  - net_count: int
  - typical_test_count: int
  - component_mix: dict[str, int]  # e.g. {"R": 80, "C": 40, "U": 12, ...}

PanelInstance
  - serial: str               # synthetic serial, e.g. "SYN-2026W23-00042"
  - panel_position: int       # 1..N within a panel
  - board_profile_id: str
  - operator_id: str          # synthetic, e.g. "OP-007"
  - line_id: str              # synthetic, e.g. "LINE-A"
  - shift: str                # "A" | "B" | "C"
  - timestamp: datetime

TestRun
  - panel: PanelInstance
  - fixture_id: str
  - test_program_version: str
  - tests: list[TestResult]
  - shorts: list[ShortResult]
  - duration_seconds: float
  - overall_result: Literal["PASS","FAIL"]

TestResult
  - test_id: str              # unique within program, e.g. "A-R47-CHECK"
  - test_type: Literal["analog_R","analog_C","analog_L","diode","transistor","digital","functional"]
  - component_refdes: str     # e.g. "R47"
  - expected: float | None
  - measured: float | None
  - lower_limit: float | None
  - upper_limit: float | None
  - units: str | None         # "ohm","F","H","V" etc.
  - result: Literal["PASS","FAIL","SKIP"]
  - failure_code: str | None  # e.g. "OOL_HIGH","OOL_LOW","OPEN","SHORT","NO_RESPONSE"

ShortResult
  - net_a: str
  - net_b: str
  - measured_resistance: float
```

---

## Generation parameters (CLI / config)

The generator accepts a config (YAML or CLI flags) with:

| Parameter | Type | Notes |
|---|---|---|
| `--board-profile` | str | Choose one of: `small`, `medium`, `large` |
| `--count` | int | Number of panels to generate |
| `--out` | path | Output directory |
| `--seed` | int | Random seed for reproducibility |
| `--fault-rate` | float | Base fault rate per panel (e.g. 0.05) |
| `--fault-profile` | str | `random`, `drift`, `cluster`, `process-change` |
| `--start-date` | iso8601 | Beginning of synthetic timestamp range |
| `--end-date` | iso8601 | End of timestamp range |
| `--operators` | int | Number of distinct synthetic operator IDs |
| `--lines` | int | Number of synthetic SMT lines |
| `--format` | str | `log` (text report), `csv`, `json`, `all` |

**Default board profiles** (initial values; refine to match realism):
- `small`: 50 components, 80 nets, 120 tests
- `medium`: 200 components, 300 nets, 450 tests
- `large`: 800 components, 1,000 nets, 1,600 tests

---

## Fault injection profiles

Realism depends on this. Implement at least four profiles:

1. **`random`** — Independent per-test, base rate `fault-rate`. Simple baseline.
2. **`drift`** — Slowly increasing fault rate over time (simulates worn probes, oven drift). Linear or sigmoid ramp from `fault-rate * 0.5` to `fault-rate * 2.0` over the date range.
3. **`cluster`** — Bursts of failures concentrated in narrow time windows (operator change, paste expiration, recipe change). Background rate low, spike rate 5-10×.
4. **`process-change`** — Step change at a configurable timestamp. Pre-change rate `fault-rate * 0.5`, post-change rate `fault-rate * 1.5` (or vice versa). Useful for testing anomaly detection.

Common failure-code distribution (approximate, refine with your knowledge):
- `OOL_HIGH` / `OOL_LOW` (out-of-limit analog): 40% of fails
- `OPEN`: 25%
- `SHORT`: 15%
- `NO_RESPONSE` (digital): 10%
- `MISSING_COMPONENT`: 7%
- `WRONG_VALUE` (gross mismatch): 3%

Within each panel, model **fault correlation** — if one component fails, related-net components have elevated failure probability. This produces realistic Pareto curves rather than flat noise.

---

## Realism rules

These are the difference between a credible portfolio asset and a dismissible toy:

1. **Timestamps cluster realistically** — three shifts per day, weekday-heavy, occasional weekend production. No tests at 03:17 on a Sunday unless it's a planned night shift.
2. **Operator IDs are stable per shift** — same operator runs hundreds of panels in sequence, not one operator per panel.
3. **Test program versions update infrequently** — same version for hundreds of runs, then a discrete bump.
4. **Refdes naming is conventional** — `R1`, `R2`, ..., `C1`, ..., `U1`, ..., not random strings.
5. **Net names are conventional** — `+5V`, `+3V3`, `GND`, `VBAT`, `MCU_RESET`, etc.
6. **Measured values cluster around expected** — Gaussian noise within tolerance for passes; just outside tolerance for OOL fails.
7. **Test duration is plausible** — total test time scales with test count (~20-60 ms per analog test, ~5-20 ms per digital test, plus overhead).
8. **Panel serials follow a format** — e.g. `SYN-YYYY-WW-NNNNN` (year, week, sequence).

---

## Output file layout

```
data/synthetic/
├── run_2026-06-13T19-32-15/
│   ├── config.yaml             # the exact config used (reproducibility)
│   ├── manifest.json           # summary: panel count, fault rate, etc.
│   ├── logs/
│   │   ├── SYN-2026W24-00001.log
│   │   ├── SYN-2026W24-00002.log
│   │   └── ...
│   ├── results.csv             # all measurements flattened
│   └── results.json            # structured equivalent
```

Each subdirectory is a self-contained generation run. Never overwrite a previous run.

---

## CLI usage examples

```bash
# small generation for smoke testing
uv run flying-probe-gen --board-profile=small --count=10 --out=data/synthetic/

# realistic dev dataset
uv run flying-probe-gen \
  --board-profile=medium \
  --count=1000 \
  --fault-profile=drift \
  --fault-rate=0.06 \
  --start-date=2026-04-01 \
  --end-date=2026-06-30 \
  --operators=8 \
  --lines=3 \
  --seed=42 \
  --out=data/synthetic/

# anomaly-detection test dataset
uv run flying-probe-gen \
  --board-profile=medium \
  --count=2000 \
  --fault-profile=process-change \
  --out=data/synthetic/
```

---

## Tests (pytest)

Place under `tests/generator/`. Required tests:

1. `test_schema_validity` — every generated panel matches the data model.
2. `test_seed_reproducibility` — same seed → identical output.
3. `test_fault_rate_within_tolerance` — empirical fault rate is within ±20% of target over 500 panels.
4. `test_no_real_data_leak` — runs a smoke search for known sentinel strings ("customer", "confidential", any real part-number patterns owner defines). Should always pass; serves as a guardrail.
5. `test_output_files_present` — log, csv, json, manifest, config all exist after a run.
6. `test_round_trip_with_parser` (cross-phase, run later) — Phase 1b parser ingests generator output without error.

---

## Implementation order (for the session that builds this)

1. Define data models (`models.py`).
2. Implement board profiles (`profiles.py`).
3. Implement fault injection (`faults.py`).
4. Implement timestamp / operator / line distributions (`schedule.py`).
5. Implement renderers — text log, CSV, JSON (`renderers/`).
6. Wire up CLI entry point (`cli.py`).
7. Write tests.
8. Generate a sample 100-panel run; visually inspect a `.log` against real format expectations.
9. Iterate on the renderer until visually plausible.

---

## Open items to refine during implementation

- Exact section headers in the text log (refine against real i3070 format from Keysight manual)
- Exact field separators / delimiters within sections
- Whether to emit "skipped" tests separately or fold into result codes
- Whether to include boundary-scan / vector test detail (probably defer to Phase 5)
- Component refdes prefixes for unusual parts (crystals "Y", connectors "J", relays "K"…)

---

## What this generator is NOT

- Not a probe-program compiler. It does not emit BT-Basic source.
- Not a realistic equipment simulator. It generates *reports*, not the measurement process.
- Not extensible to non-ICT formats in v1 (no AOI, no functional test output).
