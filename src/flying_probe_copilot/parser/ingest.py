"""Ingest a generator run directory into DuckDB — Phase 1b.

Public API:
  - ``ingest_run_directory(run_dir, con)`` → ``IngestReport``

Each run directory contains:
  - ``manifest.json`` — run-level metadata (panel_count, seed, etc.)
  - ``logs/<serial>.log`` — one per panel, one @BATCH + one @BTEST per file

Surrogate PKs are assigned using Python-side counters (one per surrogate-PK
table). DuckDB has no auto-increment in Phase 1b DDL.

Idempotency:
  - Dim tables (boards, operators, components, tests) use INSERT OR IGNORE.
  - Fact tables (panels, runs, test_runs, measurements, failures) use strict
    INSERT. A pre-flight check in cli.py prevents re-ingesting the same run_id.

Per #WARNING-5: test_runs.operator_id is populated from @BATCH.operator_id
(batch-level, not per-panel). Noted in ParseReport.notes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Sequence

import duckdb

from flying_probe_copilot.generator.models import (
    AnalogRecord,
    AnalogStatus,
    BatchLog,
    DigitalRecord,
    DigitalStatus,
    PinsFailedRecord,
    ShortsRecord,
    ShortsStatus,
    TestBlock,
    TestJetRecord,
    TwoDigitStatus,
)
from flying_probe_copilot.parser.log_parser import ParseReport, parse_log_file


# ---------------------------------------------------------------------------
# IngestReport
# ---------------------------------------------------------------------------


@dataclass
class IngestReport:
    """Summary of a completed ingest run."""

    run_id: str
    board_profile_id: str
    panels_inserted: int = 0
    test_runs_inserted: int = 0
    measurements_inserted: int = 0
    failures_inserted: int = 0
    parse_errors: int = 0
    files_processed: int = 0
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Surrogate-key state
# ---------------------------------------------------------------------------


@dataclass
class _Counters:
    """Monotonically increasing surrogate PKs, per ingest invocation."""

    component: int = 1
    test: int = 1
    test_run: int = 1
    measurement: int = 1
    failure: int = 1


# ---------------------------------------------------------------------------
# Helpers — board profile dim
# ---------------------------------------------------------------------------


def _ensure_board_dim(con: duckdb.DuckDBPyConnection, board_profile_id: str) -> None:
    """INSERT OR IGNORE the board profile into the boards dim table.

    Profile metadata is derived from the generator's known profiles; if the
    profile is unknown we still insert a placeholder so FK integrity holds.
    """
    from flying_probe_copilot.generator.profiles import get_profile

    try:
        prof = get_profile(board_profile_id)
        con.execute(
            """
            INSERT OR IGNORE INTO boards
                (board_profile_id, name, component_count, net_count, typical_test_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                prof.id,
                prof.name,
                prof.component_count,
                prof.net_count,
                prof.typical_test_count,
            ],
        )
    except ValueError:
        # Unknown profile — insert a placeholder
        con.execute(
            """
            INSERT OR IGNORE INTO boards
                (board_profile_id, name, component_count, net_count, typical_test_count)
            VALUES (?, ?, 0, 0, 0)
            """,
            [board_profile_id, board_profile_id],
        )


def _ensure_operator(con: duckdb.DuckDBPyConnection, operator_id: str) -> None:
    con.execute(
        "INSERT OR IGNORE INTO operators (operator_id) VALUES (?)", [operator_id]
    )


def _get_or_create_component(
    con: duckdb.DuckDBPyConnection,
    counters: _Counters,
    board_profile_id: str,
    refdes: str,
    component_family: str,
) -> int:
    """Return the component_id for (board_profile_id, refdes), inserting if needed."""
    row = con.execute(
        "SELECT component_id FROM components WHERE board_profile_id = ? AND refdes = ?",
        [board_profile_id, refdes],
    ).fetchone()
    if row:
        return row[0]
    cid = counters.component
    counters.component += 1
    con.execute(
        """
        INSERT OR IGNORE INTO components
            (component_id, board_profile_id, refdes, component_family)
        VALUES (?, ?, ?, ?)
        """,
        [cid, board_profile_id, refdes, component_family],
    )
    return cid


def _get_or_create_test(
    con: duckdb.DuckDBPyConnection,
    counters: _Counters,
    board_profile_id: str,
    block_designator: str,
    record_type: str,
    target_refdes: str | None,
) -> int:
    """Return the test_id for (board_profile_id, block_designator, record_type)."""
    row = con.execute(
        """
        SELECT test_id FROM tests
        WHERE board_profile_id = ? AND block_designator = ? AND record_type = ?
        """,
        [board_profile_id, block_designator, record_type],
    ).fetchone()
    if row:
        return row[0]
    tid = counters.test
    counters.test += 1
    con.execute(
        """
        INSERT OR IGNORE INTO tests
            (test_id, board_profile_id, block_designator, record_type, target_refdes)
        VALUES (?, ?, ?, ?, ?)
        """,
        [tid, board_profile_id, block_designator, record_type, target_refdes],
    )
    return tid


# ---------------------------------------------------------------------------
# Failure category helper
# ---------------------------------------------------------------------------


def _failure_category(record) -> str | None:
    """Return the failure category string for a non-pass record, or None if pass."""
    if isinstance(record, ShortsRecord):
        if record.status != ShortsStatus.PASS:
            return "SHORTS"
    elif isinstance(record, AnalogRecord):
        if record.status != AnalogStatus.PASS:
            return "ANALOG"
    elif isinstance(record, DigitalRecord):
        if record.status != DigitalStatus.PASS:
            return "DIGITAL"
    elif isinstance(record, TestJetRecord):
        if record.status != TwoDigitStatus.PASS:
            return "TJET"
    elif isinstance(record, PinsFailedRecord):
        if record.status != 0:
            return "PIN"
    return None


def _target_refdes_for(record) -> str | None:
    """Return the refdes for a record, or None for shorts/panel-level records."""
    if isinstance(record, ShortsRecord):
        return None
    if hasattr(record, "designator"):
        return record.designator
    return None


def _component_family_for_refdes(refdes: str) -> str:
    """Infer the component family prefix from a refdes string."""
    for prefix in ("R", "C", "U", "D", "L", "Q"):
        if refdes.startswith(prefix):
            return prefix
    return "X"  # unknown family


def _record_type_str(record) -> str:
    """Return the short record type string for a parsed record."""
    if isinstance(record, ShortsRecord):
        return "TS"
    if isinstance(record, AnalogRecord):
        return f"A-{record.record_type.value}"
    if isinstance(record, DigitalRecord):
        return "D-T"
    if isinstance(record, TestJetRecord):
        return "TJET"
    if isinstance(record, PinsFailedRecord):
        return "PF"
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Core ingest
# ---------------------------------------------------------------------------


def _ingest_batch_log(
    con: duckdb.DuckDBPyConnection,
    batch_log: BatchLog,
    run_id: str,
    board_profile_id: str,
    counters: _Counters,
) -> tuple[int, int, int, int]:
    """Ingest a single BatchLog; return (panels, test_runs, measurements, failures)."""
    panels_inserted = 0
    test_runs_inserted = 0
    measurements_inserted = 0
    failures_inserted = 0

    for board in batch_log.boards:
        panel = board.panel
        btest = board.btest

        # Panels
        con.execute(
            """
            INSERT INTO panels
                (panel_serial, board_profile_id, panel_position, line_id, shift, scheduled_ts)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                panel.serial,
                board_profile_id,
                panel.panel_position,
                panel.line_id,
                panel.shift,
                panel.timestamp,
            ],
        )
        panels_inserted += 1

        # Operator
        operator_id = batch_log.batch.operator_id
        _ensure_operator(con, operator_id)

        # Convert timestamps
        from flying_probe_copilot.parser.log_parser import _parse_yymmddhhmmss, ParseError

        try:
            start_dt = _parse_yymmddhhmmss(btest.start_ts)
            end_dt = _parse_yymmddhhmmss(btest.end_ts)
        except ParseError:
            # Skip this test_run if timestamps can't be parsed
            continue

        # test_runs
        tr_id = counters.test_run
        counters.test_run += 1
        con.execute(
            """
            INSERT INTO test_runs
                (test_run_id, panel_serial, run_id, operator_id, btest_status,
                 start_ts, end_ts, duration_s, multiple_test, learning,
                 known_good, board_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                tr_id,
                panel.serial,
                run_id,
                operator_id,
                int(btest.status),
                start_dt,
                end_dt,
                btest.duration_s,
                btest.multiple_test,
                btest.learning,
                btest.known_good,
                btest.board_number,
            ],
        )
        test_runs_inserted += 1

        # measurements + failures
        for tb in board.blocks:
            block = tb.block
            record = tb.record
            record_type = _record_type_str(record)
            target_refdes = _target_refdes_for(record)

            # Get or create component (None for shorts/TS)
            component_id: int | None = None
            if not isinstance(record, ShortsRecord) and target_refdes:
                family = _component_family_for_refdes(target_refdes)
                component_id = _get_or_create_component(
                    con, counters, board_profile_id, target_refdes, family
                )

            # Get or create test
            test_id = _get_or_create_test(
                con,
                counters,
                board_profile_id,
                block.designator,
                record_type,
                target_refdes if isinstance(record, ShortsRecord) is False else None,
            )

            # Build measurement fields
            measured_value: float | None = None
            limit_high: float | None = None
            limit_low: float | None = None
            limit_nominal: float | None = None
            substatus: int | None = None
            failing_vector: int | None = None
            failing_pin_count: int | None = None
            shorts_count: int | None = None
            opens_count: int | None = None
            phantoms_count: int | None = None
            pin_count: int | None = None
            status_int: int = 0

            if isinstance(record, AnalogRecord):
                measured_value = record.measured
                status_int = int(record.status)
                from flying_probe_copilot.generator.models import Limits2, Limits3

                if hasattr(record, "limits") and record.limits is not None:
                    if isinstance(record.limits, Limits3):
                        limit_nominal = record.limits.nominal
                        limit_high = record.limits.high
                        limit_low = record.limits.low
                    elif isinstance(record.limits, Limits2):
                        limit_high = record.limits.high
                        limit_low = record.limits.low

            elif isinstance(record, DigitalRecord):
                status_int = int(record.status)
                substatus = record.substatus
                failing_vector = record.failing_vector
                failing_pin_count = record.failing_pin_count

            elif isinstance(record, ShortsRecord):
                status_int = int(record.status)
                shorts_count = record.shorts_count
                opens_count = record.opens_count
                phantoms_count = record.phantoms_count

            elif isinstance(record, TestJetRecord):
                status_int = int(record.status)
                pin_count = record.pin_count

            elif isinstance(record, PinsFailedRecord):
                status_int = record.status
                pin_count = record.total_pins

            m_id = counters.measurement
            counters.measurement += 1
            con.execute(
                """
                INSERT INTO measurements
                    (measurement_id, test_run_id, test_id, component_id, record_type,
                     status, measured_value, limit_high, limit_low, limit_nominal,
                     substatus, failing_vector, failing_pin_count, shorts_count,
                     opens_count, phantoms_count, pin_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    m_id, tr_id, test_id, component_id, record_type,
                    status_int, measured_value, limit_high, limit_low, limit_nominal,
                    substatus, failing_vector, failing_pin_count, shorts_count,
                    opens_count, phantoms_count, pin_count,
                ],
            )
            measurements_inserted += 1

            # failures — only for non-pass records
            fail_cat = _failure_category(record)
            if fail_cat is not None:
                f_id = counters.failure
                counters.failure += 1
                con.execute(
                    """
                    INSERT INTO failures
                        (failure_id, measurement_id, test_run_id, panel_serial,
                         board_profile_id, record_type, status, failure_category,
                         target_refdes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        f_id, m_id, tr_id, panel.serial,
                        board_profile_id, record_type, status_int, fail_cat,
                        target_refdes,
                    ],
                )
                failures_inserted += 1

    return panels_inserted, test_runs_inserted, measurements_inserted, failures_inserted


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def ingest_run_directory(
    run_dir: Path, con: duckdb.DuckDBPyConnection
) -> IngestReport:
    """Ingest all .log files under ``run_dir`` into ``con``.

    Reads ``manifest.json`` for run-level metadata, then walks
    ``logs/*.log`` files, parses each one, and inserts rows into all 9 tables.

    Surrogate PKs are computed as the maximum existing value + 1 at the start
    of the call, so multiple calls to different run dirs are safe (the pre-flight
    check in cli.py prevents re-ingesting the same run_id).
    """
    run_dir = Path(run_dir)
    run_id = run_dir.name  # e.g. 'run_2026-04-01T08-30-00-000000'

    # Read manifest
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found in {run_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    board_profile_id = manifest["board_profile"]

    report = IngestReport(run_id=run_id, board_profile_id=board_profile_id)

    # Initialise surrogate-key counters from existing max values
    def _max_or(table: str, col: str) -> int:
        row = con.execute(f"SELECT COALESCE(MAX({col}), 0) FROM {table}").fetchone()
        return (row[0] or 0) + 1

    counters = _Counters(
        component=_max_or("components", "component_id"),
        test=_max_or("tests", "test_id"),
        test_run=_max_or("test_runs", "test_run_id"),
        measurement=_max_or("measurements", "measurement_id"),
        failure=_max_or("failures", "failure_id"),
    )

    # Ensure board dim row
    _ensure_board_dim(con, board_profile_id)

    # Insert run-level row
    con.execute(
        """
        INSERT INTO runs
            (run_id, board_profile_id, seed, fault_rate, fault_profile,
             panel_count, failing_boards)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            run_id,
            board_profile_id,
            int(manifest.get("seed", 0)),
            float(manifest.get("fault_rate", 0.0)),
            manifest.get("fault_profile", "random"),
            int(manifest.get("panel_count", 0)),
            int(manifest.get("failing_boards", 0)),
        ],
    )

    # Walk log files
    logs_dir = run_dir / "logs"
    log_files = sorted(logs_dir.glob("*.log")) if logs_dir.exists() else []

    for log_path in log_files:
        try:
            batch_log, parse_report = parse_log_file(log_path)
        except Exception as exc:
            report.notes.append(f"Failed to parse {log_path.name}: {exc}")
            report.parse_errors += 1
            continue

        report.parse_errors += len(parse_report.errors)
        report.files_processed += 1

        p, tr, m, f = _ingest_batch_log(
            con, batch_log, run_id, board_profile_id, counters
        )
        report.panels_inserted += p
        report.test_runs_inserted += tr
        report.measurements_inserted += m
        report.failures_inserted += f

    return report
