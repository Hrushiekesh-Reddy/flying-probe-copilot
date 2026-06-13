"""Tests for ``flying_probe_copilot.generator.profiles``.

Phase 1a Step B1 — RED phase.
"""

from __future__ import annotations

import pytest


def test_get_profile_small_returns_50_components_80_nets_120_tests():
    from flying_probe_copilot.generator.profiles import get_profile

    bp = get_profile("small")
    assert bp.component_count == 50
    assert bp.net_count == 80
    assert bp.typical_test_count == 120


def test_get_profile_medium_returns_200_components_300_nets_450_tests():
    from flying_probe_copilot.generator.profiles import get_profile

    bp = get_profile("medium")
    assert bp.component_count == 200
    assert bp.net_count == 300
    assert bp.typical_test_count == 450


def test_get_profile_large_returns_800_components_1000_nets_1600_tests():
    from flying_probe_copilot.generator.profiles import get_profile

    bp = get_profile("large")
    assert bp.component_count == 800
    assert bp.net_count == 1000
    assert bp.typical_test_count == 1600


def test_get_profile_unknown_name_raises_value_error():
    from flying_probe_copilot.generator.profiles import get_profile

    with pytest.raises(ValueError):
        get_profile("gigantic")


@pytest.mark.parametrize("name", ["small", "medium", "large"])
def test_profile_component_mix_sums_to_component_count(name):
    from flying_probe_copilot.generator.profiles import get_profile

    bp = get_profile(name)
    assert sum(bp.component_mix.values()) == bp.component_count, (
        f"{name}: mix sum {sum(bp.component_mix.values())} != component_count {bp.component_count}"
    )
