"""MOD-01..MOD-06 — Chunk / RetrievedChunk dataclass contracts."""

from __future__ import annotations

import dataclasses

import pytest

from flying_probe_copilot.rag import Chunk, RetrievedChunk


def _chunk(**over) -> Chunk:
    base = dict(
        chunk_id="failure-modes/opens.md#0",
        doc_id="failure-modes/opens.md",
        source_path="failure-modes/opens.md",
        heading="Open Circuit",
        text="An open is a missing electrical connection.",
        ordinal=0,
    )
    base.update(over)
    return Chunk(**base)


def test_mod01_chunk_constructs_and_reads_back():
    """MOD-01: Chunk constructs; every field reads back the value passed."""
    c = _chunk()
    assert c.chunk_id == "failure-modes/opens.md#0"
    assert c.doc_id == "failure-modes/opens.md"
    assert c.source_path == "failure-modes/opens.md"
    assert c.heading == "Open Circuit"
    assert c.text == "An open is a missing electrical connection."
    assert c.ordinal == 0


def test_mod02_chunk_is_frozen():
    """MOD-02: reassigning a Chunk field raises FrozenInstanceError."""
    c = _chunk()
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.text = "mutated"  # type: ignore[misc]


def test_mod03_chunk_value_equality():
    """MOD-03: equal-valued Chunks compare ==, a differing one !=."""
    assert _chunk() == _chunk()
    assert _chunk() != _chunk(text="different")


def test_mod04_retrieved_chunk_constructs_with_optional_ranks():
    """MOD-04: RetrievedChunk holds chunk + score + ranks; None rank allowed."""
    rc = RetrievedChunk(chunk=_chunk(), score=0.5, lexical_rank=1, vector_rank=None)
    assert rc.chunk == _chunk()
    assert rc.score == 0.5
    assert rc.lexical_rank == 1
    assert rc.vector_rank is None


def test_mod05_retrieved_chunk_is_frozen():
    """MOD-05: reassigning a RetrievedChunk field raises FrozenInstanceError."""
    rc = RetrievedChunk(chunk=_chunk(), score=0.5, lexical_rank=1, vector_rank=2)
    with pytest.raises(dataclasses.FrozenInstanceError):
        rc.score = 9.0  # type: ignore[misc]


def test_mod06_dataclass_field_sets():
    """MOD-06: both dataclasses expose exactly the documented fields."""
    chunk_fields = {f.name for f in dataclasses.fields(Chunk)}
    assert chunk_fields == {
        "chunk_id",
        "doc_id",
        "source_path",
        "heading",
        "text",
        "ordinal",
    }
    rc_fields = {f.name for f in dataclasses.fields(RetrievedChunk)}
    assert rc_fields == {"chunk", "score", "lexical_rank", "vector_rank"}
