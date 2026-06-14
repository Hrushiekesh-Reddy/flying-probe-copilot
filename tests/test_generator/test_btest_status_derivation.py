"""Integration-shaped tests for ``derive_btest_status``.

Phase 1a Step G1. Belt-and-suspenders alongside the unit tests already in
``test_models.py``. The shared helper builds a list of TestBlocks and feeds
them through the precedence algorithm.
"""

from __future__ import annotations


def _block_with(record):
    from flying_probe_copilot.generator.models import BlockRecord, TestBlock

    designator = getattr(record, "designator", "x")
    block = BlockRecord(designator=designator, status=int(record.status))
    return TestBlock(block=block, record=record)


# ---------------------------------------------------------------------------
# Single-category scenarios.
# ---------------------------------------------------------------------------


def test_pass_only_records_produce_btest_status_0():
    from flying_probe_copilot.generator.models import (
        AnalogRecord,
        AnalogStatus,
        AnalogType,
        BTESTStatus,
        DigitalRecord,
        DigitalStatus,
        Limits3,
        ShortsRecord,
        ShortsStatus,
        derive_btest_status,
    )

    blocks = [
        _block_with(
            AnalogRecord(
                record_type=AnalogType.RES,
                status=AnalogStatus.PASS,
                measured=10000.0,
                designator="R1",
                limits=Limits3(nominal=10000.0, high=10100.0, low=9900.0),
            )
        ),
        _block_with(
            DigitalRecord(
                status=DigitalStatus.PASS,
                substatus=0,
                failing_vector=0,
                failing_pin_count=0,
                designator="U1",
            )
        ),
        _block_with(
            ShortsRecord(
                status=ShortsStatus.PASS,
                shorts_count=0,
                opens_count=0,
                phantoms_count=0,
            )
        ),
    ]
    assert derive_btest_status(blocks) == BTESTStatus.PASS


def test_shorts_failure_produces_btest_status_4():
    from flying_probe_copilot.generator.models import (
        BTESTStatus,
        ShortsRecord,
        ShortsStatus,
        derive_btest_status,
    )

    blocks = [
        _block_with(
            ShortsRecord(
                status=ShortsStatus.FAIL,
                shorts_count=1,
                opens_count=0,
                phantoms_count=0,
            )
        )
    ]
    assert derive_btest_status(blocks) == BTESTStatus.FAIL_SHORTS == 4


def test_analog_failure_only_produces_btest_status_6():
    from flying_probe_copilot.generator.models import (
        AnalogRecord,
        AnalogStatus,
        AnalogType,
        BTESTStatus,
        Limits3,
        derive_btest_status,
    )

    blocks = [
        _block_with(
            AnalogRecord(
                record_type=AnalogType.RES,
                status=AnalogStatus.FAIL,
                measured=20000.0,
                designator="R12",
                limits=Limits3(nominal=10000.0, high=10100.0, low=9900.0),
            )
        )
    ]
    assert derive_btest_status(blocks) == BTESTStatus.FAIL_ANALOG == 6


def test_digital_and_analog_failures_use_priority_table():
    """Digital + analog failure with no shorts -> ANALOG wins (priority order)."""
    from flying_probe_copilot.generator.models import (
        AnalogRecord,
        AnalogStatus,
        AnalogType,
        BTESTStatus,
        DigitalRecord,
        DigitalStatus,
        Limits3,
        derive_btest_status,
    )

    blocks = [
        _block_with(
            DigitalRecord(
                status=DigitalStatus.FAIL,
                substatus=1,
                failing_vector=12,
                failing_pin_count=1,
                designator="U7",
            )
        ),
        _block_with(
            AnalogRecord(
                record_type=AnalogType.RES,
                status=AnalogStatus.FAIL,
                measured=20000.0,
                designator="R12",
                limits=Limits3(nominal=10000.0, high=10100.0, low=9900.0),
            )
        ),
    ]
    # Precedence is SHORTS -> ANALOG -> DIGITAL -> ..., so ANALOG wins here.
    assert derive_btest_status(blocks) == BTESTStatus.FAIL_ANALOG
