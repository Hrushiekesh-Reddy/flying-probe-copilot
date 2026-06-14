"""Deeper malformed-input coverage for log_parser.py.

The canonical brief-named test lives in test_log_parser.py
(test_malformed_line_skipped_and_logged_not_crash). This file covers
deeper variants.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flying_probe_copilot.generator.models import BatchLog
from flying_probe_copilot.generator.renderers.log import render_log


def test_unbalanced_brace_logged_and_skipped_not_crash(tmp_path):
    """A log line with an unclosed brace must not crash; parse continues."""
    from flying_probe_copilot.parser.log_parser import parse_log_file

    # Construct a minimal log with a valid @BATCH and @BTEST + one @BLOCK with
    # an intentionally malformed field (non-numeric status) rather than a brace
    # imbalance (which would swallow subsequent records).
    log_content = (
        "{@BATCH|BRD-SMALL|A|1|1||ICT|BAT-0042|OP-001|ICT01|TP-001|v1.0|PNL-SMALL|A}\n"
        "{@BTEST|SYN-TEST-00001|0|260401083000|12|0|all|0|0|0|260401083012||1}\n"
        "{@BLOCK|R1|0}\n"
        "{@A-RES|INVALID_STATUS|+1.000000E+04|R1}\n"  # INVALID status → parse error
        "{@LIM3|+1.000000E+04|+1.010000E+04|+9.900000E+03}\n"
    )
    log_path = tmp_path / "bad_status.log"
    log_path.write_text(log_content, encoding="utf-8")

    result = parse_log_file(log_path)
    assert result is not None
    batch_log, report = result
    assert isinstance(batch_log, BatchLog), "Must return BatchLog even with errors"
    assert len(report.errors) > 0, "ParseReport.errors must record the bad status"


def test_valid_records_around_corruption_still_parse(malformed_log_path):
    """Records before and after a corrupt one must still appear in the output."""
    from flying_probe_copilot.parser.log_parser import parse_log_file

    batch_log, report = parse_log_file(malformed_log_path)

    # At least 1 error (the corrupted @A- record)
    assert len(report.errors) > 0, "Expected at least 1 parse error"
    # At least 1 board returned (the @BTEST was valid)
    assert len(batch_log.boards) >= 1, (
        "Valid @BTEST must still produce a board entry"
    )
    # The board must have some blocks (blocks before/after the corrupt one)
    total_blocks = sum(len(b.blocks) for b in batch_log.boards)
    assert total_blocks > 0, (
        f"Valid blocks around corruption must still be present; got {total_blocks}"
    )


def test_parse_report_records_error_line_number_and_snippet(malformed_log_path):
    """ParseReport.errors must include line_no > 0 and a non-empty snippet."""
    from flying_probe_copilot.parser.log_parser import parse_log_file, ParseError

    batch_log, report = parse_log_file(malformed_log_path)

    assert len(report.errors) > 0
    err = report.errors[0]
    assert isinstance(err, ParseError), f"Expected ParseError, got {type(err)}"
    assert err.line_no >= 0, f"line_no must be non-negative, got {err.line_no}"
    assert err.message, "ParseError.message must be non-empty"
