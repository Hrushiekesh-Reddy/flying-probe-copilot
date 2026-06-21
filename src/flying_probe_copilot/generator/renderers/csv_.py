"""Flatten a ``BatchLog`` to a one-row-per-test-record CSV.

Columns (stable order, used by downstream tests and analytics):

    serial, batch_id, btest_status, block_designator, record_type, status,
    measured, lim_nominal, lim_high, lim_low, designator

Empty fields render as blank cells (csv default). Encoding is UTF-8, newline
is LF (csv module default on Windows is platform-native; we pin to ``""``).
"""

from __future__ import annotations

import csv
from pathlib import Path

from ..models import (
    AnalogRecord,
    BatchLog,
    DigitalRecord,
    Limits2,
    Limits3,
    PinsFailedRecord,
    ShortsRecord,
    TestJetRecord,
)

_COLUMNS = [
    "serial",
    "batch_id",
    "btest_status",
    "block_designator",
    "record_type",
    "status",
    "measured",
    "lim_nominal",
    "lim_high",
    "lim_low",
    "designator",
]


def _record_type_label(r) -> str:
    if isinstance(r, AnalogRecord):
        return f"A-{r.record_type.value}"
    if isinstance(r, DigitalRecord):
        return "D-T"
    if isinstance(r, ShortsRecord):
        return "TS"
    if isinstance(r, TestJetRecord):
        return "TJET"
    if isinstance(r, PinsFailedRecord):
        return "PF"
    return type(r).__name__


def _row_for_block(serial: str, batch_id: str, btest_status: int, block) -> dict:
    row = {c: "" for c in _COLUMNS}
    row["serial"] = serial
    row["batch_id"] = batch_id
    row["btest_status"] = btest_status
    row["block_designator"] = block.block.designator
    row["record_type"] = _record_type_label(block.record)
    row["status"] = int(block.record.status)
    row["designator"] = getattr(block.record, "designator", "")
    if isinstance(block.record, AnalogRecord):
        row["measured"] = block.record.measured
        if isinstance(block.record.limits, Limits3):
            row["lim_nominal"] = block.record.limits.nominal
            row["lim_high"] = block.record.limits.high
            row["lim_low"] = block.record.limits.low
        elif isinstance(block.record.limits, Limits2):
            row["lim_high"] = block.record.limits.high
            row["lim_low"] = block.record.limits.low
    return row


def render_csv(bl: BatchLog, path: Path | str) -> None:
    """Write the flattened CSV for ``bl`` to ``path``."""
    p = Path(path)
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_COLUMNS)
        writer.writeheader()
        for board in bl.boards:
            for block in board.blocks:
                writer.writerow(
                    _row_for_block(
                        board.panel.serial,
                        bl.batch.batch_id,
                        int(board.btest.status),
                        block,
                    )
                )
