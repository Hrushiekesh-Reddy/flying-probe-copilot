"""API-01..API-03 — public surface of flying_probe_copilot.rag."""

from __future__ import annotations


def test_api01_core_names_importable_and_usable():
    """API-01: the five core public names import and are callable/types."""
    from flying_probe_copilot.rag import (  # noqa: F401
        Chunk,
        HybridRetriever,
        RetrievedChunk,
        build_retriever,
        load_kb,
    )

    assert callable(build_retriever)
    assert callable(load_kb)
    assert isinstance(HybridRetriever, type)
    assert isinstance(Chunk, type)
    assert isinstance(RetrievedChunk, type)


def test_api02_index_classes_importable():
    """API-02: VectorIndex and LexicalIndex are importable types."""
    from flying_probe_copilot.rag import LexicalIndex, VectorIndex

    assert isinstance(VectorIndex, type)
    assert isinstance(LexicalIndex, type)


def test_api03_all_lists_exactly_the_public_names():
    """API-03: __all__ matches the documented public contract exactly.

    Updated for slice 2 (2026-06-20): the 7 slice-1 names plus the 4 LLM-layer
    names (answer, Answer, GeminiClient, LLMClient).
    """
    from flying_probe_copilot.rag import __all__ as public_all

    assert set(public_all) == {
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
    }


def test_api04_slice2_names_importable():
    """API-04: the 4 slice-2 LLM-layer names import and are callable/types."""
    from flying_probe_copilot.rag import (  # noqa: F401
        Answer,
        GeminiClient,
        LLMClient,
        answer,
    )

    assert callable(answer)
    assert isinstance(Answer, type)
    assert isinstance(GeminiClient, type)
