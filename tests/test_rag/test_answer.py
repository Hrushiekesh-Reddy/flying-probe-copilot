"""ANS-01..ANS-30 — answer() grounding, anti-hallucination, robustness.

All offline: hits come from a StubRetriever (or the real retriever + fake
embedder for the e2e case), and the LLM is a FakeLLMClient / RaisingLLMClient.
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from flying_probe_copilot.rag import Answer, Chunk, RetrievedChunk, answer, build_retriever
from flying_probe_copilot.rag.answer import DEFAULT_TOP_K, REFUSAL_TEXT
from tests.test_rag.conftest import FakeLLMClient, RaisingLLMClient, StubRetriever


def _hit(cid: str, text: str = "body") -> RetrievedChunk:
    chunk = Chunk(
        chunk_id=cid,
        doc_id=cid.split("#")[0],
        source_path=cid.split("#")[0],
        heading="H",
        text=text,
        ordinal=0,
    )
    return RetrievedChunk(chunk=chunk, score=1.0, lexical_rank=1, vector_rank=1)


def _json(**kw) -> str:
    return json.dumps(kw)


# --- grounded happy path ----------------------------------------------------


def test_ans01_grounded_answer_with_valid_citation():
    """ANS-01: sufficient + valid citation + answer -> grounded Answer."""
    r = StubRetriever([_hit("a.md#0")])
    c = FakeLLMClient(_json(answer="Opens are missing connections.", citations=["a.md#0"], sufficient=True))
    out = answer("why open?", retriever=r, client=c)
    assert out.refused is False
    assert out.answer_text == "Opens are missing connections."
    assert out.citations == ("a.md#0",)
    assert out.retrieved_ids == ("a.md#0",)
    assert out.question == "why open?"


def test_ans02_multiple_citations_in_retrieval_order():
    """ANS-02: citations returned in retrieval order, deduped."""
    r = StubRetriever([_hit("a.md#0"), _hit("b.md#0")])
    # Model lists them out of order; output must follow retrieval order.
    c = FakeLLMClient(_json(answer="x", citations=["b.md#0", "a.md#0"], sufficient=True))
    out = answer("q", retriever=r, client=c)
    assert out.refused is False
    assert out.citations == ("a.md#0", "b.md#0")


# --- anti-hallucination / refusal ------------------------------------------


def test_ans04_blank_question_refuses_without_calling_client():
    """ANS-04: empty question refuses; client never called."""
    out = answer("", retriever=StubRetriever([_hit("a.md#0")]), client=RaisingLLMClient())
    assert out.refused is True
    assert out.answer_text == REFUSAL_TEXT
    assert out.citations == ()
    assert out.retrieved_ids == ()


def test_ans05_whitespace_question_refuses():
    """ANS-05: whitespace-only question treated as blank."""
    out = answer("   ", retriever=StubRetriever([_hit("a.md#0")]), client=RaisingLLMClient())
    assert out.refused is True


def test_ans05b_none_question_refuses():
    """ANS-05b: non-str question refuses, no crash."""
    out = answer(None, retriever=StubRetriever([_hit("a.md#0")]), client=RaisingLLMClient())  # type: ignore[arg-type]
    assert out.refused is True


def test_ans06_no_hits_refuses_without_calling_client():
    """ANS-06: empty retrieval refuses; client never called (anti-hallucination)."""
    out = answer("q", retriever=StubRetriever([]), client=RaisingLLMClient())
    assert out.refused is True
    assert out.citations == ()
    assert out.retrieved_ids == ()


def test_ans07_model_insufficient_refuses():
    """ANS-07: sufficient=false refuses; client called once; citations empty."""
    r = StubRetriever([_hit("a.md#0")])
    c = FakeLLMClient(_json(answer="maybe", citations=["a.md#0"], sufficient=False))
    out = answer("q", retriever=r, client=c)
    assert out.refused is True
    assert c.call_count == 1
    assert out.citations == ()


def test_ans08_hallucinated_citation_dropped():
    """ANS-08: a non-retrieved citation is dropped; real one kept."""
    r = StubRetriever([_hit("a.md#0")])
    c = FakeLLMClient(_json(answer="x", citations=["a.md#0", "ghost.md#9"], sufficient=True))
    out = answer("q", retriever=r, client=c)
    assert out.refused is False
    assert out.citations == ("a.md#0",)


def test_ans09_all_citations_hallucinated_refuses():
    """ANS-09: if no cited id was retrieved, refuse (ungrounded)."""
    r = StubRetriever([_hit("a.md#0")])
    c = FakeLLMClient(_json(answer="x", citations=["ghost.md#9"], sufficient=True))
    out = answer("q", retriever=r, client=c)
    assert out.refused is True
    assert out.citations == ()


def test_ans11_empty_citations_refuses():
    """ANS-11: sufficient but zero citations -> refuse (ungrounded)."""
    r = StubRetriever([_hit("a.md#0")])
    c = FakeLLMClient(_json(answer="x", citations=[], sufficient=True))
    out = answer("q", retriever=r, client=c)
    assert out.refused is True


# --- defensive JSON parsing -------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        "I cannot comply",          # ANS-12 non-JSON
        "",                          # ANS-13 empty
        "[1, 2, 3]",                # ANS-14 valid JSON wrong shape
        json.dumps({"citations": ["a.md#0"], "sufficient": True}),  # ANS-15 missing answer
        json.dumps({"answer": "x", "citations": ["a.md#0"]}),       # ANS-17 missing sufficient
        json.dumps({"answer": "x", "citations": "a.md#0", "sufficient": True}),  # ANS-18 not a list
        json.dumps({"answer": "", "citations": ["a.md#0"], "sufficient": True}), # ANS-22 empty answer
        json.dumps({"answer": "x", "citations": ["a.md#0"], "sufficient": "yes"}),  # ANS-21 non-bool
    ],
)
def test_ans12_malformed_or_ungrounded_json_refuses(raw):
    """ANS-12..22: malformed / wrong-shape / non-strict-sufficient -> refuse, no crash."""
    r = StubRetriever([_hit("a.md#0")])
    out = answer("q", retriever=r, client=FakeLLMClient(raw))
    assert out.refused is True
    assert out.answer_text == REFUSAL_TEXT


def test_ans19_non_string_citation_items_ignored():
    """ANS-19: non-string citation items ignored; a valid string kept."""
    r = StubRetriever([_hit("a.md#0")])
    c = FakeLLMClient(_json(answer="x", citations=[123, None, "a.md#0"], sufficient=True))
    out = answer("q", retriever=r, client=c)
    assert out.refused is False
    assert out.citations == ("a.md#0",)


def test_ans20_duplicate_citations_deduped():
    """ANS-20: duplicate citations collapse to one."""
    r = StubRetriever([_hit("a.md#0")])
    c = FakeLLMClient(_json(answer="x", citations=["a.md#0", "a.md#0"], sufficient=True))
    out = answer("q", retriever=r, client=c)
    assert out.citations == ("a.md#0",)


# --- wiring / passthrough ---------------------------------------------------


def test_ans23_top_k_forwarded_as_keyword():
    """ANS-23: top_k is forwarded to the retriever."""
    r = StubRetriever([_hit("a.md#0")])
    answer("q", retriever=r, client=FakeLLMClient(_json(answer="x", citations=["a.md#0"], sufficient=True)), top_k=3)
    assert r.calls == [3]


def test_ans24_default_top_k_matches_module_constant():
    """ANS-24: default top_k matches the DEFAULT_TOP_K module constant.

    Asserts both the constant's value and that it flows through ``answer()``
    untouched; the test self-updates if the constant is bumped, but a regression
    that silently divorces the signature default from the constant still fails.
    """
    r = StubRetriever([_hit("a.md#0")])
    answer("q", retriever=r, client=FakeLLMClient(_json(answer="x", citations=["a.md#0"], sufficient=True)))
    assert DEFAULT_TOP_K == 10
    assert r.calls == [DEFAULT_TOP_K]


def test_ans26_client_called_once_with_prompt_containing_question():
    """ANS-26: client.generate called exactly once with a prompt containing the question."""
    r = StubRetriever([_hit("a.md#0")])
    c = FakeLLMClient(_json(answer="x", citations=["a.md#0"], sufficient=True))
    answer("why open circuit?", retriever=r, client=c)
    assert c.call_count == 1
    assert "why open circuit?" in c.prompts[0]
    assert "a.md#0" in c.prompts[0]


def test_ans27_end_to_end_with_real_retriever(write_kb, fake_embedder):
    """ANS-27: full offline pipeline over the real retriever + fake embedder."""
    kb = write_kb({"shorts.md": "# Shorts\n\nsolder bridge connects two nets\n"})
    r = build_retriever(kb, embedder=fake_embedder)
    retrieved = r.retrieve("solder bridge", top_k=5)
    cid = retrieved[0].chunk.chunk_id
    c = FakeLLMClient(_json(answer="A bridge shorts two nets.", citations=[cid], sufficient=True))
    out = answer("solder bridge", retriever=r, client=c)
    assert out.refused is False
    assert out.citations == (cid,)
    assert cid in out.retrieved_ids


# --- Answer dataclass -------------------------------------------------------


def test_ans28_answer_is_frozen():
    """ANS-28: Answer is immutable."""
    a = Answer(question="q", answer_text="x", citations=("a.md#0",), refused=False, retrieved_ids=("a.md#0",))
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.refused = True  # type: ignore[misc]


def test_ans29_answer_field_set():
    """ANS-29: Answer exposes exactly the documented fields."""
    names = {f.name for f in dataclasses.fields(Answer)}
    assert names == {"question", "answer_text", "citations", "refused", "retrieved_ids"}


def test_ans30_answer_equality_and_hashable():
    """ANS-30: equal-valued Answers compare == and are hashable (tuple fields)."""
    a1 = Answer(question="q", answer_text="x", citations=("a.md#0",), refused=False, retrieved_ids=("a.md#0",))
    a2 = Answer(question="q", answer_text="x", citations=("a.md#0",), refused=False, retrieved_ids=("a.md#0",))
    assert a1 == a2
    assert len({a1, a2}) == 1
