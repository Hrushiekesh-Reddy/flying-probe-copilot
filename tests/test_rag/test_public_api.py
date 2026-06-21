"""API-01..API-03 — public surface of flying_probe_copilot.rag."""

from __future__ import annotations


def test_api01_core_names_importable_and_usable():
    """API-01: the five core public names import and are callable/types."""
    from flying_probe_copilot.rag import (  # noqa: F401
        Chunk,
        RetrievedChunk,
        HybridRetriever,
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
    """API-03: __all__ matches the documented public contract exactly."""
    from flying_probe_copilot.rag import __all__ as public_all

    assert set(public_all) == {
        "build_retriever",
        "HybridRetriever",
        "Chunk",
        "RetrievedChunk",
        "load_kb",
        "VectorIndex",
        "LexicalIndex",
    }
