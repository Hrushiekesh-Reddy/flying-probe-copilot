"""Shared fixtures for tests/test_ci/.

Provides session-scoped helpers for loading workflow YAML files and pyproject.toml.
All loaded dicts are deepcopied per call to prevent cross-test mutation.
"""

from __future__ import annotations

import copy
import tomllib
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"


@pytest.fixture(scope="session")
def _workflow_dir() -> Path:
    """Return the path to .github/workflows/ — repo-root anchored."""
    return _WORKFLOW_DIR


@pytest.fixture(scope="session")
def _load_yaml():
    """Return a callable (name: str) -> dict that loads + deepcopies a workflow YAML."""
    _cache: dict[str, dict] = {}

    def _inner(name: str) -> dict:
        if name not in _cache:
            path = _WORKFLOW_DIR / name
            with open(path, encoding="utf-8") as fh:
                _cache[name] = yaml.safe_load(fh)
        return copy.deepcopy(_cache[name])

    return _inner


@pytest.fixture(scope="session")
def _load_yaml_text():
    """Return a callable (name: str) -> str that reads raw workflow YAML text."""
    _cache: dict[str, str] = {}

    def _inner(name: str) -> str:
        if name not in _cache:
            path = _WORKFLOW_DIR / name
            with open(path, encoding="utf-8") as fh:
                _cache[name] = fh.read()
        return _cache[name]

    return _inner


@pytest.fixture(scope="session")
def _pyproject() -> dict:
    """Load pyproject.toml once per session and return a deepcopy."""
    with open(REPO_ROOT / "pyproject.toml", "rb") as fh:
        return copy.deepcopy(tomllib.load(fh))
