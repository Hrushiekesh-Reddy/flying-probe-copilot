"""answer() — grounded, citation-forced Q&A with strict anti-hallucination.

The orchestrator retrieves evidence (slice 1), prompts the LLM, then validates
the response. A non-refused `Answer` requires ALL of: retrieval hits, a valid
JSON object, ``sufficient is True``, a non-empty answer, and at least one
citation that was actually retrieved. Any failure → refuse with `REFUSAL_TEXT`
and empty citations. The LLM is never called when there is nothing to ground on
(blank question or no hits).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from .llm import LLMClient
from .prompts import build_answer_prompt

REFUSAL_TEXT = (
    "I don't have enough grounded evidence in the knowledge base to answer that."
)


@dataclass(frozen=True)
class Answer:
    """Result of a grounded answer attempt.

    Fields
    ------
    question:
        The original question.
    answer_text:
        The grounded answer, or ``REFUSAL_TEXT`` when refused.
    citations:
        chunk_ids actually used, in retrieval order, de-duplicated. ``()`` on refusal.
    refused:
        ``True`` when no grounded answer could be produced.
    retrieved_ids:
        chunk_ids returned by the retriever for this question (``()`` when none).
    """

    question: str
    answer_text: str
    citations: tuple[str, ...]
    refused: bool
    retrieved_ids: tuple[str, ...]


def _refuse(question: str, retrieved_ids: tuple[str, ...]) -> Answer:
    return Answer(
        question=question,
        answer_text=REFUSAL_TEXT,
        citations=(),
        refused=True,
        retrieved_ids=retrieved_ids,
    )


def _parse(raw: str) -> dict | None:
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def answer(question, *, retriever, client: LLMClient, top_k: int = 5) -> Answer:
    """Answer ``question`` grounded in retrieved KB evidence, or refuse.

    Parameters
    ----------
    question:
        The engineer's natural-language question.
    retriever:
        A retriever exposing ``retrieve(query, *, top_k) -> list[RetrievedChunk]``.
    client:
        An :class:`LLMClient`. Not called on the blank-question or no-hits paths.
    top_k:
        Forwarded to the retriever (``0`` → no hits → refuse; ``<0`` → the
        retriever raises ``ValueError``).
    """
    if not isinstance(question, str) or not question.strip():
        return _refuse(question if isinstance(question, str) else "", ())

    hits = retriever.retrieve(question, top_k=top_k)
    retrieved_ids = tuple(rc.chunk.chunk_id for rc in hits)
    if not hits:
        return _refuse(question, ())

    prompt = build_answer_prompt(question, [rc.chunk for rc in hits])
    data = _parse(client.generate(prompt))
    if data is None:
        return _refuse(question, retrieved_ids)

    if data.get("sufficient") is not True:
        return _refuse(question, retrieved_ids)

    answer_text = data.get("answer")
    if not isinstance(answer_text, str) or not answer_text.strip():
        return _refuse(question, retrieved_ids)

    cited = data.get("citations")
    if not isinstance(cited, list):
        cited = []
    valid = {c for c in cited if isinstance(c, str) and c in set(retrieved_ids)}
    # Retrieval order, de-duplicated.
    ordered = tuple(cid for cid in retrieved_ids if cid in valid)
    if not ordered:
        return _refuse(question, retrieved_ids)

    return Answer(
        question=question,
        answer_text=answer_text,
        citations=ordered,
        refused=False,
        retrieved_ids=retrieved_ids,
    )
