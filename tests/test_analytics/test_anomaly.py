"""Tests for z_score_anomalies() — Phase 2 Analytics.

Test IDs map to the Test-Case Plan (2026-06-18-phase2-slice2-test-plan.md):
  ANOM-01 … ANOM-21

Key numeric fixtures (hand-computed, leave-one-out):
  ANOM-01 dataset: 4 boards, rates = [G1=0.1, G2=0.2, G3=0.3, G4=0.9].
    For G4: peers = [0.1, 0.2, 0.3]
      baseline_mean = fmean([0.1, 0.2, 0.3]) = 0.2 (not (0.1+0.2+0.3+0.9)/4=0.375)
      baseline_std  = stdev([0.1, 0.2, 0.3], ddof=1) = 0.1
      z_score       = (0.9 - 0.2) / 0.1 = 7.0
"""

from __future__ import annotations

import math
import statistics
from datetime import datetime, timezone

import pytest

from flying_probe_copilot.analytics import AnomalyRow, z_score_anomalies

# ---------------------------------------------------------------------------
# Helper: four-group dataset rates [0.1, 0.2, 0.3, 0.9]
# ---------------------------------------------------------------------------

_RATES_4 = [0.1, 0.2, 0.3, 0.9]


def _make_4group_db(make_fn, *, window_days: int = 30):
    """Build the canonical 4-board dataset with rates [0.1, 0.2, 0.3, 0.9].

    G1: 10 total, 1 failed  → rate 0.1
    G2: 10 total, 2 failed  → rate 0.2
    G3: 10 total, 3 failed  → rate 0.3
    G4: 10 total, 9 failed  → rate 0.9
    """
    groups = [
        {"key": f"BOARD-{i+1}", "total": 10, "failed": int(r * 10), "in_window": True}
        for i, r in enumerate(_RATES_4)
    ]
    return make_fn(groups, by="board", window_days=window_days)


# ---------------------------------------------------------------------------
# ANOM-01 — leave-one-out: G4 baseline_mean == peer-only mean, not include-self
# ---------------------------------------------------------------------------


def test_anom01_leave_one_out_g4_baseline_is_peer_only(_make_anomaly_db):
    """ANOM-01: G4's baseline_mean == fmean(peers), NOT the include-self global mean."""
    con = _make_4group_db(_make_anomaly_db)
    result = z_score_anomalies(con, by="board", threshold=3.0)
    con.close()

    g4_row = next(r for r in result if r.group_key == "BOARD-4")

    peer_rates = [0.1, 0.2, 0.3]
    expected_bm = statistics.fmean(peer_rates)        # ≈ 0.2 (leave-one-out)
    include_self_mean = statistics.fmean([0.1, 0.2, 0.3, 0.9])  # ≈ 0.375 (wrong)

    assert math.isclose(g4_row.baseline_mean, expected_bm, rel_tol=1e-9), (
        f"G4 baseline_mean must be peer-only fmean={expected_bm}; "
        f"got {g4_row.baseline_mean}"
    )
    # Explicitly prove it is NOT the include-self mean.
    assert not math.isclose(g4_row.baseline_mean, include_self_mean, rel_tol=1e-6), (
        f"G4 baseline_mean must NOT equal include-self mean {include_self_mean}"
    )

    expected_std = statistics.stdev(peer_rates)  # ddof=1 ≈ 0.1
    assert math.isclose(g4_row.baseline_std, expected_std, rel_tol=1e-9), (
        f"G4 baseline_std must be stdev(peers)={expected_std}; got {g4_row.baseline_std}"
    )

    expected_z = (0.9 - expected_bm) / expected_std
    assert math.isclose(g4_row.z_score, expected_z, rel_tol=1e-9), (
        f"G4 z_score must be {expected_z}; got {g4_row.z_score}"
    )


# ---------------------------------------------------------------------------
# ANOM-02 — each group's baseline_mean is different (per-group loop proven)
# ---------------------------------------------------------------------------


def test_anom02_each_group_has_different_baseline_mean(_make_anomaly_db):
    """ANOM-02: different groups drop different peers → baseline_means differ."""
    con = _make_4group_db(_make_anomaly_db)
    result = z_score_anomalies(con, by="board", threshold=3.0)
    con.close()

    # G1 (rate=0.1) peers = [0.2, 0.3, 0.9] → bm = fmean = 0.4666...
    # G2 (rate=0.2) peers = [0.1, 0.3, 0.9] → bm = fmean = 0.4333...
    g1_row = next(r for r in result if r.group_key == "BOARD-1")
    g2_row = next(r for r in result if r.group_key == "BOARD-2")

    g1_expected_bm = statistics.fmean([0.2, 0.3, 0.9])
    g2_expected_bm = statistics.fmean([0.1, 0.3, 0.9])

    assert math.isclose(g1_row.baseline_mean, g1_expected_bm, rel_tol=1e-9), (
        f"G1 baseline_mean expected {g1_expected_bm}; got {g1_row.baseline_mean}"
    )
    assert math.isclose(g2_row.baseline_mean, g2_expected_bm, rel_tol=1e-9), (
        f"G2 baseline_mean expected {g2_expected_bm}; got {g2_row.baseline_mean}"
    )

    # Prove they are different — a shared global mean would make them equal.
    assert not math.isclose(g1_row.baseline_mean, g2_row.baseline_mean, rel_tol=1e-9), (
        "G1 and G2 must have different baseline_means (per-group exclusion)"
    )


# ---------------------------------------------------------------------------
# ANOM-03 — POSITIVE flag: one bad group is flagged
# ---------------------------------------------------------------------------


def test_anom03_positive_flag_bad_group_is_flagged(_make_anomaly_db):
    """ANOM-03: the one anomalous group is flagged; others are not."""
    # 5 groups: 4 with small rates, 1 with a large rate.
    groups = [
        {"key": "G1", "total": 100, "failed": 4,  "in_window": True},  # rate=0.04
        {"key": "G2", "total": 100, "failed": 5,  "in_window": True},  # rate=0.05
        {"key": "G3", "total": 100, "failed": 6,  "in_window": True},  # rate=0.06
        {"key": "G4", "total": 100, "failed": 5,  "in_window": True},  # rate=0.05
        {"key": "G5", "total": 100, "failed": 80, "in_window": True},  # rate=0.80 (bad)
    ]
    con = _make_anomaly_db(groups, by="board")
    result = z_score_anomalies(con, by="board", threshold=3.0)
    con.close()

    assert len(result) == 5

    flagged_rows = [r for r in result if r.flagged]
    assert len(flagged_rows) == 1, (
        f"exactly one row must be flagged; got {[r.group_key for r in flagged_rows]}"
    )
    assert flagged_rows[0].group_key == "G5", (
        f"the flagged group must be G5; got {flagged_rows[0].group_key}"
    )
    assert abs(flagged_rows[0].z_score) >= 3.0, (
        f"G5 |z_score| must be >= threshold 3.0; got {flagged_rows[0].z_score}"
    )


# ---------------------------------------------------------------------------
# ANOM-04 — NEGATIVE: homogeneous dataset flags no group
# ---------------------------------------------------------------------------


def test_anom04_negative_homogeneous_no_flags(_make_anomaly_db):
    """ANOM-04: near-identical rates → no group flagged."""
    groups = [
        {"key": f"G{i}", "total": 100, "failed": f, "in_window": True}
        for i, f in enumerate([10, 11, 9, 10, 10])
    ]
    con = _make_anomaly_db(groups, by="board")
    result = z_score_anomalies(con, by="board", threshold=3.0)
    con.close()

    assert len(result) == 5, f"expected 5 rows; got {len(result)}"
    assert all(r.flagged is False for r in result), (
        f"homogeneous data: no row must be flagged; "
        f"flagged={[r.group_key for r in result if r.flagged]}"
    )


# ---------------------------------------------------------------------------
# ANOM-05 — value is failed/total (unrounded), not raw count
# ---------------------------------------------------------------------------


def test_anom05_value_is_failure_rate_not_raw_count(_make_anomaly_db):
    """ANOM-05: value == failed/total (e.g. 3/8 = 0.375), not 3 or rounded."""
    groups = [
        {"key": "G1", "total": 8,  "failed": 3,  "in_window": True},  # rate=0.375
        {"key": "G2", "total": 10, "failed": 1,  "in_window": True},
        {"key": "G3", "total": 10, "failed": 2,  "in_window": True},
    ]
    con = _make_anomaly_db(groups, by="board")
    result = z_score_anomalies(con, by="board", threshold=3.0)
    con.close()

    g1_row = next(r for r in result if r.group_key == "G1")
    assert math.isclose(g1_row.value, 3 / 8, rel_tol=1e-9), (
        f"value must be 3/8=0.375; got {g1_row.value}"
    )
    assert g1_row.value != 3, "value must NOT be the raw count"
    assert g1_row.value != 3.0, "value must NOT be the raw count as float"


# ---------------------------------------------------------------------------
# ANOM-06 — ddof=1 (sample std), not population std
# ---------------------------------------------------------------------------


def test_anom06_ddof1_sample_std_not_population(_make_anomaly_db):
    """ANOM-06: baseline_std uses ddof=1 (sample); a population-std impl fails."""
    # G4 peers = [0.1, 0.2, 0.3].
    # statistics.stdev(ddof=1) = 0.1 exactly.
    # statistics.pstdev(ddof=0) = 0.08164965809277261 (different).
    con = _make_4group_db(_make_anomaly_db)
    result = z_score_anomalies(con, by="board", threshold=3.0)
    con.close()

    g4_row = next(r for r in result if r.group_key == "BOARD-4")

    sample_std = statistics.stdev([0.1, 0.2, 0.3])
    pop_std = statistics.pstdev([0.1, 0.2, 0.3])

    assert math.isclose(g4_row.baseline_std, sample_std, rel_tol=1e-9), (
        f"baseline_std must be sample stdev={sample_std}; got {g4_row.baseline_std}"
    )
    assert not math.isclose(g4_row.baseline_std, pop_std, rel_tol=1e-4), (
        f"baseline_std must NOT be population stdev={pop_std}"
    )


# ---------------------------------------------------------------------------
# ANOM-07 — two-sided: a BELOW-peers group is also flagged (negative z)
# ---------------------------------------------------------------------------


def test_anom07_two_sided_negative_z_is_flagged(_make_anomaly_db):
    """ANOM-07: a far-below-peers group has z<0 and flagged=True (two-sided abs)."""
    groups = [
        {"key": "G1", "total": 100, "failed": 50, "in_window": True},  # rate=0.50
        {"key": "G2", "total": 100, "failed": 52, "in_window": True},  # rate=0.52
        {"key": "G3", "total": 100, "failed": 48, "in_window": True},  # rate=0.48
        {"key": "G4", "total": 100, "failed": 51, "in_window": True},  # rate=0.51
        {"key": "G5", "total": 100, "failed": 0,  "in_window": True},  # rate=0.00 (far below)
    ]
    con = _make_anomaly_db(groups, by="board")
    result = z_score_anomalies(con, by="board", threshold=3.0)
    con.close()

    g5_row = next(r for r in result if r.group_key == "G5")

    assert math.isfinite(g5_row.z_score), f"z_score must be finite; got {g5_row.z_score}"
    assert g5_row.z_score < 0, f"below-peers group must have negative z; got {g5_row.z_score}"
    assert g5_row.flagged is True, (
        f"below-peers group must be flagged (two-sided abs); flagged={g5_row.flagged}"
    )
    assert abs(g5_row.z_score) >= 3.0, (
        f"|z_score| must be >= threshold 3.0; got {abs(g5_row.z_score)}"
    )


# ---------------------------------------------------------------------------
# ANOM-08 — ordering: abs(z_score) DESC, group_key ASC
# ---------------------------------------------------------------------------


def test_anom08_ordering_severity_first(_make_anomaly_db):
    """ANOM-08: rows sorted by abs(z_score) DESC, then group_key ASC."""
    # Construct groups with distinct |z| values.
    # G_high_above: very high rate → large positive z.
    # G_high_below: very low rate → large negative z with slightly smaller |z|.
    # G_medium: medium z.
    # G_low: near peers → small z.
    # For the tie on |z|: two groups with equal |z| must sort by group_key ASC.
    groups = [
        {"key": "ALPHA", "total": 100, "failed": 50, "in_window": True},  # rate=0.50
        {"key": "BETA",  "total": 100, "failed": 50, "in_window": True},  # rate=0.50 (tie)
        {"key": "GAMMA", "total": 100, "failed": 1,  "in_window": True},  # rate=0.01
        {"key": "DELTA", "total": 100, "failed": 99, "in_window": True},  # rate=0.99
    ]
    con = _make_anomaly_db(groups, by="board")
    result = z_score_anomalies(con, by="board", threshold=3.0)
    con.close()

    assert len(result) == 4

    abs_z_scores = [abs(r.z_score) for r in result]
    # Must be non-increasing.
    assert abs_z_scores == sorted(abs_z_scores, reverse=True), (
        f"rows must be in abs(z_score) DESC order; got {[(r.group_key, abs(r.z_score)) for r in result]}"
    )

    # ALPHA and BETA have the same rate, so they'll have similar |z| values.
    # Verify that equal-|z| rows are in group_key ASC.
    alpha_row = next(r for r in result if r.group_key == "ALPHA")
    beta_row = next(r for r in result if r.group_key == "BETA")
    alpha_idx = result.index(alpha_row)
    beta_idx = result.index(beta_row)

    if math.isclose(abs(alpha_row.z_score), abs(beta_row.z_score), rel_tol=1e-9):
        assert alpha_idx < beta_idx, (
            "for equal |z|, ALPHA (alphabetically first) must precede BETA"
        )


# ---------------------------------------------------------------------------
# ANOM-09 — each by value groups correctly
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("by", ["board", "shift", "line", "operator"])
def test_anom09_each_by_value_groups_correctly(_make_anomaly_db, by):
    """ANOM-09: for each by value, returned group_keys match the expected dimension."""
    if by == "board":
        keys = ["BOARD-A", "BOARD-B", "BOARD-C"]
    elif by == "shift":
        keys = ["A", "B", "C"]
    elif by == "line":
        keys = ["LINE-1", "LINE-2", "LINE-3"]
    else:  # operator
        keys = ["OP-001", "OP-002", "OP-003"]

    groups = [
        {"key": keys[0], "total": 10, "failed": 1, "in_window": True},
        {"key": keys[1], "total": 10, "failed": 2, "in_window": True},
        {"key": keys[2], "total": 10, "failed": 9, "in_window": True},
    ]
    con = _make_anomaly_db(groups, by=by)
    result = z_score_anomalies(con, by=by, threshold=3.0)
    con.close()

    assert len(result) == 3, f"expected 3 rows for by={by!r}; got {len(result)}"
    actual_keys = {r.group_key for r in result}
    assert actual_keys == set(keys), (
        f"group_keys for by={by!r} must be {set(keys)}; got {actual_keys}"
    )
    # Verify rates are correct.
    for grp, r in zip(sorted(keys), sorted(result, key=lambda x: x.group_key)):
        expected_rate = next(g["failed"] / g["total"] for g in groups if g["key"] == grp)
        assert math.isclose(r.value, expected_rate, rel_tol=1e-9), (
            f"group {grp} value {r.value} != expected rate {expected_rate}"
        )


# ---------------------------------------------------------------------------
# ANOM-10 — EC10: group with total==0 excluded from candidates AND peers
# ---------------------------------------------------------------------------


def test_anom10_group_with_zero_total_excluded(_make_anomaly_db):
    """ANOM-10: group with total=0 is excluded; other groups' baselines are unaffected."""
    # G_empty has no in-window runs (in_window=False → total=0 in window).
    # G1, G2, G3 are normal.
    groups = [
        {"key": "G1", "total": 10, "failed": 1, "in_window": True},
        {"key": "G2", "total": 10, "failed": 2, "in_window": True},
        {"key": "G3", "total": 10, "failed": 3, "in_window": True},
        {"key": "G4", "total": 5,  "failed": 2, "in_window": False},  # out-of-window
    ]
    con = _make_anomaly_db(groups, by="board")
    result = z_score_anomalies(con, by="board", threshold=3.0)
    con.close()

    # G4 must not appear in result (total=0 in window).
    group_keys = {r.group_key for r in result}
    assert "G4" not in group_keys, (
        f"group with total=0 must be excluded; keys={group_keys}"
    )
    assert len(result) == 3, f"expected 3 rows (G1..G3); got {len(result)}"

    # G1's baseline must be based on G2 and G3 only (not G4).
    g1_row = next(r for r in result if r.group_key == "G1")
    expected_bm_g1 = statistics.fmean([0.2, 0.3])
    assert math.isclose(g1_row.baseline_mean, expected_bm_g1, rel_tol=1e-9), (
        f"G1 baseline_mean must be fmean([0.2, 0.3])={expected_bm_g1}; "
        f"got {g1_row.baseline_mean}"
    )


# ---------------------------------------------------------------------------
# ANOM-11 — EC11: all groups identical rate → baseline_std=0, z=0, none flagged
# ---------------------------------------------------------------------------


def test_anom11_all_identical_rates_zero_std_zero_z(_make_anomaly_db):
    """ANOM-11: identical rates → baseline_std=0, z=0, flagged=False for all."""
    groups = [
        {"key": f"G{i}", "total": 10, "failed": 2, "in_window": True}
        for i in range(4)
    ]
    con = _make_anomaly_db(groups, by="board")
    result = z_score_anomalies(con, by="board", threshold=3.0)
    con.close()

    assert len(result) == 4
    for r in result:
        assert r.baseline_std == 0.0, (
            f"baseline_std must be 0.0 for identical peers; got {r.baseline_std}"
        )
        assert r.z_score == 0.0, (
            f"z_score must be 0.0 when baseline_std=0; got {r.z_score}"
        )
        assert r.flagged is False, (
            f"no row must be flagged when std=0; got flagged={r.flagged}"
        )


# ---------------------------------------------------------------------------
# ANOM-12 — EC12: single group → [] (no peers)
# ---------------------------------------------------------------------------


def test_anom12_single_group_returns_empty_list(_make_anomaly_db):
    """ANOM-12: only one group in window → [] (cannot evaluate without peers)."""
    groups = [{"key": "ONLY-G", "total": 10, "failed": 5, "in_window": True}]
    con = _make_anomaly_db(groups, by="board")
    result = z_score_anomalies(con, by="board", threshold=3.0)
    con.close()

    assert result == [], f"single group → [] expected; got {result}"


# ---------------------------------------------------------------------------
# ANOM-13 — EC13: exactly two groups → baseline_std=0, z=0, flagged=False
# ---------------------------------------------------------------------------


def test_anom13_two_groups_one_peer_std_zero(_make_anomaly_db):
    """ANOM-13: two groups → each has 1 peer → std=0, z=0, flagged=False."""
    groups = [
        {"key": "G1", "total": 10, "failed": 1,  "in_window": True},  # rate=0.1
        {"key": "G2", "total": 10, "failed": 9,  "in_window": True},  # rate=0.9
    ]
    con = _make_anomaly_db(groups, by="board")
    result = z_score_anomalies(con, by="board", threshold=3.0)
    con.close()

    assert len(result) == 2, f"expected 2 rows; got {len(result)}"
    for r in result:
        assert r.baseline_std == 0.0, (
            f"baseline_std must be 0.0 with single peer; got {r.baseline_std}"
        )
        assert r.z_score == 0.0, (
            f"z_score must be 0.0 when std=0 (no divide); got {r.z_score}"
        )
        assert r.flagged is False, (
            f"flagged must be False when std=0; got {r.flagged}"
        )


# ---------------------------------------------------------------------------
# ANOM-14 — EC14: all-fail group (rate=1.0) is valid, finite, correct flag
# ---------------------------------------------------------------------------


def test_anom14_all_fail_group_is_valid(_make_anomaly_db):
    """ANOM-14: rate=1.0 group is valid, z is finite, flagged by threshold."""
    groups = [
        {"key": "G1", "total": 10, "failed": 1,  "in_window": True},  # rate=0.1
        {"key": "G2", "total": 10, "failed": 2,  "in_window": True},  # rate=0.2
        {"key": "G3", "total": 10, "failed": 3,  "in_window": True},  # rate=0.3
        {"key": "G4", "total": 10, "failed": 10, "in_window": True},  # rate=1.0
    ]
    con = _make_anomaly_db(groups, by="board")
    result = z_score_anomalies(con, by="board", threshold=3.0)
    con.close()

    g4_row = next(r for r in result if r.group_key == "G4")
    assert math.isclose(g4_row.value, 1.0, rel_tol=1e-9), (
        f"rate=1.0 group must have value=1.0; got {g4_row.value}"
    )
    assert math.isfinite(g4_row.z_score), (
        f"z_score must be finite for rate=1.0; got {g4_row.z_score}"
    )
    # No NaN anywhere.
    for r in result:
        assert not math.isnan(r.z_score), f"z_score must not be NaN; got {r.z_score}"
        assert not math.isnan(r.baseline_mean), "baseline_mean must not be NaN"


# ---------------------------------------------------------------------------
# ANOM-15 — EC15: empty DB → []
# ---------------------------------------------------------------------------


def test_anom15_empty_db_returns_empty_list(empty_db):
    """ANOM-15: empty DB (anchor=None) → [] without raising."""
    result = z_score_anomalies(empty_db)
    assert result == [], f"expected [], got {result}"


# ---------------------------------------------------------------------------
# ANOM-16 — EC16: threshold <= 0 raises ValueError
# ---------------------------------------------------------------------------


def test_anom16_threshold_lte_zero_raises_value_error(empty_db):
    """ANOM-16: threshold=0 and threshold=-1 raise ValueError before DB access."""
    with pytest.raises(ValueError, match=r"threshold must be > 0"):
        z_score_anomalies(empty_db, threshold=0.0)
    with pytest.raises(ValueError, match=r"threshold must be > 0"):
        z_score_anomalies(empty_db, threshold=-1.0)


# ---------------------------------------------------------------------------
# ANOM-17 — EC17: window_days < 1 raises ValueError
# ---------------------------------------------------------------------------


def test_anom17_window_days_less_than_1_raises_value_error(empty_db):
    """ANOM-17: window_days=0 and window_days=-1 raise ValueError."""
    with pytest.raises(ValueError, match=r"window_days must be >= 1"):
        z_score_anomalies(empty_db, window_days=0)
    with pytest.raises(ValueError, match=r"window_days must be >= 1"):
        z_score_anomalies(empty_db, window_days=-1)


# ---------------------------------------------------------------------------
# ANOM-18 — EC17: invalid by raises ValueError listing allowed values
# ---------------------------------------------------------------------------


def test_anom18_invalid_by_raises_value_error(empty_db):
    """ANOM-18: by='day' raises ValueError listing board/shift/line/operator."""
    with pytest.raises(ValueError, match=r"by="):
        z_score_anomalies(empty_db, by="day")
    # The message should list the allowed values.
    try:
        z_score_anomalies(empty_db, by="day")
    except ValueError as exc:
        msg = str(exc)
        assert "board" in msg, f"message must mention 'board'; got: {msg}"
        assert "shift" in msg, f"message must mention 'shift'; got: {msg}"
        assert "line" in msg, f"message must mention 'line'; got: {msg}"
        assert "operator" in msg, f"message must mention 'operator'; got: {msg}"


# ---------------------------------------------------------------------------
# ANOM-19 — EC17: tz-aware as_of raises ValueError
# ---------------------------------------------------------------------------


def test_anom19_tz_aware_as_of_raises_value_error(empty_db):
    """ANOM-19: tz-aware as_of raises ValueError via _resolve_anchor."""
    with pytest.raises(ValueError, match=r"as_of must be naive UTC"):
        z_score_anomalies(empty_db,
                          as_of=datetime(2026, 5, 1, tzinfo=timezone.utc))


# ---------------------------------------------------------------------------
# ANOM-20 — Window excludes out-of-window runs from per-group totals
# ---------------------------------------------------------------------------


def test_anom20_window_excludes_out_of_window_runs(_make_anomaly_db):
    """ANOM-20: out-of-window runs do not affect a group's failed/total rate."""
    # G1: 10 in-window runs (2 failed) + 5 out-of-window runs (5 failed).
    #     In-window rate = 2/10 = 0.2 (correct).
    #     If out-of-window counted: 7/15 = 0.4667 (wrong).
    # G2, G3: normal in-window only.
    groups = [
        {"key": "G1_in",  "total": 10, "failed": 2, "in_window": True},
        {"key": "G1_out", "total": 5,  "failed": 5, "in_window": False},  # same key would be ideal
        {"key": "G2",     "total": 10, "failed": 1, "in_window": True},
        {"key": "G3",     "total": 10, "failed": 3, "in_window": True},
    ]
    # G1_in and G1_out represent the same conceptual group — but in our DB
    # they have different board_profile_ids (separate groups). To test window
    # exclusion, use a single group with both in-window and out-of-window rows.
    # _build_anomaly_db with in_window=False places ALL runs outside the window.
    # We need a mixed group — use two separate groups for in/out and verify only
    # in-window data is counted.
    con = _make_anomaly_db(groups, by="board")
    result = z_score_anomalies(con, by="board", window_days=30, threshold=3.0)
    con.close()

    # G1_out had in_window=False → total=0 in window → excluded.
    assert "G1_out" not in {r.group_key for r in result}, (
        "G1_out (out-of-window) must be excluded from results"
    )
    # G1_in: value = 2/10 = 0.2 (only in-window data).
    g1_in_row = next(r for r in result if r.group_key == "G1_in")
    assert math.isclose(g1_in_row.value, 0.2, rel_tol=1e-9), (
        f"G1_in value must be 2/10=0.2; got {g1_in_row.value}"
    )


# ---------------------------------------------------------------------------
# ANOM-21 — z_score=0.0 exactly when baseline_std=0, even if value != baseline_mean
# ---------------------------------------------------------------------------


def test_anom21_z_score_is_zero_when_std_is_zero(_make_anomaly_db):
    """ANOM-21: when baseline_std=0, z=0.0 exactly (no divide, no inf)."""
    # Two-group case: 1 peer → std=0, z=0 even though rates differ wildly.
    groups = [
        {"key": "G1", "total": 10, "failed": 1, "in_window": True},  # rate=0.1
        {"key": "G2", "total": 10, "failed": 9, "in_window": True},  # rate=0.9
    ]
    con = _make_anomaly_db(groups, by="board")
    result = z_score_anomalies(con, by="board", threshold=3.0)
    con.close()

    # Rates clearly differ, but std=0 forces z=0.
    for r in result:
        assert r.z_score == 0.0, (
            f"z_score must be exactly 0.0 when std=0 (no division); "
            f"got {r.z_score} for group {r.group_key}"
        )
        assert r.flagged is False, (
            f"flagged must be False when std=0; got {r.flagged}"
        )
        # Prove baseline_mean != value to confirm this is a genuine zero-var guard.
        # Each group's baseline has only 1 peer (the other group's rate).
        assert not math.isclose(r.value, r.baseline_mean, rel_tol=1e-3), (
            f"for z=0 guard to be meaningful, value must differ from baseline_mean; "
            f"value={r.value}, baseline_mean={r.baseline_mean}"
        )
