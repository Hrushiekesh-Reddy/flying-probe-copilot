"""RET-01..RET-21 — HybridRetriever RRF fusion + build_retriever.

All retrievers are built over a tmp KB with the injected fake embedder, so
vector search ranks by vocabulary overlap and ranks are hand-computable.

Fusion model: score(c) = sum over retrievers of 1/(rrf_k + rank), rank base 1,
rrf_k=60 default; output sorted by score DESC then chunk_id ASC.

Note on "one-list-only" construction: both indexes tokenize identically, so a
chunk that matches lexically also matches the vector index *unless* its matching
query term is outside the fake embedder's closed vocabulary. Tests use
out-of-vocab terms (e.g. "gadget") to force lexical-only chunks.
"""

from __future__ import annotations

import pytest

from flying_probe_copilot.rag import RetrievedChunk, build_retriever


def test_ret01_both_list_chunk_outranks_one_list(write_kb, fake_embedder):
    """RET-01: a chunk in BOTH lists outranks one in only the lexical list."""
    kb = write_kb(
        {
            "a.md": "# A\n\nsolder bridge short\n",   # in-vocab -> both lists
            "b.md": "# B\n\ngadget widget tool\n",     # 'gadget' out-of-vocab -> lexical only
        }
    )
    r = build_retriever(kb, embedder=fake_embedder)
    out = r.retrieve("solder gadget", top_k=5)
    ids = [rc.chunk.chunk_id for rc in out]
    assert ids.index("a.md#0") < ids.index("b.md#0")


def test_ret02_deterministic_tiebreak_by_chunk_id(write_kb, fake_embedder):
    """RET-02: symmetric chunks resolve deterministically, lower chunk_id first."""
    kb = write_kb({"a.md": "# A\n\nsolder bridge\n", "b.md": "# B\n\nsolder bridge\n"})
    r = build_retriever(kb, embedder=fake_embedder)
    first = [rc.chunk.chunk_id for rc in r.retrieve("solder bridge", top_k=5)]
    second = [rc.chunk.chunk_id for rc in r.retrieve("solder bridge", top_k=5)]
    assert first == second  # repeatable
    assert first.index("a.md#0") < first.index("b.md#0")


def test_ret03_top_k_truncates(write_kb, fake_embedder):
    """RET-03: more candidates than top_k -> exactly top_k returned."""
    kb = write_kb(
        {
            "a.md": "# A\n\nsolder\n",
            "b.md": "# B\n\nbridge\n",
            "c.md": "# C\n\nshort\n",
        }
    )
    r = build_retriever(kb, embedder=fake_embedder)
    out = r.retrieve("solder bridge short", top_k=2)
    assert len(out) == 2


def test_ret04_empty_query_returns_empty(write_kb, fake_embedder):
    """RET-04: empty query -> []."""
    kb = write_kb({"a.md": "# A\n\nsolder\n"})
    r = build_retriever(kb, embedder=fake_embedder)
    assert r.retrieve("", top_k=5) == []


def test_ret05_rrf_arithmetic_single_list_chunk(write_kb, fake_embedder):
    """RET-05: a lone lexical-only chunk at rank 1 scores 1/(60+1); vector_rank None."""
    kb = write_kb({"a.md": "# A\n\ngadget widget\n"})  # out-of-vocab -> lexical only
    r = build_retriever(kb, embedder=fake_embedder)
    out = r.retrieve("gadget", top_k=5)
    assert len(out) == 1
    assert out[0].lexical_rank == 1
    assert out[0].vector_rank is None
    assert out[0].score == pytest.approx(1.0 / 61.0)


def test_ret06_rrf_k_is_configurable(write_kb, fake_embedder):
    """RET-06: changing rrf_k changes the fused score per the formula."""
    kb = write_kb({"a.md": "# A\n\ngadget widget\n"})
    r = build_retriever(kb, embedder=fake_embedder)
    s60 = r.retrieve("gadget", top_k=5, rrf_k=60)[0].score
    s1 = r.retrieve("gadget", top_k=5, rrf_k=1)[0].score
    assert s60 == pytest.approx(1.0 / 61.0)
    assert s1 == pytest.approx(1.0 / 2.0)


def test_ret07_partial_retriever_records_none_rank(write_kb, fake_embedder):
    """RET-07: a lexical-only chunk carries vector_rank None; a both-list chunk neither."""
    kb = write_kb(
        {"a.md": "# A\n\nsolder bridge\n", "b.md": "# B\n\ngadget tool\n"}
    )
    r = build_retriever(kb, embedder=fake_embedder)
    out = {rc.chunk.chunk_id: rc for rc in r.retrieve("solder gadget", top_k=5)}
    assert out["b.md#0"].vector_rank is None
    assert out["a.md#0"].lexical_rank is not None
    assert out["a.md#0"].vector_rank is not None


def test_ret08_whitespace_query_returns_empty(write_kb, fake_embedder):
    """RET-08: whitespace-only query -> []."""
    kb = write_kb({"a.md": "# A\n\nsolder\n"})
    r = build_retriever(kb, embedder=fake_embedder)
    assert r.retrieve("   ", top_k=5) == []


def test_ret09_no_match_returns_empty(write_kb, fake_embedder):
    """RET-09: a query matching nothing in either retriever -> []."""
    kb = write_kb({"a.md": "# A\n\nsolder bridge\n"})
    r = build_retriever(kb, embedder=fake_embedder)
    assert r.retrieve("xylophone zeppelin", top_k=5) == []


def test_ret10_top_k_over_corpus_dedups(write_kb, fake_embedder):
    """RET-10: top_k over corpus returns at most corpus size, no duplicate ids."""
    kb = write_kb({"a.md": "# A\n\nsolder bridge\n", "b.md": "# B\n\nsolder short\n"})
    r = build_retriever(kb, embedder=fake_embedder)
    out = r.retrieve("solder bridge short", top_k=99)
    ids = [rc.chunk.chunk_id for rc in out]
    assert len(ids) == len(set(ids))
    assert len(ids) <= 2


def test_ret11_both_list_chunk_appears_once(write_kb, fake_embedder):
    """RET-11: a chunk in both lists appears once, with both ranks populated."""
    kb = write_kb({"a.md": "# A\n\nsolder bridge\n"})
    r = build_retriever(kb, embedder=fake_embedder)
    out = r.retrieve("solder bridge", top_k=5)
    assert len(out) == 1
    assert out[0].lexical_rank is not None and out[0].vector_rank is not None


def test_ret12_empty_kb_returns_empty(write_kb, fake_embedder):
    """RET-12: a retriever over an empty KB returns [] for any query."""
    kb = write_kb({})
    r = build_retriever(kb, embedder=fake_embedder)
    assert r.retrieve("solder", top_k=5) == []


def test_ret13_single_chunk_match(write_kb, fake_embedder):
    """RET-13: single-chunk KB, matching query -> one RetrievedChunk."""
    kb = write_kb({"a.md": "# A\n\nsolder bridge\n"})
    r = build_retriever(kb, embedder=fake_embedder)
    out = r.retrieve("solder", top_k=5)
    assert len(out) == 1
    assert isinstance(out[0], RetrievedChunk)


def test_ret14_unicode_query(write_kb, fake_embedder):
    """RET-14: a unicode query retrieves a unicode chunk without error."""
    kb = write_kb({"a.md": "# A\n\nsolder 漂移\n"})
    r = build_retriever(kb, embedder=fake_embedder)
    out = r.retrieve("漂移", top_k=5)
    assert out and out[0].chunk.chunk_id == "a.md#0"


def test_ret15_default_kwargs(write_kb, fake_embedder):
    """RET-15: default call behaves as top_k=5, rrf_k=60."""
    kb = write_kb({"a.md": "# A\n\ngadget widget\n"})
    r = build_retriever(kb, embedder=fake_embedder)
    out = r.retrieve("gadget")
    assert len(out) <= 5
    assert out[0].score == pytest.approx(1.0 / 61.0)


def test_ret16_top_k_zero_returns_empty(write_kb, fake_embedder):
    """RET-16: top_k == 0 -> []."""
    kb = write_kb({"a.md": "# A\n\nsolder\n"})
    r = build_retriever(kb, embedder=fake_embedder)
    assert r.retrieve("solder", top_k=0) == []


def test_ret17_output_sorted_score_desc_then_id(write_kb, fake_embedder):
    """RET-17: output is sorted by score DESC then chunk_id ASC."""
    kb = write_kb(
        {
            "a.md": "# A\n\nsolder bridge\n",   # both lists -> high
            "z.md": "# Z\n\ngadget tool\n",     # lexical only -> low
        }
    )
    r = build_retriever(kb, embedder=fake_embedder)
    out = r.retrieve("solder gadget", top_k=5)
    scores = [rc.score for rc in out]
    assert scores == sorted(scores, reverse=True)


def test_ret18_build_retriever_wiring(write_kb, fake_embedder):
    """RET-18: build_retriever returns a working retriever over the KB."""
    kb = write_kb({"a.md": "# A\n\nsolder bridge\n"})
    r = build_retriever(kb, embedder=fake_embedder)
    assert r.retrieve("solder", top_k=5)[0].chunk.chunk_id == "a.md#0"


def test_ret19_build_retriever_bad_dir_raises(tmp_path, fake_embedder):
    """RET-19: build_retriever on a non-existent dir surfaces the loader error."""
    with pytest.raises(FileNotFoundError):
        build_retriever(tmp_path / "nope", embedder=fake_embedder)


def test_ret20_build_retriever_empty_kb(write_kb, fake_embedder):
    """RET-20: build_retriever over an empty KB builds; queries return []."""
    kb = write_kb({})
    r = build_retriever(kb, embedder=fake_embedder)
    assert r.retrieve("solder", top_k=5) == []


def test_ret21_negative_top_k_raises(write_kb, fake_embedder):
    """RET-21: top_k < 0 raises ValueError; rrf_k < 1 raises ValueError."""
    kb = write_kb({"a.md": "# A\n\nsolder\n"})
    r = build_retriever(kb, embedder=fake_embedder)
    with pytest.raises(ValueError):
        r.retrieve("solder", top_k=-1)
    with pytest.raises(ValueError):
        r.retrieve("solder", top_k=5, rrf_k=0)
