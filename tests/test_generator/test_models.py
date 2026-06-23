"""Tests for ``flying_probe_copilot.generator.models``.

Phase 1a Step A4 — RED phase: all of these MUST fail before models.py exists.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# BoardProfile
# ---------------------------------------------------------------------------


def test_board_profile_validates_minimum_fields(small_profile_dict):
    """A valid dict yields a BoardProfile; missing required field raises."""
    from flying_probe_copilot.generator.models import BoardProfile

    bp = BoardProfile(**small_profile_dict)
    assert bp.id == "small"
    assert bp.component_count == 50
    assert bp.net_count == 80
    assert bp.typical_test_count == 120

    bad = dict(small_profile_dict)
    bad.pop("component_count")
    with pytest.raises(ValidationError):
        BoardProfile(**bad)


# ---------------------------------------------------------------------------
# PanelInstance
# ---------------------------------------------------------------------------


def test_panel_instance_serial_format(fixed_timestamp):
    """PanelInstance accepts the canonical SYN-YYYYWww-NNNNN serial form."""
    from flying_probe_copilot.generator.models import PanelInstance

    p = PanelInstance(
        serial="SYN-2026W14-00001",
        panel_position=1,
        board_profile_id="small",
        operator_id="OP-007",
        line_id="LINE-A",
        shift="A",
        timestamp=fixed_timestamp,
    )
    assert p.serial.startswith("SYN-")
    assert p.shift == "A"


# ---------------------------------------------------------------------------
# BatchRecord
# ---------------------------------------------------------------------------


def test_batch_record_field_count():
    """BatchRecord exposes both the 13-field and 14-field forms.

    The 14-field form includes a ``version_label``; the 13-field form does not.
    """
    from flying_probe_copilot.generator.models import BatchRecord

    minimal = BatchRecord(
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
    assert minimal.version_label is None

    versioned = BatchRecord(
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
        version_label="v2.4.1",
    )
    assert versioned.version_label == "v2.4.1"


# ---------------------------------------------------------------------------
# BoardTestRecord (@BTEST)
# ---------------------------------------------------------------------------


def test_btest_record_status_uses_intenum():
    """BoardTestRecord.status is the BTESTStatus IntEnum."""
    from flying_probe_copilot.generator.models import (
        BoardTestRecord,
        BTESTStatus,
    )

    btr = BoardTestRecord(
        board_id="SYN-2026W14-00001",
        status=BTESTStatus.PASS,
        start_ts=260401083000,
        duration_s=12,
        end_ts=260401083012,
        board_number=1,
        operator_id="OP-001",
        shift="A",
        line_id="LINE-A",
    )
    assert btr.status == 0
    assert btr.status is BTESTStatus.PASS


def test_btest_record_requires_operator_id():
    """BoardTestRecord must require operator_id — omitting it raises ValidationError."""
    import pytest
    from pydantic import ValidationError

    from flying_probe_copilot.generator.models import BoardTestRecord, BTESTStatus

    with pytest.raises(ValidationError):
        BoardTestRecord(
            board_id="SYN-2026W14-00001",
            status=BTESTStatus.PASS,
            start_ts=260401083000,
            duration_s=12,
            end_ts=260401083012,
            board_number=1,
            # operator_id deliberately omitted
        )


def test_btest_record_operator_id_rejects_empty_string():
    """BoardTestRecord.operator_id must reject empty string (Field min_length=1)."""
    import pytest
    from pydantic import ValidationError

    from flying_probe_copilot.generator.models import BoardTestRecord, BTESTStatus

    with pytest.raises(ValidationError):
        BoardTestRecord(
            board_id="SYN-2026W14-00001",
            status=BTESTStatus.PASS,
            start_ts=260401083000,
            duration_s=12,
            end_ts=260401083012,
            board_number=1,
            operator_id="",
            shift="A",
            line_id="LINE-A",
        )


def test_btest_record_requires_shift_field():
    """BoardTestRecord must require an explicit shift field (BUG-007 close)."""
    import pytest
    from pydantic import ValidationError

    from flying_probe_copilot.generator.models import BoardTestRecord, BTESTStatus

    with pytest.raises(ValidationError):
        BoardTestRecord(
            board_id="SYN-X",
            status=BTESTStatus.PASS,
            start_ts=260401083000,
            duration_s=12,
            end_ts=260401083012,
            board_number=1,
            operator_id="OP-001",
            line_id="LINE-A",
        )


def test_btest_record_shift_rejects_invalid_letter():
    """BoardTestRecord.shift must be Literal['A','B','C']."""
    import pytest
    from pydantic import ValidationError

    from flying_probe_copilot.generator.models import BoardTestRecord, BTESTStatus

    with pytest.raises(ValidationError):
        BoardTestRecord(
            board_id="SYN-X",
            status=BTESTStatus.PASS,
            start_ts=260401083000,
            duration_s=12,
            end_ts=260401083012,
            board_number=1,
            operator_id="OP-001",
            shift="D",  # not in Literal["A","B","C"]
            line_id="LINE-A",
        )


def test_btest_record_line_id_rejects_empty_string():
    """BoardTestRecord.line_id must reject empty string (Field min_length=1)."""
    import pytest
    from pydantic import ValidationError

    from flying_probe_copilot.generator.models import BoardTestRecord, BTESTStatus

    with pytest.raises(ValidationError):
        BoardTestRecord(
            board_id="SYN-X",
            status=BTESTStatus.PASS,
            start_ts=260401083000,
            duration_s=12,
            end_ts=260401083012,
            board_number=1,
            operator_id="OP-001",
            shift="A",
            line_id="",
        )


def test_btest_status_intenum_includes_all_documented_codes():
    """All status codes from the spec's BTEST status vocabulary are present."""
    from flying_probe_copilot.generator.models import BTESTStatus

    expected = {
        "PASS": 0,
        "FAIL_UNCATEGORIZED": 1,
        "FAIL_PIN": 2,
        "FAIL_LEARN": 3,
        "FAIL_SHORTS": 4,
        "FAIL_ANALOG": 6,
        "FAIL_POWER": 7,
        "FAIL_DIGITAL": 8,
        "FAIL_FUNCTIONAL": 9,
        "FAIL_PRE_SHORTS": 10,
        "FAIL_HANDLER": 11,
        "FAIL_BARCODE": 12,
        "XD_OUT": 13,
        "FAIL_TJET": 14,
        "FAIL_POLARITY": 15,
        "FAIL_CCHK": 16,
        "FAIL_ANALOG_CLUSTER": 17,
        "RUNTIME_ERROR": 80,
        "ABORTED_STOP": 81,
        "ABORTED_BREAK": 82,
    }
    for name, value in expected.items():
        member = getattr(BTESTStatus, name)
        assert int(member) == value, f"{name} should be {value}, got {int(member)}"


# ---------------------------------------------------------------------------
# AnalogRecord + LIM2 / LIM3 tagged union
# ---------------------------------------------------------------------------


def test_analog_record_limits_tagged_union():
    """A-RES requires Limits3; A-DIO requires Limits2 (per Revision 1 #9)."""
    from flying_probe_copilot.generator.models import (
        AnalogRecord,
        AnalogStatus,
        AnalogType,
        Limits2,
        Limits3,
    )

    # Valid: A-RES with Limits3 (nominal + high + low)
    res = AnalogRecord(
        record_type=AnalogType.RES,
        status=AnalogStatus.PASS,
        measured=10000.0,
        designator="R12",
        limits=Limits3(nominal=10000.0, high=10100.0, low=9900.0),
    )
    assert res.status == 0
    assert isinstance(res.limits, Limits3)

    # Valid: A-DIO with Limits2 (high + low only)
    dio = AnalogRecord(
        record_type=AnalogType.DIO,
        status=AnalogStatus.PASS,
        measured=0.7,
        designator="D1",
        limits=Limits2(high=0.8, low=0.5),
    )
    assert isinstance(dio.limits, Limits2)


def test_analog_record_rejects_wrong_limit_type_for_record_type():
    """A-RES must not accept Limits2; A-DIO must not accept Limits3 (Rev1 #9)."""
    from flying_probe_copilot.generator.models import (
        AnalogRecord,
        AnalogStatus,
        AnalogType,
        Limits2,
        Limits3,
    )

    # A-RES is a LIM3 type — Limits2 must be rejected.
    with pytest.raises(ValidationError):
        AnalogRecord(
            record_type=AnalogType.RES,
            status=AnalogStatus.PASS,
            measured=10000.0,
            designator="R12",
            limits=Limits2(high=10100.0, low=9900.0),
        )

    # A-DIO is a LIM2 type — Limits3 must be rejected.
    with pytest.raises(ValidationError):
        AnalogRecord(
            record_type=AnalogType.DIO,
            status=AnalogStatus.PASS,
            measured=0.7,
            designator="D1",
            limits=Limits3(nominal=0.65, high=0.8, low=0.5),
        )


# ---------------------------------------------------------------------------
# Shorts records / destinations
# ---------------------------------------------------------------------------


def test_short_destination_pairs_well_formed():
    """ShortDestination requires both a node name and a numeric deviation."""
    from flying_probe_copilot.generator.models import ShortDestination

    sd = ShortDestination(dest_node="+3V3", deviation=0.001)
    assert sd.dest_node == "+3V3"
    assert sd.deviation == pytest.approx(0.001)

    with pytest.raises(ValidationError):
        ShortDestination(dest_node="+3V3")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# derive_btest_status — Revision 1 #BLOCKER-3 categorical precedence
# ---------------------------------------------------------------------------


def _make_block(record):
    """Helper: build a TestBlock around a single child record."""
    from flying_probe_copilot.generator.models import BlockRecord, TestBlock

    block = BlockRecord(designator=getattr(record, "designator", "x"), status=int(record.status))
    return TestBlock(block=block, record=record)


def test_pass_only_returns_PASS():
    from flying_probe_copilot.generator.models import (
        AnalogRecord,
        AnalogStatus,
        AnalogType,
        BTESTStatus,
        Limits3,
        derive_btest_status,
    )

    rec = AnalogRecord(
        record_type=AnalogType.RES,
        status=AnalogStatus.PASS,
        measured=10000.0,
        designator="R1",
        limits=Limits3(nominal=10000.0, high=10100.0, low=9900.0),
    )
    assert derive_btest_status([_make_block(rec)]) is BTESTStatus.PASS


def test_any_shorts_failure_returns_FAIL_SHORTS_even_with_other_failures():
    from flying_probe_copilot.generator.models import (
        AnalogRecord,
        AnalogStatus,
        AnalogType,
        BTESTStatus,
        Limits3,
        ShortsRecord,
        ShortsStatus,
        derive_btest_status,
    )

    failing_analog = AnalogRecord(
        record_type=AnalogType.RES,
        status=AnalogStatus.FAIL,
        measured=20000.0,
        designator="R1",
        limits=Limits3(nominal=10000.0, high=10100.0, low=9900.0),
    )
    failing_shorts = ShortsRecord(
        status=ShortsStatus.FAIL,
        shorts_count=1,
        opens_count=0,
        phantoms_count=0,
    )
    blocks = [_make_block(failing_analog), _make_block(failing_shorts)]
    assert derive_btest_status(blocks) is BTESTStatus.FAIL_SHORTS


def test_analog_failure_returns_FAIL_ANALOG_when_no_shorts():
    from flying_probe_copilot.generator.models import (
        AnalogRecord,
        AnalogStatus,
        AnalogType,
        BTESTStatus,
        Limits3,
        derive_btest_status,
    )

    rec = AnalogRecord(
        record_type=AnalogType.RES,
        status=AnalogStatus.FAIL,
        measured=20000.0,
        designator="R1",
        limits=Limits3(nominal=10000.0, high=10100.0, low=9900.0),
    )
    assert derive_btest_status([_make_block(rec)]) is BTESTStatus.FAIL_ANALOG


def test_digital_failure_when_only_digital_block_failed():
    from flying_probe_copilot.generator.models import (
        BTESTStatus,
        DigitalRecord,
        DigitalStatus,
        derive_btest_status,
    )

    rec = DigitalRecord(
        status=DigitalStatus.FAIL,
        substatus=0b000001,
        failing_vector=12,
        failing_pin_count=1,
        designator="U7",
    )
    assert derive_btest_status([_make_block(rec)]) is BTESTStatus.FAIL_DIGITAL


def test_pin_failure_when_only_pf_record_failed():
    from flying_probe_copilot.generator.models import (
        BTESTStatus,
        PinsFailedRecord,
        derive_btest_status,
    )

    rec = PinsFailedRecord(
        designator="probe_test",
        status=1,
        total_pins=2,
        pins=["10101", "10102"],
    )
    assert derive_btest_status([_make_block(rec)]) is BTESTStatus.FAIL_PIN


def test_environmental_codes_not_derived():
    """Environmental statuses (11, 12, 13, 80, 81, 82) are NEVER derived."""
    from flying_probe_copilot.generator.models import (
        BTESTStatus,
        DigitalRecord,
        DigitalStatus,
        derive_btest_status,
    )

    # Any failing subtest gives a derived status — never an environmental one.
    rec = DigitalRecord(
        status=DigitalStatus.FAIL_FATAL,
        substatus=0,
        failing_vector=0,
        failing_pin_count=0,
        designator="U7",
    )
    derived = derive_btest_status([_make_block(rec)])
    assert derived not in (
        BTESTStatus.FAIL_HANDLER,
        BTESTStatus.FAIL_BARCODE,
        BTESTStatus.XD_OUT,
        BTESTStatus.RUNTIME_ERROR,
        BTESTStatus.ABORTED_STOP,
        BTESTStatus.ABORTED_BREAK,
    )
