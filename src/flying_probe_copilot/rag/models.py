"""Data-transfer objects for the Phase 3 RAG retrieval layer.

Both dataclasses are frozen (immutable) so callers can use them as dict keys
and they survive reshaping without losing identity (mirrors the analytics layer).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    """One retrievable unit of the knowledge base.

    Fields
    ------
    chunk_id:
        Stable, deterministic identifier ``"{rel_posix_path}#{ordinal}"`` where
        the path is relative to the KB root and ordinal restarts per file.
    doc_id:
        The source document's POSIX path relative to the KB root.
    source_path:
        Same value as ``doc_id`` today; kept distinct so a future loader can
        point at an absolute or alternate location without breaking ``doc_id``.
    heading:
        The ATX heading text of the section this chunk came from. ``""`` for a
        pre-heading preamble or a heading-less file.
    text:
        The chunk's text (heading line + body, or a sub-slice for oversized
        sections).
    ordinal:
        Zero-based position of this chunk within its source document.
    """

    chunk_id: str
    doc_id: str
    source_path: str
    heading: str
    text: str
    ordinal: int


@dataclass(frozen=True)
class RetrievedChunk:
    """One ranked retrieval result.

    Fields
    ------
    chunk:
        The retrieved :class:`Chunk`.
    score:
        Fused reciprocal-rank-fusion score (higher = more relevant).
    lexical_rank:
        1-based rank in the lexical (BM25) result list, or ``None`` if the
        chunk did not appear there.
    vector_rank:
        1-based rank in the vector result list, or ``None`` if the chunk did
        not appear there.
    """

    chunk: Chunk
    score: float
    lexical_rank: int | None
    vector_rank: int | None
