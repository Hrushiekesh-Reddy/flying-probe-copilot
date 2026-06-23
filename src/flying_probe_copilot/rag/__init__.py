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

from .answer import Answer, answer
from .kb_loader import load_kb
from .lexical_index import LexicalIndex
from .llm import GeminiClient, LLMClient
from .models import Chunk, RetrievedChunk
from .retriever import HybridRetriever, build_retriever
from .vector_index import VectorIndex

__all__ = [
    # slice 1 — retrieval
    "build_retriever",
    "HybridRetriever",
    "Chunk",
    "RetrievedChunk",
    "load_kb",
    "VectorIndex",
    "LexicalIndex",
    # slice 2 — LLM answer layer
    "answer",
    "Answer",
    "GeminiClient",
    "LLMClient",
]
