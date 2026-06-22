"""LEX-01..LEX-15 — LexicalIndex (BM25) + _tokenize contracts."""

from __future__ import annotations

import pytest

from flying_probe_copilot.rag import Chunk, LexicalIndex
from flying_probe_copilot.rag.lexical_index import _tokenize


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
        _chunk("a.md#0", "solder bridge short between adjacent pads"),
        _chunk("b.md#0", "tombstone lifted chip component on one end"),
        _chunk("c.md#0", "resistor measured out of tolerance drift"),
    ]


def test_lex01_keyword_query_ranks_matching_chunk_first():
    """LEX-01: the chunk containing the query keyword ranks first."""
    idx = LexicalIndex(_corpus())
    results = idx.search("tombstone", top_k=5)
    assert results[0][0].chunk_id == "b.md#0"
    assert isinstance(results[0][1], float)


def test_lex02_results_ordered_by_score_desc():
    """LEX-02: results are ordered by BM25 score descending."""
    idx = LexicalIndex(_corpus())
    results = idx.search("solder bridge", top_k=5)
    scores = [s for _, s in results]
    assert scores == sorted(scores, reverse=True)
    assert results[0][0].chunk_id == "a.md#0"


def test_lex03_tokenize_lowercases_and_splits_on_nonalnum():
    """LEX-03: _tokenize lowercases and splits on non-alphanumeric boundaries."""
    assert _tokenize("Solder-Bridge, R12!") == ["solder", "bridge", "r12"]


def test_lex04_match_is_case_and_punctuation_insensitive():
    """LEX-04: a query differing only in case/punctuation still matches."""
    idx = LexicalIndex(_corpus())
    results = idx.search("SOLDER.", top_k=5)
    assert results[0][0].chunk_id == "a.md#0"


def test_lex05_top_k_truncates():
    """LEX-05: top_k smaller than matches returns exactly top_k."""
    idx = LexicalIndex(_corpus())
    results = idx.search("solder tombstone resistor", top_k=2)
    assert len(results) == 2


def test_lex06_top_k_over_corpus_is_bounded():
    """LEX-06: top_k larger than corpus returns at most corpus-size results."""
    idx = LexicalIndex(_corpus())
    results = idx.search("solder tombstone resistor", top_k=99)
    assert len(results) <= 3


def test_lex07_empty_query_returns_empty():
    """LEX-07: an empty query returns []."""
    idx = LexicalIndex(_corpus())
    assert idx.search("", top_k=5) == []


def test_lex08_whitespace_query_returns_empty():
    """LEX-08: a whitespace-only query returns []."""
    idx = LexicalIndex(_corpus())
    assert idx.search("   ", top_k=5) == []


def test_lex09_no_overlap_query_returns_empty():
    """LEX-09: a query whose terms appear in no chunk returns []."""
    idx = LexicalIndex(_corpus())
    assert idx.search("xylophone zeppelin", top_k=5) == []


def test_lex10_empty_index_returns_empty():
    """LEX-10: a LexicalIndex over an empty corpus returns [] for any query."""
    idx = LexicalIndex([])
    assert idx.search("solder", top_k=5) == []


def test_lex11_single_chunk_match_returns_it():
    """LEX-11: single-chunk corpus, matching query -> that one chunk."""
    idx = LexicalIndex([_chunk("a.md#0", "solder bridge defect")])
    results = idx.search("solder", top_k=5)
    assert len(results) == 1
    assert results[0][0].chunk_id == "a.md#0"


def test_lex12_duplicate_text_both_returned():
    """LEX-12: duplicate-text chunks (distinct ids) both appear with equal score."""
    idx = LexicalIndex([_chunk("a.md#0", "solder bridge"), _chunk("b.md#0", "solder bridge")])
    results = idx.search("solder", top_k=5)
    assert len(results) == 2
    assert results[0][1] == pytest.approx(results[1][1])


def test_lex13_unicode_terms_match():
    """LEX-13: unicode query terms tokenize and match a unicode chunk."""
    idx = LexicalIndex([_chunk("a.md#0", "résistance dérive 漂移")])
    results = idx.search("漂移", top_k=5)
    assert results and results[0][0].chunk_id == "a.md#0"


def test_lex14_top_k_zero_returns_empty():
    """LEX-14: top_k == 0 returns []."""
    idx = LexicalIndex(_corpus())
    assert idx.search("solder", top_k=0) == []


def test_lex15_negative_top_k_raises():
    """LEX-15: top_k < 0 raises ValueError."""
    idx = LexicalIndex(_corpus())
    with pytest.raises(ValueError):
        idx.search("solder", top_k=-1)
