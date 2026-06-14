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
