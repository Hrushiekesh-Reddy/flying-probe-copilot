"""Phase 2 analytics package — yield-over-time and failure Pareto.

Public API::

    from flying_probe_copilot.analytics import (
        yield_over_time,
        failure_pareto,
        YieldRow,
        ParetoRow,
    )
"""

from __future__ import annotations

from .models import ParetoRow, YieldRow
from .pareto import failure_pareto
from .yield_metrics import yield_over_time

__all__ = ["yield_over_time", "failure_pareto", "YieldRow", "ParetoRow"]
