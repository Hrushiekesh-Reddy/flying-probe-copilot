"""chat.py — Co-Pilot chat page for the Streamlit dashboard.

Renders a chat interface over the Phase 3 ``answer()`` pipeline: a question is
retrieved against the failure-mode KB and answered by Gemini, with forced
citations and refusal when ungrounded.

Testability
-----------
The live wiring (`get_retriever` / `get_client` / `answer_question`) is
`# pragma: no cover` and is patched out in offline tests: `render_chat` calls the
module-global `answer_question`, so a test monkeypatches `chat.answer_question`
to a fake returning a canned ``Answer`` — no model download, no API key.
"""

from __future__ import annotations

import streamlit as st

KB_DIR = "docs/knowledge-base"


@st.cache_resource
def get_retriever():  # pragma: no cover - builds the real embedder (network/model download)
    from flying_probe_copilot.rag import build_retriever

    return build_retriever(KB_DIR)


@st.cache_resource
def get_client():  # pragma: no cover - real Gemini client
    from flying_probe_copilot.rag import GeminiClient

    return GeminiClient()


def answer_question(question: str):  # pragma: no cover - live wiring (patched in tests)
    from flying_probe_copilot.rag import answer

    return answer(question, retriever=get_retriever(), client=get_client())


def _render_turn(turn: dict) -> None:
    """Render one chat turn (user question + assistant answer + citations)."""
    with st.chat_message("user"):
        st.markdown(turn["question"])
    with st.chat_message("assistant"):
        st.markdown(turn["answer_text"])
        citations = turn.get("citations") or []
        if citations:
            with st.expander(f"Citations ({len(citations)})"):
                for cid in citations:
                    st.markdown(f"- `{cid}`")


def render_chat() -> None:
    """Render the Co-Pilot chat page."""
    st.header("🤖 Co-Pilot")
    st.caption(
        "Ask a root-cause question about the failure-mode knowledge base. "
        "Answers cite the evidence used; ungrounded questions are refused."
    )

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    prompt = st.chat_input("Ask the co-pilot…")
    if prompt:
        try:
            ans = answer_question(prompt)
        except Exception as exc:  # graceful UX — surface, don't crash the page
            st.error(f"Co-Pilot is unavailable: {exc}")
        else:
            st.session_state.chat_history.append(
                {
                    "question": ans.question,
                    "answer_text": ans.answer_text,
                    "citations": list(ans.citations),
                    "refused": ans.refused,
                }
            )

    for turn in st.session_state.chat_history:
        _render_turn(turn)
