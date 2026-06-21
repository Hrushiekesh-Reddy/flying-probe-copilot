"""load_kb — ingest the failure-mode knowledge base into retrievable chunks.

Each ``.md`` file under the KB root is split into chunks anchored on ATX
headings (``#`` .. ``######``). Text before the first heading (or a heading-less
file) becomes one chunk with ``heading == ""``. A heading line inside a fenced
code block (```` ``` ````) does NOT start a new section. Sections longer than
``MAX_CHUNK_CHARS`` are sub-split on blank lines, falling back to a hard
character split when a single block has no blank lines (plan G1/G2/G3).

``README.md`` and any file whose name starts with ``_`` are skipped. Chunk ids
are deterministic: ``"{rel_posix_path}#{ordinal}"`` with ordinal restarting per
file.
"""

from __future__ import annotations

import re
from pathlib import Path

from .models import Chunk

MAX_CHUNK_CHARS = 1200

_HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$")
_BLANK_SPLIT_RE = re.compile(r"\n\s*\n")


def _split_sections(text: str) -> list[tuple[str, str]]:
    """Split markdown into ``(heading, section_text)`` pairs, fence-aware."""
    sections: list[tuple[str, list[str]]] = []
    heading = ""
    lines: list[str] = []
    in_fence = False

    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            lines.append(line)
            continue
        match = None if in_fence else _HEADING_RE.match(line)
        if match:
            sections.append((heading, lines))
            heading = match.group(1).strip()
            lines = [line]
        else:
            lines.append(line)
    sections.append((heading, lines))

    return [(h, "\n".join(ls)) for h, ls in sections]


def _subsplit(text: str) -> list[str]:
    """Sub-split an oversized section body to <= MAX_CHUNK_CHARS pieces."""
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]

    pieces: list[str] = []
    buffer = ""
    for para in _BLANK_SPLIT_RE.split(text):
        candidate = f"{buffer}\n\n{para}" if buffer else para
        if len(candidate) <= MAX_CHUNK_CHARS:
            buffer = candidate
            continue
        if buffer:
            pieces.append(buffer)
            buffer = ""
        if len(para) <= MAX_CHUNK_CHARS:
            buffer = para
        else:
            for i in range(0, len(para), MAX_CHUNK_CHARS):
                pieces.append(para[i : i + MAX_CHUNK_CHARS])
    if buffer:
        pieces.append(buffer)
    return pieces


def _is_skipped(name: str) -> bool:
    return name == "README.md" or name.startswith("_")


def load_kb(kb_dir: Path | str) -> list[Chunk]:
    """Load every ``.md`` file under ``kb_dir`` into a list of :class:`Chunk`.

    Parameters
    ----------
    kb_dir:
        Knowledge-base root directory.

    Returns
    -------
    list[Chunk]
        Chunks in deterministic order (files sorted by POSIX relative path,
        chunks in document order). ``[]`` for an empty or all-skipped corpus.

    Raises
    ------
    FileNotFoundError
        If ``kb_dir`` does not exist.
    NotADirectoryError
        If ``kb_dir`` is not a directory.
    """
    root = Path(kb_dir)
    if not root.exists():
        raise FileNotFoundError(f"kb_dir does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"kb_dir is not a directory: {root}")

    files = sorted(
        (p for p in root.rglob("*.md") if p.is_file() and not _is_skipped(p.name)),
        key=lambda p: p.relative_to(root).as_posix(),
    )

    chunks: list[Chunk] = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        ordinal = 0
        for heading, section_text in _split_sections(text):
            if not section_text.strip():
                continue
            for piece in _subsplit(section_text):
                if not piece.strip():
                    continue
                chunks.append(
                    Chunk(
                        chunk_id=f"{rel}#{ordinal}",
                        doc_id=rel,
                        source_path=rel,
                        heading=heading,
                        text=piece,
                        ordinal=ordinal,
                    )
                )
                ordinal += 1

    return chunks
