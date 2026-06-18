"""Python regex grammar for the Keysight i3070 Log Record Format.

Patterns derived from the lexical micro-syntax documented in
``specs/synthetic-log-generator.md`` (sections "Lexical micro-syntax" and
"Field schemas"). The format chapter is publicly described in Keysight's
"i3070 Log Record Format" reference; we describe per-record field counts and
allowed status enumerations here in our own Python idiom — no verbatim
strings are copied from any proprietary source.

Cross-validation reference: Virinco WATS-Client-Converter (LGPL-3.0) at
``https://github.com/Virinco/WATS-Client-Converter-i3070-ICT-Systems``. That
project's C# regex strings are NOT the source of any pattern in this file;
they served only as an external sanity check on field counts and status
enumerations.

The grammar's job is to answer "does this look like a valid log?" — full
parsing is the responsibility of the Phase 1b parser.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Core lexical building blocks
# ---------------------------------------------------------------------------


# Scientific-notation float: signed mantissa, six-digit fraction, capital E,
# signed two-digit exponent. Mirror the format produced by ``"{:+.6E}".format``.
_SCI_FLOAT = r"[+-]\d\.\d{6}E[+-]\d{2}"

# YYMMDDHHMMSS — exactly 12 digits.
_TIMESTAMP = r"\d{12}"

# A "free" field — any chars except the framing/separator set.
_FIELD = r"[^|{}\r\n]*"

# A list-length escape prefix — backslash + digits + "|" then items joined by "|".
_LIST_PREFIX = r"\\\d+"


# ---------------------------------------------------------------------------
# Per-record patterns
# ---------------------------------------------------------------------------


# @BATCH — 13 or 14 fields (extra trailing |field optional).
_BATCH = re.compile(
    r"^\{@BATCH"
    + (rf"\|{_FIELD}") * 13
    + rf"(?:\|{_FIELD})?"
    + r"\}$"
)

# @BTEST — 13 or 14 fields. Field count comes from the spec table.
# Schema: board_id | status | start_ts | duration_s | multiple_test | log_level
#         | log_set | learning | known_good | end_ts | status_qualifier
#         | board_number | operator_id | shift | line_id [| parent_panel_id]
_BTEST = re.compile(
    r"^\{@BTEST"
    rf"\|{_FIELD}"                                         # board_id
    r"\|(?:0|1|2|3|4|6|7|8|9|10|11|12|13|14|15|16|17|80|81|82|9\d)"  # status
    rf"\|{_TIMESTAMP}"                                     # start_ts
    rf"\|\d+"                                              # duration_s
    rf"\|{_FIELD}"                                         # multiple_test
    r"\|(?:none|manual|board|failures|indictments|analog|all)"  # log_level
    rf"\|{_FIELD}"                                         # log_set
    rf"\|{_FIELD}"                                         # learning
    rf"\|{_FIELD}"                                         # known_good
    rf"\|{_TIMESTAMP}"                                     # end_ts
    rf"\|{_FIELD}"                                         # status_qualifier
    rf"\|\d+"                                              # board_number
    rf"\|{_FIELD}"                                         # operator_id
    r"\|[ABC]"                                             # shift
    rf"\|{_FIELD}"                                         # line_id
    rf"(?:\|{_FIELD})?"                                    # optional parent_panel_id
    r"\}$"
)

# @BLOCK — 2 fields.
_BLOCK = re.compile(rf"^\{{@BLOCK\|{_FIELD}\|{_FIELD}\}}$")

# @A-XXX — 3 fields: status | measured_fp | designator.
_ANALOG_STATUSES = "0|1|2|3|7|11"
_ANALOG_TYPES = "RES|CAP|DIO|IND|MEA|NFE|NPN|PFE|PNP|POT|SWI|ZEN|FUS|JUM"
_ANALOG = re.compile(
    rf"^\{{@A-(?P<atype>{_ANALOG_TYPES})"
    rf"\|(?P<status>{_ANALOG_STATUSES})"
    rf"\|(?P<measured>{_SCI_FLOAT})"
    rf"\|{_FIELD}"
    r"\}$"
)

# @LIM2 / @LIM3 — 2 or 3 floats.
_LIM2 = re.compile(rf"^\{{@LIM2\|{_SCI_FLOAT}\|{_SCI_FLOAT}\}}$")
_LIM3 = re.compile(rf"^\{{@LIM3\|{_SCI_FLOAT}\|{_SCI_FLOAT}\|{_SCI_FLOAT}\}}$")

# @D-T — status | substatus | failing_vector | failing_pin_count | designator.
_DIGITAL = re.compile(
    rf"^\{{@D-T\|(?:0|1|5|7|8)\|\d+\|\d+\|\d+\|{_FIELD}\}}$"
)

# @TS — top-level shorts record (subrecords excluded — they nest separately).
_SHORTS = re.compile(
    rf"^\{{@TS\|(?:0|1|20)\|\d+\|\d+\|\d+\|{_FIELD}\}}$"
)

# @TJET — two-digit status | pin_count | designator.
_TJET = re.compile(rf"^\{{@TJET\|(?:00|01|07)\|\d+\|{_FIELD}\}}$")

# @PF — designator | status | total_pins { @PIN \N|p1|p2|... }
# The @PIN list payload appears INSIDE the @PF outer braces.
_PF = re.compile(
    rf"^\{{@PF\|{_FIELD}\|(?:0|1)\|\d+"
    rf"\{{@PIN{_LIST_PREFIX}(?:\|[0-9A-Za-z_]+)*\}}"
    r"\}$"
)

# Allowed top-level prefixes. Subrecord-only prefixes (LIM2/LIM3/TS-S/TS-D/...)
# are validated on a record-by-record basis below.
_KNOWN_PREFIXES = {
    "@BATCH",
    "@BTEST",
    "@BLOCK",
    "@A-RES",
    "@A-CAP",
    "@A-DIO",
    "@A-IND",
    "@A-MEA",
    "@A-NFE",
    "@A-NPN",
    "@A-PFE",
    "@A-PNP",
    "@A-POT",
    "@A-SWI",
    "@A-ZEN",
    "@A-FUS",
    "@A-JUM",
    "@LIM2",
    "@LIM3",
    "@D-T",
    "@TS",
    "@TJET",
    "@PF",
}


# Types that take LIM3 (3-field nominal+high+low) and LIM2 (2-field).
_LIM3_TYPES = {"RES", "CAP", "IND", "POT", "ZEN"}
_LIM2_TYPES = {"DIO", "FUS", "JUM", "MEA", "NFE", "NPN", "PFE", "PNP", "SWI"}


# ---------------------------------------------------------------------------
# Validation API
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GrammarError:
    """A single grammar violation."""

    line_number: int
    message: str
    text: str


class Grammar:
    """Lexical validator for the i3070 Log Record Format."""

    def validate(self, log_text: str) -> list[GrammarError]:
        """Return a list of ``GrammarError``s, empty if ``log_text`` is valid.

        Validation strategy:
          1. Pre-pass: every ``{`` must be matched by a ``}``.
          2. Walk records line-by-line — each non-empty line must be a single
             top-level record matching the regex for its prefix.
          3. Track preceding-analog record-type so that the very next LIM2/LIM3
             can be flagged if it's the wrong limits class.
        """
        errors: list[GrammarError] = []

        # 1. Brace balance over the whole text.
        opens = log_text.count("{")
        closes = log_text.count("}")
        if opens != closes:
            errors.append(
                GrammarError(
                    line_number=0,
                    message=f"unbalanced braces: {opens} '{{' vs {closes} '}}'",
                    text="",
                )
            )

        # 2. Per-line record validation.
        # Split on CRLF or LF — strip the trailing CR if present.
        lines = log_text.split("\n")
        last_analog_type: str | None = None
        for idx, raw in enumerate(lines, start=1):
            line = raw.rstrip("\r")
            if not line:
                continue

            prefix = self._extract_prefix(line)
            if prefix is None:
                errors.append(
                    GrammarError(
                        line_number=idx,
                        message="line does not start with '{@PREFIX'",
                        text=line,
                    )
                )
                continue

            if prefix not in _KNOWN_PREFIXES:
                errors.append(
                    GrammarError(
                        line_number=idx,
                        message=f"unknown record prefix: {prefix}",
                        text=line,
                    )
                )
                continue

            # Dispatch to the per-prefix regex.
            match = self._dispatch(prefix, line)
            if match is None:
                errors.append(
                    GrammarError(
                        line_number=idx,
                        message=f"record fails {prefix} pattern",
                        text=line,
                    )
                )
                last_analog_type = None
                continue

            # Track analog->limits pairing.
            if prefix.startswith("@A-"):
                last_analog_type = prefix.removeprefix("@A-")
            elif prefix == "@LIM2":
                if last_analog_type is not None and last_analog_type not in _LIM2_TYPES:
                    errors.append(
                        GrammarError(
                            line_number=idx,
                            message=(
                                f"@LIM2 follows @A-{last_analog_type}; "
                                f"that record requires @LIM3"
                            ),
                            text=line,
                        )
                    )
                last_analog_type = None
            elif prefix == "@LIM3":
                if last_analog_type is not None and last_analog_type not in _LIM3_TYPES:
                    errors.append(
                        GrammarError(
                            line_number=idx,
                            message=(
                                f"@LIM3 follows @A-{last_analog_type}; "
                                f"that record requires @LIM2"
                            ),
                            text=line,
                        )
                    )
                last_analog_type = None
            else:
                last_analog_type = None

        return errors

    # ------------------------------------------------------------------ helpers

    _PREFIX_RE = re.compile(r"^\{(@[A-Z][A-Z0-9-]*)")

    def _extract_prefix(self, line: str) -> str | None:
        m = self._PREFIX_RE.match(line)
        return m.group(1) if m else None

    def _dispatch(self, prefix: str, line: str) -> re.Match | None:
        if prefix == "@BATCH":
            return _BATCH.match(line)
        if prefix == "@BTEST":
            return _BTEST.match(line)
        if prefix == "@BLOCK":
            return _BLOCK.match(line)
        if prefix.startswith("@A-"):
            return _ANALOG.match(line)
        if prefix == "@LIM2":
            return _LIM2.match(line)
        if prefix == "@LIM3":
            return _LIM3.match(line)
        if prefix == "@D-T":
            return _DIGITAL.match(line)
        if prefix == "@TS":
            return _SHORTS.match(line)
        if prefix == "@TJET":
            return _TJET.match(line)
        if prefix == "@PF":
            return _PF.match(line)
        return None
