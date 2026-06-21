"""Shared fixtures for tests/test_scripts/.

Defense-in-depth: strip LLM keys from the environment for every capture-script
test so no capture test can accidentally call a live API even if the shim
monkeypatch were to silently fail.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _strip_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove LLM API keys for every capture-script test."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
