"""Canonical board profiles for the synthetic generator.

Profile sizes are per ``specs/synthetic-log-generator.md`` "Default board
profiles" section (small/medium/large = 50/200/800 components). The mix
distributions are engineering-judgment defaults representative of real PCBAs;
they sum exactly to ``component_count`` per profile so that downstream
component-instantiation code can iterate the mix and trust the totals.
"""

from __future__ import annotations

from .models import BoardProfile


# ---------------------------------------------------------------------------
# Profile registry — keyed by canonical name.
# ---------------------------------------------------------------------------


_PROFILES: dict[str, BoardProfile] = {
    "small": BoardProfile(
        id="small",
        name="small",
        component_count=50,
        net_count=80,
        typical_test_count=120,
        # R + C + U + D + L + Q = 25 + 15 + 4 + 3 + 1 + 2 = 50
        component_mix={"R": 25, "C": 15, "U": 4, "D": 3, "L": 1, "Q": 2},
    ),
    "medium": BoardProfile(
        id="medium",
        name="medium",
        component_count=200,
        net_count=300,
        typical_test_count=450,
        # 100 + 60 + 16 + 10 + 4 + 10 = 200
        component_mix={"R": 100, "C": 60, "U": 16, "D": 10, "L": 4, "Q": 10},
    ),
    "large": BoardProfile(
        id="large",
        name="large",
        component_count=800,
        net_count=1000,
        typical_test_count=1600,
        # 400 + 240 + 64 + 40 + 16 + 40 = 800
        component_mix={"R": 400, "C": 240, "U": 64, "D": 40, "L": 16, "Q": 40},
    ),
}


def get_profile(name: str) -> BoardProfile:
    """Return the canonical ``BoardProfile`` for ``name``.

    Raises ``ValueError`` for unknown names.
    """
    try:
        return _PROFILES[name]
    except KeyError as exc:
        valid = ", ".join(available_profiles())
        raise ValueError(
            f"Unknown board profile: {name!r}. Valid profiles: {valid}."
        ) from exc


_SIZE_ORDER = ["small", "medium", "large"]


def available_profiles() -> list[str]:
    """Return the names of all canonical profiles in size-ascending order.

    Order is fixed at ``small`` → ``medium`` → ``large`` (matches every doc /
    spec / CLI help quoting of the trio) rather than alphabetical. BUG-003 fix.
    """
    return [name for name in _SIZE_ORDER if name in _PROFILES]
