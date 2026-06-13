"""End-to-end lexical compliance: generated .log passes Grammar.validate.

Phase 1a Step G1 — composes profile + schedule + faults + renderer and runs
the output through the Phase 4 grammar. Any non-empty error list fails.
"""

from __future__ import annotations

from datetime import datetime, timedelta


START = datetime(2026, 4, 1, 0, 0, 0)
END = START + timedelta(weeks=4)


def _build_batch_log(profile_name: str, count: int, *, fault_profile: str, seed: int):
    """Compose a BatchLog from the public primitives.

    This mirrors what the CLI will do, but stays self-contained so the lexical
    test doesn't import the CLI module (which has heavier dependencies).
    """
    from flying_probe_copilot.generator.faults import generate_panel_faults
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
        ShortsRecord,
        ShortsStatus,
        TestBlock,
        derive_btest_status,
    )
    from flying_probe_copilot.generator.profiles import get_profile
    from flying_probe_copilot.generator.schedule import generate_panel_schedule

    profile = get_profile(profile_name)
    panels = generate_panel_schedule(
        start=START,
        end=END,
        count=count,
        seed=seed,
        operators=4,
        lines=2,
        board_profile_id=profile.id,
    )

    boards: list[BoardLog] = []
    for idx, panel in enumerate(panels):
        outcome = generate_panel_faults(
            seed=seed * 1000 + idx,
            profile=fault_profile,
            target_rate=0.10,
            panel_timestamp=panel.timestamp,
            window_start=START,
            window_end=END,
            change_point=START + (END - START) / 2,
        )
        # Build a tiny but representative set of blocks per board.
        blocks = [
            TestBlock(
                block=BlockRecord(designator="shorts", status=0),
                record=ShortsRecord(
                    status=(
                        ShortsStatus.FAIL
                        if (outcome.failed and outcome.mode == "SHORTS")
                        else ShortsStatus.PASS
                    ),
                    shorts_count=(1 if outcome.mode == "SHORTS" else 0),
                    opens_count=0,
                    phantoms_count=0,
                ),
            ),
            TestBlock(
                block=BlockRecord(designator="R12", status=0),
                record=AnalogRecord(
                    record_type=AnalogType.RES,
                    status=(
                        AnalogStatus.FAIL
                        if (outcome.failed and outcome.btest_status == BTESTStatus.FAIL_ANALOG)
                        else AnalogStatus.PASS
                    ),
                    measured=(
                        10500.0
                        if (outcome.failed and outcome.btest_status == BTESTStatus.FAIL_ANALOG)
                        else 10000.0
                    ),
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
                    status=(
                        DigitalStatus.FAIL
                        if (outcome.failed and outcome.mode == "DIGITAL")
                        else DigitalStatus.PASS
                    ),
                    substatus=(1 if outcome.mode == "DIGITAL" else 0),
                    failing_vector=(12 if outcome.mode == "DIGITAL" else 0),
                    failing_pin_count=(1 if outcome.mode == "DIGITAL" else 0),
                    designator="U7",
                ),
            ),
        ]
        derived = derive_btest_status(blocks)
        start_ts = int(panel.timestamp.strftime("%y%m%d%H%M%S"))
        end_ts = int(
            (panel.timestamp + timedelta(seconds=12)).strftime("%y%m%d%H%M%S")
        )
        btest = BoardTestRecord(
            board_id=panel.serial,
            status=derived,
            start_ts=start_ts,
            duration_s=12,
            end_ts=end_ts,
            board_number=1,
        )
        boards.append(BoardLog(panel=panel, btest=btest, blocks=blocks))

    batch = BatchRecord(
        uut_type=f"BRD-{profile_name.upper()}",
        uut_rev="A",
        fixture_id=1,
        testhead_num=1,
        process_step="ICT",
        batch_id=f"BAT-{seed:04d}",
        operator_id=boards[0].panel.operator_id if boards else "OP-001",
        controller="ICT01",
        testplan_id="TP-001",
        testplan_rev="v1.0",
        parent_panel_type=f"PNL-{profile_name.upper()}",
        parent_panel_rev="A",
    )
    return BatchLog(batch=batch, boards=boards)


def test_small_run_output_passes_grammar(tmp_path):
    from flying_probe_copilot.generator.grammar import Grammar
    from flying_probe_copilot.generator.renderers.log import render_log

    batch_log = _build_batch_log("small", count=10, fault_profile="random", seed=42)
    out = tmp_path / "small.log"
    render_log(batch_log, out)
    text = out.read_text(encoding="cp1252")
    errors = Grammar().validate(text)
    assert errors == [], f"grammar errors in small run: {errors[:3]}"


def test_medium_run_output_passes_grammar(tmp_path):
    from flying_probe_copilot.generator.grammar import Grammar
    from flying_probe_copilot.generator.renderers.log import render_log

    batch_log = _build_batch_log("medium", count=5, fault_profile="random", seed=7)
    out = tmp_path / "medium.log"
    render_log(batch_log, out)
    text = out.read_text(encoding="cp1252")
    errors = Grammar().validate(text)
    assert errors == [], f"grammar errors in medium run: {errors[:3]}"


def test_drift_profile_output_passes_grammar(tmp_path):
    from flying_probe_copilot.generator.grammar import Grammar
    from flying_probe_copilot.generator.renderers.log import render_log

    batch_log = _build_batch_log("small", count=20, fault_profile="drift", seed=99)
    out = tmp_path / "drift.log"
    render_log(batch_log, out)
    text = out.read_text(encoding="cp1252")
    errors = Grammar().validate(text)
    assert errors == [], f"grammar errors in drift run: {errors[:3]}"
