"""scripts/_capture_app.py — Streamlit shim that monkeypatches the Co-Pilot
backend then runs the real dashboard.

Loaded by capture_screenshots.py via:
    python -m streamlit run scripts/_capture_app.py

The shim replaces ``flying_probe_copilot.ui.chat.answer_question`` with
``build_canned_answer`` so the Co-Pilot page works without a live Gemini key.
The assertion below fails loudly if the rebind silently breaks (e.g., a future
refactor that changes the module import path).

FPC_CAPTURE_DRY_IMPORT=1 short-circuits the ``main()`` call so the shim can be
safely imported in tests without triggering Streamlit's runtime machinery.
"""

from __future__ import annotations

import os

from flying_probe_copilot.ui import chat as _chat
from scripts.capture_screenshots import build_canned_answer

_chat.answer_question = build_canned_answer
assert _chat.answer_question is build_canned_answer, (
    "Monkeypatch failed — chat.answer_question was not rebound. "
    "Capture would call the live Gemini path."
)

if not os.environ.get("FPC_CAPTURE_DRY_IMPORT"):
    from flying_probe_copilot.ui.app import main

    main()
