"""RETR-LIVE-01..02 — real-embedder retrieval contract for short-form queries.

Default-skipped (env-gated by ``RAG_RUN_MODEL_TESTS``) because each test loads
the real ``all-MiniLM-L6-v2`` sentence-transformer (downloads on first use,
~5s warm). The offline suite stubs the embedder and so cannot catch the rank
issue that motivated DEFAULT_TOP_K — these tests pin the empirical contract
against the real model. Run locally with ``RAG_RUN_MODEL_TESTS=1 uv run pytest
tests/test_rag/test_retrieval_real.py -v``.
"""

from __future__ import annotations

import os

import pytest

from flying_probe_copilot.rag import build_retriever
from flying_probe_copilot.rag.answer import DEFAULT_TOP_K

pytestmark = pytest.mark.skipif(
    not os.environ.get("RAG_RUN_MODEL_TESTS"),
    reason="real sentence-transformers model; set RAG_RUN_MODEL_TESTS=1",
)


@pytest.fixture(scope="module")
def real_retriever():  # pragma: no cover - real model loaded only when env-gated
    """One real-embedder retriever shared across the module's tests."""
    return build_retriever("docs/knowledge-base")


def test_retr_live01_terse_cause_query_retrieves_likely_causes_chunk(
    real_retriever,
):  # pragma: no cover - real model only via RAG_RUN_MODEL_TESTS
    """RETR-LIVE-01: terse "what causes tombstoning?" must surface the per-doc
    "Likely causes" chunk under the live ``DEFAULT_TOP_K`` default.

    Empirical baseline (2026-06-21 portfolio capture): the chunk lands around
    rank 9 because its body uses generic vocabulary ("heating", "paste", "pad")
    with no topic-word anchor. Several other docs' own "Likely causes" sections
    out-rank it. DEFAULT_TOP_K was bumped from 5 to 10 specifically so this
    chunk falls inside the cut; if it ever leaks out again, the live eval will
    refuse the question and this test will FAIL fast.
    """
    target = "failure-modes/tombstoning.md#3"
    hits = real_retriever.retrieve("what causes tombstoning?", top_k=DEFAULT_TOP_K)
    ids = [h.chunk.chunk_id for h in hits]
    assert target in ids, (
        f"terse 'what causes tombstoning?' must retrieve {target!r} at "
        f"top_k={DEFAULT_TOP_K}; got {ids}"
    )


def test_retr_live02_terse_queries_retrieve_expected_doc(
    real_retriever,
):  # pragma: no cover - real model only via RAG_RUN_MODEL_TESTS
    """RETR-LIVE-02: every terse short-form eval question retrieves at least
    one chunk from its expected source doc inside ``DEFAULT_TOP_K``.

    Mirrors the live-eval citation contract at the retrieval layer — a regression
    that pushes a target doc out of the cut would silently degrade the live eval
    to a refusal, which this test surfaces without burning a model call.
    """
    cases = [
        ("what causes tombstoning?", "failure-modes/tombstoning.md"),
        ("what are shorts?", "failure-modes/shorts.md"),
        ("what are opens?", "failure-modes/opens.md"),
        ("what is a cold solder joint?", "failure-modes/cold-solder-joint.md"),
        ("what is insufficient solder?", "failure-modes/insufficient-solder.md"),
    ]
    for question, expected_doc in cases:
        hits = real_retriever.retrieve(question, top_k=DEFAULT_TOP_K)
        ids = [h.chunk.chunk_id for h in hits]
        assert any(cid.startswith(f"{expected_doc}#") for cid in ids), (
            f"terse {question!r} must retrieve >=1 chunk from {expected_doc!r} "
            f"at top_k={DEFAULT_TOP_K}; got {ids}"
        )
