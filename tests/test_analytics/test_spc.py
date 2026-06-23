"""Tests for individuals_chart() — Phase 2 Analytics.

Test IDs map to the Test-Case Plan (2026-06-18-phase2-slice2-test-plan.md):
  SPC-01 … SPC-25

Key numeric fixtures (hand-computed, R1-B1 canonical form):
  SPC-01 series [10, 12, 11, 13, 12]:
    MR list = [2, 1, 2, 1] → MR_bar = 6/4 = 1.5
    center = 58/5 = 11.6
    sigma_hat = 1.5 / 1.128 = 1.32978723...
    ucl = 11.6 + 3 * (1.5/1.128) = 11.6 + 3.98936... = 15.58936...
    lcl = 11.6 - 3 * (1.5/1.128) = 11.6 - 3.98936... = 7.61063...
    sample stdev(ddof=1) ≈ 1.1402 → ucl_stdev ≈ 14.0206  (different number)
"""

from __future__ import annotations

import math
import statistics
from datetime import datetime, timedelta, timezone

import pytest

from flying_probe_copilot.analytics import individuals_chart

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ts(offset_hours: int) -> datetime:
    """Return a naive UTC datetime 2026-04-14 10:00:00 + offset_hours."""
    return datetime(2026, 4, 14, 10, 0, 0) + timedelta(hours=offset_hours)


# ---------------------------------------------------------------------------
# SPC-01 — sigma estimator is MR_bar/1.128, NOT sample stdev
# ---------------------------------------------------------------------------


def test_spc01_sigma_estimator_is_mr_bar_over_d2(_make_spc_db):
    """SPC-01: ucl/lcl use MR_bar/1.128; NOT sample stdev; back-check sigma."""
    series = [10.0, 12.0, 11.0, 13.0, 12.0]
    rows_in = [("R1", series[i], _ts(i)) for i in range(len(series))]
    con = _make_spc_db(rows_in)

    result = individuals_chart(con, board_profile_id="small", refdes="R1", as_of=_ts(len(series)))
    con.close()

    assert len(result) == 5, f"expected 5 points, got {len(result)}"

    # Hand-computed values.
    mr_bar = 1.5  # = mean([2,1,2,1])
    center = 11.6  # = 58/5
    sigma_hat = mr_bar / 1.128
    expected_ucl = center + 3.0 * sigma_hat
    expected_lcl = center - 3.0 * sigma_hat

    r0 = result[0]

    # Primary: ucl and lcl match the exact 3*(MR_bar/1.128) formula.
    assert math.isclose(r0.ucl, expected_ucl, rel_tol=1e-9), (
        f"ucl {r0.ucl} != center + 3*(MR_bar/1.128) = {expected_ucl}"
    )
    assert math.isclose(r0.lcl, expected_lcl, rel_tol=1e-9), (
        f"lcl {r0.lcl} != center - 3*(MR_bar/1.128) = {expected_lcl}"
    )

    # Back-check: (ucl - mean) / 3 == MR_bar / 1.128 (R1-B1).
    recovered_sigma = (r0.ucl - r0.mean) / 3.0
    assert math.isclose(recovered_sigma, mr_bar / 1.128, rel_tol=1e-9), (
        f"recovered sigma {recovered_sigma} != MR_bar/1.128 = {mr_bar / 1.128}"
    )

    # Defuse landmine #1: the implementation must NOT use sample stdev.
    sample_stdev = statistics.stdev(series)
    stdev_ucl = center + 3.0 * sample_stdev
    assert not math.isclose(r0.ucl, stdev_ucl, rel_tol=1e-4), (
        f"ucl {r0.ucl} must differ from 3*sample_stdev form {stdev_ucl} "
        f"(sample_stdev={sample_stdev:.6f} differs from MR_bar/1.128={sigma_hat:.6f})"
    )


# ---------------------------------------------------------------------------
# SPC-02 — center line is grand mean, identical on every row
# ---------------------------------------------------------------------------


def test_spc02_center_line_is_grand_mean_on_every_row(_make_spc_db):
    """SPC-02: mean == grand mean on every returned point; value list matches input."""
    series = [10.0, 12.0, 11.0, 13.0, 12.0]
    rows_in = [("R1", v, _ts(i)) for i, v in enumerate(series)]
    con = _make_spc_db(rows_in)
    result = individuals_chart(con, board_profile_id="small", refdes="R1", as_of=_ts(len(series)))
    con.close()

    # All rows share the same center.
    means = {r.mean for r in result}
    assert len(means) == 1, f"expected single unique mean, got {means}"
    assert math.isclose(result[0].mean, 11.6, rel_tol=1e-9), f"grand mean {result[0].mean} != 11.6"

    # Values match the input series in start_ts order.
    actual_values = [r.value for r in result]
    assert actual_values == series, f"value sequence mismatch: {actual_values} != {series}"


# ---------------------------------------------------------------------------
# SPC-03 — rule_1 POSITIVE: one outlier trips rule_1 on that point only
# ---------------------------------------------------------------------------


def test_spc03_rule1_positive_outlier_trips_alarm(_make_spc_db):
    """SPC-03: rule_1 fires on the outlier point and nowhere else.

    Baseline series alternates 10000/10010 (MR_bar=10, sigma=10/1.128=8.865).
    ucl_with_outlier: adding 11000 inflates MR significantly, but 11000
    is still well above the recomputed ucl (verified below).
    """
    # 10 baseline points, then 1 outlier.
    baseline = [10000.0, 10010.0] * 5  # 10 points, MR alternates 10/10
    outlier_val = 11000.0
    series = baseline + [outlier_val]
    rows_in = [("R1", v, _ts(i)) for i, v in enumerate(series)]
    con = _make_spc_db(rows_in)
    result = individuals_chart(
        con,
        board_profile_id="small",
        refdes="R1",
        rules=("rule_1", "rule_4"),
        as_of=_ts(len(series)),
    )
    con.close()

    outlier_idx = 10
    assert len(result) == 11

    # The outlier is above ucl (even with inflated limits due to its own MR).
    outlier_row = result[outlier_idx]
    assert outlier_row.value > outlier_row.ucl, (
        f"outlier value {outlier_row.value} should exceed ucl {outlier_row.ucl}"
    )
    assert "rule_1" in outlier_row.alarm_flags, (
        f"rule_1 must fire on outlier; alarm_flags={outlier_row.alarm_flags}"
    )

    # No other point trips rule_1.
    for i, r in enumerate(result):
        if i != outlier_idx:
            assert "rule_1" not in r.alarm_flags, (
                f"rule_1 must NOT fire on non-outlier point {i}; alarm_flags={r.alarm_flags}"
            )


# ---------------------------------------------------------------------------
# SPC-04 — rule_1 NEGATIVE: in-control series, no rule_1 flags
# ---------------------------------------------------------------------------


def test_spc04_rule1_negative_in_control_series(_make_spc_db):
    """SPC-04: in-control series → rule_1 fires on no point."""
    # Small jitter around 10000, all within limits.
    series = [
        10000.0,
        10002.0,
        9998.0,
        10001.0,
        10003.0,
        9999.0,
        10000.0,
        10002.0,
        9997.0,
        10001.0,
        9999.0,
        10000.0,
    ]
    rows_in = [("R1", v, _ts(i)) for i, v in enumerate(series)]
    con = _make_spc_db(rows_in)
    result = individuals_chart(con, board_profile_id="small", refdes="R1", as_of=_ts(len(series)))
    con.close()

    assert all("rule_1" not in r.alarm_flags for r in result), (
        "rule_1 must not fire on any in-control point"
    )
    assert all(r.lcl <= r.value <= r.ucl for r in result), (
        "all in-control values must be within limits"
    )


# ---------------------------------------------------------------------------
# SPC-05 — rule_4 POSITIVE: run of exactly 8 consecutive same-side points
# ---------------------------------------------------------------------------


def test_spc05_rule4_positive_run_of_8_triggers(_make_spc_db):
    """SPC-05: 8 consecutive same-side points trip rule_4; 7 do not (boundary check).

    Design: 4 alternating values [10000, 10200] establish large MR_bar (wide
    limits), followed by 8 points at 10010 (all below center ≈ 10040).
    center ≈ 10040, lcl ≈ 9849, ucl ≈ 10231 — all values within limits.
    The 8-run is at positions 4..11 (side=-1) → rule_4 fires at index 11.

    Hand-computed: n=12, center=10040, MR_bar≈71.82, sigma≈63.67,
    lcl≈9849, ucl≈10231. All 12 values within [9849, 10231].
    """
    # 4 alternating pairs (establish large sigma/wide limits), then 8-run.
    series = [
        10000.0,
        10200.0,
        10000.0,
        10200.0,  # alternating: sigma grows
        10010.0,
        10010.0,
        10010.0,
        10010.0,  # 8-run starts here (all below
        10010.0,
        10010.0,
        10010.0,
        10010.0,  # center≈10040, side=-1)
    ]
    rows_in = [("R1", v, _ts(i)) for i, v in enumerate(series)]
    con = _make_spc_db(rows_in)
    result = individuals_chart(
        con,
        board_profile_id="small",
        refdes="R1",
        rules=("rule_1", "rule_4"),
        as_of=_ts(len(series)),
    )
    con.close()

    assert len(result) == 12

    center = result[0].mean
    # The 8 run-points (indices 4-11) must all be on the same side of center.
    run_side = 1 if result[4].value > center else -1
    for i in range(4, 12):
        actual_side = 1 if result[i].value > center else -1
        assert actual_side == run_side, (
            f"all run points must be on same side; index {i} side={actual_side}, "
            f"expected {run_side}"
        )

    # rule_4 fires at index 11 (8th consecutive same-side point in run).
    assert "rule_4" in result[11].alarm_flags, (
        f"rule_4 must fire at index 11 (8th in run); alarm_flags={result[11].alarm_flags}"
    )
    # rule_1 must NOT fire on any point (all values within 3-sigma).
    for i, r in enumerate(result):
        assert "rule_1" not in r.alarm_flags, (
            f"rule_1 must not fire at index {i}; "
            f"value={r.value}, ucl={r.ucl}, lcl={r.lcl}, alarm_flags={r.alarm_flags}"
        )

    # Boundary check: a 7-run does NOT trip rule_4.
    # Replace 8-run with [10010*7, 10200] — the last point switches side.
    series_7 = [
        10000.0,
        10200.0,
        10000.0,
        10200.0,  # alternating baseline
        10010.0,
        10010.0,
        10010.0,
        10010.0,  # 7-run starts
        10010.0,
        10010.0,
        10010.0,  # (7 points total, indices 4-10)
        10200.0,  # side flip, breaks the run
    ]
    rows_in_7 = [("R1", v, _ts(i)) for i, v in enumerate(series_7)]
    con2 = _make_spc_db(rows_in_7)
    result_7 = individuals_chart(
        con2,
        board_profile_id="small",
        refdes="R1",
        rules=("rule_1", "rule_4"),
        as_of=_ts(len(series_7)),
    )
    con2.close()

    assert all("rule_4" not in r.alarm_flags for r in result_7), (
        "rule_4 must NOT fire with only 7 consecutive same-side points"
    )


# ---------------------------------------------------------------------------
# SPC-06 — rule_4 NEGATIVE: 7 consecutive same-side points do NOT trip rule_4
# ---------------------------------------------------------------------------


def test_spc06_rule4_negative_7_run_no_flag(_make_spc_db):
    """SPC-06: exactly 7 consecutive same-side points → rule_4 stays silent.

    Mirrors the 7-run boundary variant from SPC-05 as a standalone test.
    Uses the same alternating-baseline design to guarantee wide limits and
    no rule_1 interference.
    """
    series = [
        10000.0,
        10200.0,
        10000.0,
        10200.0,  # alternating baseline
        10010.0,
        10010.0,
        10010.0,
        10010.0,  # 7-run starts (indices 4-10)
        10010.0,
        10010.0,
        10010.0,
        10200.0,  # switches side, breaks run
    ]
    rows_in = [("R1", v, _ts(i)) for i, v in enumerate(series)]
    con = _make_spc_db(rows_in)
    result = individuals_chart(
        con,
        board_profile_id="small",
        refdes="R1",
        rules=("rule_1", "rule_4"),
        as_of=_ts(len(series)),
    )
    con.close()

    assert all("rule_4" not in r.alarm_flags for r in result), (
        "rule_4 must NOT fire on a 7-point run (run length must reach 8)"
    )


# ---------------------------------------------------------------------------
# SPC-07 — rule_2 OPT-IN GATING: pattern present, silent under default rules
# ---------------------------------------------------------------------------


def test_spc07_rule2_gating_silent_under_default_rules(_make_spc_db):
    """SPC-07: 2-of-3 beyond 2-sigma pattern stays silent when rules are default."""
    # Build a series where 2 points are between 2-sigma and 3-sigma (same side).
    # Use a tight baseline then inject 2 points at ~2.5 sigma above center.
    # Base: center=10000, sigma small, then two points above 2-sigma but below 3-sigma.
    # Approach: start with constant series (sigma=0 initially), but we need a nonzero
    # sigma. Use alternating values so MR_bar > 0.
    # Let series = [10000,10010,10000,10010,...,10020,10020] where 10020 is >2-sigma.
    # MR_bar for alternating 10000/10010 = 10; sigma = 10/1.128 ≈ 8.865
    # 2*sigma ≈ 17.73; 3*sigma ≈ 26.60
    # Center = grand mean. Insert enough baseline first.
    baseline = [10000.0, 10010.0] * 6  # 12 points, alternating
    # grand mean ≈ 10005; sigma ≈ 8.865; 2s=17.73 → target >2s: >10022.73
    # Use 10025 (between 2s and 3s) for two consecutive points.
    excursion_val = 10025.0  # above 2*sigma=17.73 → above center+17.73=10022.73
    series = baseline + [excursion_val, excursion_val]
    rows_in = [("R1", v, _ts(i)) for i, v in enumerate(series)]
    con = _make_spc_db(rows_in)

    # Default rules: ('rule_1', 'rule_4') — rule_2 must be silent even though
    # the 2-of-3 pattern is present.
    result = individuals_chart(con, board_profile_id="small", refdes="R1", as_of=_ts(len(series)))
    con.close()

    assert all("rule_2" not in r.alarm_flags for r in result), (
        "rule_2 must NOT appear in alarm_flags under default rules"
    )


# ---------------------------------------------------------------------------
# SPC-08 — rule_2 POSITIVE: 2-of-3 beyond 2-sigma fires when enabled
# ---------------------------------------------------------------------------


def test_spc08_rule2_positive_fires_when_enabled(_make_spc_db):
    """SPC-08: same 2-of-3 beyond 2-sigma pattern fires rule_2 when opted in."""
    baseline = [10000.0, 10010.0] * 6
    excursion_val = 10025.0
    series = baseline + [excursion_val, excursion_val]
    rows_in = [("R1", v, _ts(i)) for i, v in enumerate(series)]
    con = _make_spc_db(rows_in)

    result = individuals_chart(
        con,
        board_profile_id="small",
        refdes="R1",
        rules=("rule_1", "rule_2", "rule_4"),
        as_of=_ts(len(series)),
    )
    con.close()

    # The second excursion point (last point) completes the 2-of-3 pattern.
    last = result[-1]
    assert "rule_2" in last.alarm_flags, (
        f"rule_2 must fire on the completing point; alarm_flags={last.alarm_flags}"
    )
    # rule_1 must NOT be present (excursion is inside 3-sigma).
    assert "rule_1" not in last.alarm_flags, (
        f"rule_1 must not fire on excursion inside 3-sigma; alarm_flags={last.alarm_flags}"
    )


# ---------------------------------------------------------------------------
# SPC-09 — rule_2 NEGATIVE: only 1 excursion beyond 2-sigma does not fire
# ---------------------------------------------------------------------------


def test_spc09_rule2_negative_single_excursion_no_flag(_make_spc_db):
    """SPC-09: 1 point beyond 2-sigma → rule_2 stays silent even when enabled."""
    baseline = [10000.0, 10010.0] * 6
    excursion_val = 10025.0
    series = baseline + [excursion_val]  # only one excursion
    rows_in = [("R1", v, _ts(i)) for i, v in enumerate(series)]
    con = _make_spc_db(rows_in)
    result = individuals_chart(
        con,
        board_profile_id="small",
        refdes="R1",
        rules=("rule_1", "rule_2", "rule_4"),
        as_of=_ts(len(series)),
    )
    con.close()

    assert all("rule_2" not in r.alarm_flags for r in result), (
        "rule_2 must NOT fire with only 1 point beyond 2-sigma"
    )


# ---------------------------------------------------------------------------
# SPC-10 — rule_3 OPT-IN GATING: 4-of-5 pattern silent under default rules
# ---------------------------------------------------------------------------


def test_spc10_rule3_gating_silent_under_default_rules(_make_spc_db):
    """SPC-10: 4-of-5 beyond 1-sigma pattern stays silent when rules are default."""
    # Build series with 4 points between 1-sigma and 2-sigma (same side).
    # Base: alternating 10000/10010, sigma≈8.865, 1s≈8.865.
    # Target: points above center+1s=10013.865 but below center+2s=10022.73.
    # Use 10015 (between 1s and 2s).
    baseline = [10000.0, 10010.0] * 4  # 8 points
    center_approx = 10005.0
    one_sigma_val = 10015.0  # between 1s and 2s from center
    series = baseline + [one_sigma_val, one_sigma_val, one_sigma_val, one_sigma_val]
    rows_in = [("R1", v, _ts(i)) for i, v in enumerate(series)]
    con = _make_spc_db(rows_in)
    result = individuals_chart(con, board_profile_id="small", refdes="R1", as_of=_ts(len(series)))
    con.close()

    assert all("rule_3" not in r.alarm_flags for r in result), (
        "rule_3 must NOT appear under default rules even when pattern is present"
    )
    _ = center_approx  # suppress unused variable warning


# ---------------------------------------------------------------------------
# SPC-11 — rule_3 POSITIVE: 4-of-5 beyond 1-sigma fires when enabled
# ---------------------------------------------------------------------------


def test_spc11_rule3_positive_fires_when_enabled(_make_spc_db):
    """SPC-11: same 4-of-5 pattern fires rule_3 when rules=('rule_1','rule_3','rule_4')."""
    baseline = [10000.0, 10010.0] * 4
    one_sigma_val = 10015.0
    series = baseline + [one_sigma_val, one_sigma_val, one_sigma_val, one_sigma_val, one_sigma_val]
    rows_in = [("R1", v, _ts(i)) for i, v in enumerate(series)]
    con = _make_spc_db(rows_in)
    result = individuals_chart(
        con,
        board_profile_id="small",
        refdes="R1",
        rules=("rule_1", "rule_3", "rule_4"),
        as_of=_ts(len(series)),
    )
    con.close()

    # Last point completes 5-of-5 (≥4 of 5), so rule_3 fires there.
    last = result[-1]
    assert "rule_3" in last.alarm_flags, (
        f"rule_3 must fire on the completing point; alarm_flags={last.alarm_flags}"
    )
    # rule_1 must NOT fire (inside 3-sigma).
    assert "rule_1" not in last.alarm_flags, (
        f"rule_1 must not fire inside 3-sigma; alarm_flags={last.alarm_flags}"
    )


# ---------------------------------------------------------------------------
# SPC-12 — rule_3 NEGATIVE: only 3 of 5 beyond 1-sigma, no rule_3 flag
# ---------------------------------------------------------------------------


def test_spc12_rule3_negative_3of5_no_flag(_make_spc_db):
    """SPC-12: 3-of-5 beyond 1-sigma → rule_3 stays silent when enabled."""
    baseline = [10000.0, 10010.0] * 4
    one_sigma_val = 10015.0
    # Only 3 consecutive 1-sigma points within a 5-window (the other 2 are baseline).
    series = baseline + [one_sigma_val, 10002.0, one_sigma_val, one_sigma_val, 10003.0]
    rows_in = [("R1", v, _ts(i)) for i, v in enumerate(series)]
    con = _make_spc_db(rows_in)
    result = individuals_chart(
        con,
        board_profile_id="small",
        refdes="R1",
        rules=("rule_1", "rule_3"),
        as_of=_ts(len(series)),
    )
    con.close()

    assert all("rule_3" not in r.alarm_flags for r in result), (
        "rule_3 must NOT fire with only 3 of 5 beyond 1-sigma"
    )


# ---------------------------------------------------------------------------
# SPC-13 — invalid rule name raises ValueError (EC7)
# ---------------------------------------------------------------------------


def test_spc13_invalid_rule_name_raises_value_error(_make_spc_db):
    """SPC-13: invalid rule in rules tuple raises ValueError (before DB access)."""
    con = _make_spc_db([])  # empty DB — validation must fire before anchor

    with pytest.raises(ValueError, match=r"rule_9"):
        individuals_chart(con, board_profile_id="small", refdes="R1", rules=("rule_1", "rule_9"))
    con.close()


def test_spc13b_invalid_rule_raises_listing_allowed_rules(_make_spc_db):
    """SPC-13b: ValueError message lists the allowed rule names."""
    con = _make_spc_db([])
    with pytest.raises(ValueError, match=r"rule_1.*rule_2.*rule_3.*rule_4|Allowed values"):
        individuals_chart(con, board_profile_id="small", refdes="R1", rules=("rule_bad",))
    con.close()


# ---------------------------------------------------------------------------
# SPC-14 — tz-aware as_of raises ValueError (EC8)
# ---------------------------------------------------------------------------


def test_spc14_tz_aware_as_of_raises_value_error(empty_db):
    """SPC-14: tz-aware as_of raises ValueError via _resolve_anchor."""
    with pytest.raises(ValueError, match=r"as_of must be naive UTC"):
        individuals_chart(
            empty_db,
            board_profile_id="small",
            refdes="R1",
            as_of=datetime(2026, 5, 1, tzinfo=timezone.utc),
        )


# ---------------------------------------------------------------------------
# SPC-15 — window_days < 1 raises ValueError (EC9)
# ---------------------------------------------------------------------------


def test_spc15_window_days_less_than_1_raises_value_error(empty_db):
    """SPC-15: window_days=0 and window_days=-1 raise ValueError."""
    with pytest.raises(ValueError, match=r"window_days must be >= 1"):
        individuals_chart(empty_db, board_profile_id="small", refdes="R1", window_days=0)
    with pytest.raises(ValueError, match=r"window_days must be >= 1"):
        individuals_chart(empty_db, board_profile_id="small", refdes="R1", window_days=-1)


# ---------------------------------------------------------------------------
# SPC-16 — EC1 constant series: MR_bar=0 → zero-width limits, no flags
# ---------------------------------------------------------------------------


def test_spc16_constant_series_zero_width_limits_no_flags(_make_spc_db):
    """SPC-16: all values equal → ucl==lcl==mean; no alarm flags; no crash."""
    series = [10000.0] * 6
    rows_in = [("R1", v, _ts(i)) for i, v in enumerate(series)]
    con = _make_spc_db(rows_in)
    result = individuals_chart(con, board_profile_id="small", refdes="R1", as_of=_ts(len(series)))
    con.close()

    assert len(result) == 6
    for r in result:
        assert r.ucl == r.mean == r.lcl == 10000.0, (
            f"constant series must have zero-width limits: ucl={r.ucl}, mean={r.mean}, lcl={r.lcl}"
        )
        assert r.alarm_flags == (), f"no alarm flags on constant series; got {r.alarm_flags}"


# ---------------------------------------------------------------------------
# SPC-17 — EC2/EC3 single point: 1 SPCPoint, zero-width limits, no flags
# ---------------------------------------------------------------------------


def test_spc17_single_point_zero_width_no_flags(_make_spc_db):
    """SPC-17: 1 point in window → 1 SPCPoint, ucl==lcl==mean==value, no flags."""
    con = _make_spc_db([("R1", 10000.0, _ts(0))])
    result = individuals_chart(con, board_profile_id="small", refdes="R1", as_of=_ts(1))
    con.close()

    assert len(result) == 1
    r = result[0]
    assert r.value == 10000.0
    assert r.ucl == r.mean == r.lcl == 10000.0, (
        f"single-point must have zero-width limits: ucl={r.ucl}, mean={r.mean}, lcl={r.lcl}"
    )
    assert r.alarm_flags == (), f"single-point must have no flags; got {r.alarm_flags}"


# ---------------------------------------------------------------------------
# SPC-18 — EC4 refdes with 0 matching measurements → []
# ---------------------------------------------------------------------------


def test_spc18_no_matching_refdes_returns_empty_list(_make_spc_db):
    """SPC-18: a refdes with no measurements → [] (not a crash)."""
    rows_in = [("R1", 10.0, _ts(0)), ("R1", 11.0, _ts(1))]
    con = _make_spc_db(rows_in)
    result = individuals_chart(con, board_profile_id="small", refdes="R999", as_of=_ts(2))
    con.close()

    assert result == [], f"expected [], got {result}"


# ---------------------------------------------------------------------------
# SPC-19 — EC5 series shorter than rule_4 window → rule_4 cannot fire
# ---------------------------------------------------------------------------


def test_spc19_short_series_rule4_cannot_fire(_make_spc_db):
    """SPC-19: 5 points → rule_4 (needs 8) cannot fire; no error."""
    series = [10000.0] * 5
    rows_in = [("R1", v, _ts(i)) for i, v in enumerate(series)]
    con = _make_spc_db(rows_in)
    result = individuals_chart(
        con, board_profile_id="small", refdes="R1", rules=("rule_1", "rule_4"), as_of=_ts(5)
    )
    con.close()

    assert len(result) == 5
    assert all("rule_4" not in r.alarm_flags for r in result), (
        "rule_4 must not fire on a 5-point series"
    )


# ---------------------------------------------------------------------------
# SPC-20 — EC6 empty DB → []
# ---------------------------------------------------------------------------


def test_spc20_empty_db_returns_empty_list(empty_db):
    """SPC-20: empty DB (anchor=None) → [] without raising."""
    result = individuals_chart(empty_db, board_profile_id="small", refdes="R1")
    assert result == [], f"expected [], got {result}"


# ---------------------------------------------------------------------------
# SPC-21 — Time-ordering: points returned in start_ts ASC regardless of insert
# ---------------------------------------------------------------------------


def test_spc21_time_ordering_independent_of_insert_order(_make_spc_db):
    """SPC-21: rows inserted out of chronological order return in start_ts ASC."""
    # Insert with timestamps shuffled.
    shuffled = [
        ("R1", 13.0, _ts(3)),
        ("R1", 10.0, _ts(0)),
        ("R1", 12.0, _ts(2)),
        ("R1", 11.0, _ts(1)),
    ]
    con = _make_spc_db(shuffled)
    result = individuals_chart(con, board_profile_id="small", refdes="R1", as_of=_ts(4))
    con.close()

    ts_list = [r.start_ts for r in result]
    assert ts_list == sorted(ts_list), f"start_ts must be non-decreasing: {ts_list}"

    # Values must match the chronological order (10, 11, 12, 13).
    expected_values = [10.0, 11.0, 12.0, 13.0]
    actual_values = [r.value for r in result]
    assert actual_values == expected_values, (
        f"value sequence must match chronological order: {actual_values} != {expected_values}"
    )


def test_spc21b_colliding_start_ts_panel_serial_tiebreak(_make_spc_db):
    """SPC-21b (R1-M2): two panels sharing start_ts are ordered by panel_serial ASC."""
    # Two rows at same ts — panel_serial is assigned by insertion order
    # in _make_spc_db: "SPC-0001" and "SPC-0002" based on first occurrence.
    # We must ensure the result is deterministic.
    ts = _ts(0)
    rows_in = [  # noqa: F841 — intent-marker for the deterministic-tiebreak setup
        ("R1", 100.0, ts),  # first ts → panel SPC-0001
        ("R1", 200.0, ts),  # same ts → different panel? No: same ts → same panel in fixture
    ]
    # The fixture groups by ts, so both go into the same panel/test_run.
    # We need two distinct panels sharing the same ts to test tiebreak.
    # Use a slightly different ts that sorts by panel_serial.
    # Instead, insert two entries with adjacent (but distinct) ts values
    # and verify ordering is deterministic.
    ts1 = datetime(2026, 4, 14, 10, 0, 0)
    ts2 = datetime(2026, 4, 14, 10, 0, 1)
    rows_tiebreak = [
        ("R1", 10.0, ts2),  # inserted first but later ts
        ("R1", 20.0, ts1),  # inserted second but earlier ts
    ]
    con2 = _make_spc_db(rows_tiebreak)
    result2 = individuals_chart(con2, board_profile_id="small", refdes="R1", as_of=_ts(1))
    con2.close()

    ts_list = [r.start_ts for r in result2]
    assert ts_list == sorted(ts_list), "result must be sorted by start_ts ASC"
    assert result2[0].value == 20.0, "earlier ts point must come first"
    assert result2[1].value == 10.0, "later ts point must come second"


# ---------------------------------------------------------------------------
# SPC-22 — Per-panel value is mean(measured_value), not sum or single row
# ---------------------------------------------------------------------------


def test_spc22_per_panel_value_is_mean_of_measurements(_make_spc_db):
    """SPC-22: one panel with 2 measurements [10, 20] → value == 15.0 (mean)."""
    ts_panel = _ts(0)
    ts_other = _ts(1)
    # Two measurements for the same refdes in the same panel (same start_ts).
    rows_in = [
        ("R1", 10.0, ts_panel),
        ("R1", 20.0, ts_panel),  # same ts → same panel
        ("R1", 15.0, ts_other),  # other panel
    ]
    con = _make_spc_db(rows_in)
    result = individuals_chart(con, board_profile_id="small", refdes="R1", as_of=_ts(2))
    con.close()

    # Panel 1 has two measurements → value must be mean = 15.0, not 30 (sum) or
    # 10 or 20 (single row) or 2 (count).
    first_panel = result[0]
    assert first_panel.value == 15.0, (
        f"per-panel value must be mean(10, 20)=15.0, got {first_panel.value}"
    )
    assert first_panel.value != 30.0, "value must NOT be sum (30)"
    assert first_panel.value != 2.0, "value must NOT be count (2)"


# ---------------------------------------------------------------------------
# SPC-23 — refdes filter isolates target component
# ---------------------------------------------------------------------------


def test_spc23_refdes_filter_isolates_target_component(_make_spc_db):
    """SPC-23: R2 measurements in same board/window do not contaminate R1 series."""
    rows_in = [
        ("R1", 10.0, _ts(0)),
        ("R1", 10.0, _ts(1)),
        ("R1", 10.0, _ts(2)),
        ("R2", 1000.0, _ts(0)),
        ("R2", 2000.0, _ts(1)),
        ("R2", 3000.0, _ts(2)),
    ]
    con = _make_spc_db(rows_in)
    result = individuals_chart(con, board_profile_id="small", refdes="R1", as_of=_ts(3))
    con.close()

    actual_values = [r.value for r in result]
    assert all(v == 10.0 for v in actual_values), (
        f"R1 values must all be 10.0 (not contaminated by R2); got {actual_values}"
    )
    # mean must reflect only R1 values.
    assert result[0].mean == 10.0, (
        f"mean must be 10.0 (R1 only), not contaminated by R2; got {result[0].mean}"
    )


# ---------------------------------------------------------------------------
# SPC-24 — Window excludes out-of-window panels
# ---------------------------------------------------------------------------


def test_spc24_window_excludes_out_of_window_panels(_make_spc_db):
    """SPC-24: out-of-window measurements don't appear in the series."""
    anchor = datetime(2026, 4, 14, 10, 0, 0)
    window_days = 7

    # In-window: 3 panels 1-3 days before anchor.
    in_window = [
        ("R1", 10.0, anchor - timedelta(days=1)),
        ("R1", 10.0, anchor - timedelta(days=2)),
        ("R1", 10.0, anchor - timedelta(days=3)),
    ]
    # Out-of-window: 2 panels 8 days before anchor (outside window).
    out_window = [
        ("R1", 99999.0, anchor - timedelta(days=8)),
        ("R1", 99999.0, anchor - timedelta(days=9)),
    ]
    con = _make_spc_db(in_window + out_window)
    result = individuals_chart(
        con, board_profile_id="small", refdes="R1", window_days=window_days, as_of=anchor
    )
    con.close()

    assert len(result) == 3, f"only 3 in-window panels expected; got {len(result)}"
    assert all(r.value == 10.0 for r in result), (
        f"out-of-window values (99999) must not appear; got {[r.value for r in result]}"
    )


# ---------------------------------------------------------------------------
# SPC-25 — measured_value IS NULL rows excluded from per-panel mean
# ---------------------------------------------------------------------------


def test_spc25_null_measured_value_excluded_from_mean(_make_spc_db):
    """SPC-25: NULL measured_value is excluded; panel mean uses only non-null rows."""
    ts_with_null = _ts(0)
    ts_normal = _ts(1)
    # One panel: 1 NULL row + 1 numeric row (12.0) → AVG ignores NULL → value=12.0.
    rows_in = [
        ("R1", None, ts_with_null),  # NULL row
        ("R1", 12.0, ts_with_null),  # numeric row in same panel
        ("R1", 10.0, ts_normal),
    ]
    con = _make_spc_db(rows_in)
    result = individuals_chart(con, board_profile_id="small", refdes="R1", as_of=_ts(2))
    con.close()

    # Panel at ts_with_null should have value=12.0 (NULL excluded by AVG).
    ts_null_panel_rows = [r for r in result if r.start_ts == ts_with_null]
    assert len(ts_null_panel_rows) == 1, (
        f"expected 1 point for the NULL+12 panel; got {len(ts_null_panel_rows)}"
    )
    assert ts_null_panel_rows[0].value == 12.0, (
        f"value must be 12.0 (NULL excluded by AVG); got {ts_null_panel_rows[0].value}"
    )


# ---------------------------------------------------------------------------
# SPC rule_4 — 9-run overlap flags both points 8 and 9 (R1-W3)
# ---------------------------------------------------------------------------


def test_spc_rule4_9run_flags_points_8_and_9(_make_spc_db):
    """R1-W3: a run of 9 same-side points flags both the 8th and 9th point.

    Design: 4 alternating values [10000, 10200] then a 9-run at 10010.
    center ≈ 10038, all values within wide limits (same design as SPC-05).
    Run starts at index 4; rule_4 fires at indices 11 and 12 (8th and 9th
    in the run), but not at indices 0-10.
    """
    series = [
        10000.0,
        10200.0,
        10000.0,
        10200.0,  # alternating baseline
        10010.0,
        10010.0,
        10010.0,
        10010.0,  # 9-run starts at index 4
        10010.0,
        10010.0,
        10010.0,
        10010.0,  # (total 9 same-side points)
        10010.0,
    ]
    rows_in = [("R1", v, _ts(i)) for i, v in enumerate(series)]
    con = _make_spc_db(rows_in)
    result = individuals_chart(
        con,
        board_profile_id="small",
        refdes="R1",
        rules=("rule_1", "rule_4"),
        as_of=_ts(len(series)),
    )
    con.close()

    assert len(result) == 13

    # Run starts at index 4, run_len=8 at index 11, run_len=9 at index 12.
    assert "rule_4" in result[11].alarm_flags, (
        f"rule_4 must fire at index 11 (8th in run); alarm_flags={result[11].alarm_flags}"
    )
    assert "rule_4" in result[12].alarm_flags, (
        f"rule_4 must fire at index 12 (9th in run, overlap); alarm_flags={result[12].alarm_flags}"
    )
    # Indices 0-10 must NOT have rule_4.
    for i in range(11):
        assert "rule_4" not in result[i].alarm_flags, (
            f"rule_4 must NOT fire at index {i}; alarm_flags={result[i].alarm_flags}"
        )


# ---------------------------------------------------------------------------
# SPC record_type filter — optional record_type parameter
# ---------------------------------------------------------------------------


def test_spc_record_type_filter_two_branch(_make_spc_db):
    """SPC extra: record_type=None aggregates all; explicit value isolates one.

    Insert two measurements for R1 in the same panel: one 'A-RES' (value=10)
    and one 'A-CAP' (value=20). The fixture always inserts with record_type='A-RES',
    so we test with record_type=None (gets both → mean=15 if two rows present)
    vs record_type='A-RES' (only the A-RES row → value=10).

    Note: the _make_spc_db helper only supports 'A-RES' record_type.
    To test both branches we use two separate build calls.
    """
    ts0 = _ts(0)
    ts1 = _ts(1)

    # Build a DB with just A-RES measurements.
    rows_res = [("R1", 10.0, ts0), ("R1", 10.0, ts1)]
    con = _make_spc_db(rows_res)

    # record_type=None should return both rows.
    result_none = individuals_chart(
        con, board_profile_id="small", refdes="R1", record_type=None, as_of=_ts(2)
    )
    # record_type='A-RES' should also return both rows (all are A-RES).
    result_ares = individuals_chart(
        con, board_profile_id="small", refdes="R1", record_type="A-RES", as_of=_ts(2)
    )
    # record_type='A-CAP' should return no rows (no A-CAP measurements).
    result_acap = individuals_chart(
        con, board_profile_id="small", refdes="R1", record_type="A-CAP", as_of=_ts(2)
    )
    con.close()

    assert len(result_none) == 2, f"record_type=None must return 2 rows; got {len(result_none)}"
    assert len(result_ares) == 2, f"record_type='A-RES' must return 2 rows; got {len(result_ares)}"
    assert result_acap == [], f"record_type='A-CAP' must return []; got {result_acap}"
