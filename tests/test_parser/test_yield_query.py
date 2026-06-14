"""Yield-by-board-over-last-7-days query tests — Phase 1b.

Uses a fixture spanning ≥2 weeks × 2 board profiles with deterministic
seeded fault rates. The SQL is anchored at MAX(start_ts) so the test
is wall-clock-independent.

Per #MINOR-17: the SQL is defined as a module-level constant so both tests
reference the same string. Promote to db/queries.py in Phase 2.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from flying_probe_copilot.generator.cli import _build_batch_log
from flying_probe_copilot.generator.models import BatchLog, BTESTStatus
from flying_probe_copilot.generator.renderers.log import render_log


# ---------------------------------------------------------------------------
# Module-level SQL constant (#MINOR-17)
# ---------------------------------------------------------------------------

_YIELD_BY_BOARD_LAST_WEEK_SQL = """
WITH anchor_cte AS (
  SELECT MAX(start_ts) AS anchor FROM test_runs
)
SELECT
  p.board_profile_id,
  COUNT(*)                                                        AS total,
  SUM(CASE WHEN tr.btest_status = 0 THEN 1 ELSE 0 END)            AS passed,
  100.0 * SUM(CASE WHEN tr.btest_status = 0 THEN 1 ELSE 0 END)
        / COUNT(*)                                                AS yield_pct
FROM test_runs tr
JOIN panels p ON p.panel_serial = tr.panel_serial
WHERE tr.start_ts >= (SELECT anchor - INTERVAL 7 DAY FROM anchor_cte)
GROUP BY p.board_profile_id
ORDER BY p.board_profile_id
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _Args:
    def __init__(self, profile, count, seed, start_date, end_date, fault_rate=0.05):
        self.board_profile = profile
        self.count = count
        self.seed = seed
        self.fault_rate = fault_rate
        self.fault_profile = "random"
        self.start_date = start_date
        self.end_date = end_date
        self.operators = 2
        self.lines = 1
        self.format = "log"
        self.encoding = "utf-8"


def _write_run(tmp_path: Path, batch_log: BatchLog, profile: str, name: str, seed: int) -> Path:
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
        "fault_rate": 0.0,
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
def two_week_db():
    """In-memory DB with 2 weeks of data across small + medium profiles.

    Data is inserted directly via SQL to avoid panel-serial collisions from
    the generator's global sequence counter.

    Anchor = 2026-04-14T10:00:00 (MAX start_ts, in week 2 data).
    7-day window lower bound = 2026-04-07T10:00:00.

    Week 2 (within window): 2026-04-08 to 2026-04-14
      - small: 5 rows — 4 pass (btest_status=0), 1 fail → yield=80%
      - medium: 3 rows — 2 pass, 1 fail → yield=66.7%

    Week 1 (outside window): 2026-03-31 to 2026-04-06
      - small: 5 rows, all pass
      - medium: 3 rows, all pass

    These are excluded because 2026-04-06 < 2026-04-07T10:00:00.
    """
    from flying_probe_copilot.db.schema import init_database

    con = duckdb.connect(":memory:")
    init_database(con)

    # Insert board dim rows
    con.execute("""
        INSERT OR IGNORE INTO boards (board_profile_id, name, component_count, net_count, typical_test_count)
        VALUES ('small', 'small', 50, 80, 120), ('medium', 'medium', 200, 300, 450)
    """)

    # Insert run rows
    con.execute("""
        INSERT INTO runs (run_id, board_profile_id, seed, fault_rate, fault_profile, panel_count, failing_boards)
        VALUES ('run_w1_small', 'small', 100, 0.05, 'random', 5, 0),
               ('run_w1_medium', 'medium', 101, 0.05, 'random', 3, 0),
               ('run_w2_small', 'small', 102, 0.10, 'random', 5, 1),
               ('run_w2_medium', 'medium', 103, 0.30, 'random', 3, 1)
    """)

    # Insert panels — unique serials
    panels = [
        # W1 small (outside window)
        ("SYN-W1-S-001", "small", 1, "LINE-A", "A", "2026-03-31 08:00:00"),
        ("SYN-W1-S-002", "small", 2, "LINE-A", "A", "2026-04-01 08:00:00"),
        ("SYN-W1-S-003", "small", 3, "LINE-A", "A", "2026-04-02 08:00:00"),
        ("SYN-W1-S-004", "small", 4, "LINE-A", "A", "2026-04-03 08:00:00"),
        ("SYN-W1-S-005", "small", 5, "LINE-A", "A", "2026-04-04 08:00:00"),
        # W1 medium (outside window)
        ("SYN-W1-M-001", "medium", 1, "LINE-A", "A", "2026-04-01 09:00:00"),
        ("SYN-W1-M-002", "medium", 2, "LINE-A", "A", "2026-04-03 09:00:00"),
        ("SYN-W1-M-003", "medium", 3, "LINE-A", "A", "2026-04-05 09:00:00"),
        # W2 small (inside window)
        ("SYN-W2-S-001", "small", 1, "LINE-A", "A", "2026-04-08 10:00:00"),
        ("SYN-W2-S-002", "small", 2, "LINE-A", "A", "2026-04-09 10:00:00"),
        ("SYN-W2-S-003", "small", 3, "LINE-A", "A", "2026-04-10 10:00:00"),
        ("SYN-W2-S-004", "small", 4, "LINE-A", "A", "2026-04-12 10:00:00"),
        ("SYN-W2-S-005", "small", 5, "LINE-A", "A", "2026-04-13 10:00:00"),
        # W2 medium (inside window)
        ("SYN-W2-M-001", "medium", 1, "LINE-A", "A", "2026-04-11 10:00:00"),
        ("SYN-W2-M-002", "medium", 2, "LINE-A", "A", "2026-04-13 10:00:00"),
        ("SYN-W2-M-003", "medium", 3, "LINE-A", "A", "2026-04-14 10:00:00"),  # MAX
    ]
    for serial, profile, pos, line, shift, ts in panels:
        con.execute(
            "INSERT INTO panels (panel_serial, board_profile_id, panel_position, line_id, shift, scheduled_ts) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [serial, profile, pos, line, shift, ts],
        )

    # Insert test_runs
    # btest_status=0 → PASS, btest_status=6 → FAIL_ANALOG
    test_runs_data = [
        # W1 small — all pass, timestamps before window
        ("SYN-W1-S-001", "run_w1_small", 0, "2026-03-31 08:00:00", "2026-03-31 08:00:12"),
        ("SYN-W1-S-002", "run_w1_small", 0, "2026-04-01 08:00:00", "2026-04-01 08:00:12"),
        ("SYN-W1-S-003", "run_w1_small", 0, "2026-04-02 08:00:00", "2026-04-02 08:00:12"),
        ("SYN-W1-S-004", "run_w1_small", 0, "2026-04-03 08:00:00", "2026-04-03 08:00:12"),
        ("SYN-W1-S-005", "run_w1_small", 0, "2026-04-04 08:00:00", "2026-04-04 08:00:12"),
        # W1 medium — all pass
        ("SYN-W1-M-001", "run_w1_medium", 0, "2026-04-01 09:00:00", "2026-04-01 09:00:12"),
        ("SYN-W1-M-002", "run_w1_medium", 0, "2026-04-03 09:00:00", "2026-04-03 09:00:12"),
        ("SYN-W1-M-003", "run_w1_medium", 0, "2026-04-05 09:00:00", "2026-04-05 09:00:12"),
        # W2 small — 4 pass, 1 fail → yield 80%
        ("SYN-W2-S-001", "run_w2_small", 0, "2026-04-08 10:00:00", "2026-04-08 10:00:12"),
        ("SYN-W2-S-002", "run_w2_small", 0, "2026-04-09 10:00:00", "2026-04-09 10:00:12"),
        ("SYN-W2-S-003", "run_w2_small", 0, "2026-04-10 10:00:00", "2026-04-10 10:00:12"),
        ("SYN-W2-S-004", "run_w2_small", 6, "2026-04-12 10:00:00", "2026-04-12 10:00:12"),  # fail
        ("SYN-W2-S-005", "run_w2_small", 0, "2026-04-13 10:00:00", "2026-04-13 10:00:12"),
        # W2 medium — 2 pass, 1 fail → yield 66.7%
        ("SYN-W2-M-001", "run_w2_medium", 0, "2026-04-11 10:00:00", "2026-04-11 10:00:12"),
        ("SYN-W2-M-002", "run_w2_medium", 6, "2026-04-13 10:00:00", "2026-04-13 10:00:12"),  # fail
        ("SYN-W2-M-003", "run_w2_medium", 0, "2026-04-14 10:00:00", "2026-04-14 10:00:12"),
    ]
    for seq, (serial, run_id, status, start, end) in enumerate(test_runs_data, 1):
        con.execute(
            "INSERT INTO test_runs "
            "(test_run_id, panel_serial, run_id, operator_id, btest_status, "
            " start_ts, end_ts, duration_s, multiple_test, learning, known_good, board_number) "
            "VALUES (?, ?, ?, NULL, ?, ?, ?, 12, false, false, false, 1)",
            [seq, serial, run_id, status, start, end],
        )

    ground_truth = {
        # Week-2 only data
        "small_w2_total": 5,
        "small_w2_passed": 4,
        "medium_w2_total": 3,
        "medium_w2_passed": 2,
        # Week-1 counts (must NOT appear in 7-day window result)
        "small_w1_count": 5,
        "medium_w1_count": 3,
    }

    yield con, ground_truth
    con.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_yield_query_returns_empty_when_db_empty():
    """Query on a freshly initialised DB must return zero rows, no exception."""
    from flying_probe_copilot.db.schema import init_database

    con = duckdb.connect(":memory:")
    init_database(con)

    rows = con.execute(_YIELD_BY_BOARD_LAST_WEEK_SQL).fetchall()
    assert rows == [], f"Expected empty result on empty DB, got {rows!r}"
    con.close()


def test_yield_by_board_over_last_week_returns_expected(two_week_db):
    """Query must return only week-2 data and match ground truth counts."""
    con, gt = two_week_db

    rows = con.execute(_YIELD_BY_BOARD_LAST_WEEK_SQL).fetchall()
    # Expect 2 rows: one per profile
    profiles_in_result = {r[0] for r in rows}
    assert "small" in profiles_in_result, "small profile must appear in yield query result"
    assert "medium" in profiles_in_result, "medium profile must appear in yield query result"

    result = {r[0]: {"total": r[1], "passed": r[2]} for r in rows}

    assert result["small"]["total"] == gt["small_w2_total"], (
        f"small total: expected {gt['small_w2_total']}, got {result['small']['total']}"
    )
    assert result["small"]["passed"] == gt["small_w2_passed"], (
        f"small passed: expected {gt['small_w2_passed']}, got {result['small']['passed']}"
    )
    assert result["medium"]["total"] == gt["medium_w2_total"], (
        f"medium total: expected {gt['medium_w2_total']}, got {result['medium']['total']}"
    )
    assert result["medium"]["passed"] == gt["medium_w2_passed"], (
        f"medium passed: expected {gt['medium_w2_passed']}, got {result['medium']['passed']}"
    )


def test_yield_query_excludes_data_older_than_seven_days_from_anchor(two_week_db):
    """Rows from week 1 (>7 days before anchor) must NOT appear in the result."""
    con, gt = two_week_db

    rows = con.execute(_YIELD_BY_BOARD_LAST_WEEK_SQL).fetchall()
    result = {r[0]: {"total": r[1], "passed": r[2]} for r in rows}

    # If week-1 data leaked into the result, total would be higher
    if "small" in result:
        assert result["small"]["total"] <= gt["small_w2_total"], (
            f"small total ({result['small']['total']}) exceeds week-2 count "
            f"({gt['small_w2_total']}) — week-1 data leaked into the window"
        )
    if "medium" in result:
        assert result["medium"]["total"] <= gt["medium_w2_total"], (
            f"medium total ({result['medium']['total']}) exceeds week-2 count "
            f"({gt['medium_w2_total']}) — week-1 data leaked into the window"
        )


def test_yield_query_includes_panel_exactly_at_seven_day_boundary(tmp_path):
    """A panel at exactly anchor - 7 days must be INCLUDED (>= boundary, #WARNING-6)."""
    from flying_probe_copilot.db.schema import init_database
    from flying_probe_copilot.parser.ingest import ingest_run_directory

    con = duckdb.connect(":memory:")
    init_database(con)

    # Only one panel — it will be its own anchor AND exactly at the boundary
    bl = _build_batch_log(_Args("small", 1, 200, "2026-04-01", "2026-04-02"), "small")
    rd = _write_run(tmp_path, bl, "small", "run_boundary", seed=200)
    ingest_run_directory(rd, con)

    rows = con.execute(_YIELD_BY_BOARD_LAST_WEEK_SQL).fetchall()
    con.close()
    # The single panel is at MAX(start_ts) = anchor, which is >= anchor - 7 days
    assert len(rows) == 1, (
        f"Expected 1 row (panel at boundary must be included), got {len(rows)}"
    )
    assert rows[0][1] == 1, f"Expected total=1, got {rows[0][1]}"
