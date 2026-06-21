"""LexicalIndex — BM25 lexical retrieval over KB chunks.

A chunk is a *candidate* for a query iff it shares at least one query token
(token-overlap test), independent of the BM25 score sign: rank_bm25 returns
negative scores for terms present in the only/most documents, so score > 0 is
NOT a valid match test (see plan Revision 1, B3). Candidates are ranked by BM25
score (descending), tie-broken by chunk_id ascending for determinism.
"""

from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

from .models import Chunk

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    """Lowercase and split on non-alphanumeric (Unicode ``\\w``) boundaries."""
    return _TOKEN_RE.findall(text.lower())


class LexicalIndex:
    """rank_bm25 lexical index over a list of :class:`Chunk`."""

    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = list(chunks)
        self._tokens: list[list[str]] = [_tokenize(c.text) for c in self._chunks]
        self._token_sets: list[set[str]] = [set(t) for t in self._tokens]
        # BM25Okapi raises on an empty corpus; build lazily only when populated.
        self._bm25 = BM25Okapi(self._tokens) if self._tokens else None

    def search(self, query: str, top_k: int) -> list[tuple[Chunk, float]]:
        """Return up to ``top_k`` ``(chunk, score)`` ranked by BM25 score DESC.

        Parameters
        ----------
        query:
            Free-text query. Empty / whitespace-only queries return ``[]``.
        top_k:
            Maximum results. ``0`` returns ``[]``; negative raises ``ValueError``.

        Returns
        -------
        list[tuple[Chunk, float]]
            Candidate chunks (sharing >= 1 query token) ranked by score DESC,
            chunk_id ASC. ``[]`` when nothing matches or the index is empty.

        Raises
        ------
        ValueError
            If ``top_k < 0``.
        """
        if top_k < 0:
            raise ValueError(f"top_k must be >= 0; received {top_k!r}")
        if top_k == 0 or self._bm25 is None:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        query_set = set(query_tokens)
        scores = self._bm25.get_scores(query_tokens)

        candidates = [
            (self._chunks[i], float(scores[i]))
            for i in range(len(self._chunks))
            if self._token_sets[i] & query_set
        ]
        if not candidates:
            return []

        candidates.sort(key=lambda cs: (-cs[1], cs[0].chunk_id))
        return candidates[:top_k]
