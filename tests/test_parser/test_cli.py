"""Tests for src/flying_probe_copilot/parser/cli.py.

Tests exercise the cli.main([...]) in-process entry point.
Per #MINOR-16: NOT tested via 'uv run parser' — console-script
registration is verified by code presence (pyproject.toml edit) only.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flying_probe_copilot.generator.models import BatchLog, BTESTStatus
from flying_probe_copilot.generator.renderers.log import render_log


def _write_run(tmp_path: Path, batch_log: BatchLog, profile: str) -> Path:
    """Write a minimal run directory and return its path."""
    run_dir = tmp_path / f"run_{profile}_cli_test"
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


def test_cli_main_returns_zero_for_valid_run_dir(small_batch_log, tmp_path):
    """cli.main(["--input", ..., "--db", ...]) must return 0 for a valid run dir."""
    from flying_probe_copilot.parser.cli import main

    run_dir = _write_run(tmp_path, small_batch_log, "small")
    db_path = tmp_path / "test_output.duckdb"

    ret = main(["--input", str(run_dir), "--db", str(db_path)])
    assert ret == 0, f"Expected exit code 0, got {ret}"
    assert db_path.exists(), "DuckDB file must be created"


def test_cli_main_populates_db_with_panels(small_batch_log, tmp_path):
    """After cli.main(), DuckDB must contain the expected number of panels."""
    from flying_probe_copilot.parser.cli import main
    import duckdb

    run_dir = _write_run(tmp_path, small_batch_log, "small")
    db_path = tmp_path / "test_panels.duckdb"

    main(["--input", str(run_dir), "--db", str(db_path)])

    con = duckdb.connect(str(db_path))
    count = con.execute("SELECT COUNT(*) FROM panels").fetchone()[0]
    con.close()
    assert count == len(small_batch_log.boards), (
        f"Expected {len(small_batch_log.boards)} panels, got {count}"
    )


def test_cli_main_returns_nonzero_for_missing_input(tmp_path):
    """cli.main() must return non-zero when --input dir does not exist."""
    from flying_probe_copilot.parser.cli import main

    missing = tmp_path / "nonexistent_run_dir"
    db_path = tmp_path / "should_not_exist.duckdb"

    ret = main(["--input", str(missing), "--db", str(db_path)])
    assert ret != 0, f"Expected non-zero exit for missing input, got {ret}"


def test_cli_creates_parent_directory_for_db_file_if_missing(small_batch_log, tmp_path):
    """cli.main() must create parent directories for --db path if they don't exist."""
    from flying_probe_copilot.parser.cli import main

    run_dir = _write_run(tmp_path, small_batch_log, "small")
    db_path = tmp_path / "nested" / "dir" / "output.duckdb"

    ret = main(["--input", str(run_dir), "--db", str(db_path)])
    assert ret == 0, f"Expected exit code 0 with nested db dir, got {ret}"
    assert db_path.exists(), "DuckDB file must be created in nested parent dir"


def test_cli_exits_with_code_2_when_run_already_ingested(small_batch_log, tmp_path):
    """Re-ingesting the same run_id must return exit code 2."""
    from flying_probe_copilot.parser.cli import main

    run_dir = _write_run(tmp_path, small_batch_log, "small")
    db_path = tmp_path / "test_rerun.duckdb"

    # First ingest — should succeed
    ret1 = main(["--input", str(run_dir), "--db", str(db_path)])
    assert ret1 == 0, f"First ingest must succeed (exit 0), got {ret1}"

    # Second ingest of same run — must return 2
    ret2 = main(["--input", str(run_dir), "--db", str(db_path)])
    assert ret2 == 2, f"Re-ingest must exit with code 2, got {ret2}"


def test_cli_returns_nonzero_for_missing_manifest(tmp_path):
    """A run dir with no manifest.json must return non-zero exit code."""
    from flying_probe_copilot.parser.cli import main

    run_dir = tmp_path / "run_no_manifest"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir()
    db_path = tmp_path / "nm.duckdb"

    ret = main(["--input", str(run_dir), "--db", str(db_path)])
    assert ret != 0, "Expected non-zero exit when manifest.json is missing"


def test_cli_returns_one_on_ingest_exception(tmp_path):
    """An exception during ingest (e.g. missing manifest) must return exit code 1."""
    from flying_probe_copilot.parser.cli import main

    # Create a run dir with a manifest that has invalid JSON to trigger a parse exception
    run_dir = tmp_path / "run_bad_manifest"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir()
    (run_dir / "manifest.json").write_text("NOT JSON {{{", encoding="utf-8")
    db_path = tmp_path / "bad.duckdb"

    ret = main(["--input", str(run_dir), "--db", str(db_path)])
    assert ret == 1, f"Expected exit code 1 for ingest exception, got {ret}"


def test_cli_encoding_auto_handles_cp1252(small_batch_log, tmp_path):
    """--encoding=auto must successfully parse a cp1252-encoded log."""
    from flying_probe_copilot.parser.cli import main
    import duckdb

    # Write a run dir with cp1252 encoding
    run_dir = tmp_path / "run_cp1252_cli"
    run_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = run_dir / "logs"
    logs_dir.mkdir()
    for board in small_batch_log.boards:
        single = BatchLog(batch=small_batch_log.batch, boards=[board])
        render_log(single, logs_dir / f"{board.panel.serial}.log", encoding="cp1252")
    failing = sum(1 for b in small_batch_log.boards if b.btest.status != BTESTStatus.PASS)
    manifest = {
        "panel_count": len(small_batch_log.boards),
        "fault_rate": 0.05,
        "fault_profile": "random",
        "seed": 42,
        "board_profile": "small",
        "failing_boards": failing,
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    db_path = tmp_path / "test_cp1252.duckdb"
    ret = main(["--input", str(run_dir), "--db", str(db_path), "--encoding", "auto"])
    assert ret == 0, f"Expected exit code 0 for cp1252 log with --encoding=auto, got {ret}"

    con = duckdb.connect(str(db_path))
    count = con.execute("SELECT COUNT(*) FROM panels").fetchone()[0]
    con.close()
    assert count == len(small_batch_log.boards), (
        f"Expected {len(small_batch_log.boards)} panels from cp1252 log, got {count}"
    )
