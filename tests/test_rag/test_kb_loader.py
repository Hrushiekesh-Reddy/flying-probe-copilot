"""KB-01..KB-18 — load_kb chunking, ids, skips, edges, errors."""

from __future__ import annotations

import pytest

from flying_probe_copilot.rag import Chunk, load_kb
from flying_probe_copilot.rag.kb_loader import MAX_CHUNK_CHARS

DOC = """# First

Body of the first section.

# Second

Body of the second section.
"""


def test_kb01_one_chunk_per_heading_section(write_kb):
    """KB-01: N heading sections -> N chunks; each carries heading + body."""
    kb = write_kb({"a.md": DOC})
    chunks = load_kb(kb)
    assert len(chunks) == 2
    assert all(isinstance(c, Chunk) for c in chunks)
    assert chunks[0].heading == "First"
    assert "Body of the first section." in chunks[0].text
    assert chunks[1].heading == "Second"
    assert "Body of the second section." in chunks[1].text


def test_kb02_preamble_before_first_heading_becomes_a_chunk(write_kb):
    """KB-02: text before the first heading -> one chunk, heading="" ordinal 0."""
    kb = write_kb({"a.md": "Intro preamble line.\n\n# Real\n\nbody\n"})
    chunks = load_kb(kb)
    assert chunks[0].heading == ""
    assert chunks[0].ordinal == 0
    assert "Intro preamble line." in chunks[0].text
    assert chunks[1].heading == "Real"


def test_kb03_oversized_section_subsplits_on_blank_lines(write_kb):
    """KB-03: a body over MAX_CHUNK_CHARS sub-splits; each sub-chunk keeps heading."""
    para = "x" * 700
    kb = write_kb({"a.md": f"# Big\n\n{para}\n\n{para}\n"})
    chunks = load_kb(kb)
    big = [c for c in chunks if c.heading == "Big"]
    assert len(big) >= 2
    assert all(len(c.text) <= MAX_CHUNK_CHARS for c in big)


def test_kb04_section_at_or_under_limit_is_single_chunk(write_kb):
    """KB-04: body at/under MAX_CHUNK_CHARS is one chunk (no split)."""
    body = "y" * (MAX_CHUNK_CHARS - 50)
    kb = write_kb({"a.md": f"# H\n\n{body}\n"})
    chunks = load_kb(kb)
    assert len([c for c in chunks if c.heading == "H"]) == 1


def test_kb05_oversized_no_blank_lines_hard_splits(write_kb):
    """KB-05: oversized body with no blank lines hard-splits at the char cap."""
    body = "z" * (MAX_CHUNK_CHARS + 500)
    kb = write_kb({"a.md": f"# H\n\n{body}\n"})
    chunks = load_kb(kb)
    hs = [c for c in chunks if c.heading == "H"]
    assert len(hs) >= 2
    assert all(len(c.text) <= MAX_CHUNK_CHARS for c in hs)


def test_kb06_chunk_ids_are_relpath_ordinal_and_unique(write_kb):
    """KB-06: chunk_id == '{relpath}#{ordinal}', ordinals per-file, all unique."""
    kb = write_kb({"a.md": DOC, "b.md": DOC})
    chunks = load_kb(kb)
    ids = [c.chunk_id for c in chunks]
    assert "a.md#0" in ids and "a.md#1" in ids
    assert "b.md#0" in ids and "b.md#1" in ids
    assert len(ids) == len(set(ids))


def test_kb07_loading_is_deterministic(write_kb):
    """KB-07: loading the same KB twice yields identical ids in identical order."""
    kb = write_kb({"a.md": DOC, "b.md": DOC})
    first = [c.chunk_id for c in load_kb(kb)]
    second = [c.chunk_id for c in load_kb(kb)]
    assert first == second


def test_kb08_nested_subdir_uses_posix_relpath(write_kb):
    """KB-08: a nested file's chunk_id uses POSIX '/' relative to kb_dir."""
    kb = write_kb({"failure-modes/opens.md": DOC})
    chunks = load_kb(kb)
    assert all(c.chunk_id.startswith("failure-modes/opens.md#") for c in chunks)
    assert all("\\" not in c.chunk_id for c in chunks)


def test_kb09_readme_is_skipped(write_kb):
    """KB-09: README.md contributes no chunks; a normal doc loads."""
    kb = write_kb({"README.md": DOC, "a.md": DOC})
    chunks = load_kb(kb)
    assert all(c.doc_id != "README.md" for c in chunks)
    assert any(c.doc_id == "a.md" for c in chunks)


def test_kb10_underscore_files_are_skipped(write_kb):
    """KB-10: a file starting with '_' contributes no chunks."""
    kb = write_kb({"_draft.md": DOC, "a.md": DOC})
    chunks = load_kb(kb)
    assert all(c.doc_id != "_draft.md" for c in chunks)
    assert any(c.doc_id == "a.md" for c in chunks)


def test_kb11_empty_directory_returns_empty(write_kb):
    """KB-11: an existing empty directory returns []."""
    kb = write_kb({})
    assert load_kb(kb) == []


def test_kb12_only_skipped_files_returns_empty(write_kb):
    """KB-12: a corpus of only README/underscore files returns []."""
    kb = write_kb({"README.md": DOC, "_notes.md": DOC})
    assert load_kb(kb) == []


def test_kb13_whitespace_only_file_yields_no_chunks(write_kb):
    """KB-13: an empty/whitespace-only file produces no chunks."""
    kb = write_kb({"a.md": "   \n\n  \n"})
    assert load_kb(kb) == []


def test_kb14_hash_inside_code_fence_is_not_a_heading(write_kb):
    """KB-14: a '#'-line inside a fenced code block does not start a section."""
    doc = "# Real\n\n```\n# not a heading\ncode line\n```\n\nafter\n"
    kb = write_kb({"a.md": doc})
    chunks = load_kb(kb)
    assert len(chunks) == 1
    assert chunks[0].heading == "Real"
    assert "# not a heading" in chunks[0].text


def test_kb15_unicode_is_preserved(write_kb):
    """KB-15: unicode in heading/body is loaded verbatim; id well-formed."""
    kb = write_kb({"a.md": "# Défaut café 短路\n\nrésistance dérive 漂移\n"})
    chunks = load_kb(kb)
    assert "café" in chunks[0].heading
    assert "漂移" in chunks[0].text
    assert chunks[0].chunk_id == "a.md#0"


def test_kb16_non_markdown_files_ignored(write_kb):
    """KB-16: only .md files are ingested; .txt is ignored."""
    kb = write_kb({"a.md": DOC, "notes.txt": "# Heading\n\nbody\n"})
    chunks = load_kb(kb)
    assert all(c.doc_id == "a.md" for c in chunks)


def test_kb17_missing_dir_raises(write_kb, tmp_path):
    """KB-17: a non-existent kb_dir raises FileNotFoundError, not []."""
    missing = tmp_path / "does-not-exist"
    with pytest.raises(FileNotFoundError):
        load_kb(missing)


def test_kb18_file_instead_of_dir_raises(write_kb, tmp_path):
    """KB-18: kb_dir pointing at a file raises NotADirectoryError."""
    f = tmp_path / "afile.md"
    f.write_text(DOC, encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        load_kb(f)
