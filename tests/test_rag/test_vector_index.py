"""VEC-01..VEC-17 — VectorIndex (chromadb + injected fake embedder)."""

from __future__ import annotations

import pytest

from flying_probe_copilot.rag import Chunk, VectorIndex


def _chunk(cid: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=cid,
        doc_id=cid.split("#")[0],
        source_path=cid.split("#")[0],
        heading="",
        text=text,
        ordinal=0,
    )


def _corpus() -> list[Chunk]:
    return [
        _chunk("a.md#0", "solder bridge short"),
        _chunk("b.md#0", "tombstone resistor"),
        _chunk("c.md#0", "capacitor drift"),
    ]


def test_vec01_nearest_by_overlap_ranks_first(fake_embedder):
    """VEC-01: the chunk with greatest vocab overlap ranks first."""
    idx = VectorIndex(embedder=fake_embedder)
    idx.add(_corpus())
    results = idx.search("solder bridge", top_k=5)
    assert results[0][0].chunk_id == "a.md#0"
    assert isinstance(results[0][1], float)


def test_vec02_order_follows_overlap(fake_embedder):
    """VEC-02: returned order matches known nearest->farthest overlap order."""
    idx = VectorIndex(embedder=fake_embedder)
    idx.add(
        [
            _chunk("a.md#0", "solder bridge short"),  # overlap 2 with 'solder bridge'
            _chunk("b.md#0", "solder open"),  # overlap 1
        ]
    )
    results = idx.search("solder bridge", top_k=5)
    assert [c.chunk_id for c, _ in results] == ["a.md#0", "b.md#0"]


def test_vec03_top_k_truncates(fake_embedder):
    """VEC-03: top_k smaller than corpus returns exactly top_k."""
    idx = VectorIndex(embedder=fake_embedder)
    idx.add(_corpus())
    results = idx.search("solder tombstone capacitor", top_k=2)
    assert len(results) == 2


def test_vec04_top_k_over_corpus_is_bounded(fake_embedder):
    """VEC-04: top_k larger than corpus returns at most corpus-size."""
    idx = VectorIndex(embedder=fake_embedder)
    idx.add(_corpus())
    results = idx.search("solder tombstone capacitor", top_k=99)
    assert len(results) <= 3


def test_vec05_empty_index_returns_empty(fake_embedder):
    """VEC-05: querying an index with no chunks returns []."""
    idx = VectorIndex(embedder=fake_embedder)
    assert idx.search("solder", top_k=5) == []


def test_vec06_empty_query_returns_empty(fake_embedder):
    """VEC-06: an empty query returns []."""
    idx = VectorIndex(embedder=fake_embedder)
    idx.add(_corpus())
    assert idx.search("", top_k=5) == []


def test_vec07_whitespace_query_returns_empty(fake_embedder):
    """VEC-07: a whitespace-only query returns []."""
    idx = VectorIndex(embedder=fake_embedder)
    idx.add(_corpus())
    assert idx.search("   ", top_k=5) == []


def test_vec08_zero_overlap_query_returns_empty(fake_embedder):
    """VEC-08: a query sharing no vocab term (zero vector) returns []."""
    idx = VectorIndex(embedder=fake_embedder)
    idx.add(_corpus())
    assert idx.search("xylophone zeppelin", top_k=5) == []


def test_vec09_single_chunk_returned(fake_embedder):
    """VEC-09: add one chunk; query returns just it."""
    idx = VectorIndex(embedder=fake_embedder)
    idx.add([_chunk("a.md#0", "solder bridge")])
    results = idx.search("solder", top_k=5)
    assert len(results) == 1
    assert results[0][0].chunk_id == "a.md#0"


def test_vec10_empty_add_then_query(fake_embedder):
    """VEC-10: add([]) then query returns [] without error."""
    idx = VectorIndex(embedder=fake_embedder)
    idx.add([])
    assert idx.search("solder", top_k=5) == []


def test_vec11_duplicate_text_distinct_ids_both_stored(fake_embedder):
    """VEC-11: duplicate text with distinct ids both retrievable."""
    idx = VectorIndex(embedder=fake_embedder)
    idx.add([_chunk("a.md#0", "solder bridge"), _chunk("b.md#0", "solder bridge")])
    results = idx.search("solder", top_k=5)
    assert {c.chunk_id for c, _ in results} == {"a.md#0", "b.md#0"}


def test_vec12_readd_same_id_upserts(fake_embedder):
    """VEC-12: re-adding the same chunk_id upserts (no duplicate, no error)."""
    idx = VectorIndex(embedder=fake_embedder)
    idx.add([_chunk("a.md#0", "solder bridge")])
    idx.add([_chunk("a.md#0", "solder bridge short")])
    results = idx.search("solder", top_k=5)
    assert len(results) == 1
    assert results[0][0].text == "solder bridge short"


def test_vec13_unicode_chunk_retrievable(fake_embedder):
    """VEC-13: unicode text stores and retrieves without error."""
    idx = VectorIndex(embedder=fake_embedder)
    idx.add([_chunk("a.md#0", "solder 漂移")])
    results = idx.search("solder", top_k=5)
    assert results and results[0][0].chunk_id == "a.md#0"


def test_vec14_injected_embedder_is_used_no_model_load(fake_embedder, monkeypatch):
    """VEC-14: the injected embedder is the only embedding source (no ST load)."""
    import flying_probe_copilot.rag.vector_index as vi

    def _boom(*a, **k):  # pragma: no cover - must never be called
        raise AssertionError("SentenceTransformer must not load when embedder injected")

    monkeypatch.setattr(vi, "SentenceTransformer", _boom, raising=False)
    idx = VectorIndex(embedder=fake_embedder)
    idx.add(_corpus())
    assert idx.search("solder", top_k=1)[0][0].chunk_id == "a.md#0"


def test_vec15_default_embedder_is_lazy(monkeypatch):
    """VEC-15: constructing with no embedder does not load the default model."""
    import flying_probe_copilot.rag.vector_index as vi

    def _boom(*a, **k):  # pragma: no cover - must never be called
        raise AssertionError("default model must load lazily, not at construction")

    monkeypatch.setattr(vi, "SentenceTransformer", _boom, raising=False)
    VectorIndex()  # construction must not embed anything


def test_vec16_top_k_zero_returns_empty(fake_embedder):
    """VEC-16: top_k == 0 returns []."""
    idx = VectorIndex(embedder=fake_embedder)
    idx.add(_corpus())
    assert idx.search("solder", top_k=0) == []


def test_vec17_negative_top_k_raises(fake_embedder):
    """VEC-17: top_k < 0 raises ValueError."""
    idx = VectorIndex(embedder=fake_embedder)
    idx.add(_corpus())
    with pytest.raises(ValueError):
        idx.search("solder", top_k=-1)
