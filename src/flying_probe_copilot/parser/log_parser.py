"""Keysight i3070 Log Record Format parser — Phase 1b.

Public API:
  - ``tokenize(text)``        → Iterator[tuple[str, list[str]]]
  - ``parse_log_file(path)``  → tuple[BatchLog, ParseReport]
  - ``_parse_yymmddhhmmss(value)`` → datetime   (exported for tests)
  - ``ParseError``            dataclass
  - ``ParseReport``           dataclass

The parser is intentionally lenient: per-record errors are caught, appended
to ``ParseReport.errors``, and the offending record is skipped.  Other records
in the same file continue to parse normally.

Encoding strategy (#WARNING-14):
  - Try UTF-8 first.
  - On UnicodeDecodeError fall back to cp1252.
  - If both fail, append a ``FileUndecodableError`` to ParseReport.errors and
    return an empty ``BatchLog``.

Timestamp conversion (#BLOCKER-4):
  - YYMMDDHHMMSS ints are converted via Python's ``strptime("%y%m%d%H%M%S")``
    which has the standard century pivot: 00-68 → 2000-2068, 69-99 → 1969-1999.
  - Unrepresentable values raise ``ParseError``.

Subrecords @TS-S/@TS-D/@TS-O/@TS-P and @PF/@PIN sub-lists are intentionally
not persisted (per plan OUT-OF-SCOPE); they are consumed by the tokenizer and
noted in ParseReport.notes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator

from flying_probe_copilot.generator.models import (
    AnalogRecord,
    AnalogType,
    AnalogStatus,
    AnalogType,
    BatchLog,
    BatchRecord,
    BlockRecord,
    BoardLog,
    BoardTestRecord,
    BTESTStatus,
    DigitalRecord,
    DigitalStatus,
    Limits2,
    Limits3,
    LIM2_TYPES,
    LIM3_TYPES,
    PanelInstance,
    PinsFailedRecord,
    ShortsRecord,
    ShortsStatus,
    TestBlock,
    TestJetRecord,
    TwoDigitStatus,
)


# ---------------------------------------------------------------------------
# ParseError + ParseReport
# ---------------------------------------------------------------------------


@dataclass
class ParseError(Exception):
    """A single parse error recorded during tokenization or record parsing.

    Inherits from Exception so it can be raised by _parse_yymmddhhmmss and
    caught by the calling parser, then appended to ParseReport.errors.
    """

    line_no: int
    snippet: str
    message: str

    def __str__(self) -> str:
        return f"Line {self.line_no}: {self.message} — {self.snippet[:80]!r}"


@dataclass
class ParseReport:
    """Accumulates parse errors and notes for a single log file."""

    errors: list[ParseError] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    record_count: int = 0


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------


def tokenize(text: str) -> Iterator[tuple[str, list[str], int]]:
    """Yield ``(prefix, fields, line_no)`` for every ``{@PREFIX|...}`` record.

    The outer ``{...}`` wrapper is stripped; nested ``{...}`` (e.g. ``@PIN``
    subrecords inside ``@PF``) are yielded as a single unit.

    Backslash characters inside the braces are treated as literal characters
    — no escape processing (#MINOR-15).

    Yields tuples of (prefix: str, fields: list[str], line_no: int).
    """
    # Track brace depth to handle nested records (e.g. @PF with @PIN sub-list)
    depth = 0
    start = -1
    start_line = 0
    line_no = 1

    for i, ch in enumerate(text):
        if ch == "\n":
            line_no += 1
        if ch == "{" and depth == 0:
            depth = 1
            start = i
            start_line = line_no
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start != -1:
                # We have a complete top-level record
                inner = text[start + 1 : i]  # strip outer braces
                # Remove nested brace groups to extract outer fields only
                outer_inner = _strip_nested_braces(inner)
                parts = outer_inner.split("|")
                if parts and parts[0].startswith("@"):
                    prefix = parts[0]
                    yield prefix, parts[1:], start_line
                start = -1


def _strip_nested_braces(text: str) -> str:
    """Return ``text`` with all ``{...}`` groups replaced by empty string."""
    result = []
    depth = 0
    for ch in text:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif depth == 0:
            result.append(ch)
    return "".join(result)


# ---------------------------------------------------------------------------
# Timestamp helper (#BLOCKER-4)
# ---------------------------------------------------------------------------


def _parse_yymmddhhmmss(value: int | str) -> datetime:
    """Convert a YYMMDDHHMMSS integer or string to a ``datetime``.

    Uses Python ``strptime("%y%m%d%H%M%S")`` with the standard century pivot:
      - YY 00-68  → 2000-2068
      - YY 69-99  → 1969-1999

    Raises ``ParseError`` (line_no=0) on any parse failure.
    """
    s = str(value).zfill(12)
    try:
        return datetime.strptime(s, "%y%m%d%H%M%S")
    except ValueError as exc:
        raise ParseError(
            line_no=0,
            snippet=s,
            message=f"Cannot parse YYMMDDHHMMSS value: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Per-record parsers
# ---------------------------------------------------------------------------


def _parse_batch(fields: list[str]) -> BatchRecord:
    """Parse @BATCH fields into a BatchRecord."""
    # 13-field or 14-field form
    if len(fields) < 13:
        raise ValueError(f"@BATCH: expected ≥13 fields, got {len(fields)}: {fields}")
    return BatchRecord(
        uut_type=fields[0],
        uut_rev=fields[1],
        fixture_id=int(fields[2]),
        testhead_num=int(fields[3]),
        testhead_type=fields[4],
        process_step=fields[5],
        batch_id=fields[6],
        operator_id=fields[7],
        controller=fields[8],
        testplan_id=fields[9],
        testplan_rev=fields[10],
        parent_panel_type=fields[11],
        parent_panel_rev=fields[12],
        version_label=fields[13] if len(fields) > 13 else None,
    )


def _parse_btest(fields: list[str]) -> tuple[BoardTestRecord, datetime, datetime]:
    """Parse @BTEST fields into (BoardTestRecord, start_dt, end_dt)."""
    if len(fields) < 15:
        raise ValueError(f"@BTEST: expected ≥15 fields, got {len(fields)}: {fields}")
    start_dt = _parse_yymmddhhmmss(int(fields[2]))
    end_dt = _parse_yymmddhhmmss(int(fields[9]))
    operator_id = fields[12]
    shift = fields[13]
    line_id = fields[14]
    btest = BoardTestRecord(
        board_id=fields[0],
        status=BTESTStatus(int(fields[1])),
        start_ts=int(fields[2]),
        duration_s=int(fields[3]),
        multiple_test=fields[4] == "1",
        log_level=fields[5] if fields[5] else "all",
        log_set=int(fields[6]) if fields[6] else 0,
        learning=fields[7] == "1",
        known_good=fields[8] == "1",
        end_ts=int(fields[9]),
        status_qualifier=fields[10] if len(fields) > 10 else "",
        board_number=int(fields[11]) if len(fields) > 11 else 1,
        operator_id=operator_id,
        shift=shift,
        line_id=line_id,
        parent_panel_id=fields[15] if len(fields) > 15 else None,
    )
    return btest, start_dt, end_dt


def _parse_block(fields: list[str]) -> BlockRecord:
    """Parse @BLOCK fields."""
    if len(fields) < 2:
        raise ValueError(f"@BLOCK: expected ≥2 fields, got {len(fields)}: {fields}")
    return BlockRecord(designator=fields[0], status=int(fields[1]))


def _parse_analog(prefix: str, fields: list[str]) -> AnalogRecord:
    """Parse @A-* fields (without limit subrecord; limits must be attached later)."""
    # @A-RES|status|measured|designator → 3 fields after prefix
    type_str = prefix[3:]  # e.g. "RES" from "@A-RES"
    if len(fields) < 3:
        raise ValueError(f"{prefix}: expected ≥3 fields, got {len(fields)}: {fields}")
    record_type = AnalogType(type_str)
    status = AnalogStatus(int(fields[0]))
    measured = float(fields[1])
    designator = fields[2]
    # Limits will be attached by attach_limits; use a placeholder Limits2 or Limits3
    if record_type in LIM2_TYPES:
        limits_placeholder: Limits2 | Limits3 = Limits2(high=0.0, low=0.0)
    else:
        limits_placeholder = Limits3(nominal=0.0, high=0.0, low=0.0)
    return AnalogRecord(
        record_type=record_type,
        status=status,
        measured=measured,
        designator=designator,
        limits=limits_placeholder,
    )


def _attach_lim2(rec: AnalogRecord, fields: list[str]) -> AnalogRecord:
    """Return a new AnalogRecord with Limits2 attached."""
    if len(fields) < 2:
        raise ValueError(f"@LIM2: expected ≥2 fields, got {len(fields)}: {fields}")
    return AnalogRecord(
        record_type=rec.record_type,
        status=rec.status,
        measured=rec.measured,
        designator=rec.designator,
        limits=Limits2(high=float(fields[0]), low=float(fields[1])),
    )


def _attach_lim3(rec: AnalogRecord, fields: list[str]) -> AnalogRecord:
    """Return a new AnalogRecord with Limits3 attached."""
    if len(fields) < 3:
        raise ValueError(f"@LIM3: expected ≥3 fields, got {len(fields)}: {fields}")
    return AnalogRecord(
        record_type=rec.record_type,
        status=rec.status,
        measured=rec.measured,
        designator=rec.designator,
        limits=Limits3(
            nominal=float(fields[0]),
            high=float(fields[1]),
            low=float(fields[2]),
        ),
    )


def _parse_digital(fields: list[str]) -> DigitalRecord:
    """Parse @D-T fields."""
    if len(fields) < 5:
        raise ValueError(f"@D-T: expected ≥5 fields, got {len(fields)}: {fields}")
    return DigitalRecord(
        status=DigitalStatus(int(fields[0])),
        substatus=int(fields[1]),
        failing_vector=int(fields[2]),
        failing_pin_count=int(fields[3]),
        designator=fields[4],
    )


def _parse_shorts(fields: list[str]) -> ShortsRecord:
    """Parse @TS fields (summary only; subrecords not persisted per plan OOS)."""
    if len(fields) < 5:
        raise ValueError(f"@TS: expected ≥5 fields, got {len(fields)}: {fields}")
    return ShortsRecord(
        status=ShortsStatus(int(fields[0])),
        shorts_count=int(fields[1]),
        opens_count=int(fields[2]),
        phantoms_count=int(fields[3]),
        designator=fields[4],
    )


def _parse_tjet(fields: list[str]) -> TestJetRecord:
    """Parse @TJET fields. Status may be zero-padded '00'."""
    if len(fields) < 3:
        raise ValueError(f"@TJET: expected ≥3 fields, got {len(fields)}: {fields}")
    return TestJetRecord(
        status=TwoDigitStatus(int(fields[0])),
        pin_count=int(fields[1]),
        designator=fields[2],
    )


def _parse_pf(fields: list[str], raw_inner: str) -> PinsFailedRecord:
    """Parse @PF outer fields; @PIN subrecord content ignored per OOS rule."""
    # Fields from outer: designator|status|total_pins (nested {@PIN...} stripped)
    if len(fields) < 3:
        raise ValueError(f"@PF: expected ≥3 fields, got {len(fields)}: {fields}")
    designator = fields[0]
    status_val = int(fields[1])
    total_pins = int(fields[2])
    return PinsFailedRecord(
        designator=designator,
        status=status_val,  # type: ignore[arg-type]
        total_pins=total_pins,
        pins=[],  # subrecord content not persisted per OOS rule
    )


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def _read_file(path: Path, encoding_hint: str = "auto") -> tuple[str, str]:
    """Read path, returning (text, encoding_used).

    encoding_hint: 'auto' | 'utf-8' | 'cp1252'
    Raises ParseError (line_no=0) if all decoders fail.
    """
    raw = path.read_bytes()

    if encoding_hint == "auto":
        candidates = ["utf-8", "cp1252"]
    else:
        candidates = [encoding_hint]

    last_exc: Exception | None = None
    for enc in candidates:
        try:
            return raw.decode(enc), enc
        except (UnicodeDecodeError, LookupError) as exc:
            last_exc = exc

    raise ParseError(
        line_no=0,
        snippet=str(path),
        message=f"File undecodable with encodings {candidates}: {last_exc}",
    )


def parse_log_file(
    path: Path, encoding: str = "auto"
) -> tuple[BatchLog, ParseReport]:
    """Parse a single .log file into ``(BatchLog, ParseReport)``.

    The parser is tolerant: per-record errors are caught and appended to
    ``ParseReport.errors``; valid records continue to be processed.

    If the @BTEST timestamp is unparseable, the entire @BTEST and its
    downstream @BLOCKs are skipped for that board.
    """
    report = ParseReport()
    path = Path(path)

    try:
        text, enc_used = _read_file(path, encoding)
    except ParseError as exc:
        report.errors.append(exc)
        # Return an empty BatchLog — no batch record available
        empty_batch = BatchRecord(
            uut_type="UNKNOWN",
            uut_rev="",
            fixture_id=0,
            testhead_num=0,
            process_step="",
            batch_id="",
            operator_id="",
            controller="",
            testplan_id="",
            testplan_rev="",
            parent_panel_type="",
            parent_panel_rev="",
        )
        return BatchLog(batch=empty_batch, boards=[]), report

    # Collect all tokens with their line numbers
    tokens = list(tokenize(text))
    report.record_count = len(tokens)

    batch_rec: BatchRecord | None = None
    boards: list[BoardLog] = []

    # State machine over the token stream
    i = 0
    current_btest: BoardTestRecord | None = None
    current_btest_start_dt: datetime | None = None
    current_btest_end_dt: datetime | None = None
    current_blocks: list[TestBlock] = []
    pending_analog: AnalogRecord | None = None
    pending_block: BlockRecord | None = None
    btest_skip = False  # True when this @BTEST board is being skipped

    while i < len(tokens):
        prefix, fields, line_no = tokens[i]
        i += 1

        try:
            if prefix == "@BATCH":
                batch_rec = _parse_batch(fields)

            elif prefix == "@BTEST":
                # Commit previous board if any
                if current_btest is not None and not btest_skip:
                    # Flush any pending analog
                    if pending_analog is not None and pending_block is not None:
                        current_blocks.append(
                            TestBlock(block=pending_block, record=pending_analog)
                        )
                        pending_analog = None
                        pending_block = None
                    boards.append(
                        _make_board_log(
                            current_btest, current_btest_start_dt, current_btest_end_dt,
                            current_blocks,
                        )
                    )
                elif current_btest is not None and btest_skip:
                    report.errors.append(
                        ParseError(
                            line_no=line_no,
                            snippet=str(fields[:3]),
                            message="@BTEST board skipped due to earlier parse error",
                        )
                    )

                btest_skip = False
                current_blocks = []
                pending_analog = None
                pending_block = None

                try:
                    current_btest, current_btest_start_dt, current_btest_end_dt = (
                        _parse_btest(fields)
                    )
                except ParseError as ts_exc:
                    ts_exc.line_no = line_no
                    report.errors.append(ts_exc)
                    current_btest = None
                    btest_skip = True

            elif prefix == "@BLOCK":
                if btest_skip:
                    continue
                # Flush any pending analog record (it should have got its LIM already)
                if pending_analog is not None and pending_block is not None:
                    current_blocks.append(
                        TestBlock(block=pending_block, record=pending_analog)
                    )
                    pending_analog = None
                    pending_block = None
                pending_block = _parse_block(fields)

            elif prefix.startswith("@A-"):
                if btest_skip:
                    continue
                pending_analog = _parse_analog(prefix, fields)
                # Don't append yet — wait for the @LIM2/@LIM3 that follows

            elif prefix == "@LIM2":
                if btest_skip:
                    continue
                if pending_analog is not None:
                    pending_analog = _attach_lim2(pending_analog, fields)
                    if pending_block is not None:
                        current_blocks.append(
                            TestBlock(block=pending_block, record=pending_analog)
                        )
                    pending_analog = None
                    pending_block = None

            elif prefix == "@LIM3":
                if btest_skip:
                    continue
                if pending_analog is not None:
                    pending_analog = _attach_lim3(pending_analog, fields)
                    if pending_block is not None:
                        current_blocks.append(
                            TestBlock(block=pending_block, record=pending_analog)
                        )
                    pending_analog = None
                    pending_block = None

            elif prefix == "@D-T":
                if btest_skip:
                    continue
                rec = _parse_digital(fields)
                if pending_block is not None:
                    current_blocks.append(TestBlock(block=pending_block, record=rec))
                    pending_block = None

            elif prefix == "@TS":
                if btest_skip:
                    continue
                rec = _parse_shorts(fields)
                if pending_block is not None:
                    current_blocks.append(TestBlock(block=pending_block, record=rec))
                    pending_block = None

            elif prefix == "@TJET":
                if btest_skip:
                    continue
                rec = _parse_tjet(fields)
                if pending_block is not None:
                    current_blocks.append(TestBlock(block=pending_block, record=rec))
                    pending_block = None

            elif prefix == "@PF":
                if btest_skip:
                    continue
                # fields already has nested {@PIN...} stripped by tokenizer
                rec = _parse_pf(fields, "")
                if pending_block is not None:
                    current_blocks.append(TestBlock(block=pending_block, record=rec))
                    pending_block = None
                report.notes.append(
                    f"Line {line_no}: @PF subrecord (@PIN) content not persisted — OOS Phase 1b"
                )

            elif prefix in ("@TS-S", "@TS-D", "@TS-O", "@TS-P"):
                # Subrecords not persisted per plan OOS rule
                report.notes.append(
                    f"Line {line_no}: {prefix} subrecord not persisted — OOS Phase 1b"
                )

        except (ValueError, KeyError, IndexError) as exc:
            report.errors.append(
                ParseError(
                    line_no=line_no,
                    snippet="|".join(fields[:4]),
                    message=str(exc),
                )
            )
            # Reset pending state for this malformed record
            pending_analog = None
            pending_block = None

    # Flush the last board
    if current_btest is not None and not btest_skip:
        if pending_analog is not None and pending_block is not None:
            current_blocks.append(
                TestBlock(block=pending_block, record=pending_analog)
            )
        boards.append(
            _make_board_log(
                current_btest, current_btest_start_dt, current_btest_end_dt,
                current_blocks,
            )
        )
    elif current_btest is None and btest_skip:
        pass  # already recorded the error above

    if batch_rec is None:
        batch_rec = BatchRecord(
            uut_type="UNKNOWN",
            uut_rev="",
            fixture_id=0,
            testhead_num=0,
            process_step="",
            batch_id="",
            operator_id="",
            controller="",
            testplan_id="",
            testplan_rev="",
            parent_panel_type="",
            parent_panel_rev="",
        )

    return BatchLog(batch=batch_rec, boards=boards), report


def _make_board_log(
    btest: BoardTestRecord,
    start_dt: datetime | None,
    end_dt: datetime | None,
    blocks: list[TestBlock],
) -> BoardLog:
    """Construct a BoardLog with a synthetic PanelInstance."""
    panel = PanelInstance(
        serial=btest.board_id,
        panel_position=btest.board_number,
        board_profile_id="unknown",
        operator_id=btest.operator_id,
        line_id=btest.line_id,
        shift=btest.shift,
        timestamp=start_dt or datetime(2026, 1, 1),
    )
    return BoardLog(panel=panel, btest=btest, blocks=blocks)
