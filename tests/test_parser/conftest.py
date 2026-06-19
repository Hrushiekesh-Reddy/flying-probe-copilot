"""Shared pytest fixtures for tests/test_parser/.

Import rules (Revision 1 #BLOCKER-1):
  - Top-level imports: stdlib + duckdb + flying_probe_copilot.generator.* ONLY.
  - Any flying_probe_copilot.parser.* or flying_probe_copilot.db.* import
    MUST be deferred inside the fixture body where it is needed. This prevents
    pytest collection failure while parser/db modules are not yet created.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import pytest

from flying_probe_copilot.generator.blocks import generate_blocks
from flying_probe_copilot.generator.cli import _build_batch_log
from flying_probe_copilot.generator.faults import generate_panel_faults
from flying_probe_copilot.generator.models import (
    BatchLog,
    BatchRecord,
    BoardLog,
    BoardTestRecord,
    BTESTStatus,
    derive_btest_status,
)
from flying_probe_copilot.generator.profiles import get_profile
from flying_probe_copilot.generator.renderers.log import render_log
from flying_probe_copilot.generator.schedule import generate_panel_schedule


# ---------------------------------------------------------------------------
# Minimal argparse-like namespace for _build_batch_log
# ---------------------------------------------------------------------------


class _Args:
    """Minimal argparse namespace substitute for generator helper calls."""

    def __init__(
        self,
        board_profile: str,
        count: int,
        seed: int = 42,
        fault_rate: float = 0.05,
        fault_profile: str = "random",
        start_date: str = "2026-04-01",
        end_date: str = "2026-04-08",
        operators: int = 4,
        lines: int = 2,
        format: str = "log",
        encoding: str = "cp1252",
    ):
        self.board_profile = board_profile
        self.count = count
        self.seed = seed
        self.fault_rate = fault_rate
        self.fault_profile = fault_profile
        self.start_date = start_date
        self.end_date = end_date
        self.operators = operators
        self.lines = lines
        self.format = format
        self.encoding = encoding


# ---------------------------------------------------------------------------
# In-memory DB fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def in_mem_db():
    """In-memory DuckDB connection initialised with the Phase 1b schema."""
    from flying_probe_copilot.db.schema import init_database

    conn = duckdb.connect(":memory:")
    init_database(conn)
    yield conn
    conn.close()


@pytest.fixture
def tmp_db(tmp_path):
    """DuckDB file in tmp_path initialised with the Phase 1b schema."""
    from flying_probe_copilot.db.schema import init_database

    db_path = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_path))
    init_database(conn)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# BatchLog fixtures (in-memory, no file I/O)
# ---------------------------------------------------------------------------


@pytest.fixture
def small_batch_log() -> BatchLog:
    """3 small-profile panels, seed=42. Fully deterministic."""
    args = _Args(board_profile="small", count=3, seed=42)
    return _build_batch_log(args, "small")


@pytest.fixture
def medium_batch_log() -> BatchLog:
    """3 medium-profile panels, seed=43. Fully deterministic."""
    args = _Args(board_profile="medium", count=3, seed=43)
    return _build_batch_log(args, "medium")


# ---------------------------------------------------------------------------
# Run-directory fixture
# ---------------------------------------------------------------------------


def _write_run_dir(
    tmp_path: Path,
    board_profile: str,
    count: int,
    seed: int,
    fault_rate: float,
    start_date: str,
    end_date: str,
    encoding: str = "cp1252",
) -> Path:
    """Write a generator run directory to tmp_path and return the run dir path."""
    args = _Args(
        board_profile=board_profile,
        count=count,
        seed=seed,
        fault_rate=fault_rate,
        start_date=start_date,
        end_date=end_date,
        encoding=encoding,
    )
    batch_log = _build_batch_log(args, board_profile)

    run_dir = tmp_path / f"run_{board_profile}_{seed}"
    run_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = run_dir / "logs"
    logs_dir.mkdir()

    for board in batch_log.boards:
        single = BatchLog(batch=batch_log.batch, boards=[board])
        render_log(single, logs_dir / f"{board.panel.serial}.log", encoding=encoding)

    failing = sum(
        1 for b in batch_log.boards if b.btest.status != BTESTStatus.PASS
    )
    manifest = {
        "panel_count": count,
        "fault_rate": fault_rate,
        "fault_profile": "random",
        "seed": seed,
        "board_profile": board_profile,
        "failing_boards": failing,
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    return run_dir


@pytest.fixture
def small_run_dir(tmp_path) -> Path:
    """A fully-written generator run dir with 10 small panels (seed=42)."""
    return _write_run_dir(
        tmp_path,
        board_profile="small",
        count=10,
        seed=42,
        fault_rate=0.10,
        start_date="2026-04-08",
        end_date="2026-04-15",
    )


@pytest.fixture
def sample_run_dir(tmp_path) -> Path:
    """Run dir with 10 small + 5 medium panels across a 2-week window.

    Two separate run directories are written (one per profile), then a
    combined 'manifest' run dir is synthesised so the parser's
    ingest_run_directory has a single path to walk.
    """
    # Week 1: days [-14, -8] — inverted fault rates (small=30%, medium=10%)
    small_w1 = _write_run_dir(
        tmp_path / "small_w1",
        board_profile="small",
        count=5,
        seed=100,
        fault_rate=0.30,
        start_date="2026-03-29",
        end_date="2026-04-05",
    )
    medium_w1 = _write_run_dir(
        tmp_path / "medium_w1",
        board_profile="medium",
        count=3,
        seed=101,
        fault_rate=0.10,
        start_date="2026-03-29",
        end_date="2026-04-05",
    )

    # Week 2: days [-7, 0] — target fault rates (small=10%, medium=30%)
    small_w2 = _write_run_dir(
        tmp_path / "small_w2",
        board_profile="small",
        count=5,
        seed=102,
        fault_rate=0.10,
        start_date="2026-04-06",
        end_date="2026-04-13",
    )
    medium_w2 = _write_run_dir(
        tmp_path / "medium_w2",
        board_profile="medium",
        count=2,
        seed=103,
        fault_rate=0.30,
        start_date="2026-04-06",
        end_date="2026-04-13",
    )

    return {
        "small_w1": small_w1,
        "medium_w1": medium_w1,
        "small_w2": small_w2,
        "medium_w2": medium_w2,
    }


@pytest.fixture
def roundtrip_run_dir(tmp_path) -> Path:
    """Run dir with 10 small + 5 medium panels for round-trip tests."""
    # Small: 10 panels
    small_dir = _write_run_dir(
        tmp_path / "rt_small",
        board_profile="small",
        count=10,
        seed=42,
        fault_rate=0.05,
        start_date="2026-04-01",
        end_date="2026-04-08",
    )
    # Medium: 5 panels
    medium_dir = _write_run_dir(
        tmp_path / "rt_medium",
        board_profile="medium",
        count=5,
        seed=43,
        fault_rate=0.05,
        start_date="2026-04-01",
        end_date="2026-04-08",
    )
    return {"small": small_dir, "medium": medium_dir}


# ---------------------------------------------------------------------------
# Malformed log fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def malformed_log_path(tmp_path) -> Path:
    """A .log file with one corrupt @A-RES record (invalid non-numeric status field).

    The closing brace is kept intact so the tokenizer still yields the record;
    but the status field is replaced with 'CORRUPT' so the record parser fails.
    This ensures ParseReport.errors is populated for the malformed record while
    surrounding valid records continue to parse normally.
    """
    args = _Args(board_profile="small", count=1, seed=99)
    batch_log = _build_batch_log(args, "small")

    # Render a valid log first, then doctor one line
    log_path = tmp_path / "malformed.log"
    render_log(batch_log, log_path, encoding="utf-8")

    raw = log_path.read_text(encoding="utf-8")
    lines = raw.splitlines(keepends=True)

    # Find an @A- line and corrupt the status field (second pipe-delimited field)
    # e.g. {@A-RES|0|+9.97E+03|R1} → {@A-RES|CORRUPT|+9.97E+03|R1}
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("{@A-") and stripped.endswith("}"):
            # Replace first field after the record-type with 'CORRUPT'
            content = stripped[1:-1]  # strip outer braces
            parts = content.split("|")
            if len(parts) >= 2:
                parts[1] = "CORRUPT"
                lines[i] = "{" + "|".join(parts) + "}\n"
                break

    log_path.write_text("".join(lines), encoding="utf-8")
    return log_path
