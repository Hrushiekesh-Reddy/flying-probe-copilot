"""LLM client layer for the Phase 3 co-pilot.

`LLMClient` is the minimal interface the answer layer depends on — anything with
`generate(prompt: str) -> str`. Tests inject a fake; production uses
`GeminiClient`. The only code that touches the network (`_call_model`) is
`# pragma: no cover` — it requires a real key + connectivity and is exercised
only by Manual QA. Construction is lazy: no `google.genai` import and no
key read happen until `generate()` is actually called with a resolvable key.
"""

from __future__ import annotations

import os
from typing import Protocol, runtime_checkable

from dotenv import load_dotenv

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"


@runtime_checkable
class LLMClient(Protocol):
    """Anything that turns a prompt into a text completion."""

    def generate(self, prompt: str) -> str:
        ...


def _call_model(api_key: str, prompt: str, model_name: str) -> str:  # pragma: no cover - live API
    # Imported lazily so the SDK is not pulled in on every `import
    # flying_probe_copilot.rag` — keeps cold-import cheap and import-time
    # side-effect-free.
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return response.text


class GeminiClient:
    """Google Gemini-backed `LLMClient` (google-genai 1.x+)."""

    def __init__(self, model_name: str = DEFAULT_GEMINI_MODEL, api_key: str | None = None) -> None:
        self._model_name = model_name
        self._api_key = api_key

    def _resolve_key(self) -> str | None:
        if self._api_key:
            return self._api_key
        load_dotenv()
        return os.environ.get("GOOGLE_API_KEY")

    def generate(self, prompt: str) -> str:
        key = self._resolve_key()
        if not key:
            raise ValueError(
                "GOOGLE_API_KEY not set; add it to .env or pass api_key= to GeminiClient"
            )
        return _call_model(key, prompt, self._model_name)  # pragma: no cover - live API
