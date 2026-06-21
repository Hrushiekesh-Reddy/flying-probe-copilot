"""Shared fixtures for tests/test_ui/.

``ui_db_path`` is now defined in ``tests/conftest.py`` (lifted in Phase 4
slice 2, MD-3) so it is accessible to both ``tests/test_ui/`` and
``tests/test_scripts/``.  This file retains only the ``_strip_llm_env`` autouse
fixture, which is test_ui-specific (no other suite needs LLM key stripping).
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Offline guard: no real LLM key is visible to any UI test (chat page included)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _strip_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove LLM keys for every UI test so the chat page cannot call a live API."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
