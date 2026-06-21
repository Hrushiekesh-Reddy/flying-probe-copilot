"""Command-line entry point for the Phase 1b log parser and DuckDB ingest.

Usage:
  uv run parser --input <run_dir> --db <path.duckdb> [--encoding auto|utf-8|cp1252]

Pre-flight check (#WARNING-13): if the run_id (directory basename) already
exists in the runs table, exits with code 2 and a helpful message to stderr.

Parent directory for --db is created automatically (#MINOR-16 / Step 17).

Tested via cli.main([...]) in-process; NOT via 'uv run parser' (#MINOR-16).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

from flying_probe_copilot.db.schema import init_database
from flying_probe_copilot.parser.ingest import ingest_run_directory


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="flying-probe-parser",
        description="Ingest Keysight i3070 .log files into a DuckDB database.",
    )
    p.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to a generator run directory (contains manifest.json + logs/).",
    )
    p.add_argument(
        "--db",
        required=True,
        type=Path,
        help="Path to the DuckDB file to write (created if it does not exist).",
    )
    p.add_argument(
        "--encoding",
        default="auto",
        choices=["auto", "utf-8", "cp1252"],
        help=("Log file encoding. 'auto' tries utf-8 then falls back to cp1252 (default: auto)."),
    )
    return p


def main(argv: list[str] | None = None) -> int:
    """Entry point for the parser CLI.

    Returns:
      0 — success
      1 — missing/invalid input
      2 — run already ingested (pre-flight check)
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    run_dir: Path = args.input
    db_path: Path = args.db

    # Validate input directory
    if not run_dir.exists() or not run_dir.is_dir():
        print(
            f"ERROR: --input directory does not exist or is not a directory: {run_dir}",
            file=sys.stderr,
        )
        return 1

    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        print(
            f"ERROR: manifest.json not found in {run_dir}",
            file=sys.stderr,
        )
        return 1

    # Create parent directory for --db if missing
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Open DuckDB and initialise schema
    con = duckdb.connect(str(db_path))
    init_database(con)

    # Pre-flight: check if run_id already ingested (#WARNING-13)
    run_id = run_dir.name
    existing = con.execute("SELECT 1 FROM runs WHERE run_id = ?", [run_id]).fetchone()
    if existing:
        print(
            f"ERROR: run_id {run_id!r} already ingested; "
            f"re-ingest is not supported in v1 (Phase 2 will add --overwrite)",
            file=sys.stderr,
        )
        con.close()
        return 2

    # Ingest (BUG-005: thread --encoding through to parse_log_file)
    try:
        report = ingest_run_directory(run_dir, con, encoding=args.encoding)
    except Exception as exc:
        print(f"ERROR during ingest: {exc}", file=sys.stderr)
        con.close()
        return 1
    finally:
        pass

    con.close()

    # Summary to stdout
    print(
        f"Ingested run {report.run_id!r} "
        f"({report.board_profile_id}, "
        f"panels={report.panels_inserted}, "
        f"test_runs={report.test_runs_inserted}, "
        f"measurements={report.measurements_inserted}, "
        f"failures={report.failures_inserted}, "
        f"parse_errors={report.parse_errors})"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
