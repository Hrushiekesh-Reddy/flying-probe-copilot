"""Render a ``BatchLog`` to structured JSON via pydantic ``model_dump_json``.

The output is round-trippable through ``BatchLog.model_validate_json``.
"""

from __future__ import annotations

from pathlib import Path

from ..models import BatchLog


def render_json(bl: BatchLog, path: Path | str) -> None:
    """Write ``bl`` as pretty-printed JSON to ``path``."""
    text = bl.model_dump_json(indent=2)
    Path(path).write_text(text, encoding="utf-8")
