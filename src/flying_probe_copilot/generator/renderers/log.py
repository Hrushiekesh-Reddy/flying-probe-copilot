"""Render a ``BatchLog`` to real-format Keysight i3070 text.

Lexical rules implemented (per ``specs/synthetic-log-generator.md``):

* Every record is wrapped in ``{...}``.
* Fields separated by ``|``.
* Empty optional fields render as adjacent ``||`` — never omitted.
* All measured / limit floats render via ``"{:+.6E}".format(value)``:
  signed mantissa, six-digit fraction, capital ``E``, signed two-digit
  exponent. Per Revision 1 #MINOR-10.
* Default encoding is ``cp1252`` with ``\\r\\n`` line endings (per the
  dominant i3070 ecosystem convention). Pass ``encoding="utf-8"`` to switch
  to UTF-8 + bare ``\\n``.
* Record-per-line: top-level records inside ``@BTEST`` emit on their own
  lines; limits subrecords (``@LIM2``/``@LIM3``) follow immediately on the
  next line, paired with their analog parent.

This renderer is a pure serializer — it does NOT derive ``@BTEST`` status;
callers must do that upstream via ``models.derive_btest_status``.
"""

from __future__ import annotations

from pathlib import Path

from ..models import (
    AnalogRecord,
    BatchLog,
    BoardLog,
    BoardTestRecord,
    DigitalRecord,
    Limits2,
    Limits3,
    PinsFailedRecord,
    ShortsRecord,
    TestBlock,
    TestJetRecord,
)

# ---------------------------------------------------------------------------
# Field formatters
# ---------------------------------------------------------------------------


def _fmt_float(x: float) -> str:
    """Render ``x`` in the canonical scientific notation."""
    return f"{x:+.6E}"


def _fmt_bool(b: bool) -> str:
    """Render a bool as ``0``/``1``."""
    return "1" if b else "0"


def _fmt_two_digit_status(code: int) -> str:
    """Render a TwoDigitStatus / shorts substatus zero-padded to 2 digits."""
    return f"{int(code):02d}"


# ---------------------------------------------------------------------------
# Record renderers
# ---------------------------------------------------------------------------


def _render_batch(bl: BatchLog) -> str:
    b = bl.batch
    fields = [
        b.uut_type,
        b.uut_rev,
        str(b.fixture_id),
        str(b.testhead_num),
        b.testhead_type,
        b.process_step,
        b.batch_id,
        b.operator_id,
        b.controller,
        b.testplan_id,
        b.testplan_rev,
        b.parent_panel_type,
        b.parent_panel_rev,
    ]
    if b.version_label is not None:
        fields.append(b.version_label)
    return "{@BATCH|" + "|".join(fields) + "}"


def _render_btest(btr: BoardTestRecord) -> str:
    fields = [
        btr.board_id,
        str(int(btr.status)),
        str(btr.start_ts),
        str(btr.duration_s),
        _fmt_bool(btr.multiple_test),
        btr.log_level,
        str(btr.log_set),
        _fmt_bool(btr.learning),
        _fmt_bool(btr.known_good),
        str(btr.end_ts),
        btr.status_qualifier,
        str(btr.board_number),
        btr.operator_id,
        btr.shift,
        btr.line_id,
    ]
    if btr.parent_panel_id is not None:
        fields.append(btr.parent_panel_id)
    return "{@BTEST|" + "|".join(fields) + "}"


def _render_block(tb: TestBlock) -> str:
    return f"{{@BLOCK|{tb.block.designator}|{int(tb.block.status)}}}"


def _render_analog(rec: AnalogRecord) -> list[str]:
    """Render an analog record AND its limits subrecord on the next line."""
    head = (
        f"{{@A-{rec.record_type.value}"
        f"|{int(rec.status)}"
        f"|{_fmt_float(rec.measured)}"
        f"|{rec.designator}}}"
    )
    if isinstance(rec.limits, Limits3):
        lim = (
            f"{{@LIM3|{_fmt_float(rec.limits.nominal)}"
            f"|{_fmt_float(rec.limits.high)}"
            f"|{_fmt_float(rec.limits.low)}}}"
        )
    elif isinstance(rec.limits, Limits2):
        lim = f"{{@LIM2|{_fmt_float(rec.limits.high)}|{_fmt_float(rec.limits.low)}}}"
    else:  # pragma: no cover — model_validator prevents this
        raise TypeError(f"Unknown limits type: {type(rec.limits).__name__}")
    return [head, lim]


def _render_digital(rec: DigitalRecord) -> str:
    return (
        f"{{@D-T|{int(rec.status)}"
        f"|{rec.substatus}"
        f"|{rec.failing_vector}"
        f"|{rec.failing_pin_count}"
        f"|{rec.designator}}}"
    )


def _render_shorts(rec: ShortsRecord) -> str:
    return (
        f"{{@TS|{int(rec.status)}"
        f"|{rec.shorts_count}"
        f"|{rec.opens_count}"
        f"|{rec.phantoms_count}"
        f"|{rec.designator}}}"
    )


def _render_tjet(rec: TestJetRecord) -> str:
    return f"{{@TJET|{_fmt_two_digit_status(int(rec.status))}|{rec.pin_count}|{rec.designator}}}"


def _render_pf(rec: PinsFailedRecord) -> str:
    pin_list = f"{{@PIN\\{len(rec.pins)}" + ("|" + "|".join(rec.pins) if rec.pins else "") + "}"
    return f"{{@PF|{rec.designator}|{rec.status}|{rec.total_pins}{pin_list}}}"


def _render_test_block(tb: TestBlock) -> list[str]:
    lines = [_render_block(tb)]
    r = tb.record
    if isinstance(r, AnalogRecord):
        lines.extend(_render_analog(r))
    elif isinstance(r, DigitalRecord):
        lines.append(_render_digital(r))
    elif isinstance(r, ShortsRecord):
        lines.append(_render_shorts(r))
    elif isinstance(r, TestJetRecord):
        lines.append(_render_tjet(r))
    elif isinstance(r, PinsFailedRecord):
        lines.append(_render_pf(r))
    else:  # pragma: no cover
        raise TypeError(f"Unknown record type: {type(r).__name__}")
    return lines


def _render_board(b: BoardLog) -> list[str]:
    lines = [_render_btest(b.btest)]
    for tb in b.blocks:
        lines.extend(_render_test_block(tb))
    return lines


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def render_log(bl: BatchLog, path: Path | str, *, encoding: str = "cp1252") -> None:
    """Write the i3070-format text of ``bl`` to ``path``.

    Line endings: CRLF for cp1252 default, LF for utf-8. Writing is binary to
    guarantee exact byte content (no platform translation).
    """
    line_sep = b"\n" if encoding.lower().startswith("utf") else b"\r\n"
    lines: list[str] = [_render_batch(bl)]
    for board in bl.boards:
        lines.extend(_render_board(board))
    buf = line_sep.join(line.encode(encoding) for line in lines) + line_sep
    Path(path).write_bytes(buf)
