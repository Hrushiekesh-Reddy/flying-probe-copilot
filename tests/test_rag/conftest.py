"""Shared fixtures for the Phase 3 slice-1 RAG retrieval tests.

The unit suite is fully offline and deterministic: it injects a model-free
``FakeEmbedder`` (binary bag-of-words over a closed vocabulary) so vector search
ranks strictly by vocabulary overlap and the nearest chunk is hand-computable.
No SentenceTransformer model is ever loaded or downloaded by these tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

from flying_probe_copilot.rag.lexical_index import _tokenize


class FakeEmbedder:
    """Deterministic, model-free embedder for tests.

    Embeds each text as a binary presence vector over a fixed, ordered
    vocabulary: position ``i`` is ``1.0`` when the vocab term at index ``i``
    appears in the (tokenized) text, else ``0.0``.  Under cosine distance this
    makes similarity order strictly by vocabulary overlap, so a test can know in
    advance which chunk is nearest a given query.  A text sharing no vocab term
    embeds to the all-zero vector (the no-overlap / no-match case).
    """

    def __init__(self, vocab: list[str]) -> None:
        self._vocab = list(vocab)
        self._index = {term: i for i, term in enumerate(self._vocab)}

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vec = [0.0] * len(self._vocab)
            for token in set(_tokenize(text)):
                pos = self._index.get(token)
                if pos is not None:
                    vec[pos] = 1.0
            vectors.append(vec)
        return vectors


@pytest.fixture
def fake_embedder() -> FakeEmbedder:
    """A FakeEmbedder over a small, fixed failure-mode vocabulary."""
    return FakeEmbedder(
        [
            "solder",
            "bridge",
            "open",
            "short",
            "tombstone",
            "resistor",
            "capacitor",
            "drift",
        ]
    )


@pytest.fixture
def write_kb(tmp_path: Path) -> Callable[[dict[str, str]], Path]:
    """Factory: write a KB tree from ``{relpath: markdown}`` and return its dir.

    Relative paths may include subdirectories (POSIX ``/``); parents are
    created as needed.  Returns the KB root directory.
    """

    def _write(files: dict[str, str]) -> Path:
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir(exist_ok=True)
        for rel, content in files.items():
            target = kb_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return kb_dir

    return _write
