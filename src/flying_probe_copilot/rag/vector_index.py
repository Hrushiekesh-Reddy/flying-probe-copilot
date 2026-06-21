"""VectorIndex — ChromaDB vector retrieval with an injectable embedder.

The collection uses cosine space (``hnsw:space="cosine"``) so similarity orders
by direction, not magnitude (plan Revision 1, B1). Embeddings are computed by an
injected :class:`Embedder` and passed to Chroma explicitly, so Chroma never
loads its own embedding model. The default production embedder
(:class:`SentenceTransformerEmbedder`) is lazy: the SentenceTransformer model is
imported and loaded only on first embed when no embedder is injected — the unit
suite injects a deterministic fake embedder and never touches it.

All-zero embeddings (no recognised content under the embedder) are skipped on
``add`` and short-circuit ``search`` to ``[]`` — they are not rankable under
cosine (plan Revision 1, W4 / G8).
"""

from __future__ import annotations

import uuid
from typing import Protocol

import chromadb

from .lexical_index import _tokenize
from .models import Chunk

DEFAULT_MODEL = "all-MiniLM-L6-v2"

# Lazy handle to the SentenceTransformer class — imported only when the default
# embedder actually loads a model. Tests monkeypatch this symbol to assert it is
# never invoked offline.
SentenceTransformer = None


class Embedder(Protocol):
    """Anything that turns texts into fixed-length float vectors."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


def _load_sentence_transformer(model_name: str):  # pragma: no cover - needs download
    global SentenceTransformer
    if SentenceTransformer is None:
        from sentence_transformers import SentenceTransformer as _ST

        SentenceTransformer = _ST
    return SentenceTransformer(model_name)


class SentenceTransformerEmbedder:
    """Default production embedder backed by sentence-transformers (lazy load)."""

    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:  # pragma: no cover - default path
        self._model_name = model_name
        self._model = None

    def embed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover - needs download
        if self._model is None:
            self._model = _load_sentence_transformer(self._model_name)
        vectors = self._model.encode(list(texts), normalize_embeddings=True)
        return [[float(x) for x in row] for row in vectors]


def _is_zero(vec: list[float]) -> bool:
    return not any(vec)


class VectorIndex:
    """In-memory ChromaDB vector index over KB chunks."""

    def __init__(self, embedder: Embedder | None = None) -> None:
        self._embedder = embedder
        self._client = chromadb.EphemeralClient()
        # Unique name per instance: EphemeralClient shares process-level state,
        # so a fixed name would collide across indexes in one test run.
        self._collection = self._client.create_collection(
            name=f"kb_{uuid.uuid4().hex}", metadata={"hnsw:space": "cosine"}
        )
        self._by_id: dict[str, Chunk] = {}

    def _get_embedder(self) -> Embedder:
        if self._embedder is None:
            self._embedder = SentenceTransformerEmbedder()  # pragma: no cover - default path
        return self._embedder

    def add(self, chunks: list[Chunk]) -> None:
        """Embed and upsert chunks. All-zero embeddings are skipped."""
        if not chunks:
            return
        embeddings = self._get_embedder().embed([c.text for c in chunks])

        ids: list[str] = []
        vecs: list[list[float]] = []
        docs: list[str] = []
        for chunk, vec in zip(chunks, embeddings):
            if _is_zero(vec):
                continue
            ids.append(chunk.chunk_id)
            vecs.append(vec)
            docs.append(chunk.text)
            self._by_id[chunk.chunk_id] = chunk

        if ids:
            self._collection.upsert(ids=ids, embeddings=vecs, documents=docs)

    def search(self, query: str, top_k: int) -> list[tuple[Chunk, float]]:
        """Return up to ``top_k`` ``(chunk, similarity)`` nearest the query.

        Parameters
        ----------
        query:
            Free-text query. Empty / whitespace-only / zero-vector queries
            return ``[]``.
        top_k:
            Maximum results. ``0`` returns ``[]``; negative raises ``ValueError``.

        Returns
        -------
        list[tuple[Chunk, float]]
            Chunks ordered nearest-first, similarity = ``1 - cosine_distance``.

        Raises
        ------
        ValueError
            If ``top_k < 0``.
        """
        if top_k < 0:
            raise ValueError(f"top_k must be >= 0; received {top_k!r}")
        count = self._collection.count()
        if top_k == 0 or count == 0:
            return []
        if not _tokenize(query):
            return []

        query_vec = self._get_embedder().embed([query])[0]
        if _is_zero(query_vec):
            return []

        n = min(top_k, count)
        res = self._collection.query(query_embeddings=[query_vec], n_results=n)
        ids = res["ids"][0]
        distances = res["distances"][0]

        results: list[tuple[Chunk, float]] = []
        for chunk_id, dist in zip(ids, distances):
            chunk = self._by_id.get(chunk_id)
            if chunk is not None:
                results.append((chunk, 1.0 - float(dist)))
        return results
