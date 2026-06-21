"""Phase 3 RAG package — offline hybrid retrieval (slice 1).

Public API::

    from flying_probe_copilot.rag import (
        build_retriever,
        HybridRetriever,
        Chunk,
        RetrievedChunk,
        load_kb,
        VectorIndex,
        LexicalIndex,
    )

Slice 1 covers retrieval only (ChromaDB vector + rank_bm25 lexical + reciprocal
rank fusion) over the failure-mode KB in ``docs/knowledge-base/``. LLM answer
generation and citation are slice-2 concerns.
"""

from __future__ import annotations

from .models import Chunk, RetrievedChunk
from .kb_loader import load_kb
from .lexical_index import LexicalIndex
from .vector_index import VectorIndex
from .retriever import HybridRetriever, build_retriever

__all__ = [
    "build_retriever",
    "HybridRetriever",
    "Chunk",
    "RetrievedChunk",
    "load_kb",
    "VectorIndex",
    "LexicalIndex",
]
