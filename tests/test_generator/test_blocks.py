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


# ---------------------------------------------------------------------------
# Within-panel fault correlation — wired through generate_blocks.
#
# Bug: prior to this change, ``_pick_failing_component`` marked exactly one
# component as failing per panel and ``correlation_multiplier`` /
# ``correlated_failure_rate`` (defined in ``faults.py``) were never invoked
# from the CLI output path. The realistic clustered-failure Pareto curves the
# heuristic was designed to produce never appeared in generator output.
#
# These tests pin the contract that the multiplier is now applied: when the
# primary failing component is known, refdes-numerical neighbors (±1, ±3 in
# the same family) must show elevated fail counts vs far components.
# ---------------------------------------------------------------------------


def _count_failed_designators(blocks_iter):
    """Iterate over an iterable of blocks and count fails by designator."""
    counts: Counter[str] = Counter()
    for block in blocks_iter:
        if isinstance(block.record, AnalogRecord):
            if block.record.status != AnalogStatus.PASS:
                counts[block.record.designator] += 1
        elif isinstance(block.record, DigitalRecord):
            if block.record.status != DigitalStatus.PASS:
                counts[block.record.designator] += 1
    return counts


def test_neighbor_fail_rate_elevated_vs_far_when_primary_pinned(monkeypatch):
    """Pin primary=R50; over 500 ANALOG_OOL panels R49 must fail more than R10.

    This is the headline correlation contract: the ±1 refdes neighbor of the
    primary failure should have a materially higher empirical fail rate than
    a far component in the same family. Without correlation wired in, both
    rates are zero (only the primary fails), so this test fails RED.
    """
    from flying_probe_copilot.generator import blocks as blocks_mod

    monkeypatch.setattr(
        blocks_mod, "_pick_failing_component", lambda outcome, profile, rng: ("R", 50)
    )

    profile = get_profile("medium")
    outcome = _outcome_for("ANALOG_OOL")

    counts: Counter[str] = Counter()
    for seed in range(500):
        counts.update(_count_failed_designators(generate_blocks(profile, outcome, seed)))

    r49 = counts["R49"]
    r51 = counts["R51"]
    r10 = counts["R10"]

    assert r49 > r10, (
        f"R49 (±1 neighbor) must fail more than R10 (far). Got R49={r49}, R10={r10}."
    )
    assert r51 > r10, (
        f"R51 (±1 neighbor) must fail more than R10 (far). Got R51={r51}, R10={r10}."
    )
    assert r49 + r51 >= 3 * max(1, r10), (
        f"Combined ±1 neighbors should be ≥3× the far rate (a generous margin "
        f"that survives stochastic noise). Got R49+R51={r49 + r51}, R10={r10}."
    )


def test_failure_pareto_clusters_around_primary_under_correlation(monkeypatch):
    """1000 panels, primary pinned to R50: top-3 failing refdes account for >30% of fails.

    With correlation off (RED), top-3 = {R50, <two random Rs>} and total fails
    ≈ 1000 (only the primary fails per panel), so R50 alone is ~100% of fails
    and the heuristic produces no extra clustering — the Pareto question is
    not meaningfully testable. With correlation on, neighbors accumulate extra
    fails and the top-3 still dominate by a wide margin precisely because the
    ±1 boost is concentrated on R49/R51.

    The threshold of 30% is well below the empirical share with the chosen
    baseline (which puts the top-3 share at >50% in practice) and well above
    what any uniform-noise model would produce — so it's a robust regression
    guard.
    """
    from flying_probe_copilot.generator import blocks as blocks_mod

    monkeypatch.setattr(
        blocks_mod, "_pick_failing_component", lambda outcome, profile, rng: ("R", 50)
    )

    profile = get_profile("medium")
    outcome = _outcome_for("ANALOG_OOL")

    counts: Counter[str] = Counter()
    for seed in range(1000):
        counts.update(_count_failed_designators(generate_blocks(profile, outcome, seed)))

    total = sum(counts.values())
    top3 = counts.most_common(3)
    top3_share = sum(c for _, c in top3) / total

    top3_names = {name for name, _ in top3}

    assert "R50" in top3_names, (
        f"Pinned primary R50 must be in the top-3 failing refdes. Top-3: {top3}"
    )
    assert top3_names & {"R49", "R51"}, (
        f"At least one ±1 neighbor of R50 must be in the top-3 failing refdes. "
        f"Top-3: {top3}"
    )
    assert top3_share > 0.30, (
        f"Top-3 failing refdes must account for >30% of all failures under "
        f"correlation. Got {top3_share:.2%} from {top3} (total fails: {total})."
    )


def test_correlation_secondary_fails_stay_within_same_family(monkeypatch):
    """Pin DIGITAL primary=U8; over 500 seeded panels, every fail must be a U_.

    Cross-family correlation must not exist: ``correlation_multiplier`` returns
    1.0 across prefixes, so an R/C/L block must never get a secondary fail when
    the primary is a U. This protects the existing
    ``test_failing_component_family_matches_outcome_mode_digital`` contract
    against accidental cross-family leakage through the new correlation pass.
    """
    from flying_probe_copilot.generator import blocks as blocks_mod

    monkeypatch.setattr(
        blocks_mod, "_pick_failing_component", lambda outcome, profile, rng: ("U", 8)
    )

    profile = get_profile("medium")
    outcome = _outcome_for("DIGITAL")

    counts: Counter[str] = Counter()
    for seed in range(500):
        counts.update(_count_failed_designators(generate_blocks(profile, outcome, seed)))

    non_u = [d for d in counts if not d.startswith("U")]
    assert non_u == [], (
        f"DIGITAL primary must produce only U-family fails. Cross-family fails: {non_u}"
    )
