"""Data-transfer objects for the Phase 2 analytics layer.

Both dataclasses are frozen (immutable) so callers can use them as dict keys
and they survive pandas/Streamlit reshaping without losing identity.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class YieldRow:
    """One row of yield-over-time output.

    Fields
    ------
    group_key:
        The value of the grouping column (board_profile_id, shift, etc.).
        NULL operator_id is bucketed as ``"<unknown>"`` (L14) — defensive
        only; the schema is ``NOT NULL`` post-BUG-007 close.
    total:
        Count of all test_runs in the window for this group.
    passed:
        Count of test_runs where btest_status == 0 (PASS).
    yield_pct:
        ``100.0 * passed / total`` as an unrounded float (L3 / R1-C).
        Callers round at presentation time.
    """

    group_key: str
    total: int
    passed: int
    yield_pct: float


@dataclass(frozen=True)
class ParetoRow:
    """One row of failure-Pareto output.

    Fields
    ------
    key:
        The value of the grouping column (record_type, target_refdes, etc.).
    count:
        Number of failure rows in this group within the window.
    pct_of_total:
        ``100.0 * count / overall_total`` as an unrounded float (R1-C).
    cumulative_pct:
        Running sum of ``pct_of_total`` from rank 1 down to this row,
        computed over the FULL group set before ``LIMIT top_n`` is applied
        (R1-O).  Equals 100.0 only when all groups are included.
    """

    key: str
    count: int
    pct_of_total: float
    cumulative_pct: float
