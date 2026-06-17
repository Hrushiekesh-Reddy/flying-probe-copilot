"""End-to-end lexical compliance: real CLI block-generation path passes Grammar.

Phase 1a Step G1 — composes profile + schedule + faults + ``generate_blocks``
+ renderer (the exact orchestration ``cli._build_batch_log`` performs) and
runs the output through the Phase 4 grammar. Any non-empty error list fails.

Why this file matters: BUG-002 was a P0 in which the CLI hardcoded a 4-block
sample per panel instead of scaling with ``profile.component_mix``. The fix
landed in ``blocks.generate_blocks`` and the CLI was rewired to call it, but
this test originally built its panels with a local 4-block fixture — mimicking
the pre-fix buggy code path and never exercising ``generate_blocks``. PR #3
review flagged the coverage gap. This rewrite routes the lexical assertion
through ``generate_blocks`` and validates every emitted block of every
profile, not just the first four.
"""

from __future__ import annotations

from datetime import datetime, timedelta


START = datetime(2026, 4, 1, 0, 0, 0)
END = START + timedelta(weeks=4)


def _build_batch_log_via_cli_path(
    profile_name: str, count: int, *, fault_profile: str, seed: int
):
    """Compose a ``BatchLog`` using the exact path ``cli._build_batch_log`` uses.

    Mirrors ``src/flying_probe_copilot/generator/cli.py::_build_batch_log``
    (panel seed = ``seed * 1000 + idx``, change-point midway through the
    window, 12-second board test duration) but stays self-contained so the
    lexical test doesn't import the CLI module.
    """
    from flying_probe_copilot.generator.blocks import generate_blocks
    from flying_probe_copilot.generator.faults import generate_panel_faults
    from flying_probe_copilot.generator.models import (
        BatchLog,
        BatchRecord,
        BoardLog,
        BoardTestRecord,
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

    change_point = START + (END - START) / 2

    boards: list[BoardLog] = []
    for idx, panel in enumerate(panels):
        panel_seed = seed * 1000 + idx
        outcome = generate_panel_faults(
            seed=panel_seed,
            profile=fault_profile,
            target_rate=0.10,
            panel_timestamp=panel.timestamp,
            window_start=START,
            window_end=END,
            change_point=change_point,
        )
        blocks = generate_blocks(profile, outcome, panel_seed)
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
            operator_id=panel.operator_id,
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


def _assert_blocks_scale_with_profile(batch_log, profile_name: str) -> None:
    """Guardrail against a BUG-002-style regression to hardcoded N-block panels.

    Each board must emit at least ``component_count + 1`` blocks (one ``shorts``
    block + one block per component in ``profile.component_mix``). If this
    assertion ever fails, ``generate_blocks`` has silently shrunk back to a
    sample-sized output and the grammar pass below would be reviewing the
    wrong code path.
    """
    from flying_probe_copilot.generator.profiles import get_profile

    expected_min = get_profile(profile_name).component_count + 1
    for board in batch_log.boards:
        assert len(board.blocks) >= expected_min, (
            f"profile={profile_name!r} board={board.panel.serial} emitted "
            f"{len(board.blocks)} blocks; expected ≥{expected_min} "
            "(shorts + one per component). Did generate_blocks regress to a "
            "hardcoded sample?"
        )


def test_small_profile_cli_path_output_passes_grammar(tmp_path):
    from flying_probe_copilot.generator.grammar import Grammar
    from flying_probe_copilot.generator.renderers.log import render_log

    batch_log = _build_batch_log_via_cli_path(
        "small", count=3, fault_profile="random", seed=42
    )
    _assert_blocks_scale_with_profile(batch_log, "small")
    out = tmp_path / "small.log"
    render_log(batch_log, out)
    text = out.read_text(encoding="cp1252")
    errors = Grammar().validate(text)
    assert errors == [], f"grammar errors in small CLI-path run: {errors[:3]}"


def test_medium_profile_cli_path_output_passes_grammar(tmp_path):
    from flying_probe_copilot.generator.grammar import Grammar
    from flying_probe_copilot.generator.renderers.log import render_log

    batch_log = _build_batch_log_via_cli_path(
        "medium", count=2, fault_profile="random", seed=7
    )
    _assert_blocks_scale_with_profile(batch_log, "medium")
    out = tmp_path / "medium.log"
    render_log(batch_log, out)
    text = out.read_text(encoding="cp1252")
    errors = Grammar().validate(text)
    assert errors == [], f"grammar errors in medium CLI-path run: {errors[:3]}"


def test_large_profile_cli_path_output_passes_grammar(tmp_path):
    from flying_probe_copilot.generator.grammar import Grammar
    from flying_probe_copilot.generator.renderers.log import render_log

    batch_log = _build_batch_log_via_cli_path(
        "large", count=1, fault_profile="random", seed=99
    )
    _assert_blocks_scale_with_profile(batch_log, "large")
    out = tmp_path / "large.log"
    render_log(batch_log, out)
    text = out.read_text(encoding="cp1252")
    errors = Grammar().validate(text)
    assert errors == [], f"grammar errors in large CLI-path run: {errors[:3]}"


def test_drift_profile_cli_path_output_passes_grammar(tmp_path):
    from flying_probe_copilot.generator.grammar import Grammar
    from flying_probe_copilot.generator.renderers.log import render_log

    batch_log = _build_batch_log_via_cli_path(
        "small", count=20, fault_profile="drift", seed=99
    )
    _assert_blocks_scale_with_profile(batch_log, "small")
    out = tmp_path / "drift.log"
    render_log(batch_log, out)
    text = out.read_text(encoding="cp1252")
    errors = Grammar().validate(text)
    assert errors == [], f"grammar errors in drift CLI-path run: {errors[:3]}"
