"""PRM-01..PRM-10 — build_answer_prompt content guarantees + edges."""

from __future__ import annotations

from flying_probe_copilot.rag import Chunk
from flying_probe_copilot.rag.prompts import build_answer_prompt


def _chunk(cid: str, heading: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=cid,
        doc_id=cid.split("#")[0],
        source_path=cid.split("#")[0],
        heading=heading,
        text=text,
        ordinal=0,
    )


def _two() -> list[Chunk]:
    return [
        _chunk("a.md#0", "Opens", "An open is a missing connection."),
        _chunk("b.md#0", "Shorts", "A short bridges two nets."),
    ]


def test_prm01_contains_question():
    """PRM-01: the prompt contains the verbatim question."""
    q = "why did this net read open?"
    assert q in build_answer_prompt(q, _two())


def test_prm02_contains_every_chunk_id():
    """PRM-02: every chunk_id appears in the prompt."""
    out = build_answer_prompt("q", _two())
    assert "a.md#0" in out and "b.md#0" in out


def test_prm03_contains_each_chunk_text():
    """PRM-03: each chunk's text body appears."""
    out = build_answer_prompt("q", _two())
    assert "An open is a missing connection." in out
    assert "A short bridges two nets." in out


def test_prm04_contains_json_and_citation_instruction():
    """PRM-04: prompt instructs JSON output with citations + sufficient fields."""
    out = build_answer_prompt("q", _two())
    assert "JSON" in out
    assert "citations" in out
    assert "sufficient" in out


def test_prm05_contains_each_heading():
    """PRM-05: each chunk heading appears."""
    out = build_answer_prompt("q", _two())
    assert "Opens" in out and "Shorts" in out


def test_prm06_no_chunks_returns_string():
    """PRM-06: zero chunks returns a string (no raise) with the instruction."""
    out = build_answer_prompt("q", [])
    assert isinstance(out, str)
    assert "JSON" in out


def test_prm07_unicode_preserved():
    """PRM-07: unicode question/heading/text appear intact."""
    chunks = [_chunk("u.md#0", "Dérive 漂移", "résistance dérive 漂移")]
    out = build_answer_prompt("pourquoi 漂移?", chunks)
    assert "漂移" in out and "résistance dérive 漂移" in out


def test_prm08_many_chunks_all_present():
    """PRM-08: with 5+ chunks every id + text survives (no truncation)."""
    chunks = [_chunk(f"d{i}.md#0", f"H{i}", f"body number {i}") for i in range(6)]
    out = build_answer_prompt("q", chunks)
    for i in range(6):
        assert f"d{i}.md#0" in out
        assert f"body number {i}" in out


def test_prm09_empty_heading_ok():
    """PRM-09: a chunk with empty heading still contributes id + text."""
    out = build_answer_prompt("q", [_chunk("p.md#0", "", "preamble body")])
    assert "p.md#0" in out and "preamble body" in out


def test_prm10_identical_text_both_ids_present():
    """PRM-10: duplicate text under distinct ids both appear (no dedupe)."""
    chunks = [_chunk("a.md#0", "H", "same body"), _chunk("b.md#0", "H", "same body")]
    out = build_answer_prompt("q", chunks)
    assert "a.md#0" in out and "b.md#0" in out
