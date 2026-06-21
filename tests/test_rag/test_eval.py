"""DATA-01..06, EVAL-01..06 — Phase 3 10-question evaluation.

Offline: each question is driven through ``answer()`` with a StubRetriever
returning a hit for the expected doc + a FakeLLMClient citing it, proving the
citation-pattern pipeline deterministically. The live ≥8/10 accuracy test is
env-gated (``RAG_RUN_LLM_EVAL``) and default-skipped — it needs the real model
+ key and is the Phase 3 exit-criterion measurement.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from flying_probe_copilot.rag import Chunk, RetrievedChunk, answer
from flying_probe_copilot.rag.answer import REFUSAL_TEXT
from tests.test_rag.conftest import FakeLLMClient, RaisingLLMClient, StubRetriever
from tests.test_rag.eval_dataset import EVAL_QUESTIONS

KB_ROOT = Path(__file__).resolve().parents[2] / "docs" / "knowledge-base"


def _hit(chunk_id: str) -> RetrievedChunk:
    chunk = Chunk(
        chunk_id=chunk_id,
        doc_id=chunk_id.split("#")[0],
        source_path=chunk_id.split("#")[0],
        heading="H",
        text="evidence body",
        ordinal=0,
    )
    return RetrievedChunk(chunk=chunk, score=1.0, lexical_rank=1, vector_rank=1)


# --- dataset integrity ------------------------------------------------------


def test_data01_exactly_ten_questions():
    """DATA-01: the eval set has exactly 10 entries."""
    assert len(EVAL_QUESTIONS) == 10


def test_data02_pairs_are_nonempty_str():
    """DATA-02: each entry is a (question, expected_doc) of non-empty strings."""
    for q, doc in EVAL_QUESTIONS:
        assert isinstance(q, str) and q.strip()
        assert isinstance(doc, str) and doc.strip()


def test_data03_expected_docs_exist():
    """DATA-03: every expected_doc is a real file under docs/knowledge-base/."""
    for _q, doc in EVAL_QUESTIONS:
        assert (KB_ROOT / doc).is_file(), f"missing KB doc: {doc}"


def test_data04_questions_are_distinct():
    """DATA-04: no duplicate questions (case/space-insensitive)."""
    norm = [q.strip().casefold() for q, _ in EVAL_QUESTIONS]
    assert len(set(norm)) == len(norm)


def test_data05_all_eight_docs_covered():
    """DATA-05: the dataset spans all 8 seeded failure-mode docs."""
    docs = {doc for _q, doc in EVAL_QUESTIONS}
    on_disk = {f"failure-modes/{p.name}" for p in (KB_ROOT / "failure-modes").glob("*.md")}
    assert docs == on_disk


# --- offline citation-pattern ----------------------------------------------


@pytest.mark.parametrize("question,expected_doc", EVAL_QUESTIONS)
def test_eval01_offline_citation_pattern(question, expected_doc):
    """EVAL-01: each question yields a non-refused answer citing the expected doc."""
    cid = f"{expected_doc}#0"
    retriever = StubRetriever([_hit(cid)])
    client = FakeLLMClient(
        json.dumps({"answer": "grounded answer", "citations": [cid], "sufficient": True})
    )
    out = answer(question, retriever=retriever, client=client)
    assert out.refused is False
    assert out.answer_text.strip()
    assert cid in out.citations


def test_eval02_citation_must_be_retrieved():
    """EVAL-02: a model citing a non-retrieved doc is refused (grounding, not echo)."""
    retriever = StubRetriever([_hit("failure-modes/opens.md#0")])
    client = FakeLLMClient(
        json.dumps({"answer": "x", "citations": ["failure-modes/ghost.md#0"], "sufficient": True})
    )
    out = answer("why open?", retriever=retriever, client=client)
    assert out.refused is True


def test_eval03_off_domain_refuses_without_llm():
    """EVAL-03: an off-domain question (no hits) refuses without calling the LLM."""
    out = answer("what is the best pizza topping?", retriever=StubRetriever([]), client=RaisingLLMClient())
    assert out.refused is True
    assert out.answer_text == REFUSAL_TEXT
    assert out.citations == ()


# --- live accuracy harness (env-gated, default-skipped) ---------------------


@pytest.mark.skipif(
    not os.environ.get("RAG_RUN_LLM_EVAL"),
    reason="live LLM eval; set RAG_RUN_LLM_EVAL=1 (needs GOOGLE_API_KEY + network)",
)
def test_eval_live_at_least_8_of_10():  # pragma: no cover - live model + network
    """EVAL exit criterion: ≥8/10 questions cite the expected source doc (real Gemini)."""
    from flying_probe_copilot.rag import GeminiClient, build_retriever

    retriever = build_retriever("docs/knowledge-base")
    client = GeminiClient()
    correct = 0
    for question, expected_doc in EVAL_QUESTIONS:
        out = answer(question, retriever=retriever, client=client)
        if not out.refused and any(c.startswith(expected_doc) for c in out.citations):
            correct += 1
    assert correct >= 8, f"only {correct}/10 cited the expected doc"
