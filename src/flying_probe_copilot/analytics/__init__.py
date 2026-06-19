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

from .models import AnomalyRow, ParetoRow, SPCPoint, YieldRow
from .pareto import failure_pareto
from .yield_metrics import yield_over_time
from .spc import individuals_chart
from .anomaly import z_score_anomalies

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
