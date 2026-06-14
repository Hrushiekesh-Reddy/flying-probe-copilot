# SPEC: Synthetic HP3070 / i3070 Log Generator

**Owning phase:** 1a
**Module path:** `src/flying_probe_copilot/generator/`
**Status:** Spec revised 2026-06-13 (Phase 1a Step 2) — format target changed from "simplified text report" to **real Keysight i3070 Log Record Format** based on public-sources research; original simplified description preserved in commit history.

---

## Purpose

Generate realistic HP3070 / Keysight i3070 in-circuit test (ICT) log files that are **lexically conformant to the real i3070 Log Record Format**. Output is the **single source of test data** for the repo. Every committed test, sample, and demo uses generator output.

The generator's output should be ingestable by any third-party i3070 parser without modification (e.g. the Virinco WATS-Client-Converter, the future Phase 1b parser).

---

## Output format overview — Keysight i3070 Log Record Format

The Keysight i3070 emits log files in a **record-oriented, machine-readable** format (NOT a human-readable sectioned report). Every record is enclosed in `{ ... }`. The lexical rules below are derived from Keysight's "i3070 Log Record Format" chapter (publicly mirrored at `https://github.com/Virinco/WATS-Client-Converter-i3070-ICT-Systems`) cross-validated against that project's regex grammar.

### Lexical micro-syntax (universal)

| Construct | Meaning |
|---|---|
| `{...}` | Encloses a single record (or subrecord). Records nest. |
| `@PREFIX` | Record type tag, immediately after `{`. Prefix always starts with `@`. |
| `\|` | Field separator. |
| `\` | Introduces a **list** field; immediately followed by the list count, then `\|`-separated items. |
| `~N\|payload` | **Literal-length escape** for a field whose payload may contain `{`, `}`, `\|`, `\`, ASCII 4, or ASCII 10. `N` is the decimal byte length. |
| ASCII 4 (CTRL-D) outside a literal | Marks "record truncated". |
| Empty fields | Kept as adjacent `\|\|` — fields default to `0` / `""` / etc. by type. |
| Floats | Scientific notation, six-mantissa-digit form: `+1.246700E+01`, `-3.654285E-05`. |
| Bools | `0`/`1` OR `N`/`Y` per field. |
| Timestamps | `YYMMDDHHMMSS` (12-digit int). |
| Pin format | `BRRCC` (board number, row, column on the testhead). |

### Record hierarchy and prefixes (Phase 1a covers v1 subset)

```
@BATCH                                          one per file (panel/batch)
└── @BTEST                                      one per board / panel position
    ├── @BLOCK shorts                           shorts test block
    │   └── @TS                                 shorts result
    │       ├── @TS-S, @TS-D, @TS-O, @TS-P      (only when log-level allows detail)
    ├── @BLOCK <refdes_or_block_name>           one per test block
    │   └── @A-RES | @A-CAP | @A-DIO | @A-IND   analog test record
    │       | @A-MEA | @A-NFE | @A-NPN          (one of 14 analog types)
    │       | @A-PFE | @A-PNP | @A-POT
    │       | @A-SWI | @A-ZEN | @A-FUS | @A-JUM
    │       └── @LIM2 or @LIM3                  limits subrecord (immediately follows)
    ├── @BLOCK <refdes>                         (digital block)
    │   └── @D-T                                digital test record
    ├── @BLOCK <refdes>                         (probe/VTEP/polarity/etc.)
    │   └── @TJET | @PCHK | @CCHK | @PRB | @PF
```

**v1 scope:** `@BATCH`, `@BTEST`, `@BLOCK`, `@A-RES`, `@A-CAP`, `@A-DIO`, `@A-IND`, `@A-MEA`, `@A-NPN`, `@A-PFE`, `@A-PNP`, `@A-RES`, `@A-ZEN`, `@A-JUM`, `@A-FUS`, `@A-NFE`, `@A-POT`, `@A-SWI`, `@D-T`, `@TS`, `@TS-S`, `@TS-D`, `@TS-O`, `@TS-P`, `@PF`, `@PIN`, `@TJET`, `@LIM2`, `@LIM3`. Boundary-scan (`@BS-*`) and probe (`@PRB`/`@DPIN`) deferred to Phase 5 per realism budget.

### Field schemas (Phase 1a v1 records)

**`@BATCH`** — 13 or 14 fields (14-field form is newer):
`uut_type | uut_rev | fixture_id | testhead_num | testhead_type | process_step | batch_id | operator_id | controller | testplan_id | testplan_rev | parent_panel_type | parent_panel_rev [| version_label]`

**`@BTEST`** — 12 or 13 fields (13-field form is newer):
`board_id | status | start_ts | duration_s | multiple_test | log_level | log_set | learning | known_good | end_ts | status_qualifier | board_number [| parent_panel_id]`

**`@BLOCK`** — `block_designator | block_status` (status = worst contained subtest status).

**`@A-XXX`** (all 14 analog types share shape) — `status | measured_fp | subtest_designator`. Followed immediately by a limits subrecord:
- **`@LIM2`** (used by: DIO, FUS, JUM, MEA, NFE, NPN, PFE, PNP, SWI) — `high | low`.
- **`@LIM3`** (used by: CAP, IND, POT, RES, ZEN) — `nominal | high | low`.

**`@D-T`** — `status | substatus_bitmask | failing_vector | failing_pin_count | test_designator`. Substatus is a 6-bit bitmask: bit0=fail, bit1=SAFEGUARD timeout, bit2=hardware error, bit3=pause, bit4=halt, bit5=overvoltage.

**`@TS`** — `status | shorts_count | opens_count | phantoms_count | designator`.
- **`@TS-S`** subrecord — `count | phantoms | source_node`.
- **`@TS-D`** list — `\n_items | dst_node | deviation_fp | dst_node | deviation_fp | ...`.
- **`@TS-O`** — `source_node | dest_node | deviation_fp`.
- **`@TS-P`** — `deviation_fp`.

**`@TJET`** — `two_digit_status | pin_count | designator` (status: `00`=pass, `01`=fail, `07`=fatal).

**`@PF`** + **`@PIN`** — `@PF | designator | status | total_pins { @PIN \\n | p1 | p2 | ... }` where each pin is in `BRRCC` form.

### Status-code vocabulary (numeric only — no `"PASS"`/`"FAIL"` literal strings)

**`@BTEST` overall status (canonical board-level result):**
| Code | Meaning |
|---|---|
| 0 | passed |
| 1 | uncategorized failure |
| 2 | failed pin test |
| 3 | failed in learn mode |
| 4 | failed shorts test |
| 6 | failed analog test |
| 7 | failed power-supply test |
| 8 | failed digital or boundary-scan test |
| 9 | failed functional test |
| 10 | failed pre-shorts |
| 11 | failed in handler |
| 12 | failed barcode |
| 13 | X'd out |
| 14 | failed VTEP / TestJet |
| 15 | failed polarity |
| 16 | failed ConnectCheck (Mux) |
| 17 | failed analog cluster |
| 80 | runtime error |
| 81 | aborted (STOP) |
| 82 | aborted (BREAK) |
| 90–99 | user-definable |

**Per-record statuses:**
- `@A-*` (analog): 0=pass, 1=fail, 2=fail-compliance-limit, 3=fail-detector-timeout, 7=fail (MEA only), 11=operator-aborted.
- `@D-T` (digital): 0=pass, 1=fail, 5=CRC fail, 7=fatal (not completed), 8=chain integrity fail.
- `@TS` (shorts): 0=pass, 1=fail, 20=learning-passed.
- `@TJET` / `@PCHK` / `@CCHK` (two-digit family): `00`=pass, `01`=fail, `07`=fatal.
- `@PF` / `@PRB`: 0=pass, 1=fail.

### Encoding and line endings

- **Default encoding:** Windows-1252 (per the Virinco parser default; matches dominant i3070 ecosystem).
- **Line endings:** CRLF (`\r\n`) by default. UTF-8 LF available via `--encoding=utf8` flag for cross-platform users.
- **Record-per-line:** emit one top-level subrecord per line inside `@BTEST` (matches the most plausible real-factory output and is parser-friendly). Limits subrecords (`@LIM2`/`@LIM3`) remain inline with their analog parent.

---

## Data model

Implement as **pydantic v2** models in `src/flying_probe_copilot/generator/models.py`. Models map 1:1 to the real format's records so the renderer is a straightforward serialization.

```python
class BoardProfile(BaseModel):
    """A board family — drives synthesis volume and mix."""
    id: str
    name: str
    component_count: int            # total components
    net_count: int                  # total nets
    typical_test_count: int         # total analog + digital tests
    component_mix: dict[str, int]   # e.g. {"R": 80, "C": 40, "U": 12, "D": 5, "L": 3, "Q": 8}

class PanelInstance(BaseModel):
    """One board instance going through test."""
    serial: str                     # e.g. "SYN-2026W24-00042"
    panel_position: int             # 1..N within a panel
    board_profile_id: str
    operator_id: str                # e.g. "OP-007"
    line_id: str                    # e.g. "LINE-A"
    shift: Literal["A","B","C"]
    timestamp: datetime             # start-of-test

# --- Record-level models — each maps to one @PREFIX record ---

class BatchRecord(BaseModel):
    """Maps to @BATCH — one per file."""
    uut_type: str
    uut_rev: str
    fixture_id: int
    testhead_num: int
    testhead_type: str = ""         # documented but unused upstream
    process_step: str               # "ICT" / "FUNCTIONAL"
    batch_id: str
    operator_id: str
    controller: str                 # hostname
    testplan_id: str
    testplan_rev: str
    parent_panel_type: str
    parent_panel_rev: str
    version_label: str | None = None  # 14-field form only

class BoardTestRecord(BaseModel):
    """Maps to @BTEST — one per board within @BATCH."""
    board_id: str                   # serial
    status: BTESTStatus             # IntEnum, see status-vocabulary table
    start_ts: int                   # YYMMDDHHMMSS
    duration_s: int
    multiple_test: bool = False
    log_level: Literal["none","manual","board","failures","indictments","analog","all"] = "all"
    log_set: int = 0                # unused
    learning: bool = False
    known_good: bool = False
    end_ts: int                     # YYMMDDHHMMSS
    status_qualifier: str = ""
    board_number: int
    parent_panel_id: str | None = None  # 13-field form

class BlockRecord(BaseModel):
    """Maps to @BLOCK — contains one or more test records."""
    designator: str                 # e.g. "R12", "shorts", "u34_tj"
    status: int                     # worst contained subtest status

class Limits2(BaseModel):
    """Maps to @LIM2 — range-only limits."""
    high: float
    low: float

class Limits3(BaseModel):
    """Maps to @LIM3 — nominal + tolerance limits."""
    nominal: float
    high: float
    low: float

class AnalogRecord(BaseModel):
    """Maps to @A-RES / @A-CAP / @A-DIO / @A-IND / @A-MEA / @A-NFE /
    @A-NPN / @A-PFE / @A-PNP / @A-POT / @A-SWI / @A-ZEN / @A-FUS / @A-JUM."""
    record_type: AnalogType         # Literal of the 14 analog prefixes
    status: AnalogStatus            # IntEnum: 0/1/2/3/7/11
    measured: float                 # serialized in scientific notation
    designator: str                 # e.g. "R12"
    limits: Limits2 | Limits3       # tagged union; LIM2 vs LIM3 follows record_type per spec

class DigitalRecord(BaseModel):
    """Maps to @D-T."""
    status: DigitalStatus           # IntEnum: 0/1/5/7/8
    substatus: int                  # 6-bit bitmask
    failing_vector: int
    failing_pin_count: int
    designator: str

class ShortsRecord(BaseModel):
    """Maps to @TS plus child subrecords."""
    status: ShortsStatus            # IntEnum: 0/1/20
    shorts_count: int
    opens_count: int
    phantoms_count: int
    designator: str = "shorts_test"
    detail_source_nodes: list["ShortsSourceNodeDetail"] = []  # @TS-S + @TS-D
    detail_opens: list["ShortOpenDetail"] = []                # @TS-O entries
    detail_phantoms: list[float] = []                         # @TS-P entries

class ShortsSourceNodeDetail(BaseModel):
    """Maps to @TS-S { @TS-D \\n|... }."""
    source_node: str
    shorts_count: int
    phantoms_count: int
    destinations: list["ShortDestination"]   # @TS-D pairs

class ShortDestination(BaseModel):
    dest_node: str
    deviation: float

class ShortOpenDetail(BaseModel):
    """Maps to @TS-O."""
    source_node: str
    dest_node: str
    deviation: float

class TestJetRecord(BaseModel):
    """Maps to @TJET."""
    status: TwoDigitStatus          # IntEnum: 0/1/7 rendered as "00"/"01"/"07"
    pin_count: int
    designator: str

class PinsFailedRecord(BaseModel):
    """Maps to @PF + @PIN list."""
    designator: str
    status: Literal[0, 1]
    total_pins: int
    pins: list[str]                 # BRRCC-formatted

# --- Composite — what the generator builds per board ---

class BoardLog(BaseModel):
    """One @BTEST and all its contained blocks/records."""
    panel: PanelInstance
    btest: BoardTestRecord
    blocks: list["TestBlock"]

class TestBlock(BaseModel):
    """One @BLOCK and its single child test record."""
    block: BlockRecord
    record: AnalogRecord | DigitalRecord | ShortsRecord | TestJetRecord | PinsFailedRecord

class BatchLog(BaseModel):
    """One @BATCH and all its child @BTESTs — represents one log file."""
    batch: BatchRecord
    boards: list[BoardLog]
```

**IntEnum definitions** (defined in `models.py` alongside):
- `BTESTStatus` — `PASS=0, FAIL_UNCATEGORIZED=1, FAIL_PIN=2, FAIL_LEARN=3, FAIL_SHORTS=4, FAIL_ANALOG=6, FAIL_POWER=7, FAIL_DIGITAL=8, FAIL_FUNCTIONAL=9, FAIL_PRE_SHORTS=10, FAIL_HANDLER=11, FAIL_BARCODE=12, XD_OUT=13, FAIL_TJET=14, FAIL_POLARITY=15, FAIL_CCHK=16, FAIL_ANALOG_CLUSTER=17, RUNTIME_ERROR=80, ABORTED_STOP=81, ABORTED_BREAK=82` (90-99 reserved for user).
- `AnalogStatus` — `PASS=0, FAIL=1, FAIL_COMPLIANCE=2, FAIL_DETECTOR_TIMEOUT=3, FAIL_MEA_SPECIFIC=7, OPERATOR_ABORTED=11`.
- `DigitalStatus` — `PASS=0, FAIL=1, FAIL_CRC=5, FAIL_FATAL=7, FAIL_CHAIN_INTEGRITY=8`.
- `ShortsStatus` — `PASS=0, FAIL=1, LEARNING_PASSED=20`.
- `TwoDigitStatus` — `PASS=0, FAIL=1, FAIL_FATAL=7` (rendered as zero-padded two-digit).
- `AnalogType` — `RES, CAP, DIO, IND, MEA, NFE, NPN, PFE, PNP, POT, SWI, ZEN, FUS, JUM` (string enum; lowercase, mapped to `@A-{NAME}` when rendered; e.g. `RES → @A-RES`).

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

Common per-board failure-mode distribution (approximate; this targets *which @BTEST status code* a failing board gets, NOT a separate string vocabulary — the real format uses numeric statuses only). Adjust under user-tunable knobs:

| Failing-board fate | @BTEST status | Share of failing boards |
|---|---|---|
| analog out-of-limit (single component) | `6` (FAIL_ANALOG) | ~40% |
| shorts (unexpected node-to-node) | `4` (FAIL_SHORTS) | ~25% |
| open (missing trace / cold joint, surfaces in analog block as OOL) | `6` (FAIL_ANALOG) | ~15% |
| digital no-response | `8` (FAIL_DIGITAL) | ~10% |
| missing component (analog or probe-detected) | `6` (FAIL_ANALOG) or `2` (FAIL_PIN) | ~7% |
| gross wrong value | `6` (FAIL_ANALOG) | ~3% |

Per-record failure code (in `@A-*` / `@D-T` / `@TS` records) reflects the test's local result (e.g. analog out-of-limit emits `@A-RES|1|<measured>|R47`, then the limits subrecord shows the limits crossed). The @BTEST overall status is derived from the worst per-record status using the precedence table in the format chapter.

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

Place under `tests/test_generator/`. Required tests:

1. `test_schema_validity` — every generated panel matches the pydantic data model.
2. `test_seed_reproducibility` — same seed → byte-identical `.log` / `.csv` / `.json` output.
3. `test_fault_rate_within_tolerance` — empirical fault rate is within ±20% of target over 500 panels.
4. `test_no_real_data_leak` — sentinel-string smoke search ("customer", "confidential", any real part-number patterns owner defines later); always passes.
5. `test_output_files_present` — log, csv, json, manifest, config all exist after a run.
6. `test_lexical_compliance` — generator's `.log` output passes a **Python regex grammar derived from the Keysight format chapter** (cross-validated against the Virinco C# regex grammar):
   - balanced `{...}` braces; no unescaped braces inside fields
   - every `@PREFIX` recognized
   - every status code is one of the documented enumerations
   - floats match scientific-notation pattern
   - timestamps match `YYMMDDHHMMSS`
   - `@LIM2` follows {DIO,FUS,JUM,MEA,NFE,NPN,PFE,PNP,SWI}; `@LIM3` follows {CAP,IND,POT,RES,ZEN}
   - `@PIN` payloads in `BRRCC` form
   - field counts per record match the documented schemas
7. `test_btest_status_derivation` — overall `@BTEST` status is correctly derived from the worst contained subtest status.
8. `test_round_trip_with_parser` (cross-phase, run in Phase 1b) — Phase 1b parser ingests generator output without error.

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

Most original open items are now resolved by the public-sources research (see Step 2 Explore report). Remaining:

- Realistic record-count distribution per board profile (small/medium/large) — currently engineering-judgment defaults; refine with real data later.
- Per-fixture realistic `BRRCC` ranges — defaults inferred from public testhead size info; refine when owner has access to real fixture mapping.
- Component refdes prefixes for unusual parts (crystals "Y", connectors "J", relays "K"…) — generator should accept any string, default mix lists `R/C/L/D/Q/U`.
- Exact contents of `@RPT` (free-form report messages from BT-Basic `report` statement) — kept short and templated in v1; deferred refinement.
- Whether to emit boundary-scan (`@BS-CON` / `@BS-O` / `@BS-S` / `@NODE`) — deferred to Phase 5.
- Whether to emit probe / `@PRB` / `@DPIN` detail — deferred to Phase 5.
- CRLF vs LF detection — default CRLF (Windows-1252), opt-in LF (UTF-8) via `--encoding` flag.

---

## What this generator is NOT

- Not a probe-program compiler. It does not emit BT-Basic source.
- Not a realistic equipment simulator. It generates *reports*, not the measurement process.
- Not extensible to non-ICT formats in v1 (no AOI, no functional test output).
