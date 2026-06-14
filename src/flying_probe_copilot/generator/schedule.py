"""Realistic panel scheduling — timestamps, operators, lines, shifts, versions.

Produces an ordered sequence of ``PanelInstance`` objects whose distribution
mirrors a real PCBA shop floor:

* Three shifts per day (A 06-14, B 14-22, C 22-06) with combined coverage of
  ~80% weekday production and lighter weekend runs.
* Operators are stable within a shift — same operator runs ~50-200 panels
  consecutively, then rotates.
* SMT lines are assigned round-robin across configured ``--lines`` count.
* Panel serials follow ``SYN-YYYYWww-NNNNN`` (ISO year + ISO week + 5-digit
  sequence within the schedule).
* Test-program revision (returned by ``test_program_versions``) holds for
  several hundred panels between discrete bumps.

All randomness flows through a single ``random.Random(seed)`` instance so the
schedule is byte-reproducible.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from random import Random

from .models import PanelInstance


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_SHIFT_WINDOWS: dict[str, tuple[int, int]] = {
    # shift_letter: (start_hour, length_hours)
    "A": (6, 8),   # 06:00 - 14:00
    "B": (14, 8),  # 14:00 - 22:00
    "C": (22, 8),  # 22:00 - 06:00 (wraps midnight)
}


def _serial_for(ts: datetime, sequence: int) -> str:
    iso_year, iso_week, _ = ts.isocalendar()
    return f"SYN-{iso_year:04d}W{iso_week:02d}-{sequence:05d}"


def _line_id_for_index(idx: int, n_lines: int) -> str:
    # n_lines limited to 26 (A..Z). Plenty for synthetic data.
    letter = chr(ord("A") + (idx % n_lines))
    return f"LINE-{letter}"


def _shift_for_hour(hour: int) -> str:
    """Return the shift letter (A/B/C) whose hour-of-day window contains ``hour``."""
    if 6 <= hour < 14:
        return "A"
    if 14 <= hour < 22:
        return "B"
    return "C"  # 22-23 or 0-5


def _shift_window_start(ts: datetime, shift: str) -> datetime:
    """Return the start datetime of the shift-window instance that physically
    contains ``ts``.

    For shifts A and B the window starts at 06:00 / 14:00 on ``ts.date()``.
    For shift C the window wraps midnight: when ``ts.hour < 6``, the
    containing window started at 22:00 on the *previous* calendar day.
    """
    start_hour = _SHIFT_WINDOWS[shift][0]
    if shift == "C" and ts.hour < 6:
        prev = ts - timedelta(days=1)
        return datetime(prev.year, prev.month, prev.day, 22, 0, 0)
    return datetime(ts.year, ts.month, ts.day, start_hour, 0, 0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_panel_schedule(
    *,
    start: datetime,
    end: datetime,
    count: int,
    seed: int,
    operators: int,
    lines: int,
    board_profile_id: str,
) -> list[PanelInstance]:
    """Generate ``count`` ``PanelInstance`` records spanning ``[start, end)``.

    Distribution rules:
      * Raw timestamps are drawn uniformly over ``[start, end)``. Each
        panel's shift letter (A/B/C) is then *derived* from the raw draw's
        hour-of-day, so the snapped timestamp always lands inside the same
        shift-window instance that physically contained the raw draw.
      * Timestamps are snapped within their shift's 8h window (0..7h59m
        offset from the window's start). Shift C wraps midnight, so an
        early-morning raw draw anchors to the previous calendar day's 22:00
        window-start.
      * Operators rotate every 60-180 panels.
      * Lines are assigned round-robin in chronological emission order.
      * testplan_rev (returned via ``test_program_versions``) holds for
        roughly 200 panels between bumps (Poisson-ish via geometric draws).
    """
    if count <= 0:
        return []
    if end <= start:
        raise ValueError("end must be after start")
    if operators < 1 or lines < 1:
        raise ValueError("operators and lines must be >= 1")
    if lines > 26:
        raise ValueError("lines must be <= 26 (A..Z labelling)")

    rng = Random(seed)

    # 1. Draw raw timestamps over the window.
    span_seconds = (end - start).total_seconds()
    raw_seconds = sorted(rng.uniform(0.0, span_seconds) for _ in range(count))
    raw_datetimes = [start + timedelta(seconds=s) for s in raw_seconds]

    # 2. Derive each panel's shift from its raw timestamp's hour-of-day,
    #    then snap within that shift's 8-hour window. Anchoring to the raw
    #    draw (rather than re-drawing the shift uniformly) keeps the snapped
    #    timestamp inside the *same* shift-window instance that physically
    #    contained the raw draw — critical for shift C, whose window wraps
    #    midnight.
    shift_letters: list[str] = []
    snapped_timestamps: list[datetime] = []
    for ts in raw_datetimes:
        shift = _shift_for_hour(ts.hour)
        window_start = _shift_window_start(ts, shift)
        length_hours = _SHIFT_WINDOWS[shift][1]
        offset_minutes = rng.randint(0, length_hours * 60 - 1)
        snapped = window_start + timedelta(minutes=offset_minutes)
        shift_letters.append(shift)
        snapped_timestamps.append(snapped)

    # Re-sort by snapped timestamp to keep emission chronological.
    order = sorted(range(count), key=lambda i: snapped_timestamps[i])
    snapped_timestamps = [snapped_timestamps[i] for i in order]
    shift_letters = [shift_letters[i] for i in order]

    # 3. Operator assignment: a single operator runs N consecutive panels.
    operator_ids = [f"OP-{i:03d}" for i in range(1, operators + 1)]
    operator_sequence: list[str] = []
    idx = 0
    while idx < count:
        op = rng.choice(operator_ids)
        run_length = rng.randint(60, 200)
        for _ in range(run_length):
            if idx >= count:
                break
            operator_sequence.append(op)
            idx += 1

    # 4. Build PanelInstance objects.
    panels: list[PanelInstance] = []
    for i, (ts, shift, op) in enumerate(
        zip(snapped_timestamps, shift_letters, operator_sequence)
    ):
        serial = _serial_for(ts, i + 1)
        panels.append(
            PanelInstance(
                serial=serial,
                panel_position=1,  # one panel per board for v1
                board_profile_id=board_profile_id,
                operator_id=op,
                line_id=_line_id_for_index(i, lines),
                shift=shift,
                timestamp=ts,
            )
        )
    return panels


def test_program_versions(panels: list[PanelInstance]) -> list[str]:
    """Return the per-panel testplan revision string.

    Versions hold for ~200 consecutive panels, then bump.
    """
    if not panels:
        return []
    # Deterministic from the first panel's serial digest — keeps this pure.
    rng = Random(hash(panels[0].serial) & 0xFFFF_FFFF)
    versions: list[str] = []
    major, minor = 1, 0
    remaining = rng.randint(150, 300)
    for _ in panels:
        if remaining <= 0:
            minor += 1
            if minor > 9:
                minor = 0
                major += 1
            remaining = rng.randint(150, 300)
        versions.append(f"v{major}.{minor}")
        remaining -= 1
    return versions
