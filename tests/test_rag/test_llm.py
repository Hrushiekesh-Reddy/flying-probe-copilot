"""LLM-01..LLM-05 — GeminiClient lazy construction + missing-key guard.

The live generate() path needs a real key + network and is `# pragma: no cover`
(Manual QA). These tests cover only the offline-reachable surface: construction
must not touch genai, and the missing-key guard must raise before any API call.
"""

from __future__ import annotations

import pytest

from flying_probe_copilot.rag import GeminiClient, LLMClient


def test_llm01_construct_does_not_touch_genai(monkeypatch):
    """LLM-01: constructing GeminiClient performs no genai activity (lazy)."""
    import flying_probe_copilot.rag.llm as llm

    # If genai were imported/used at construct time, this would fire.
    monkeypatch.setattr(llm, "_call_model", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("live path must not run at construct")), raising=False)
    GeminiClient()
    GeminiClient(model_name="gemini-3.5-flash", api_key="explicit")


def test_llm03_satisfies_llmclient_protocol():
    """LLM-03/04: GeminiClient is usable as an LLMClient (runtime_checkable)."""
    client = GeminiClient(api_key="x")
    assert isinstance(client, LLMClient)
    assert hasattr(client, "generate")


def test_llm05_missing_key_raises_valueerror(monkeypatch):
    """LLM-05: generate() with no key raises ValueError before any API call."""
    import flying_probe_copilot.rag.llm as llm

    # Prevent _resolve_key from reloading the real key out of the repo .env.
    monkeypatch.setattr(llm, "load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    client = GeminiClient()  # no explicit api_key
    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        client.generate("any prompt")


def test_llm05b_explicit_key_skips_env(monkeypatch):
    """LLM-05b: an explicit api_key resolves without reading env/.env."""
    import flying_probe_copilot.rag.llm as llm

    def _boom(*a, **k):  # pragma: no cover - must not be called
        raise AssertionError("load_dotenv must not run when api_key is explicit")

    monkeypatch.setattr(llm, "load_dotenv", _boom)
    monkeypatch.setattr(llm, "_call_model", lambda key, prompt, model: f"ok:{key}")
    client = GeminiClient(api_key="explicit-key")
    assert client.generate("hi") == "ok:explicit-key"
