"""Fault injection — profiles, distributions, and within-panel correlation.

Four supported profiles (spec section "Fault injection profiles"):

* ``random`` — independent Bernoulli per panel at ``target_rate``.
* ``drift`` — linear ramp from ``0.5*target_rate`` to ``2.0*target_rate``
  across ``[window_start, window_end)``.
* ``cluster`` — three narrow time windows in which the fail-rate is 6× the
  baseline; baseline elsewhere is ``0.2*target_rate``.
* ``process-change`` — step at ``change_point``: ``0.5*target_rate`` before,
  ``2.0*target_rate`` after.

Within a single panel, ``correlation_multiplier`` provides a 1.5× boost for
refdes neighbors (same prefix, ``|i - j| == 1``) and a 1.2× boost for nearby
ones (``|i - j| <= 3``). The heuristic is a *synthesis convenience*, not a
physical claim — see Revision 1 #WARNING-8 in ``docs/plans/2026-06-13-plan.md``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from random import Random

from .models import BTESTStatus


# ---------------------------------------------------------------------------
# Failure-mode -> @BTEST status mapping (spec table, rev 1).
# ---------------------------------------------------------------------------


# Failure-mode shares per the spec's "failing-board fate" table.
FAILURE_MODE_SHARES: dict[str, float] = {
    "ANALOG_OOL": 0.40,
    "SHORTS": 0.25,
    "OPEN": 0.15,
    "DIGITAL": 0.10,
    "MISSING": 0.07,
    "GROSS": 0.03,
}

_MODE_TO_BTEST: dict[str, BTESTStatus] = {
    "ANALOG_OOL": BTESTStatus.FAIL_ANALOG,
    "SHORTS": BTESTStatus.FAIL_SHORTS,
    "OPEN": BTESTStatus.FAIL_ANALOG,  # opens surface as analog OOL
    "DIGITAL": BTESTStatus.FAIL_DIGITAL,
    "MISSING": BTESTStatus.FAIL_ANALOG,
    "GROSS": BTESTStatus.FAIL_ANALOG,
}


def btest_status_for_mode(mode: str) -> BTESTStatus:
    """Return the canonical @BTEST status code for a failure mode."""
    try:
        return _MODE_TO_BTEST[mode]
    except KeyError as exc:
        raise ValueError(f"Unknown failure mode: {mode!r}") from exc


# ---------------------------------------------------------------------------
# Per-panel outcome
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PanelOutcome:
    """Result of fault injection for a single panel."""

    failed: bool
    mode: str | None  # None when failed is False
    btest_status: BTESTStatus


def _effective_rate(
    *,
    profile: str,
    target_rate: float,
    panel_timestamp: datetime,
    window_start: datetime,
    window_end: datetime,
    change_point: datetime | None,
) -> float:
    span = (window_end - window_start).total_seconds()
    if span <= 0:
        return target_rate
    progress = max(0.0, min(1.0, (panel_timestamp - window_start).total_seconds() / span))

    if profile == "random":
        return target_rate
    if profile == "drift":
        # Linear ramp 0.5*target_rate -> 2.0*target_rate.
        return target_rate * (0.5 + 1.5 * progress)
    if profile == "cluster":
        # Three narrow 5% windows at 20%/50%/80% of the run get a 6× boost.
        for center in (0.20, 0.50, 0.80):
            if abs(progress - center) <= 0.025:
                return target_rate * 6.0
        return target_rate * 0.2
    if profile == "process-change":
        if change_point is None or panel_timestamp < change_point:
            return target_rate * 0.5
        return target_rate * 2.0
    raise ValueError(f"Unknown fault profile: {profile!r}")


def _draw_mode(rng: Random) -> str:
    """Draw a failure mode according to FAILURE_MODE_SHARES."""
    modes = list(FAILURE_MODE_SHARES.keys())
    weights = list(FAILURE_MODE_SHARES.values())
    return rng.choices(modes, weights=weights, k=1)[0]


def generate_panel_faults(
    *,
    seed: int,
    profile: str,
    target_rate: float,
    panel_timestamp: datetime,
    window_start: datetime,
    window_end: datetime,
    change_point: datetime | None,
) -> PanelOutcome:
    """Decide whether a single panel fails and, if so, in which mode."""
    rng = Random(seed)
    rate = _effective_rate(
        profile=profile,
        target_rate=target_rate,
        panel_timestamp=panel_timestamp,
        window_start=window_start,
        window_end=window_end,
        change_point=change_point,
    )
    failed = rng.random() < rate
    if not failed:
        return PanelOutcome(failed=False, mode=None, btest_status=BTESTStatus.PASS)
    mode = _draw_mode(rng)
    return PanelOutcome(failed=True, mode=mode, btest_status=btest_status_for_mode(mode))


# ---------------------------------------------------------------------------
# Within-panel correlation (Revision 1 #WARNING-8)
# ---------------------------------------------------------------------------


_REFDES_RE = re.compile(r"^([A-Z]+)(\d+)$")


def _split_refdes(refdes: str) -> tuple[str, int] | None:
    m = _REFDES_RE.match(refdes)
    if not m:
        return None
    return m.group(1), int(m.group(2))


def correlation_multiplier(failed_refdes: str, candidate_refdes: str) -> float:
    """Return the fail-rate multiplier for ``candidate`` given ``failed`` failed.

    Heuristic:
      * Different prefix (e.g. R vs C) -> 1.0 (no correlation).
      * Same prefix, ``|i - j| == 1`` -> 1.5 (immediate neighbor).
      * Same prefix, ``|i - j| <= 3`` -> 1.2 (near neighbor).
      * Otherwise -> 1.0.
    """
    a = _split_refdes(failed_refdes)
    b = _split_refdes(candidate_refdes)
    if a is None or b is None:
        return 1.0
    prefix_a, num_a = a
    prefix_b, num_b = b
    if prefix_a != prefix_b:
        return 1.0
    if num_a == num_b:
        return 1.0
    delta = abs(num_a - num_b)
    if delta == 1:
        return 1.5
    if delta <= 3:
        return 1.2
    return 1.0


def correlated_failure_rate(
    *,
    baseline: float,
    forced_failed: str,
    candidates: list[str],
    trials: int,
    seed: int,
) -> tuple[float, float]:
    """Run ``trials`` Bernoulli trials per candidate at the boosted rate.

    Returns the empirical failure rate for each candidate in input order.
    """
    if len(candidates) != 2:
        raise ValueError("correlated_failure_rate currently expects exactly 2 candidates")
    rng = Random(seed)
    rate_a = min(1.0, baseline * correlation_multiplier(forced_failed, candidates[0]))
    rate_b = min(1.0, baseline * correlation_multiplier(forced_failed, candidates[1]))
    a_fails = sum(1 for _ in range(trials) if rng.random() < rate_a)
    b_fails = sum(1 for _ in range(trials) if rng.random() < rate_b)
    return a_fails / trials, b_fails / trials
