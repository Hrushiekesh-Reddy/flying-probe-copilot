"""Command-line entry point for the synthetic log generator.

Composes ``profiles``, ``schedule``, ``faults``, ``models``, and ``renderers``
into a single end-to-end run that writes ``config.yaml``, ``manifest.json``,
``logs/*.log``, ``results.csv`` and ``results.json`` to a fresh run directory
under ``--out``.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from .blocks import generate_blocks
from .faults import generate_panel_faults
from .models import (
    BatchLog,
    BatchRecord,
    BoardLog,
    BoardTestRecord,
    BTESTStatus,
    derive_btest_status,
)
from .profiles import available_profiles, get_profile
from .renderers.csv_ import render_csv
from .renderers.json_ import render_json
from .renderers.log import render_log
from .schedule import generate_panel_schedule


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="flying-probe-gen",
        description="Synthetic HP3070 / Keysight i3070 ICT log generator.",
    )
    p.add_argument("--board-profile", required=True, help="small | medium | large")
    p.add_argument("--count", type=int, required=True, help="number of panels")
    p.add_argument("--out", required=True, type=Path, help="output root directory")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--fault-rate", type=float, default=0.05)
    p.add_argument(
        "--fault-profile",
        default="random",
        choices=["random", "drift", "cluster", "process-change"],
    )
    p.add_argument("--start-date", default="2026-04-01")
    p.add_argument("--end-date", default="2026-04-29")
    p.add_argument("--operators", type=int, default=4)
    p.add_argument("--lines", type=int, default=2)
    p.add_argument(
        "--format", default="all", choices=["log", "csv", "json", "all"]
    )
    p.add_argument(
        "--encoding",
        default="cp1252",
        help="Output encoding for .log files (cp1252 | utf-8)",
    )
    return p


def _resolve_run_dir(out: Path) -> Path:
    """Pick a unique ``run_YYYY-MM-DDTHH-MM-SS`` subdirectory under ``out``."""
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S-%f")
    run = out / f"run_{stamp}"
    run.mkdir(parents=True, exist_ok=False)
    return run


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _build_batch_log(args, profile_name: str) -> BatchLog:
    profile = get_profile(profile_name)
    start = datetime.fromisoformat(args.start_date)
    end = datetime.fromisoformat(args.end_date)

    panels = generate_panel_schedule(
        start=start,
        end=end,
        count=args.count,
        seed=args.seed,
        operators=args.operators,
        lines=args.lines,
        board_profile_id=profile.id,
    )

    change_point = start + (end - start) / 2

    boards: list[BoardLog] = []
    for idx, panel in enumerate(panels):
        panel_seed = args.seed * 1000 + idx
        outcome = generate_panel_faults(
            seed=panel_seed,
            profile=args.fault_profile,
            target_rate=args.fault_rate,
            panel_timestamp=panel.timestamp,
            window_start=start,
            window_end=end,
            change_point=change_point,
        )
        blocks = generate_blocks(profile, outcome, panel_seed)
        derived = derive_btest_status(blocks)
        start_ts = int(panel.timestamp.strftime("%y%m%d%H%M%S"))
        end_ts = int(
            (panel.timestamp + timedelta(seconds=12)).strftime("%y%m%d%H%M%S")
        )
        btest = BoardTestRecord(
            board_id=panel.serial,
            status=derived,
            start_ts=start_ts,
            duration_s=12,
            end_ts=end_ts,
            board_number=1,
        )
        boards.append(BoardLog(panel=panel, btest=btest, blocks=blocks))

    batch = BatchRecord(
        uut_type=f"BRD-{profile_name.upper()}",
        uut_rev="A",
        fixture_id=1,
        testhead_num=1,
        process_step="ICT",
        batch_id=f"BAT-{args.seed:04d}",
        operator_id=boards[0].panel.operator_id if boards else "OP-001",
        controller="ICT01",
        testplan_id="TP-001",
        testplan_rev="v1.0",
        parent_panel_type=f"PNL-{profile_name.upper()}",
        parent_panel_rev="A",
    )
    return BatchLog(batch=batch, boards=boards)


# ---------------------------------------------------------------------------
# Output writing
# ---------------------------------------------------------------------------


def _write_outputs(run_dir: Path, batch_log: BatchLog, args) -> None:
    logs_dir = run_dir / "logs"
    logs_dir.mkdir()

    # One log file per board (one @BATCH wrapping one @BTEST). For v1 we keep
    # a single batch with multiple boards inside, but also emit a convenience
    # per-board log file using the panel serial as the filename. The CLI test
    # checks for ``logs/*.log`` with count == --count, so we emit one per board.
    for board in batch_log.boards:
        single = BatchLog(batch=batch_log.batch, boards=[board])
        if args.format in ("log", "all"):
            render_log(
                single, logs_dir / f"{board.panel.serial}.log", encoding=args.encoding
            )

    if args.format in ("csv", "all"):
        render_csv(batch_log, run_dir / "results.csv")
    if args.format in ("json", "all"):
        render_json(batch_log, run_dir / "results.json")


def _write_config_and_manifest(run_dir: Path, args, batch_log: BatchLog) -> None:
    cfg = {
        "board_profile": args.board_profile,
        "count": args.count,
        "seed": args.seed,
        "fault_rate": args.fault_rate,
        "fault_profile": args.fault_profile,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "operators": args.operators,
        "lines": args.lines,
        "format": args.format,
        "encoding": args.encoding,
    }
    (run_dir / "config.yaml").write_text(
        yaml.safe_dump(cfg, sort_keys=True), encoding="utf-8"
    )

    failing = sum(
        1
        for board in batch_log.boards
        if board.btest.status != BTESTStatus.PASS
    )
    manifest = {
        "panel_count": args.count,
        "fault_rate": args.fault_rate,
        "fault_profile": args.fault_profile,
        "seed": args.seed,
        "board_profile": args.board_profile,
        "failing_boards": failing,
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.board_profile not in available_profiles():
        parser.error(
            f"unknown board profile {args.board_profile!r}; "
            f"valid: {', '.join(available_profiles())}"
        )

    batch_log = _build_batch_log(args, args.board_profile)
    run_dir = _resolve_run_dir(args.out)
    _write_outputs(run_dir, batch_log, args)
    _write_config_and_manifest(run_dir, args, batch_log)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
