"""Tests for src/flying_probe_copilot/parser/ingest.py.

Asserts correct row counts and data integrity when a BatchLog is ingested
into a DuckDB database.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flying_probe_copilot.generator.models import BatchLog, BTESTStatus


# ---------------------------------------------------------------------------
# Helper to write a single-profile run directory
# ---------------------------------------------------------------------------


def _write_single_run(tmp_path: Path, batch_log: BatchLog, profile: str, suffix: str = "") -> Path:
    """Write a run directory for a single BatchLog and return the run dir path."""
    from flying_probe_copilot.generator.models import BTESTStatus
    from flying_probe_copilot.generator.renderers.log import render_log

    run_dir = tmp_path / f"run_{profile}_ingest_test{suffix}"
    run_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = run_dir / "logs"
    logs_dir.mkdir()

    for board in batch_log.boards:
        single = BatchLog(batch=batch_log.batch, boards=[board])
        render_log(single, logs_dir / f"{board.panel.serial}.log", encoding="utf-8")

    failing = sum(1 for b in batch_log.boards if b.btest.status != BTESTStatus.PASS)
    manifest = {
        "panel_count": len(batch_log.boards),
        "fault_rate": 0.05,
        "fault_profile": "random",
        "seed": 42,
        "board_profile": profile,
        "failing_boards": failing,
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    return run_dir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_ingest_inserts_correct_panel_count(in_mem_db, small_batch_log, tmp_path):
    """After ingest, panels table must have one row per board in the BatchLog."""
    from flying_probe_copilot.parser.ingest import ingest_run_directory

    run_dir = _write_single_run(tmp_path, small_batch_log, "small")
    ingest_run_directory(run_dir, in_mem_db)

    count = in_mem_db.execute("SELECT COUNT(*) FROM panels").fetchone()[0]
    assert count == len(small_batch_log.boards), (
        f"Expected {len(small_batch_log.boards)} panels, got {count}"
    )


def test_ingest_inserts_correct_test_runs_count(in_mem_db, small_batch_log, tmp_path):
    """After ingest, test_runs table must have one row per board."""
    from flying_probe_copilot.parser.ingest import ingest_run_directory

    run_dir = _write_single_run(tmp_path, small_batch_log, "small")
    ingest_run_directory(run_dir, in_mem_db)

    count = in_mem_db.execute("SELECT COUNT(*) FROM test_runs").fetchone()[0]
    assert count == len(small_batch_log.boards), (
        f"Expected {len(small_batch_log.boards)} test_runs, got {count}"
    )


def test_ingest_inserts_correct_measurements_count_for_failing_panel(
    in_mem_db, small_batch_log, tmp_path
):
    """After ingest, measurements count must equal total blocks across all boards."""
    from flying_probe_copilot.parser.ingest import ingest_run_directory

    run_dir = _write_single_run(tmp_path, small_batch_log, "small")
    ingest_run_directory(run_dir, in_mem_db)

    expected = sum(len(b.blocks) for b in small_batch_log.boards)
    count = in_mem_db.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]
    assert count == expected, (
        f"Expected {expected} measurements, got {count}"
    )


def test_ingest_inserts_failures_only_for_non_pass_status(
    in_mem_db, small_batch_log, tmp_path
):
    """failures table must contain rows only for non-PASS measurements."""
    from flying_probe_copilot.parser.ingest import ingest_run_directory
    from flying_probe_copilot.generator.models import (
        AnalogRecord, DigitalRecord, ShortsRecord, TestJetRecord, PinsFailedRecord,
        AnalogStatus, DigitalStatus, ShortsStatus, TwoDigitStatus, BTESTStatus,
    )

    run_dir = _write_single_run(tmp_path, small_batch_log, "small")
    ingest_run_directory(run_dir, in_mem_db)

    # Compute expected failure count from in-memory model
    expected_failures = 0
    for board in small_batch_log.boards:
        for tb in board.blocks:
            rec = tb.record
            if isinstance(rec, AnalogRecord) and rec.status != AnalogStatus.PASS:
                expected_failures += 1
            elif isinstance(rec, DigitalRecord) and rec.status != DigitalStatus.PASS:
                expected_failures += 1
            elif isinstance(rec, ShortsRecord) and rec.status != ShortsStatus.PASS:
                expected_failures += 1
            elif isinstance(rec, TestJetRecord) and rec.status != TwoDigitStatus.PASS:
                expected_failures += 1
            elif isinstance(rec, PinsFailedRecord) and rec.status != 0:
                expected_failures += 1

    count = in_mem_db.execute("SELECT COUNT(*) FROM failures").fetchone()[0]
    assert count == expected_failures, (
        f"Expected {expected_failures} failures, got {count}"
    )


def test_ingest_components_global_per_profile_refdes(in_mem_db, tmp_path):
    """Two runs from the same profile must not create duplicate component rows.

    Components are keyed on (board_profile_id, refdes); INSERT OR IGNORE
    must deduplicate them across multiple ingests.
    """
    from flying_probe_copilot.parser.ingest import ingest_run_directory
    from flying_probe_copilot.generator.cli import _build_batch_log

    class _A1:
        board_profile = "small"
        count = 2
        seed = 42
        fault_rate = 0.05
        fault_profile = "random"
        start_date = "2026-03-01"
        end_date = "2026-03-15"
        operators = 2
        lines = 1
        format = "log"
        encoding = "utf-8"

    class _A2:
        board_profile = "small"
        count = 2
        seed = 99
        fault_rate = 0.05
        fault_profile = "random"
        start_date = "2026-06-01"  # well separated — different ISO weeks → unique serials
        end_date = "2026-06-15"
        operators = 2
        lines = 1
        format = "log"
        encoding = "utf-8"

    # First run
    bl1 = _build_batch_log(_A1(), "small")
    run_dir1 = _write_single_run(tmp_path / "r1", bl1, "small", "_run1")
    ingest_run_directory(run_dir1, in_mem_db)
    count_after_first = in_mem_db.execute("SELECT COUNT(*) FROM components").fetchone()[0]
    assert count_after_first > 0, "First ingest must produce component rows"

    # Second run — same profile but different date range → different panel serials
    bl2 = _build_batch_log(_A2(), "small")
    run_dir2 = _write_single_run(tmp_path / "r2", bl2, "small", "_run2")
    ingest_run_directory(run_dir2, in_mem_db)
    count_after_second = in_mem_db.execute("SELECT COUNT(*) FROM components").fetchone()[0]

    assert count_after_second == count_after_first, (
        f"Component count changed from {count_after_first} to {count_after_second} "
        f"after second small-profile ingest — INSERT OR IGNORE not working"
    )


def test_ingest_populates_runs_table_from_manifest(in_mem_db, small_batch_log, tmp_path):
    """runs table must have 1 row after ingest with correct manifest fields."""
    from flying_probe_copilot.parser.ingest import ingest_run_directory

    run_dir = _write_single_run(tmp_path, small_batch_log, "small")
    ingest_run_directory(run_dir, in_mem_db)

    rows = in_mem_db.execute(
        "SELECT run_id, board_profile_id, seed, fault_rate, fault_profile, "
        "panel_count, failing_boards FROM runs"
    ).fetchall()
    assert len(rows) == 1, f"Expected 1 run row, got {len(rows)}"
    row = rows[0]
    assert row[1] == "small", f"Expected board_profile_id='small', got {row[1]!r}"
    assert row[2] == 42, f"Expected seed=42, got {row[2]}"
    assert row[3] == pytest.approx(0.05), f"Expected fault_rate=0.05, got {row[3]}"


def test_ingest_medium_profile_ingests_successfully(in_mem_db, medium_batch_log, tmp_path):
    """Medium profile (with Limits2 analog records) must ingest without errors."""
    from flying_probe_copilot.parser.ingest import ingest_run_directory

    run_dir = _write_single_run(tmp_path, medium_batch_log, "medium")
    report = ingest_run_directory(run_dir, in_mem_db)

    assert report.panels_inserted == len(medium_batch_log.boards), (
        f"Expected {len(medium_batch_log.boards)} panels from medium profile"
    )
    assert report.parse_errors == 0, f"Unexpected parse errors: {report.parse_errors}"


def test_ingest_unknown_profile_does_not_crash(in_mem_db, tmp_path):
    """An unknown board_profile in manifest.json must not crash the ingest."""
    from flying_probe_copilot.parser.ingest import ingest_run_directory
    from flying_probe_copilot.generator.cli import _build_batch_log

    class _A:
        board_profile = "small"
        count = 1
        seed = 77
        fault_rate = 0.05
        fault_profile = "random"
        start_date = "2026-08-01"
        end_date = "2026-08-05"
        operators = 1
        lines = 1
        format = "log"
        encoding = "utf-8"

    bl = _build_batch_log(_A(), "small")
    run_dir = tmp_path / "run_unknown_profile"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir()
    from flying_probe_copilot.generator.renderers.log import render_log
    from flying_probe_copilot.generator.models import BatchLog

    for board in bl.boards:
        single = BatchLog(batch=bl.batch, boards=[board])
        render_log(single, run_dir / "logs" / f"{board.panel.serial}.log", encoding="utf-8")
    # Override board_profile in manifest to an unknown value
    manifest = {
        "panel_count": 1,
        "fault_rate": 0.05,
        "fault_profile": "random",
        "seed": 77,
        "board_profile": "xlarge",  # not in profiles registry
        "failing_boards": 0,
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    # Should not raise; just uses placeholder board dim row
    report = ingest_run_directory(run_dir, in_mem_db)
    assert report.board_profile_id == "xlarge"


def test_ingest_run_with_no_logs_dir_handles_gracefully(in_mem_db, tmp_path):
    """A run directory with no logs/ subdirectory must not crash."""
    from flying_probe_copilot.parser.ingest import ingest_run_directory

    run_dir = tmp_path / "run_no_logs"
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "panel_count": 0,
        "fault_rate": 0.0,
        "fault_profile": "random",
        "seed": 0,
        "board_profile": "small",
        "failing_boards": 0,
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    report = ingest_run_directory(run_dir, in_mem_db)
    assert report.panels_inserted == 0
    assert report.files_processed == 0


def test_ingest_helper_failure_category_all_types():
    """_failure_category must return the correct category string for each type."""
    from flying_probe_copilot.parser.ingest import _failure_category
    from flying_probe_copilot.generator.models import (
        AnalogRecord, AnalogStatus, AnalogType, Limits2,
        DigitalRecord, DigitalStatus,
        ShortsRecord, ShortsStatus,
        TestJetRecord, TwoDigitStatus,
        PinsFailedRecord,
    )

    # Passing records → None
    shorts_pass = ShortsRecord(status=ShortsStatus.PASS, shorts_count=0, opens_count=0, phantoms_count=0)
    assert _failure_category(shorts_pass) is None

    # Failing records → correct category
    shorts_fail = ShortsRecord(status=ShortsStatus.FAIL, shorts_count=1, opens_count=0, phantoms_count=0)
    assert _failure_category(shorts_fail) == "SHORTS"

    analog_fail = AnalogRecord(
        record_type=AnalogType.DIO, status=AnalogStatus.FAIL,
        measured=1.0, designator="D1", limits=Limits2(high=2.0, low=0.5)
    )
    assert _failure_category(analog_fail) == "ANALOG"

    dig_fail = DigitalRecord(status=DigitalStatus.FAIL, substatus=0, failing_vector=0, failing_pin_count=1, designator="U1")
    assert _failure_category(dig_fail) == "DIGITAL"

    tjet_fail = TestJetRecord(status=TwoDigitStatus.FAIL, pin_count=10, designator="TJET1")
    assert _failure_category(tjet_fail) == "TJET"

    pf_fail = PinsFailedRecord(designator="U2", status=1, total_pins=5, pins=["A", "B"])
    assert _failure_category(pf_fail) == "PIN"


def test_ingest_component_family_for_unknown_refdes():
    """Refdes not starting with a known letter must return 'X' family."""
    from flying_probe_copilot.parser.ingest import _component_family_for_refdes

    assert _component_family_for_refdes("R12") == "R"
    assert _component_family_for_refdes("C5") == "C"
    assert _component_family_for_refdes("XY99") == "X"  # 'X' not in known families


def test_ingest_record_type_str_tjet_and_pf_and_unknown():
    """_record_type_str returns 'TJET', 'PF', or 'UNKNOWN' for unrecognized types."""
    from flying_probe_copilot.parser.ingest import _record_type_str
    from flying_probe_copilot.generator.models import (
        TestJetRecord, TwoDigitStatus,
        PinsFailedRecord,
    )

    tjet = TestJetRecord(status=TwoDigitStatus.PASS, pin_count=8, designator="TJET1")
    assert _record_type_str(tjet) == "TJET"

    pf = PinsFailedRecord(designator="U3", status=0, total_pins=4, pins=[])
    assert _record_type_str(pf) == "PF"

    class _Unknown:
        pass

    assert _record_type_str(_Unknown()) == "UNKNOWN"


def test_ingest_target_refdes_for_record_without_designator_attr():
    """_target_refdes_for must return None for a record with no 'designator' attribute."""
    from flying_probe_copilot.parser.ingest import _target_refdes_for
    from flying_probe_copilot.generator.models import ShortsRecord, ShortsStatus

    # ShortsRecord has no designator field — returns None via first branch
    shorts = ShortsRecord(status=ShortsStatus.PASS, shorts_count=0, opens_count=0, phantoms_count=0)
    assert _target_refdes_for(shorts) is None

    # A plain object with no designator attr — falls through to return None (line 220)
    class _NoDesignator:
        pass

    assert _target_refdes_for(_NoDesignator()) is None


def test_ingest_tjet_and_pf_blocks_produce_measurements(in_mem_db, tmp_path):
    """A BatchLog with TestJetRecord and PinsFailedRecord blocks must produce measurements."""
    from flying_probe_copilot.parser.ingest import _ingest_batch_log, _Counters
    from flying_probe_copilot.db.schema import init_database
    from flying_probe_copilot.generator.models import (
        BatchLog, BatchRecord, BoardLog, BoardTestRecord, PanelInstance,
        BTESTStatus, BlockRecord, TestBlock,
        TestJetRecord, TwoDigitStatus,
        PinsFailedRecord,
    )
    from datetime import datetime

    init_database(in_mem_db)

    # Ensure board dim row exists
    in_mem_db.execute(
        "INSERT OR IGNORE INTO boards (board_profile_id, name, component_count, net_count, typical_test_count)"
        " VALUES ('small', 'small', 50, 100, 51)"
    )
    in_mem_db.execute(
        "INSERT OR IGNORE INTO operators (operator_id) VALUES ('OP01')"
    )

    batch = BatchRecord(
        uut_type="TST", uut_rev="A", fixture_id=1, testhead_num=1,
        testhead_type="", process_step="TEST", batch_id="BAT-0099",
        operator_id="OP01", controller="ctrl1", testplan_id="tp1",
        testplan_rev="1", parent_panel_type="PPT", parent_panel_rev="A",
    )
    panel = PanelInstance(
        serial="SYN-2026W30-001", panel_position=1, board_profile_id="small",
        operator_id="OP01", line_id="L1", shift="A",
        timestamp=datetime(2026, 7, 20, 8, 0, 0),
    )
    btest = BoardTestRecord(
        board_id="SYN-2026W30-001", status=BTESTStatus.PASS,
        start_ts=260720080000, duration_s=120, end_ts=260720082000,
        board_number=1, operator_id="OP-001",
    )
    tjet_block = TestBlock(
        block=BlockRecord(designator="TJET1", status=0),
        record=TestJetRecord(status=TwoDigitStatus.PASS, pin_count=8, designator="TJET1"),
    )
    pf_block = TestBlock(
        block=BlockRecord(designator="U3", status=1),
        record=PinsFailedRecord(designator="U3", status=1, total_pins=4, pins=["P1", "P2"]),
    )
    board_log = BoardLog(panel=panel, btest=btest, blocks=[tjet_block, pf_block])
    batch_log = BatchLog(batch=batch, boards=[board_log])

    # Insert run-level row first (required FK)
    in_mem_db.execute(
        "INSERT INTO runs (run_id, board_profile_id, seed, fault_rate, fault_profile, panel_count, failing_boards)"
        " VALUES ('run_tjet_pf_test', 'small', 0, 0.0, 'random', 1, 0)"
    )

    counters = _Counters()
    p, tr, m, f = _ingest_batch_log(in_mem_db, batch_log, "run_tjet_pf_test", "small", counters)

    assert p == 1, f"Expected 1 panel, got {p}"
    assert tr == 1, f"Expected 1 test_run, got {tr}"
    assert m == 2, f"Expected 2 measurements (1 TJET + 1 PF), got {m}"
    # PF with status=1 is a failure
    assert f == 1, f"Expected 1 failure (PF status=1), got {f}"

    # Verify measurement record types
    rows = in_mem_db.execute(
        "SELECT record_type FROM measurements ORDER BY measurement_id"
    ).fetchall()
    types = [r[0] for r in rows]
    assert "TJET" in types, f"Expected TJET measurement, got {types}"
    assert "PF" in types, f"Expected PF measurement, got {types}"


def test_ingest_bad_btest_timestamp_skips_test_run(in_mem_db, tmp_path):
    """A board with an invalid start_ts must have its test_run skipped (no crash)."""
    from flying_probe_copilot.parser.ingest import _ingest_batch_log, _Counters
    from flying_probe_copilot.db.schema import init_database
    from flying_probe_copilot.generator.models import (
        BatchLog, BatchRecord, BoardLog, BoardTestRecord, PanelInstance,
        BTESTStatus, BlockRecord, TestBlock, ShortsRecord, ShortsStatus,
    )
    from datetime import datetime

    init_database(in_mem_db)

    in_mem_db.execute(
        "INSERT OR IGNORE INTO boards (board_profile_id, name, component_count, net_count, typical_test_count)"
        " VALUES ('small', 'small', 50, 100, 51)"
    )
    in_mem_db.execute(
        "INSERT OR IGNORE INTO operators (operator_id) VALUES ('OP01')"
    )

    batch = BatchRecord(
        uut_type="TST", uut_rev="A", fixture_id=1, testhead_num=1,
        testhead_type="", process_step="TEST", batch_id="BAT-0100",
        operator_id="OP01", controller="ctrl1", testplan_id="tp1",
        testplan_rev="1", parent_panel_type="PPT", parent_panel_rev="A",
    )
    panel = PanelInstance(
        serial="SYN-2026W31-001", panel_position=1, board_profile_id="small",
        operator_id="OP01", line_id="L1", shift="A",
        timestamp=datetime(2026, 7, 27, 8, 0, 0),
    )
    # start_ts = 999999999999 → month=99 → strptime raises ValueError → ParseError
    btest = BoardTestRecord(
        board_id="SYN-2026W31-001", status=BTESTStatus.PASS,
        start_ts=999999999999, duration_s=120, end_ts=999999999999,
        board_number=1, operator_id="OP-001",
    )
    shorts_block = TestBlock(
        block=BlockRecord(designator="TS1", status=0),
        record=ShortsRecord(status=ShortsStatus.PASS, shorts_count=0, opens_count=0, phantoms_count=0),
    )
    board_log = BoardLog(panel=panel, btest=btest, blocks=[shorts_block])
    batch_log = BatchLog(batch=batch, boards=[board_log])

    in_mem_db.execute(
        "INSERT INTO runs (run_id, board_profile_id, seed, fault_rate, fault_profile, panel_count, failing_boards)"
        " VALUES ('run_bad_ts_test', 'small', 0, 0.0, 'random', 1, 0)"
    )

    counters = _Counters()
    p, tr, m, f = _ingest_batch_log(in_mem_db, batch_log, "run_bad_ts_test", "small", counters)

    # Panel is inserted, but test_run is skipped due to bad timestamp
    assert p == 1, f"Expected 1 panel (panel insert is before timestamp parse), got {p}"
    assert tr == 0, f"Expected 0 test_runs (bad timestamp skipped), got {tr}"
    assert m == 0, f"Expected 0 measurements (skipped with test_run), got {m}"


def test_ingest_missing_manifest_raises_file_not_found(in_mem_db, tmp_path):
    """ingest_run_directory must raise FileNotFoundError when manifest.json is absent."""
    from flying_probe_copilot.parser.ingest import ingest_run_directory

    run_dir = tmp_path / "run_no_manifest_test"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir()
    # No manifest.json written

    with pytest.raises(FileNotFoundError, match="manifest.json"):
        ingest_run_directory(run_dir, in_mem_db)


def test_ingest_parse_exception_captured_in_report(in_mem_db, tmp_path):
    """When parse_log_file raises an exception, ingest captures it in parse_errors."""
    from unittest.mock import patch
    from flying_probe_copilot.parser.ingest import ingest_run_directory

    run_dir = tmp_path / "run_bad_log_exc_test"
    run_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = run_dir / "logs"
    logs_dir.mkdir()
    (logs_dir / "exploding.log").write_text("{@BATCH|X}", encoding="utf-8")

    manifest = {
        "panel_count": 1,
        "fault_rate": 0.0,
        "fault_profile": "random",
        "seed": 0,
        "board_profile": "small",
        "failing_boards": 0,
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    # Force parse_log_file to raise an OSError — exercises the except branch
    with patch(
        "flying_probe_copilot.parser.ingest.parse_log_file",
        side_effect=OSError("simulated I/O failure"),
    ):
        report = ingest_run_directory(run_dir, in_mem_db)

    assert report.parse_errors >= 1, (
        f"Expected at least 1 parse error after simulated exception, got {report.parse_errors}"
    )
    assert any("simulated I/O failure" in note for note in report.notes), (
        f"Expected failure note in report.notes, got: {report.notes}"
    )


def test_multi_operator_run_distinct_operators_per_panel(tmp_path):
    """Multi-panel run with distinct per-panel operators must ingest with distinct operator_ids.

    Constructs 4 boards with explicitly distinct operators (OP-001..OP-004) to
    prove the ingest layer writes per-panel operator_id from @BTEST, not the
    batch-level @BATCH.operator_id.

    Success criterion: each panel_serial's test_runs.operator_id == its @BTEST.operator_id.
    """
    import json as json_module
    from datetime import datetime
    from flying_probe_copilot.db.schema import init_database
    from flying_probe_copilot.generator.models import (
        BatchLog, BatchRecord, BoardLog, BoardTestRecord, BTESTStatus,
        PanelInstance,
    )
    from flying_probe_copilot.generator.renderers.log import render_log
    from flying_probe_copilot.parser.ingest import ingest_run_directory
    import duckdb

    con = duckdb.connect(":memory:")
    init_database(con)

    # Build 4 boards each with a distinct operator_id
    distinct_ops = ["OP-001", "OP-002", "OP-003", "OP-004"]
    batch_record = BatchRecord(
        uut_type="BRD-SMALL", uut_rev="A", fixture_id=1, testhead_num=1,
        process_step="ICT", batch_id="BAT-MULTI",
        operator_id="OP-001",  # batch-level — parser should NOT use this per-panel
        controller="ICT01", testplan_id="TP-001", testplan_rev="v1.0",
        parent_panel_type="PNL-SMALL", parent_panel_rev="A",
    )
    boards = []
    for i, op_id in enumerate(distinct_ops, start=1):
        panel = PanelInstance(
            serial=f"SYN-MULTI-{i:05d}",
            panel_position=i,
            board_profile_id="small",
            operator_id=op_id,
            line_id="LINE-A",
            shift="A",
            timestamp=datetime(2026, 4, 1, 8, i * 5, 0),
        )
        btest = BoardTestRecord(
            board_id=f"SYN-MULTI-{i:05d}",
            status=BTESTStatus.PASS,
            start_ts=int(f"260401080{i:01d}00"),
            duration_s=12,
            end_ts=int(f"260401080{i:01d}12"),
            board_number=i,
            operator_id=op_id,
        )
        boards.append(BoardLog(panel=panel, btest=btest, blocks=[]))

    batch_log = BatchLog(batch=batch_record, boards=boards)

    # Write run directory
    run_dir = tmp_path / "run_multi_op_test"
    run_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = run_dir / "logs"
    logs_dir.mkdir()
    for board in batch_log.boards:
        single = BatchLog(batch=batch_log.batch, boards=[board])
        render_log(single, logs_dir / f"{board.panel.serial}.log", encoding="utf-8")
    manifest = {
        "panel_count": 4,
        "fault_rate": 0.0,
        "fault_profile": "random",
        "seed": 0,
        "board_profile": "small",
        "failing_boards": 0,
    }
    (run_dir / "manifest.json").write_text(
        json_module.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    report = ingest_run_directory(run_dir, con)
    assert report.panels_inserted == 4, f"Expected 4 panels, got {report.panels_inserted}"
    assert report.test_runs_inserted == 4, f"Expected 4 test_runs, got {report.test_runs_inserted}"

    rows = con.execute(
        "SELECT panel_serial, operator_id FROM test_runs ORDER BY panel_serial"
    ).fetchall()
    assert len(rows) == 4
    ingested_ops = {r[1] for r in rows}
    assert len(ingested_ops) == 4, (
        f"Expected 4 distinct operator_ids in test_runs, got {ingested_ops}"
    )

    # Each panel_serial's operator_id must match the per-panel @BTEST.operator_id
    serial_to_panel_op = {b.panel.serial: b.panel.operator_id for b in batch_log.boards}
    for panel_serial, operator_id in rows:
        expected_op = serial_to_panel_op[panel_serial]
        assert operator_id == expected_op, (
            f"Panel {panel_serial}: expected operator_id={expected_op!r}, "
            f"got {operator_id!r} — ingest must use @BTEST.operator_id, not @BATCH"
        )

    # operators dim must have all 4 distinct operators
    op_rows = con.execute("SELECT operator_id FROM operators ORDER BY operator_id").fetchall()
    op_ids = {r[0] for r in op_rows}
    assert ingested_ops.issubset(op_ids), (
        f"All ingested operator_ids must be in operators dim; "
        f"ingested={ingested_ops}, dim={op_ids}"
    )

    con.close()
