"""Tests for the three renderers (log/csv/json).

Phase 1a Step F1 — RED phase. Tests are grouped by renderer.
"""

from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime

import pytest


# ---------------------------------------------------------------------------
# Helper: build a tiny but valid BatchLog using only public model APIs.
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_batch_log():
    from flying_probe_copilot.generator.models import (
        AnalogRecord,
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
        PanelInstance,
        ShortsRecord,
        ShortsStatus,
        TestBlock,
    )

    panel = PanelInstance(
        serial="SYN-2026W14-00001",
        panel_position=1,
        board_profile_id="small",
        operator_id="OP-007",
        line_id="LINE-A",
        shift="A",
        timestamp=datetime(2026, 4, 1, 8, 30, 0),
    )

    btest = BoardTestRecord(
        board_id=panel.serial,
        status=BTESTStatus.PASS,
        start_ts=260401083000,
        duration_s=12,
        end_ts=260401083012,
        board_number=1,
        operator_id="OP-001",
        shift="A",
        line_id="LINE-A",
    )

    blocks = [
        TestBlock(
            block=BlockRecord(designator="R12", status=0),
            record=AnalogRecord(
                record_type=AnalogType.RES,
                status=AnalogStatus.PASS,
                measured=10000.0,
                designator="R12",
                limits=Limits3(nominal=10000.0, high=10100.0, low=9900.0),
            ),
        ),
        TestBlock(
            block=BlockRecord(designator="D1", status=0),
            record=AnalogRecord(
                record_type=AnalogType.DIO,
                status=AnalogStatus.PASS,
                measured=0.7,
                designator="D1",
                limits=Limits2(high=0.8, low=0.5),
            ),
        ),
        TestBlock(
            block=BlockRecord(designator="U7", status=0),
            record=DigitalRecord(
                status=DigitalStatus.PASS,
                substatus=0,
                failing_vector=0,
                failing_pin_count=0,
                designator="U7",
            ),
        ),
        TestBlock(
            block=BlockRecord(designator="shorts", status=0),
            record=ShortsRecord(
                status=ShortsStatus.PASS,
                shorts_count=0,
                opens_count=0,
                phantoms_count=0,
            ),
        ),
    ]

    board_log = BoardLog(panel=panel, btest=btest, blocks=blocks)
    batch = BatchRecord(
        uut_type="BRD-X",
        uut_rev="A",
        fixture_id=1,
        testhead_num=1,
        process_step="ICT",
        batch_id="BAT-0001",
        operator_id="OP-007",
        controller="ICT01",
        testplan_id="TP-001",
        testplan_rev="A",
        parent_panel_type="PNL-X",
        parent_panel_rev="A",
    )
    return BatchLog(batch=batch, boards=[board_log])


# ===========================================================================
# Log renderer
# ===========================================================================


class TestLogRenderer:
    def test_emits_balanced_braces(self, sample_batch_log, tmp_path):
        from flying_probe_copilot.generator.renderers.log import render_log

        out = tmp_path / "x.log"
        render_log(sample_batch_log, out)
        text = out.read_text(encoding="cp1252")
        assert text.count("{") == text.count("}"), "braces must balance"

    def test_emits_scientific_notation_floats_with_six_mantissa_digits(
        self, sample_batch_log, tmp_path
    ):
        from flying_probe_copilot.generator.renderers.log import render_log

        out = tmp_path / "x.log"
        render_log(sample_batch_log, out)
        text = out.read_text(encoding="cp1252")
        # Every numeric measured / lim field uses the form +1.234567E+04.
        pattern = re.compile(r"[+-]\d\.\d{6}E[+-]\d{2}")
        floats_found = pattern.findall(text)
        assert floats_found, "expected scientific-notation floats in output"

    def test_emits_timestamp_in_yymmddhhmmss_format(self, sample_batch_log, tmp_path):
        from flying_probe_copilot.generator.renderers.log import render_log

        out = tmp_path / "x.log"
        render_log(sample_batch_log, out)
        text = out.read_text(encoding="cp1252")
        # 260401083000 must appear (start_ts) and 260401083012 (end_ts).
        assert "260401083000" in text
        assert "260401083012" in text

    def test_emits_lim3_after_a_res(self, sample_batch_log, tmp_path):
        from flying_probe_copilot.generator.renderers.log import render_log

        out = tmp_path / "x.log"
        render_log(sample_batch_log, out)
        text = out.read_text(encoding="cp1252")
        # @A-RES line must be immediately followed (next line) by @LIM3.
        lines = [ln for ln in text.splitlines() if ln]
        for i, ln in enumerate(lines):
            if ln.startswith("{@A-RES"):
                assert lines[i + 1].startswith("{@LIM3"), (
                    f"expected @LIM3 immediately after @A-RES, got {lines[i + 1]!r}"
                )
                return
        pytest.fail("did not find an @A-RES line in output")

    def test_emits_lim2_after_a_dio(self, sample_batch_log, tmp_path):
        from flying_probe_copilot.generator.renderers.log import render_log

        out = tmp_path / "x.log"
        render_log(sample_batch_log, out)
        text = out.read_text(encoding="cp1252")
        lines = [ln for ln in text.splitlines() if ln]
        for i, ln in enumerate(lines):
            if ln.startswith("{@A-DIO"):
                assert lines[i + 1].startswith("{@LIM2"), (
                    f"expected @LIM2 immediately after @A-DIO, got {lines[i + 1]!r}"
                )
                return
        pytest.fail("did not find an @A-DIO line in output")

    def test_emits_crlf_line_endings_by_default(self, sample_batch_log, tmp_path):
        """Revision 1 #WARNING-4 — read binary, assert CRLF (no bare LF)."""
        from flying_probe_copilot.generator.renderers.log import render_log

        out = tmp_path / "x.log"
        render_log(sample_batch_log, out)
        raw = out.read_bytes()
        assert b"\r\n" in raw
        # No bare LF that isn't preceded by CR.
        assert b"\n" not in raw.replace(b"\r\n", b"")

    def test_emits_utf8_lf_when_encoding_flag_set(self, sample_batch_log, tmp_path):
        from flying_probe_copilot.generator.renderers.log import render_log

        out = tmp_path / "x.log"
        render_log(sample_batch_log, out, encoding="utf-8")
        raw = out.read_bytes()
        assert b"\n" in raw
        assert b"\r\n" not in raw

    def test_btest_status_derived_from_worst_subtest(self, tmp_path):
        """When one block contains a shorts failure, the @BTEST field shows 4."""
        from flying_probe_copilot.generator.models import (
            BatchLog,
            BatchRecord,
            BlockRecord,
            BoardLog,
            BoardTestRecord,
            BTESTStatus,
            PanelInstance,
            ShortsRecord,
            ShortsStatus,
            TestBlock,
            derive_btest_status,
        )
        from flying_probe_copilot.generator.renderers.log import render_log

        panel = PanelInstance(
            serial="SYN-2026W14-00009",
            panel_position=1,
            board_profile_id="small",
            operator_id="OP-007",
            line_id="LINE-A",
            shift="A",
            timestamp=datetime(2026, 4, 1, 8, 30, 0),
        )
        blocks = [
            TestBlock(
                block=BlockRecord(designator="shorts", status=1),
                record=ShortsRecord(
                    status=ShortsStatus.FAIL,
                    shorts_count=1,
                    opens_count=0,
                    phantoms_count=0,
                ),
            ),
        ]
        derived = derive_btest_status(blocks)
        assert derived == BTESTStatus.FAIL_SHORTS

        btest = BoardTestRecord(
            board_id=panel.serial,
            status=derived,
            start_ts=260401083000,
            duration_s=2,
            end_ts=260401083002,
            board_number=1,
            operator_id="OP-007",
            shift="A",
            line_id="LINE-A",
        )
        board_log = BoardLog(panel=panel, btest=btest, blocks=blocks)
        batch = BatchRecord(
            uut_type="BRD-X",
            uut_rev="A",
            fixture_id=1,
            testhead_num=1,
            process_step="ICT",
            batch_id="BAT-0001",
            operator_id="OP-007",
            controller="ICT01",
            testplan_id="TP-001",
            testplan_rev="A",
            parent_panel_type="PNL-X",
            parent_panel_rev="A",
        )
        out = tmp_path / "x.log"
        render_log(BatchLog(batch=batch, boards=[board_log]), out)
        text = out.read_text(encoding="cp1252")
        # The @BTEST line should have ...|4|... in the status slot.
        btest_line = next(
            ln for ln in text.splitlines() if ln.startswith("{@BTEST")
        )
        # Fields: @BTEST | board_id | status | ...
        fields = btest_line[1:-1].split("|")  # strip { } then split
        assert fields[2] == "4", f"expected status field '4', got {fields[2]!r}"

    def test_btest_renders_operator_id_at_position_12(self, sample_batch_log, tmp_path):
        """operator_id must appear at index 13 in the pipe-split @BTEST line.

        The @BTEST line starts with {@BTEST, so split[0]="@BTEST" and the first
        field is split[1]=board_id. operator_id is the 13th field after @BTEST
        (zero-indexed as field[12]), so split[13]=="OP-001".
        """
        from flying_probe_copilot.generator.renderers.log import render_log

        out = tmp_path / "op_id_pos.log"
        render_log(sample_batch_log, out)
        text = out.read_text(encoding="cp1252")
        btest_line = next(ln for ln in text.splitlines() if ln.startswith("{@BTEST"))
        split = btest_line[1:-1].split("|")
        assert split[13] == "OP-001", (
            f"Expected operator_id 'OP-001' at split[13], got {split[13]!r}. "
            f"Full split: {split}"
        )


# ===========================================================================
# CSV renderer
# ===========================================================================


class TestCsvRenderer:
    def test_one_row_per_test_record(self, sample_batch_log, tmp_path):
        from flying_probe_copilot.generator.renderers.csv_ import render_csv

        out = tmp_path / "results.csv"
        render_csv(sample_batch_log, out)
        with out.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        # sample_batch_log has 1 board x 4 blocks = 4 rows.
        assert len(rows) == 4

    def test_csv_parseable_by_stdlib(self, sample_batch_log, tmp_path):
        from flying_probe_copilot.generator.renderers.csv_ import render_csv

        out = tmp_path / "results.csv"
        render_csv(sample_batch_log, out)
        text = out.read_text(encoding="utf-8")
        # If this round-trips, stdlib accepts the file.
        rows = list(csv.reader(io.StringIO(text)))
        assert rows, "csv must contain at least a header row"

    def test_columns_include_serial_block_record_type_status_measured(
        self, sample_batch_log, tmp_path
    ):
        from flying_probe_copilot.generator.renderers.csv_ import render_csv

        out = tmp_path / "results.csv"
        render_csv(sample_batch_log, out)
        with out.open("r", newline="", encoding="utf-8") as f:
            header = next(csv.reader(f))
        for required in (
            "serial",
            "block_designator",
            "record_type",
            "status",
            "measured",
        ):
            assert required in header, f"missing column {required!r} in {header}"


# ===========================================================================
# JSON renderer
# ===========================================================================


class TestJsonRenderer:
    def test_json_parseable_by_stdlib(self, sample_batch_log, tmp_path):
        from flying_probe_copilot.generator.renderers.json_ import render_json

        out = tmp_path / "results.json"
        render_json(sample_batch_log, out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "batch" in data
        assert "boards" in data
        assert isinstance(data["boards"], list)

    def test_json_round_trips_through_pydantic(self, sample_batch_log, tmp_path):
        from flying_probe_copilot.generator.models import BatchLog
        from flying_probe_copilot.generator.renderers.json_ import render_json

        out = tmp_path / "results.json"
        render_json(sample_batch_log, out)
        text = out.read_text(encoding="utf-8")
        clone = BatchLog.model_validate_json(text)
        assert clone.boards[0].panel.serial == sample_batch_log.boards[0].panel.serial
