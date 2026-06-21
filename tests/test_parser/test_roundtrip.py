"""Round-trip tests: generator → run directory → parser CLI → DuckDB → query.

Tests assert that the in-memory BatchLog produced by the generator matches
what ends up in the DuckDB database after a full parse+ingest cycle.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import duckdb
import pytest

from flying_probe_copilot.generator.cli import _build_batch_log
from flying_probe_copilot.generator.models import (
    BatchLog,
    BTESTStatus,
)
from flying_probe_copilot.generator.renderers.log import render_log

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _Args:
    def __init__(self, profile, count, seed, start_date="2026-04-01", end_date="2026-04-08"):
        self.board_profile = profile
        self.count = count
        self.seed = seed
        self.fault_rate = 0.05
        self.fault_profile = "random"
        self.start_date = start_date
        self.end_date = end_date
        self.operators = 4
        self.lines = 2
        self.format = "log"
        self.encoding = "utf-8"


def _make_run_dir(
    tmp_path: Path, batch_log: BatchLog, profile: str, name: str, seed: int = 42
) -> Path:
    """Write a run directory and return it."""
    run_dir = tmp_path / name
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
        "seed": seed,
        "board_profile": profile,
        "failing_boards": failing,
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    return run_dir


@pytest.fixture
def small_10_log():
    """10 small-profile panels, seed=42, weeks 14-15 of 2026."""
    return _build_batch_log(_Args("small", 10, 42, "2026-04-01", "2026-04-08"), "small")


@pytest.fixture
def medium_5_log():
    """5 medium-profile panels, seed=43, weeks 20-21 of 2026 (no serial overlap)."""
    return _build_batch_log(_Args("medium", 5, 43, "2026-05-12", "2026-05-19"), "medium")


# ---------------------------------------------------------------------------
# Round-trip tests (Steps 18-21)
# ---------------------------------------------------------------------------


def test_generator_to_parser_to_db_preserves_panel_count(small_10_log, medium_5_log, tmp_path):
    """panels table must have 10 + 5 = 15 rows after ingesting both profiles."""
    from flying_probe_copilot.parser.cli import main

    db_path = tmp_path / "rt_panels.duckdb"
    small_dir = _make_run_dir(tmp_path, small_10_log, "small", "run_rt_small", seed=42)
    medium_dir = _make_run_dir(tmp_path, medium_5_log, "medium", "run_rt_medium", seed=43)

    assert main(["--input", str(small_dir), "--db", str(db_path)]) == 0
    assert main(["--input", str(medium_dir), "--db", str(db_path)]) == 0

    con = duckdb.connect(str(db_path))
    count = con.execute("SELECT COUNT(*) FROM panels").fetchone()[0]
    con.close()
    assert count == 15, f"Expected 15 panels, got {count}"


def test_roundtrip_preserves_test_runs_count(small_10_log, medium_5_log, tmp_path):
    """test_runs table must have 15 rows."""
    from flying_probe_copilot.parser.cli import main

    db_path = tmp_path / "rt_test_runs.duckdb"
    small_dir = _make_run_dir(tmp_path, small_10_log, "small", "run_rt2_small", seed=42)
    medium_dir = _make_run_dir(tmp_path, medium_5_log, "medium", "run_rt2_medium", seed=43)

    main(["--input", str(small_dir), "--db", str(db_path)])
    main(["--input", str(medium_dir), "--db", str(db_path)])

    con = duckdb.connect(str(db_path))
    count = con.execute("SELECT COUNT(*) FROM test_runs").fetchone()[0]
    con.close()
    assert count == 15, f"Expected 15 test_runs, got {count}"


def test_roundtrip_preserves_measurements_count_within_one_percent_tolerance(
    small_10_log, medium_5_log, tmp_path
):
    """measurements count must match in-memory block total within 1% tolerance."""
    from flying_probe_copilot.parser.cli import main

    expected = sum(len(b.blocks) for b in small_10_log.boards) + sum(
        len(b.blocks) for b in medium_5_log.boards
    )
    db_path = tmp_path / "rt_measurements.duckdb"
    small_dir = _make_run_dir(tmp_path, small_10_log, "small", "run_rt3_small", seed=42)
    medium_dir = _make_run_dir(tmp_path, medium_5_log, "medium", "run_rt3_medium", seed=43)

    main(["--input", str(small_dir), "--db", str(db_path)])
    main(["--input", str(medium_dir), "--db", str(db_path)])

    con = duckdb.connect(str(db_path))
    count = con.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]
    con.close()

    assert expected > 0
    rel_err = abs(count - expected) / expected
    assert rel_err <= 0.01, (
        f"measurements count {count} vs expected {expected} — "
        f"relative error {rel_err:.2%} exceeds 1% tolerance"
    )


def test_roundtrip_preserves_btest_status_distribution(small_10_log, medium_5_log, tmp_path):
    """btest_status distribution in DB must match in-memory distribution."""
    from collections import Counter

    from flying_probe_copilot.parser.cli import main

    # Build expected distribution from in-memory logs
    in_memory_dist: Counter = Counter()
    for board in small_10_log.boards:
        in_memory_dist[int(board.btest.status)] += 1
    for board in medium_5_log.boards:
        in_memory_dist[int(board.btest.status)] += 1

    db_path = tmp_path / "rt_status.duckdb"
    small_dir = _make_run_dir(tmp_path, small_10_log, "small", "run_rt4_small", seed=42)
    medium_dir = _make_run_dir(tmp_path, medium_5_log, "medium", "run_rt4_medium", seed=43)

    main(["--input", str(small_dir), "--db", str(db_path)])
    main(["--input", str(medium_dir), "--db", str(db_path)])

    con = duckdb.connect(str(db_path))
    rows = con.execute(
        "SELECT btest_status, COUNT(*) FROM test_runs GROUP BY btest_status"
    ).fetchall()
    con.close()

    db_dist: Counter = Counter({r[0]: r[1] for r in rows})
    assert db_dist == in_memory_dist, (
        f"btest_status distribution mismatch:\n"
        f"  DB:        {dict(db_dist)}\n"
        f"  in-memory: {dict(in_memory_dist)}"
    )


def test_roundtrip_first_panel_start_ts_matches_in_memory_panel_timestamp(small_10_log, tmp_path):
    """start_ts in test_runs must equal the generator's panel.timestamp (#BLOCKER-4)."""
    from flying_probe_copilot.parser.cli import main

    db_path = tmp_path / "rt_timestamp.duckdb"
    small_dir = _make_run_dir(tmp_path, small_10_log, "small", "run_rt5_small", seed=42)
    main(["--input", str(small_dir), "--db", str(db_path)])

    # Get the first panel's serial and expected timestamp from the generator
    first_board = small_10_log.boards[0]
    expected_ts = first_board.panel.timestamp  # datetime  # noqa: F841
    expected_start_ts_int = first_board.btest.start_ts  # YYMMDDHHMMSS int

    # Parse the YYMMDDHHMMSS int back to a datetime using the same helper
    from flying_probe_copilot.parser.log_parser import _parse_yymmddhhmmss

    expected_dt = _parse_yymmddhhmmss(expected_start_ts_int)

    con = duckdb.connect(str(db_path))
    row = con.execute(
        "SELECT start_ts FROM test_runs WHERE panel_serial = ?",
        [first_board.btest.board_id],
    ).fetchone()
    con.close()

    assert row is not None, f"No test_run found for panel {first_board.btest.board_id!r}"
    db_dt: datetime = row[0]

    # DuckDB returns timestamps as Python datetime objects
    if hasattr(db_dt, "replace"):
        db_dt = db_dt.replace(tzinfo=None)

    assert db_dt == expected_dt, f"start_ts mismatch: DB={db_dt!r}, expected={expected_dt!r}"
