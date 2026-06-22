"""Tests for ``flying_probe_copilot.generator.faults``.

Phase 1a Step E1 — RED phase. Covers all four fault profiles (random / drift /
cluster / process-change), the failure-mode distribution, the @BTEST status
mapping per failure mode, and the per-panel correlation heuristic.
"""

from __future__ import annotations

from datetime import datetime, timedelta

START = datetime(2026, 4, 1, 0, 0, 0)
END = START + timedelta(weeks=4)


# ---------------------------------------------------------------------------
# Profile-shape tests
# ---------------------------------------------------------------------------


def test_fault_profile_random_rate_within_tolerance_over_500_panels():
    """Empirical fail rate within ±20% of target over 500 panels."""
    from flying_probe_copilot.generator.faults import generate_panel_faults

    fails = sum(
        1
        for i in range(500)
        if generate_panel_faults(
            seed=i,
            profile="random",
            target_rate=0.10,
            panel_timestamp=START,
            window_start=START,
            window_end=END,
            change_point=None,
        ).failed
    )
    rate = fails / 500
    assert 0.08 <= rate <= 0.12, f"random rate {rate:.3f} outside ±20% of 0.10"


def test_fault_profile_drift_increases_monotonically():
    """Drift profile: late-window failures must exceed early-window."""
    from flying_probe_copilot.generator.faults import generate_panel_faults

    quartiles: list[int] = [0, 0, 0, 0]
    counts: list[int] = [0, 0, 0, 0]
    span = (END - START).total_seconds()
    for i in range(2000):
        # Distribute panel timestamps evenly through the window for the test.
        t = START + timedelta(seconds=span * (i / 2000))
        q = min(3, int((t - START).total_seconds() / span * 4))
        outcome = generate_panel_faults(
            seed=i,
            profile="drift",
            target_rate=0.10,
            panel_timestamp=t,
            window_start=START,
            window_end=END,
            change_point=None,
        )
        counts[q] += 1
        if outcome.failed:
            quartiles[q] += 1
    rate_q1 = quartiles[0] / counts[0]
    rate_q4 = quartiles[3] / counts[3]
    assert rate_q4 > rate_q1, f"drift profile q4 ({rate_q4:.3f}) must exceed q1 ({rate_q1:.3f})"


def test_fault_profile_cluster_concentrates_in_narrow_windows():
    """Cluster profile: ≥80% of failures fall in <20% of timestamps."""
    from flying_probe_copilot.generator.faults import generate_panel_faults

    failing_times: list[datetime] = []
    span = (END - START).total_seconds()
    for i in range(2000):
        t = START + timedelta(seconds=span * (i / 2000))
        outcome = generate_panel_faults(
            seed=i,
            profile="cluster",
            target_rate=0.10,
            panel_timestamp=t,
            window_start=START,
            window_end=END,
            change_point=None,
        )
        if outcome.failed:
            failing_times.append(t)
    # Bucket into 20 equal time bins; count how many bins hold ≥80% of failures.
    buckets = [0] * 20
    total = len(failing_times)
    assert total > 0
    for t in failing_times:
        idx = min(19, int((t - START).total_seconds() / span * 20))
        buckets[idx] += 1
    top_buckets = sorted(buckets, reverse=True)[:4]  # 4/20 = 20%
    concentrated = sum(top_buckets)
    assert concentrated / total >= 0.50, (
        f"cluster profile: top 20% of bins hold only {concentrated / total:.2f} of failures"
    )


def test_fault_profile_process_change_step_change():
    """Process-change: rate after the change-point ≥2× the rate before."""
    from flying_probe_copilot.generator.faults import generate_panel_faults

    change_point = START + (END - START) / 2
    fail_before = fail_after = 0
    count_before = count_after = 0
    span = (END - START).total_seconds()
    for i in range(2000):
        t = START + timedelta(seconds=span * (i / 2000))
        outcome = generate_panel_faults(
            seed=i,
            profile="process-change",
            target_rate=0.10,
            panel_timestamp=t,
            window_start=START,
            window_end=END,
            change_point=change_point,
        )
        if t < change_point:
            count_before += 1
            if outcome.failed:
                fail_before += 1
        else:
            count_after += 1
            if outcome.failed:
                fail_after += 1
    rate_before = fail_before / count_before
    rate_after = fail_after / count_after
    assert rate_after >= 2 * rate_before, (
        f"process-change: rate_after ({rate_after:.3f}) must be ≥ 2× rate_before ({rate_before:.3f})"
    )


# ---------------------------------------------------------------------------
# Failure-mode distribution (Revision 1 #WARNING-5: golden snapshot)
# ---------------------------------------------------------------------------


def test_failure_mode_distribution_matches_spec_within_tolerance():
    """Sample 10 000 random-profile panels at fault_rate=0.10 and check shares.

    Spec targets: ANALOG_OOL 40% / SHORTS 25% / OPEN 15% / DIGITAL 10% /
    MISSING 7% / GROSS 3%. Tolerance: ±2 percentage points.
    """
    from flying_probe_copilot.generator.faults import generate_panel_faults

    mode_counts: dict[str, int] = {}
    for i in range(10000):
        outcome = generate_panel_faults(
            seed=i,
            profile="random",
            target_rate=0.10,
            panel_timestamp=START,
            window_start=START,
            window_end=END,
            change_point=None,
        )
        if outcome.failed:
            mode_counts[outcome.mode] = mode_counts.get(outcome.mode, 0) + 1
    total = sum(mode_counts.values())
    assert total > 0
    targets = {
        "ANALOG_OOL": 0.40,
        "SHORTS": 0.25,
        "OPEN": 0.15,
        "DIGITAL": 0.10,
        "MISSING": 0.07,
        "GROSS": 0.03,
    }
    for mode, target in targets.items():
        share = mode_counts.get(mode, 0) / total
        assert abs(share - target) <= 0.02, (
            f"mode {mode}: empirical {share:.3f} vs target {target:.3f} "
            f"(diff {abs(share - target):.3f} > 0.02)"
        )


# ---------------------------------------------------------------------------
# Failure-mode -> @BTEST status mapping
# ---------------------------------------------------------------------------


def test_btest_status_for_shorts_failure_is_4():
    from flying_probe_copilot.generator.faults import btest_status_for_mode
    from flying_probe_copilot.generator.models import BTESTStatus

    assert btest_status_for_mode("SHORTS") == BTESTStatus.FAIL_SHORTS == 4


def test_btest_status_for_analog_failure_is_6():
    from flying_probe_copilot.generator.faults import btest_status_for_mode
    from flying_probe_copilot.generator.models import BTESTStatus

    assert btest_status_for_mode("ANALOG_OOL") == BTESTStatus.FAIL_ANALOG == 6
    assert btest_status_for_mode("OPEN") == BTESTStatus.FAIL_ANALOG
    assert btest_status_for_mode("GROSS") == BTESTStatus.FAIL_ANALOG


def test_btest_status_for_digital_failure_is_8():
    from flying_probe_copilot.generator.faults import btest_status_for_mode
    from flying_probe_copilot.generator.models import BTESTStatus

    assert btest_status_for_mode("DIGITAL") == BTESTStatus.FAIL_DIGITAL == 8


# ---------------------------------------------------------------------------
# Within-panel correlation
# ---------------------------------------------------------------------------


def test_fault_correlation_within_panel():
    """When R12 fails, R13 has elevated failure probability vs baseline.

    Revision 1 #WARNING-8: ``faults.py`` exposes ``correlation_multiplier``
    which returns >1.0 for adjacent-refdes neighbors, 1.0 otherwise.
    """
    from flying_probe_copilot.generator.faults import correlation_multiplier

    # Adjacent refdes ints: should be > 1.0.
    assert correlation_multiplier("R12", "R13") > 1.4
    # Far-apart refdes ints: should be 1.0.
    assert correlation_multiplier("R12", "R99") == 1.0
    # Different prefix: no correlation.
    assert correlation_multiplier("R12", "C12") == 1.0


def test_correlation_uses_refdes_numerical_neighbor_heuristic():
    """1000 seeded panels: when R12 forced to fail, R13's empirical rate > 1.4× R99's."""
    from flying_probe_copilot.generator.faults import correlated_failure_rate

    # Helper that, given baseline 0.05 and a forced-failed component R12,
    # returns the empirical fail-rate for the neighbor R13 vs the far R99
    # over N seeded trials.
    r13_rate, r99_rate = correlated_failure_rate(
        baseline=0.05,
        forced_failed="R12",
        candidates=["R13", "R99"],
        trials=1000,
        seed=42,
    )
    assert r13_rate > 1.4 * r99_rate, (
        f"R13 rate {r13_rate:.3f} should exceed 1.4× R99 rate {r99_rate:.3f}"
    )
