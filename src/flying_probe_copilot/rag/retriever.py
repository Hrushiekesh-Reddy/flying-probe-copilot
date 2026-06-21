"""HybridRetriever — reciprocal-rank-fusion over lexical + vector retrieval.

Fusion: for each retriever's ranked list (rank base 1), a chunk accrues
``1 / (rrf_k + rank)``; the fused score is the sum across both retrievers
(equal weight). Results are sorted by fused score DESC, then ``chunk_id`` ASC
for deterministic ordering, and truncated to ``top_k``.

RRF does NOT universally rank a both-list chunk above a one-list chunk (a
one-list rank-1 chunk can beat a both-list pair at high ranks); it holds for the
low-rank regime of a small corpus (plan Revision 1, B2).
"""

from __future__ import annotations

from pathlib import Path

from .kb_loader import load_kb
from .lexical_index import LexicalIndex
from .models import Chunk, RetrievedChunk
from .vector_index import Embedder, VectorIndex


class HybridRetriever:
    """Hybrid lexical + vector retriever over a fixed set of chunks."""

    def __init__(self, chunks: list[Chunk], embedder: Embedder | None = None) -> None:
        self._chunks = list(chunks)
        self._lexical = LexicalIndex(self._chunks)
        self._vector = VectorIndex(embedder=embedder)
        self._vector.add(self._chunks)

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        rrf_k: int = 60,
    ) -> list[RetrievedChunk]:
        """Return up to ``top_k`` fused results for ``query``.

        Parameters
        ----------
        query:
            Free-text query. Empty / whitespace-only / no-match queries return ``[]``.
        top_k:
            Maximum results. ``0`` returns ``[]``; negative raises ``ValueError``.
        rrf_k:
            Reciprocal-rank-fusion constant. Must be >= 1.

        Returns
        -------
        list[RetrievedChunk]
            Sorted by fused score DESC, then ``chunk_id`` ASC.

        Raises
        ------
        ValueError
            If ``top_k < 0`` or ``rrf_k < 1``.
        """
        if top_k < 0:
            raise ValueError(f"top_k must be >= 0; received {top_k!r}")
        if rrf_k < 1:
            raise ValueError(f"rrf_k must be >= 1; received {rrf_k!r}")
        if top_k == 0 or not self._chunks:
            return []

        full = len(self._chunks)
        lexical_hits = self._lexical.search(query, top_k=full)
        vector_hits = self._vector.search(query, top_k=full)

        chunk_by_id: dict[str, Chunk] = {}
        lexical_rank: dict[str, int] = {}
        vector_rank: dict[str, int] = {}

        for rank, (chunk, _score) in enumerate(lexical_hits, start=1):
            lexical_rank[chunk.chunk_id] = rank
            chunk_by_id[chunk.chunk_id] = chunk
        for rank, (chunk, _score) in enumerate(vector_hits, start=1):
            vector_rank[chunk.chunk_id] = rank
            chunk_by_id[chunk.chunk_id] = chunk

        fused: list[RetrievedChunk] = []
        for chunk_id, chunk in chunk_by_id.items():
            l_rank = lexical_rank.get(chunk_id)
            v_rank = vector_rank.get(chunk_id)
            score = 0.0
            if l_rank is not None:
                score += 1.0 / (rrf_k + l_rank)
            if v_rank is not None:
                score += 1.0 / (rrf_k + v_rank)
            fused.append(
                RetrievedChunk(
                    chunk=chunk,
                    score=score,
                    lexical_rank=l_rank,
                    vector_rank=v_rank,
                )
            )

        fused.sort(key=lambda rc: (-rc.score, rc.chunk.chunk_id))
        return fused[:top_k]


def build_retriever(
    kb_dir: Path | str,
    *,
    embedder: Embedder | None = None,
) -> HybridRetriever:
    """Load the KB at ``kb_dir`` and return a ready :class:`HybridRetriever`.

    Propagates :class:`FileNotFoundError` / :class:`NotADirectoryError` from
    :func:`load_kb` on a bad ``kb_dir``.
    """
    chunks = load_kb(kb_dir)
    return HybridRetriever(chunks, embedder=embedder)
