"""Public API smoke tests — Phase 2 Analytics.

Slice 1 (A-01..A-03):
  A-01: Import + callability (yield_over_time, failure_pareto).
  A-02: YieldRow dataclass schema matches L9.
  A-03: ParetoRow dataclass schema matches L10.

Slice 2 additions (API-01..API-04):
  API-01: individuals_chart, z_score_anomalies, SPCPoint, AnomalyRow importable + callable.
  API-02: SPCPoint dataclass field set + types + frozen (L6).
  API-03: AnomalyRow dataclass field set + types + frozen + no placeholder_fields (L9).
  API-04: Regression guard — neither new dataclass reintroduces placeholder_fields.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime


def test_public_api_importable():
    """A-01: All four public names import from the analytics package."""
    from flying_probe_copilot.analytics import (  # noqa: F401
        ParetoRow,
        YieldRow,
        failure_pareto,
        yield_over_time,
    )

    assert callable(yield_over_time), "yield_over_time must be callable"
    assert callable(failure_pareto), "failure_pareto must be callable"
    assert isinstance(YieldRow, type), "YieldRow must be a type"
    assert isinstance(ParetoRow, type), "ParetoRow must be a type"


def test_yield_row_dataclass_shape():
    """A-02: YieldRow exposes exactly the 4 fields defined in L9, frozen=True."""
    from flying_probe_copilot.analytics import YieldRow

    fields = {f.name: f for f in dataclasses.fields(YieldRow)}

    expected = {"group_key", "total", "passed", "yield_pct"}
    assert set(fields) == expected, (
        f"YieldRow field set mismatch: expected {expected}, got {set(fields)}"
    )

    # Type annotations
    hints = YieldRow.__dataclass_fields__
    assert hints["group_key"].type in (str, "str"), "group_key must be str"
    assert hints["total"].type in (int, "int"), "total must be int"
    assert hints["passed"].type in (int, "int"), "passed must be int"
    assert hints["yield_pct"].type in (float, "float"), "yield_pct must be float"

    # frozen=True check — assigning to a field should raise FrozenInstanceError
    row = YieldRow(group_key="small", total=5, passed=4, yield_pct=80.0)
    try:
        row.group_key = "other"  # type: ignore[misc]
        raise AssertionError("YieldRow must be frozen (immutable)")
    except dataclasses.FrozenInstanceError:
        pass


def test_pareto_row_dataclass_shape():
    """A-03: ParetoRow exposes exactly the 4 fields defined in L10, frozen=True."""
    from flying_probe_copilot.analytics import ParetoRow

    fields = {f.name: f for f in dataclasses.fields(ParetoRow)}

    expected = {"key", "count", "pct_of_total", "cumulative_pct"}
    assert set(fields) == expected, (
        f"ParetoRow field set mismatch: expected {expected}, got {set(fields)}"
    )

    # Type annotations
    hints = ParetoRow.__dataclass_fields__
    assert hints["key"].type in (str, "str"), "key must be str"
    assert hints["count"].type in (int, "int"), "count must be int"
    assert hints["pct_of_total"].type in (float, "float"), "pct_of_total must be float"
    assert hints["cumulative_pct"].type in (float, "float"), "cumulative_pct must be float"

    # frozen=True check
    row = ParetoRow(key="A-RES", count=10, pct_of_total=50.0, cumulative_pct=50.0)
    try:
        row.key = "other"  # type: ignore[misc]
        raise AssertionError("ParetoRow must be frozen (immutable)")
    except dataclasses.FrozenInstanceError:
        pass


# ---------------------------------------------------------------------------
# API-01 — Slice 2 public names importable and callable
# ---------------------------------------------------------------------------


def test_api01_slice2_public_names_importable():
    """API-01: individuals_chart, z_score_anomalies, SPCPoint, AnomalyRow are public."""
    from flying_probe_copilot.analytics import (  # noqa: F401
        AnomalyRow,
        SPCPoint,
        individuals_chart,
        z_score_anomalies,
    )
    from flying_probe_copilot.analytics import __all__ as public_all

    assert callable(individuals_chart), "individuals_chart must be callable"
    assert callable(z_score_anomalies), "z_score_anomalies must be callable"
    assert isinstance(SPCPoint, type), "SPCPoint must be a type"
    assert isinstance(AnomalyRow, type), "AnomalyRow must be a type"

    # All four must appear in __all__.
    assert "individuals_chart" in public_all, "individuals_chart must be in __all__"
    assert "z_score_anomalies" in public_all, "z_score_anomalies must be in __all__"
    assert "SPCPoint" in public_all, "SPCPoint must be in __all__"
    assert "AnomalyRow" in public_all, "AnomalyRow must be in __all__"


# ---------------------------------------------------------------------------
# API-02 — SPCPoint dataclass field set, types, frozen=True (L6)
# ---------------------------------------------------------------------------


def test_api02_spc_point_dataclass_shape():
    """API-02: SPCPoint has exactly the L6 fields, correct types, frozen=True."""
    from flying_probe_copilot.analytics import SPCPoint

    fields = {f.name: f for f in dataclasses.fields(SPCPoint)}
    expected = {"panel_serial", "start_ts", "value", "mean", "ucl", "lcl", "alarm_flags"}
    assert set(fields) == expected, (
        f"SPCPoint field set mismatch: expected {expected}, got {set(fields)}"
    )

    hints = SPCPoint.__dataclass_fields__
    assert hints["panel_serial"].type in (str, "str"), "panel_serial must be str"
    assert hints["start_ts"].type in (datetime, "datetime"), "start_ts must be datetime"
    assert hints["value"].type in (float, "float"), "value must be float"
    assert hints["mean"].type in (float, "float"), "mean must be float"
    assert hints["ucl"].type in (float, "float"), "ucl must be float"
    assert hints["lcl"].type in (float, "float"), "lcl must be float"

    # frozen=True: assigning to a field must raise FrozenInstanceError.
    ts = datetime(2026, 4, 14, 10, 0, 0)
    row = SPCPoint(
        panel_serial="SPC-001", start_ts=ts, value=1.0, mean=1.0, ucl=2.0, lcl=0.0, alarm_flags=()
    )
    try:
        row.value = 99.0  # type: ignore[misc]
        raise AssertionError("SPCPoint must be frozen (immutable)")
    except dataclasses.FrozenInstanceError:
        pass


# ---------------------------------------------------------------------------
# API-03 — AnomalyRow dataclass field set, types, frozen=True, no placeholder_fields
# ---------------------------------------------------------------------------


def test_api03_anomaly_row_dataclass_shape():
    """API-03: AnomalyRow has exactly the L9 fields + no placeholder_fields."""
    from flying_probe_copilot.analytics import AnomalyRow

    fields = {f.name: f for f in dataclasses.fields(AnomalyRow)}
    expected = {"group_key", "value", "baseline_mean", "baseline_std", "z_score", "flagged"}
    assert set(fields) == expected, (
        f"AnomalyRow field set mismatch: expected {expected}, got {set(fields)}"
    )

    # Regression guard: placeholder_fields must NOT be present (removed 2026-06-18).
    assert "placeholder_fields" not in fields, "AnomalyRow must not reintroduce placeholder_fields"

    hints = AnomalyRow.__dataclass_fields__
    assert hints["group_key"].type in (str, "str"), "group_key must be str"
    assert hints["value"].type in (float, "float"), "value must be float"
    assert hints["baseline_mean"].type in (float, "float"), "baseline_mean must be float"
    assert hints["baseline_std"].type in (float, "float"), "baseline_std must be float"
    assert hints["z_score"].type in (float, "float"), "z_score must be float"
    assert hints["flagged"].type in (bool, "bool"), "flagged must be bool"

    # frozen=True.
    row = AnomalyRow(
        group_key="G1", value=0.5, baseline_mean=0.2, baseline_std=0.1, z_score=3.0, flagged=True
    )
    try:
        row.z_score = 99.0  # type: ignore[misc]
        raise AssertionError("AnomalyRow must be frozen (immutable)")
    except dataclasses.FrozenInstanceError:
        pass


# ---------------------------------------------------------------------------
# API-04 — Regression guard: neither new dataclass reintroduces placeholder_fields
# ---------------------------------------------------------------------------


def test_api04_no_placeholder_fields_regression():
    """API-04: neither SPCPoint nor AnomalyRow has placeholder_fields (2026-06-18 removal)."""
    from flying_probe_copilot.analytics import AnomalyRow, SPCPoint

    spc_field_names = {f.name for f in dataclasses.fields(SPCPoint)}
    anomaly_field_names = {f.name for f in dataclasses.fields(AnomalyRow)}

    assert "placeholder_fields" not in spc_field_names, (
        "SPCPoint must not contain placeholder_fields"
    )
    assert "placeholder_fields" not in anomaly_field_names, (
        "AnomalyRow must not contain placeholder_fields"
    )
