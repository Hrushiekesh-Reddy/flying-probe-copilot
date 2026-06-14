"""Tests for ``flying_probe_copilot.generator.blocks`` — BUG-002 RED phase.

The block builder must scale the per-panel test count by ``profile.component_mix``
instead of emitting a hardcoded 4-block sample. These tests pin the contract so
that the implementation (``generate_blocks``) can be written against them.
"""

from __future__ import annotations

from collections import Counter

import pytest

from flying_probe_copilot.generator.blocks import generate_blocks
from flying_probe_copilot.generator.faults import PanelOutcome
from flying_probe_copilot.generator.models import (
    AnalogRecord,
    AnalogStatus,
    AnalogType,
    BTESTStatus,
    DigitalRecord,
    DigitalStatus,
    ShortsRecord,
    ShortsStatus,
)
from flying_probe_copilot.generator.profiles import get_profile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _passing_outcome() -> PanelOutcome:
    return PanelOutcome(failed=False, mode=None, btest_status=BTESTStatus.PASS)


def _outcome_for(mode: str) -> PanelOutcome:
    from flying_probe_copilot.generator.faults import btest_status_for_mode

    return PanelOutcome(
        failed=True, mode=mode, btest_status=btest_status_for_mode(mode)
    )


# Component-type prefix -> the expected concrete record type / AnalogType.
_ANALOG_TYPE_FOR_PREFIX = {
    "R": AnalogType.RES,
    "C": AnalogType.CAP,
    "L": AnalogType.IND,
    "D": AnalogType.DIO,
    "Q": AnalogType.NPN,
}


# ---------------------------------------------------------------------------
# Block-count scaling tests — the headline BUG-002 fix.
# ---------------------------------------------------------------------------


def test_small_profile_emits_one_shorts_plus_50_analog_or_digital_blocks():
    """Small profile (50 components) -> 1 shorts + 50 component blocks = 51."""
    blocks = generate_blocks(get_profile("small"), _passing_outcome(), seed=1)
    assert len(blocks) == 51


def test_medium_profile_emits_201_blocks():
    """Medium profile (200 components) -> 1 shorts + 200 = 201 blocks."""
    blocks = generate_blocks(get_profile("medium"), _passing_outcome(), seed=2)
    assert len(blocks) == 201


def test_large_profile_emits_801_blocks():
    """Large profile (800 components) -> 1 shorts + 800 = 801 blocks."""
    blocks = generate_blocks(get_profile("large"), _passing_outcome(), seed=3)
    assert len(blocks) == 801


# ---------------------------------------------------------------------------
# Block-mix tests — composition must match profile.component_mix exactly.
# ---------------------------------------------------------------------------


def test_block_mix_matches_profile_component_mix():
    """Counts of each record type must equal profile.component_mix exactly.

    With a deterministic seed and no sampling for the mix itself (we iterate
    the mix), the counts must be exact, not within a tolerance.
    """
    profile = get_profile("medium")
    blocks = generate_blocks(profile, _passing_outcome(), seed=4)

    # Expected: 1 shorts + R=100, C=60, U=16, D=10, L=4, Q=10.
    shorts_blocks = [b for b in blocks if isinstance(b.record, ShortsRecord)]
    assert len(shorts_blocks) == 1, "must emit exactly one shorts block"

    analog = [b for b in blocks if isinstance(b.record, AnalogRecord)]
    digital = [b for b in blocks if isinstance(b.record, DigitalRecord)]

    # Count analog by AnalogType.
    by_atype: Counter[AnalogType] = Counter(b.record.record_type for b in analog)

    assert by_atype[AnalogType.RES] == profile.component_mix["R"]
    assert by_atype[AnalogType.CAP] == profile.component_mix["C"]
    assert by_atype[AnalogType.IND] == profile.component_mix["L"]
    assert by_atype[AnalogType.DIO] == profile.component_mix["D"]
    assert by_atype[AnalogType.NPN] == profile.component_mix["Q"]
    assert len(digital) == profile.component_mix["U"]


def test_first_block_is_shorts():
    """The shorts block must be emitted first so derive_btest_status sees it."""
    blocks = generate_blocks(get_profile("small"), _passing_outcome(), seed=5)
    assert isinstance(blocks[0].record, ShortsRecord)


# ---------------------------------------------------------------------------
# Refdes diversity — the hardcoded R12-everywhere bug must not regress.
# ---------------------------------------------------------------------------


def test_block_refdes_diversity():
    """Large profile must surface every refdes in [R1..R400], [C1..C240], etc."""
    profile = get_profile("large")
    blocks = generate_blocks(profile, _passing_outcome(), seed=6)

    # Collect designators from the record (the source of truth for refdes).
    designators: set[str] = set()
    for b in blocks:
        if isinstance(b.record, ShortsRecord):
            continue
        designators.add(b.record.designator)

    # Check the full ranges exist for each component family.
    for prefix, count in profile.component_mix.items():
        expected = {f"{prefix}{i}" for i in range(1, count + 1)}
        missing = expected - designators
        assert not missing, (
            f"{prefix} family missing refdes: sample={sorted(missing)[:5]}"
        )


# ---------------------------------------------------------------------------
# Reproducibility — fixed seed -> byte-identical output.
# ---------------------------------------------------------------------------


def test_seed_reproducibility_for_blocks():
    """Same (profile, outcome, seed) -> byte-identical block list."""
    profile = get_profile("medium")
    outcome = _outcome_for("ANALOG_OOL")

    a = generate_blocks(profile, outcome, seed=99)
    b = generate_blocks(profile, outcome, seed=99)

    a_json = [tb.model_dump_json() for tb in a]
    b_json = [tb.model_dump_json() for tb in b]
    assert a_json == b_json


# ---------------------------------------------------------------------------
# Measured-value semantics.
# ---------------------------------------------------------------------------


def test_analog_pass_measured_within_limits():
    """For every passing analog block, measured must satisfy low <= m <= high."""
    blocks = generate_blocks(get_profile("medium"), _passing_outcome(), seed=7)
    for b in blocks:
        if isinstance(b.record, AnalogRecord) and b.record.status == AnalogStatus.PASS:
            lim = b.record.limits
            assert lim.low <= b.record.measured <= lim.high, (
                f"{b.record.designator}: measured {b.record.measured} "
                f"outside [{lim.low}, {lim.high}]"
            )


def test_analog_fail_measured_outside_limits():
    """For the failing analog block in an ANALOG_OOL outcome, measured must be out of limits."""
    outcome = _outcome_for("ANALOG_OOL")
    blocks = generate_blocks(get_profile("medium"), outcome, seed=8)

    failed_analog = [
        b
        for b in blocks
        if isinstance(b.record, AnalogRecord) and b.record.status != AnalogStatus.PASS
    ]
    assert len(failed_analog) >= 1, (
        "ANALOG_OOL outcome must produce at least one failing analog block"
    )
    for b in failed_analog:
        lim = b.record.limits
        assert not (lim.low <= b.record.measured <= lim.high), (
            f"{b.record.designator}: failing measured {b.record.measured} "
            f"unexpectedly inside [{lim.low}, {lim.high}]"
        )


# ---------------------------------------------------------------------------
# Failure-mode -> failing component family routing.
# ---------------------------------------------------------------------------


def test_failing_component_family_matches_outcome_mode_digital():
    """When outcome.mode == 'DIGITAL', a U block fails and no R/C/L/D/Q fails."""
    outcome = _outcome_for("DIGITAL")
    blocks = generate_blocks(get_profile("medium"), outcome, seed=9)

    failed_digital = [
        b
        for b in blocks
        if isinstance(b.record, DigitalRecord) and b.record.status != DigitalStatus.PASS
    ]
    failed_analog = [
        b
        for b in blocks
        if isinstance(b.record, AnalogRecord) and b.record.status != AnalogStatus.PASS
    ]
    assert len(failed_digital) >= 1, "DIGITAL outcome must fail a U block"
    assert failed_analog == [], (
        "DIGITAL outcome must not fail any analog block (got "
        f"{[b.record.designator for b in failed_analog]})"
    )


def test_shorts_only_failure_does_not_fail_analog():
    """SHORTS outcome -> shorts block status != 0; every other block passes."""
    outcome = _outcome_for("SHORTS")
    blocks = generate_blocks(get_profile("medium"), outcome, seed=10)

    shorts = blocks[0].record
    assert isinstance(shorts, ShortsRecord)
    assert shorts.status != ShortsStatus.PASS, "SHORTS outcome must fail shorts block"

    other_failures = [
        b
        for b in blocks[1:]
        if (
            (isinstance(b.record, AnalogRecord) and b.record.status != AnalogStatus.PASS)
            or (
                isinstance(b.record, DigitalRecord)
                and b.record.status != DigitalStatus.PASS
            )
        )
    ]
    assert other_failures == [], (
        "SHORTS-only outcome must not fail analog/digital blocks (got "
        f"{[b.record.designator for b in other_failures]})"
    )
