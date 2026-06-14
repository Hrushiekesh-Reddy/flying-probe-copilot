"""CLI integration tests.

Phase 1a Step H1 — RED phase. Exercises the public CLI by invoking
``main(argv=[...])`` in-process; this avoids spawning subprocesses and keeps
tests fast.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


def _invoke(argv: list[str]) -> int:
    """Call the CLI's ``main`` in-process and return its exit code."""
    from flying_probe_copilot.generator.cli import main

    try:
        return main(argv)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 0


def test_cli_help_lists_all_documented_flags(capsys):
    rc = _invoke(["--help"])
    assert rc == 0
    captured = capsys.readouterr().out
    for flag in (
        "--board-profile",
        "--count",
        "--out",
        "--seed",
        "--fault-rate",
        "--fault-profile",
        "--start-date",
        "--end-date",
        "--operators",
        "--lines",
        "--format",
        "--encoding",
    ):
        assert flag in captured, f"--help missing {flag}"


def test_cli_run_writes_run_directory_with_expected_files(tmp_path):
    rc = _invoke(
        [
            "--board-profile=small",
            "--count=5",
            f"--out={tmp_path}",
            "--seed=42",
        ]
    )
    assert rc == 0
    runs = sorted(tmp_path.iterdir())
    assert runs, "no run directory created"
    run = runs[0]
    assert (run / "config.yaml").exists()
    assert (run / "manifest.json").exists()
    assert (run / "logs").is_dir()
    log_files = list((run / "logs").glob("*.log"))
    assert len(log_files) == 5
    assert (run / "results.csv").exists()
    assert (run / "results.json").exists()


def test_cli_unknown_board_profile_exits_non_zero(tmp_path):
    rc = _invoke(
        [
            "--board-profile=gigantic",
            "--count=2",
            f"--out={tmp_path}",
        ]
    )
    assert rc != 0


def test_cli_resolved_config_yaml_round_trips_through_yaml_loader(tmp_path):
    rc = _invoke(
        [
            "--board-profile=small",
            "--count=2",
            f"--out={tmp_path}",
            "--seed=123",
        ]
    )
    assert rc == 0
    run = next(tmp_path.iterdir())
    cfg_text = (run / "config.yaml").read_text(encoding="utf-8")
    cfg = yaml.safe_load(cfg_text)
    assert cfg["board_profile"] == "small"
    assert cfg["count"] == 2
    assert cfg["seed"] == 123


def test_cli_manifest_json_contains_panel_count_fault_rate_seed(tmp_path):
    rc = _invoke(
        [
            "--board-profile=small",
            "--count=3",
            f"--out={tmp_path}",
            "--seed=7",
            "--fault-rate=0.15",
        ]
    )
    assert rc == 0
    run = next(tmp_path.iterdir())
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["panel_count"] == 3
    assert abs(manifest["fault_rate"] - 0.15) < 1e-9
    assert manifest["seed"] == 7


def test_cli_same_start_end_date_runs_as_one_day_window(tmp_path):
    """Bugbot regression: --start-date == --end-date is a 24h window, not a crash."""
    rc = _invoke(
        [
            "--board-profile=small",
            "--count=2",
            f"--out={tmp_path}",
            "--seed=42",
            "--start-date=2026-05-10",
            "--end-date=2026-05-10",
        ]
    )
    assert rc == 0
    run = next(tmp_path.iterdir())
    assert (run / "logs").is_dir()
    assert (run / "manifest.json").exists()
    # Logs should land on (or wrap into) 2026-05-10 — the timestamp is in
    # the @BTEST start_ts field as YYMMDDHHMMSS. Spot-check the first log.
    log_file = next((run / "logs").iterdir())
    raw = log_file.read_bytes().decode("cp1252")
    # YYMMDDHHMMSS for 2026-05-10 starts with 260510 (within the 24h window).
    assert "|260510" in raw or "|260511" in raw  # window includes both endpoints


def test_cli_end_before_start_errors_clearly(tmp_path, capsys):
    """Bugbot regression: end < start exits non-zero with a clear message."""
    rc = _invoke(
        [
            "--board-profile=small",
            "--count=1",
            f"--out={tmp_path}",
            "--start-date=2026-05-10",
            "--end-date=2026-05-09",
        ]
    )
    assert rc != 0
    captured = capsys.readouterr()
    combined = captured.err + captured.out
    assert "--end-date" in combined
    assert "--start-date" in combined
