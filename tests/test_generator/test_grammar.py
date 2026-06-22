"""Tests for ``flying_probe_copilot.generator.grammar``.

Phase 1a Step D1 — RED phase. The grammar module exposes a ``Grammar`` class
with ``validate(log_text) -> list[GrammarError]`` returning [] for a valid log.
Patterns are derived from the Keysight i3070 Log Record Format chapter.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Accept cases
# ---------------------------------------------------------------------------


def _validate(text: str):
    from flying_probe_copilot.generator.grammar import Grammar

    return Grammar().validate(text)


def test_grammar_accepts_minimal_batch_btest():
    text = (
        "{@BATCH|BRD-X|A|1|1||ICT|BAT-0001|OP-007|ICT01|TP-001|A|PNL-X|A}\r\n"
        "{@BTEST|SYN-2026W14-00001|0|260401083000|12|0|all|0|0|0|260401083012||1|OP-001|A|LINE-A}\r\n"
    )
    assert _validate(text) == []


def test_grammar_accepts_a_res_with_lim3():
    text = "{@A-RES|0|+1.000000E+04|R12}\r\n{@LIM3|+1.000000E+04|+1.010000E+04|+9.900000E+03}\r\n"
    assert _validate(text) == []


def test_grammar_accepts_a_cap_with_lim3():
    text = "{@A-CAP|0|+1.000000E-06|C1}\r\n{@LIM3|+1.000000E-06|+1.100000E-06|+9.000000E-07}\r\n"
    assert _validate(text) == []


def test_grammar_accepts_a_dio_with_lim2():
    text = "{@A-DIO|0|+7.000000E-01|D1}\r\n{@LIM2|+8.000000E-01|+5.000000E-01}\r\n"
    assert _validate(text) == []


def test_grammar_accepts_d_t_with_substatus_bitmask():
    text = "{@D-T|0|0|0|0|U7}\r\n"
    assert _validate(text) == []


def test_grammar_accepts_ts_with_subrecords():
    text = "{@TS|0|0|0|0|shorts}\r\n"
    assert _validate(text) == []


def test_grammar_accepts_tjet_two_digit_status():
    text = "{@TJET|00|14|U7}\r\n"
    assert _validate(text) == []


def test_grammar_accepts_pf_with_pin_list():
    text = "{@PF|U7|0|2{@PIN\\2|10101|10102}}\r\n"
    assert _validate(text) == []


# ---------------------------------------------------------------------------
# Reject cases
# ---------------------------------------------------------------------------


def test_grammar_rejects_unbalanced_braces():
    text = "{@BTEST|SYN-2026W14-00001|0|260401083000|12|0|all|0|0|0|260401083012||1|OP-001\r\n"
    errors = _validate(text)
    assert errors, "expected unbalanced braces to be reported"


def test_grammar_rejects_unknown_prefix():
    text = "{@FOO|x|y|z}\r\n"
    errors = _validate(text)
    assert errors, "expected unknown @FOO prefix to be reported"


def test_grammar_rejects_invalid_status_code_in_analog():
    text = "{@A-RES|99|+1.000000E+04|R12}\r\n{@LIM3|+1.000000E+04|+1.010000E+04|+9.900000E+03}\r\n"
    errors = _validate(text)
    assert errors, "expected analog status code 99 to be rejected"


def test_grammar_rejects_non_scientific_float():
    text = "{@A-RES|0|10000|R12}\r\n{@LIM3|+1.000000E+04|+1.010000E+04|+9.900000E+03}\r\n"
    errors = _validate(text)
    assert errors, "expected non-scientific measured value to be rejected"


def test_grammar_rejects_invalid_timestamp_length():
    text = (
        "{@BTEST|SYN-2026W14-00001|0|2604010830|12|0|all|0|0|0|260401083012||1|OP-001|A|LINE-A}\r\n"
    )
    errors = _validate(text)
    assert errors, "expected 10-digit timestamp to be rejected (need 12)"


def test_grammar_rejects_a_res_with_lim2_instead_of_lim3():
    text = "{@A-RES|0|+1.000000E+04|R12}\r\n{@LIM2|+1.010000E+04|+9.900000E+03}\r\n"
    errors = _validate(text)
    assert errors, "expected A-RES followed by LIM2 to be rejected"


def test_grammar_accepts_btest_13_field_and_14_field_forms():
    """13-field @BTEST (no parent_panel_id) and 14-field (with parent_panel_id) must both pass."""
    thirteen = "{@BTEST|SYN-2026W14-00001|0|260401083000|12|0|all|0|0|0|260401083012||1|OP-001|A|LINE-A}\r\n"
    fourteen = "{@BTEST|SYN-2026W14-00001|0|260401083000|12|0|all|0|0|0|260401083012||1|OP-001|A|LINE-A|PNL-X-001}\r\n"
    assert _validate(thirteen) == []
    assert _validate(fourteen) == []


def test_grammar_btest_requires_operator_id_field():
    """A 12-field @BTEST (the OLD format, no operator_id) must fail grammar validation."""
    old_twelve_field = (
        "{@BTEST|SYN-2026W14-00001|0|260401083000|12|0|all|0|0|0|260401083012||1}\r\n"
    )
    errors = _validate(old_twelve_field)
    assert errors, "expected OLD 12-field @BTEST (missing operator_id) to be rejected by grammar"
