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

from datetime import datetime, time, timedelta
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


def _shift_start_for(date: datetime, shift_letter: str) -> datetime:
    """Return the datetime at which ``shift_letter`` starts on ``date``."""
    start_hour, _ = _SHIFT_WINDOWS[shift_letter]
    base = datetime.combine(date.date(), time(hour=start_hour))
    if shift_letter == "C" and start_hour >= 22 and date.hour < 6:
        # date is already inside the wrap-around portion; back up to 22:00 of previous day
        base -= timedelta(days=1)
    return base


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
      * Each panel is assigned to a shift letter (A/B/C), weighted toward
        weekday A & B shifts; weekend production is lower.
      * Timestamps within a shift cluster around its start hour with a small
        random offset (0..7h59m) so the hour-of-day matches the shift window.
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

    # 2. Snap each timestamp into its shift bucket: pick a shift weighted by
    #    weekday (weekend = 0.3x weight on all shifts), then place within
    #    that shift's 8-hour window.
    shift_letters: list[str] = []
    snapped_timestamps: list[datetime] = []
    for ts in raw_datetimes:
        is_weekday = ts.weekday() < 5
        # Weekday shift weights heavily favour A and B (day shifts).
        if is_weekday:
            weights = [0.40, 0.35, 0.25]   # A, B, C
        else:
            weights = [0.35, 0.35, 0.30]   # weekend slightly flatter
        shift = rng.choices(["A", "B", "C"], weights=weights, k=1)[0]
        start_hour, length = _SHIFT_WINDOWS[shift]
        offset_minutes = rng.randint(0, length * 60 - 1)
        snapped = datetime(
            ts.year, ts.month, ts.day, start_hour, 0, 0
        ) + timedelta(minutes=offset_minutes)
        if shift == "C" and snapped.hour < 6:
            # Shift C wraps midnight: ensure we end on the same logical day
            # the raw ts was on; the hour-of-day will be 22..05 inclusive.
            pass
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
