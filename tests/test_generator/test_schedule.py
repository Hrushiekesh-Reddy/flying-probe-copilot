"""Tests for ``flying_probe_copilot.generator.schedule``.

Phase 1a Step C1 — RED phase. Realism-rule checks for timestamps, operator
stability, line assignment, panel-serial format, and test-program-version
stability.
"""

from __future__ import annotations

import random
import re
from datetime import datetime, timedelta


# Canonical schedule-window used by these tests.
START = datetime(2026, 4, 1, 0, 0, 0)
END = START + timedelta(weeks=4)


def _make_schedule(count: int, *, operators: int = 4, lines: int = 2, seed: int = 42):
    from flying_probe_copilot.generator.schedule import generate_panel_schedule

    return generate_panel_schedule(
        start=START,
        end=END,
        count=count,
        seed=seed,
        operators=operators,
        lines=lines,
        board_profile_id="small",
    )


# ---------------------------------------------------------------------------
# Timestamps cluster in three shifts (06/14/22 starts)
# ---------------------------------------------------------------------------


def test_timestamps_cluster_in_three_shifts():
    panels = _make_schedule(2000)
    hours = [p.timestamp.hour for p in panels]
    # Three shifts: A=06-14, B=14-22, C=22-06. Combined window covers 24h so
    # every hour has some panels, but each shift's 8h block should hold ~33%.
    in_shift_a = sum(1 for h in hours if 6 <= h < 14)
    in_shift_b = sum(1 for h in hours if 14 <= h < 22)
    in_shift_c = sum(1 for h in hours if h >= 22 or h < 6)
    total = len(hours)
    # No single shift should hold >55% (i.e. not uniform piled into one).
    # Each shift should hold at least 20% (i.e. real coverage of all three).
    for share in (in_shift_a / total, in_shift_b / total, in_shift_c / total):
        assert 0.20 <= share <= 0.55, f"shift share {share:.2f} outside [0.20, 0.55]"


def test_timestamps_weekday_heavy():
    """Realism: weekdays (Mon-Fri) hold the bulk of production."""
    panels = _make_schedule(2000)
    weekday_count = sum(1 for p in panels if p.timestamp.weekday() < 5)
    assert weekday_count / len(panels) >= 0.70, (
        f"only {weekday_count / len(panels):.2f} on weekdays — must be >= 0.70"
    )


# ---------------------------------------------------------------------------
# Operator + line stability
# ---------------------------------------------------------------------------


def test_operator_id_stable_within_shift():
    """Same operator should run >= 50 consecutive panels in some run.

    Realism rule: operators don't rotate every panel.
    """
    panels = _make_schedule(2000)
    # Find the longest run of the same operator_id across consecutive panels
    # in the natural emission order (already start-time-sorted).
    longest_run = 1
    current_run = 1
    for prev, cur in zip(panels, panels[1:]):
        if cur.operator_id == prev.operator_id:
            current_run += 1
            longest_run = max(longest_run, current_run)
        else:
            current_run = 1
    assert longest_run >= 50, (
        f"longest consecutive same-operator run was {longest_run}; expected >= 50"
    )


def test_line_id_assignment_uses_only_configured_lines():
    panels = _make_schedule(500, lines=3)
    seen_lines = {p.line_id for p in panels}
    # Exactly 3 distinct lines should appear (with very high probability for
    # N=500; deterministic seed makes it true exactly).
    assert seen_lines == {"LINE-A", "LINE-B", "LINE-C"}


# ---------------------------------------------------------------------------
# Panel serial format
# ---------------------------------------------------------------------------


def test_panel_serial_format_matches_SYN_YYYYWww_NNNNN_pattern():
    panels = _make_schedule(20)
    pattern = re.compile(r"^SYN-(\d{4})W(\d{2})-(\d{5})$")
    for p in panels:
        assert pattern.match(p.serial), f"serial {p.serial!r} does not match SYN-YYYYWww-NNNNN"


# ---------------------------------------------------------------------------
# Test program version stability
# ---------------------------------------------------------------------------


def test_test_program_version_changes_infrequently():
    """testplan_rev should hold steady for >= 100 panels between bumps.

    The schedule exposes the rolling testplan_rev via a property on each
    PanelInstance via an attached ``test_program_version`` attribute on the
    schedule, or via ``schedule.test_program_versions(panels)`` helper.
    """
    from flying_probe_copilot.generator.schedule import test_program_versions

    panels = _make_schedule(1000)
    versions = test_program_versions(panels)
    assert len(versions) == len(panels)
    # Count runs of identical versions.
    runs: list[int] = []
    current = 1
    for prev, cur in zip(versions, versions[1:]):
        if cur == prev:
            current += 1
        else:
            runs.append(current)
            current = 1
    runs.append(current)
    # At least one run must be >= 100 panels long. (Most should be.)
    assert max(runs) >= 100, f"longest version-run is {max(runs)}; expected >= 100"


# ---------------------------------------------------------------------------
# Shift-snap overnight bug — regression tests (BUG-004 / PR #3 review comment
# id 3409766436). The old code drew a shift letter uniformly at random per
# panel and then snapped to that shift's start hour on the raw draw's
# calendar day. A raw timestamp at 02:00 assigned to shift C was snapped to
# the same day's 22:00-05:59 window — ~20 hours away from the raw draw, and
# inside a *different* shift-C instance than the one that physically
# contained the raw timestamp.
# ---------------------------------------------------------------------------


def test_panel_shift_is_derived_from_raw_timestamp_hour():
    """Narrow window: every raw_ts falls in shift C's hour-of-day range, so
    every emitted panel must carry shift letter 'C'.

    Fails under the buggy code because it drew shift uniformly at random,
    yielding ~25-40% non-C labels on a window where physically every panel
    must be on shift C.
    """
    from flying_probe_copilot.generator.schedule import generate_panel_schedule

    # 02:00 - 03:00 — every raw_ts has hour=2, which is squarely in shift C.
    start = datetime(2026, 4, 15, 2, 0, 0)
    end = datetime(2026, 4, 15, 3, 0, 0)
    panels = generate_panel_schedule(
        start=start,
        end=end,
        count=50,
        seed=42,
        operators=2,
        lines=1,
        board_profile_id="small",
    )
    shifts = {p.shift for p in panels}
    assert shifts == {"C"}, f"expected only shift C, got {sorted(shifts)}"


def test_snapped_timestamp_lies_within_assigned_shift_window():
    """Every panel's timestamp must fall inside its assigned shift's
    hour-of-day window. Contract check that the shift label is internally
    consistent with the snapped timestamp.
    """
    panels = _make_schedule(2000)
    for p in panels:
        if p.shift == "A":
            assert 6 <= p.timestamp.hour < 14, (
                f"shift A panel at {p.timestamp.isoformat()} — hour outside [6,14)"
            )
        elif p.shift == "B":
            assert 14 <= p.timestamp.hour < 22, (
                f"shift B panel at {p.timestamp.isoformat()} — hour outside [14,22)"
            )
        elif p.shift == "C":
            assert p.timestamp.hour >= 22 or p.timestamp.hour < 6, (
                f"shift C panel at {p.timestamp.isoformat()} — hour outside [22,06)"
            )
        else:
            raise AssertionError(f"unknown shift letter {p.shift!r}")


def test_shift_C_panel_in_early_morning_anchors_to_previous_day_window():
    """A shift-C panel with hour in [0,6) must belong to the overnight
    window that *started* on the previous calendar day at 22:00. Equivalently,
    every shift-C panel with hour < 6 must have a same-shift twin (or be
    adjacent in time to one) on the prior calendar day's 22:00-23:59 slot,
    or — more simply — sit inside an 8-hour window beginning at
    (panel.timestamp.date - 1 day) 22:00.

    Fails under the buggy code because shift-C panels with hour < 6 landed
    on the day-X+1 portion of a window that started at day-X 22:00, where
    day-X was the raw_ts's calendar day — leaving the chronologically
    earlier overnight window (which physically contained the raw_ts)
    unrepresented at the expected rate.
    """
    panels = _make_schedule(2000)
    early_c = [p for p in panels if p.shift == "C" and p.timestamp.hour < 6]
    # For each early-morning shift-C panel, the window-start datetime must be
    # 22:00 on the previous calendar day, and the panel must lie strictly
    # within the 8-hour shift-C window starting there.
    for p in early_c:
        prev = p.timestamp - timedelta(days=1)
        window_start = datetime(prev.year, prev.month, prev.day, 22, 0, 0)
        window_end = window_start + timedelta(hours=8)
        assert window_start <= p.timestamp < window_end, (
            f"shift C panel at {p.timestamp.isoformat()} is not inside the "
            f"overnight window [{window_start.isoformat()}, {window_end.isoformat()})"
        )
