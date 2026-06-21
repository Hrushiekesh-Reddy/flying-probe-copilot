"""CHAT-01..CHAT-09 — AppTest headless smoke tests for the Co-Pilot chat page.

Offline: every test monkeypatches the module-global ``chat.answer_question`` to a
fake returning a canned ``Answer``, so no retriever/model/key is ever touched.
The smoke functions are self-contained (inner imports) because
``AppTest.from_function`` source-extracts only the passed function's body.
"""

from __future__ import annotations

from streamlit.testing.v1 import AppTest

from flying_probe_copilot.rag import Answer
from flying_probe_copilot.rag.answer import REFUSAL_TEXT
from flying_probe_copilot.ui import chat


def _grounded(question: str) -> Answer:
    return Answer(
        question=question,
        answer_text="Tombstoning: a chip lifts on one end during reflow.",
        citations=("failure-modes/tombstoning.md#0",),
        refused=False,
        retrieved_ids=("failure-modes/tombstoning.md#0",),
    )


def _refusal(question: str) -> Answer:
    return Answer(
        question=question,
        answer_text=REFUSAL_TEXT,
        citations=(),
        refused=True,
        retrieved_ids=(),
    )


def _smoke_chat() -> None:
    """Self-contained page runner for AppTest (inner import)."""
    from flying_probe_copilot.ui import chat as chat_mod

    chat_mod.render_chat()


def test_chat01_initial_render_no_input(monkeypatch):
    """CHAT-01: initial render — header present, no chat_message, backend not called."""
    calls = []
    monkeypatch.setattr(chat, "answer_question", lambda q: calls.append(q))
    at = AppTest.from_function(_smoke_chat).run()
    assert not at.exception
    assert any("Co-Pilot" in h.value for h in at.header)
    assert len(at.chat_message) == 0
    assert calls == []


def test_chat02_chat_input_present(monkeypatch):
    """CHAT-02: a chat_input widget is available to submit a question."""
    monkeypatch.setattr(chat, "answer_question", _grounded)
    at = AppTest.from_function(_smoke_chat).run()
    assert len(at.chat_input) >= 1


def test_chat03_grounded_submit_renders_answer_and_citation(monkeypatch):
    """CHAT-03: a grounded answer renders answer text + citation; no st.error."""
    monkeypatch.setattr(chat, "answer_question", _grounded)
    at = AppTest.from_function(_smoke_chat).run()
    at.chat_input[0].set_value("why tombstone?").run()
    assert not at.exception
    assert not at.error  # grounded path must not hit the error branch
    assert len(at.chat_message) == 2  # user + assistant
    md_text = " ".join(m.value for m in at.markdown)
    assert "Tombstoning" in md_text
    assert "failure-modes/tombstoning.md#0" in md_text


def test_chat05_refusal_renders_refusal_text(monkeypatch):
    """CHAT-05: a refusal renders REFUSAL_TEXT and no citations."""
    monkeypatch.setattr(chat, "answer_question", _refusal)
    at = AppTest.from_function(_smoke_chat).run()
    at.chat_input[0].set_value("best pizza topping?").run()
    assert not at.exception
    md_text = " ".join(m.value for m in at.markdown)
    assert REFUSAL_TEXT in md_text


def test_chat06_two_turns_accumulate_history(monkeypatch):
    """CHAT-06: two sequential submits on one AppTest yield two turns."""
    monkeypatch.setattr(chat, "answer_question", _grounded)
    at = AppTest.from_function(_smoke_chat).run()
    at.chat_input[0].set_value("q1").run()
    at.chat_input[0].set_value("q2").run()
    assert not at.exception
    assert len(at.session_state["chat_history"]) == 2
    # 2 turns x (user + assistant) = 4 chat_message blocks
    assert len(at.chat_message) == 4


def test_chat08_backend_error_is_handled_gracefully(monkeypatch):
    """CHAT-08: a backend exception renders st.error, appends no turn, no crash."""
    def _boom(question):
        raise RuntimeError("gemini down")

    monkeypatch.setattr(chat, "answer_question", _boom)
    at = AppTest.from_function(_smoke_chat).run()
    at.chat_input[0].set_value("anything").run()
    assert not at.exception  # page did not crash
    assert len(at.error) >= 1
    assert at.session_state["chat_history"] == []
