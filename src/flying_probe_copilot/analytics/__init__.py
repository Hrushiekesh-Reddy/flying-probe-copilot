"""Phase 2 analytics package — yield-over-time, failure Pareto, SPC, anomaly.

Public API::

    from flying_probe_copilot.analytics import (
        yield_over_time,
        failure_pareto,
        individuals_chart,
        z_score_anomalies,
        YieldRow,
        ParetoRow,
        SPCPoint,
        AnomalyRow,
    )
"""

from __future__ import annotations

from .anomaly import z_score_anomalies
from .models import AnomalyRow, ParetoRow, SPCPoint, YieldRow
from .pareto import failure_pareto
from .spc import individuals_chart
from .yield_metrics import yield_over_time

__all__ = [
    "yield_over_time",
    "failure_pareto",
    "individuals_chart",
    "z_score_anomalies",
    "YieldRow",
    "ParetoRow",
    "SPCPoint",
    "AnomalyRow",
]
