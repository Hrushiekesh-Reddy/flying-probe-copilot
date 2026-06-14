"""Shared pytest fixtures — repo root.

Per Revision 1 Resolution #BLOCKER-2: this file MUST NOT import from
``flying_probe_copilot.*`` at module top level. Doing so would break pytest
collection during early TDD phases when the package modules don't yet exist.
Model-dependent fixtures live in ``tests/test_generator/conftest.py`` or
inline in their test files.
"""

from __future__ import annotations

import random
from datetime import datetime

import pytest


@pytest.fixture
def seeded_random() -> random.Random:
    """A ``random.Random`` instance seeded with 42 for deterministic tests."""
    return random.Random(42)


@pytest.fixture
def small_profile_dict() -> dict:
    """Plain-dict representation of the canonical ``small`` board profile.

    Mirrors spec lines ~308-310. Tests that need a real ``BoardProfile`` model
    instance should construct it from this dict inside the test or via a
    fixture in ``tests/test_generator/conftest.py``.
    """
    return {
        "id": "small",
        "name": "small",
        "component_count": 50,
        "net_count": 80,
        "typical_test_count": 120,
        "component_mix": {"R": 25, "C": 15, "U": 4, "D": 3, "L": 1, "Q": 2},
    }


@pytest.fixture
def medium_profile_dict() -> dict:
    """Plain-dict representation of the canonical ``medium`` board profile."""
    return {
        "id": "medium",
        "name": "medium",
        "component_count": 200,
        "net_count": 300,
        "typical_test_count": 450,
        "component_mix": {"R": 100, "C": 60, "U": 16, "D": 10, "L": 4, "Q": 10},
    }


@pytest.fixture
def fixed_timestamp() -> datetime:
    """Reference timestamp for deterministic time-based tests."""
    return datetime(2026, 4, 1, 8, 30, 0)
