"""Reproducibility tests — same seed produces byte-identical artifacts.

Phase 1a Step H1 — RED phase. Exercises the CLI twice with the same seed and
compares byte content of every output file.
"""

from __future__ import annotations


def _invoke(argv):
    from flying_probe_copilot.generator.cli import main

    try:
        return main(argv)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 0


def _two_runs(tmp_factory, seed: int):
    a = tmp_factory.mktemp("a")
    b = tmp_factory.mktemp("b")
    rc_a = _invoke(["--board-profile=small", "--count=5", f"--out={a}", f"--seed={seed}"])
    rc_b = _invoke(["--board-profile=small", "--count=5", f"--out={b}", f"--seed={seed}"])
    assert rc_a == 0 and rc_b == 0
    return next(a.iterdir()), next(b.iterdir())


def test_same_seed_produces_byte_identical_log_files(tmp_path_factory):
    run_a, run_b = _two_runs(tmp_path_factory, seed=42)
    logs_a = sorted((run_a / "logs").glob("*.log"))
    logs_b = sorted((run_b / "logs").glob("*.log"))
    assert len(logs_a) == len(logs_b) == 5
    for la, lb in zip(logs_a, logs_b):
        assert la.read_bytes() == lb.read_bytes(), f"{la.name} differs"


def test_same_seed_produces_byte_identical_csv(tmp_path_factory):
    run_a, run_b = _two_runs(tmp_path_factory, seed=42)
    assert (run_a / "results.csv").read_bytes() == (run_b / "results.csv").read_bytes()


def test_same_seed_produces_byte_identical_json(tmp_path_factory):
    run_a, run_b = _two_runs(tmp_path_factory, seed=42)
    assert (run_a / "results.json").read_bytes() == (run_b / "results.json").read_bytes()
