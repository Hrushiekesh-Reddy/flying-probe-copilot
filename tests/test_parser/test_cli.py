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


def test_cli_encoding_utf8_fails_on_cp1252_log(small_batch_log, tmp_path):
    """BUG-005: --encoding=utf-8 against a cp1252 log must fail (and surface a parse error),
    proving the flag is actually threaded into the parser instead of silently falling
    back to auto-detect."""
    from flying_probe_copilot.parser.cli import main

    run_dir = tmp_path / "run_cp1252_strict"
    run_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = run_dir / "logs"
    logs_dir.mkdir()
    # Render with cp1252; ensure at least one byte that's invalid utf-8 ends up in the file
    for board in small_batch_log.boards:
        single = BatchLog(batch=small_batch_log.batch, boards=[board])
        log_path = logs_dir / f"{board.panel.serial}.log"
        render_log(single, log_path, encoding="cp1252")
        # Inject a cp1252-only byte (0x92 = right single quote) so utf-8 decode must fail
        with log_path.open("ab") as fh:
            fh.write(b"{@COMMENT|don\x92t parse me as utf-8}\r\n")
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

    db_path = tmp_path / "test_utf8_strict.duckdb"
    ret = main(["--input", str(run_dir), "--db", str(db_path), "--encoding", "utf-8"])
    # CLI catches the parse error and returns exit 0 with parse_errors > 0,
    # OR returns 1 if every file failed. Either way, parse_errors must be > 0.
    import duckdb
    con = duckdb.connect(str(db_path))
    rows = con.execute(
        "SELECT COUNT(*) FROM panels"
    ).fetchone()
    panel_count = rows[0] if rows else 0
    con.close()
    # Under the bug, --encoding was ignored and auto-detect succeeded — all panels ingested.
    # After BUG-005 fix, strict utf-8 on a cp1252 file must skip at least one log.
    assert panel_count < len(small_batch_log.boards), (
        f"BUG-005: --encoding=utf-8 was ignored — got {panel_count} panels from cp1252 input, "
        f"expected fewer than {len(small_batch_log.boards)}"
    )


def test_runs_row_not_persisted_when_ingest_raises_mid_loop(
    small_batch_log, tmp_path, monkeypatch
):
    """BUG-006: if _ingest_batch_log raises mid-loop, the runs row must NOT be
    persisted — otherwise the CLI re-ingest guard (exit code 2) would block any retry
    after the cause is fixed.

    Forces a mid-loop exception by monkeypatching _ingest_batch_log to raise on the
    first call, then asserts that the runs row is absent and that a follow-up ingest
    (with the patch lifted) succeeds with exit code 0.
    """
    import duckdb
    from flying_probe_copilot.parser import ingest as ingest_mod
    from flying_probe_copilot.parser.cli import main

    run_dir = _write_run(tmp_path, small_batch_log, "small")
    db_path = tmp_path / "bug006.duckdb"

    real = ingest_mod._ingest_batch_log

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated mid-loop ingest failure")

    monkeypatch.setattr(ingest_mod, "_ingest_batch_log", _boom)
    ret = main(["--input", str(run_dir), "--db", str(db_path)])
    assert ret == 1, f"Mid-loop exception must yield exit 1, got {ret}"

    con = duckdb.connect(str(db_path))
    runs = con.execute(
        "SELECT COUNT(*) FROM runs WHERE run_id = ?", [run_dir.name]
    ).fetchone()[0]
    con.close()
    assert runs == 0, (
        f"BUG-006: failed ingest left {runs} stranded runs row(s) — re-ingest would be blocked"
    )

    # Lift the patch and retry — must succeed, proving the run is genuinely retry-able.
    monkeypatch.setattr(ingest_mod, "_ingest_batch_log", real)
    ret2 = main(["--input", str(run_dir), "--db", str(db_path)])
    assert ret2 == 0, f"Retry after failure must succeed (exit 0), got {ret2}"

    con = duckdb.connect(str(db_path))
    runs2 = con.execute(
        "SELECT COUNT(*) FROM runs WHERE run_id = ?", [run_dir.name]
    ).fetchone()[0]
    con.close()
    assert runs2 == 1, f"Successful retry must persist exactly one runs row, got {runs2}"


def test_partial_multi_file_failure_rolls_back_earlier_panels(
    small_batch_log, tmp_path, monkeypatch
):
    """BUG-008: when _ingest_batch_log succeeds on early files then raises on a later
    one, the earlier files' panels/test_runs/measurements MUST be rolled back. Without
    a transaction the partial state would remain, and a retry would hit
    PRIMARY KEY conflicts on panels.panel_serial instead of completing cleanly.
    """
    import duckdb
    from flying_probe_copilot.parser import ingest as ingest_mod
    from flying_probe_copilot.parser.cli import main

    # Ensure the run dir has multiple log files so "early success then late failure" is meaningful
    assert len(small_batch_log.boards) >= 3, (
        "Test requires a multi-file run; small_batch_log fixture has too few boards"
    )

    run_dir = _write_run(tmp_path, small_batch_log, "small")
    db_path = tmp_path / "bug008.duckdb"

    real = ingest_mod._ingest_batch_log
    call_count = {"n": 0}

    def _succeed_then_boom(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] >= 3:
            raise RuntimeError("simulated late-file ingest failure")
        return real(*args, **kwargs)

    monkeypatch.setattr(ingest_mod, "_ingest_batch_log", _succeed_then_boom)
    ret = main(["--input", str(run_dir), "--db", str(db_path)])
    assert ret == 1, f"Mid-loop exception must yield exit 1, got {ret}"

    # The transaction must have rolled back the 2 earlier-file successes
    con = duckdb.connect(str(db_path))
    panels = con.execute("SELECT COUNT(*) FROM panels").fetchone()[0]
    test_runs = con.execute("SELECT COUNT(*) FROM test_runs").fetchone()[0]
    measurements = con.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]
    runs = con.execute("SELECT COUNT(*) FROM runs WHERE run_id = ?", [run_dir.name]).fetchone()[0]
    con.close()
    assert panels == 0, f"BUG-008: rollback failed — {panels} panel rows survived"
    assert test_runs == 0, f"BUG-008: rollback failed — {test_runs} test_run rows survived"
    assert measurements == 0, f"BUG-008: rollback failed — {measurements} measurement rows survived"
    assert runs == 0, f"runs row must not be persisted on failure, got {runs}"

    # Retry without the patch — must succeed cleanly, no PK conflicts
    monkeypatch.setattr(ingest_mod, "_ingest_batch_log", real)
    ret2 = main(["--input", str(run_dir), "--db", str(db_path)])
    assert ret2 == 0, f"Retry after rollback must succeed (exit 0), got {ret2}"

    con = duckdb.connect(str(db_path))
    panels = con.execute("SELECT COUNT(*) FROM panels").fetchone()[0]
    con.close()
    assert panels == len(small_batch_log.boards), (
        f"Retry must insert all {len(small_batch_log.boards)} panels, got {panels}"
    )
