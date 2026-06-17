"""Public API smoke tests — Phase 2 Analytics.

A-01: Import + callability.
A-02: YieldRow dataclass schema matches L9.
A-03: ParetoRow dataclass schema matches L10.
"""

from __future__ import annotations

import dataclasses


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
    """A-02: YieldRow exposes exactly the 5 fields defined in L9, frozen=True."""
    from flying_probe_copilot.analytics import YieldRow

    fields = {f.name: f for f in dataclasses.fields(YieldRow)}

    expected = {"group_key", "total", "passed", "yield_pct", "placeholder_fields"}
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
    row = YieldRow(group_key="small", total=5, passed=4, yield_pct=80.0, placeholder_fields=())
    try:
        row.group_key = "other"  # type: ignore[misc]
        raise AssertionError("YieldRow must be frozen (immutable)")
    except dataclasses.FrozenInstanceError:
        pass


def test_pareto_row_dataclass_shape():
    """A-03: ParetoRow exposes exactly the 5 fields defined in L10, frozen=True."""
    from flying_probe_copilot.analytics import ParetoRow

    fields = {f.name: f for f in dataclasses.fields(ParetoRow)}

    expected = {"key", "count", "pct_of_total", "cumulative_pct", "placeholder_fields"}
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
    row = ParetoRow(key="A-RES", count=10, pct_of_total=50.0, cumulative_pct=50.0, placeholder_fields=())
    try:
        row.key = "other"  # type: ignore[misc]
        raise AssertionError("ParetoRow must be frozen (immutable)")
    except dataclasses.FrozenInstanceError:
        pass
