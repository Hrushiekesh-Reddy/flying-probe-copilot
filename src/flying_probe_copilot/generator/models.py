"""Pydantic v2 data models for the synthetic HP3070 / i3070 log generator.

Maps 1:1 to the real Keysight i3070 Log Record Format records described in
``specs/synthetic-log-generator.md`` (section "Data model"). All enumerations
use the numeric codes documented in Keysight's "i3070 Log Record Format"
chapter; nothing in this module is copied verbatim from any proprietary
source. Cross-validated against the Virinco WATS-Client-Converter regex
grammar (LGPL-3.0; cited as reference, not source of strings).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum, IntEnum
from typing import Callable, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# Status IntEnums — numeric codes per the spec's status vocabulary tables.
# ---------------------------------------------------------------------------


class BTESTStatus(IntEnum):
    """Overall @BTEST status — board-level result code."""

    PASS = 0
    FAIL_UNCATEGORIZED = 1
    FAIL_PIN = 2
    FAIL_LEARN = 3
    FAIL_SHORTS = 4
    FAIL_ANALOG = 6
    FAIL_POWER = 7
    FAIL_DIGITAL = 8
    FAIL_FUNCTIONAL = 9
    FAIL_PRE_SHORTS = 10
    FAIL_HANDLER = 11
    FAIL_BARCODE = 12
    XD_OUT = 13
    FAIL_TJET = 14
    FAIL_POLARITY = 15
    FAIL_CCHK = 16
    FAIL_ANALOG_CLUSTER = 17
    RUNTIME_ERROR = 80
    ABORTED_STOP = 81
    ABORTED_BREAK = 82


class AnalogStatus(IntEnum):
    """@A-* record status codes."""

    PASS = 0
    FAIL = 1
    FAIL_COMPLIANCE = 2
    FAIL_DETECTOR_TIMEOUT = 3
    FAIL_MEA_SPECIFIC = 7
    OPERATOR_ABORTED = 11


class DigitalStatus(IntEnum):
    """@D-T record status codes."""

    PASS = 0
    FAIL = 1
    FAIL_CRC = 5
    FAIL_FATAL = 7
    FAIL_CHAIN_INTEGRITY = 8


class ShortsStatus(IntEnum):
    """@TS record status codes."""

    PASS = 0
    FAIL = 1
    LEARNING_PASSED = 20


class TwoDigitStatus(IntEnum):
    """Two-digit @TJET / @PCHK / @CCHK status — rendered zero-padded."""

    PASS = 0
    FAIL = 1
    FAIL_FATAL = 7


class AnalogType(str, Enum):
    """The 14 analog test-record types. Rendered as ``@A-{value}``."""

    RES = "RES"
    CAP = "CAP"
    DIO = "DIO"
    IND = "IND"
    MEA = "MEA"
    NFE = "NFE"
    NPN = "NPN"
    PFE = "PFE"
    PNP = "PNP"
    POT = "POT"
    SWI = "SWI"
    ZEN = "ZEN"
    FUS = "FUS"
    JUM = "JUM"


# LIM2 vs LIM3 mapping per spec line "@LIM2 follows {DIO,FUS,JUM,MEA,NFE,NPN,
# PFE,PNP,SWI}; @LIM3 follows {CAP,IND,POT,RES,ZEN}".
LIM2_TYPES: frozenset[AnalogType] = frozenset(
    {
        AnalogType.DIO,
        AnalogType.FUS,
        AnalogType.JUM,
        AnalogType.MEA,
        AnalogType.NFE,
        AnalogType.NPN,
        AnalogType.PFE,
        AnalogType.PNP,
        AnalogType.SWI,
    }
)
LIM3_TYPES: frozenset[AnalogType] = frozenset(
    {
        AnalogType.CAP,
        AnalogType.IND,
        AnalogType.POT,
        AnalogType.RES,
        AnalogType.ZEN,
    }
)


# ---------------------------------------------------------------------------
# Higher-level objects (panel / board profile).
# ---------------------------------------------------------------------------


class BoardProfile(BaseModel):
    """A board family — drives synthesis volume and mix."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    component_count: int
    net_count: int
    typical_test_count: int
    component_mix: dict[str, int]


class PanelInstance(BaseModel):
    """One board instance going through test."""

    model_config = ConfigDict(extra="forbid")

    serial: str
    panel_position: int
    board_profile_id: str
    operator_id: str
    line_id: str
    shift: Literal["A", "B", "C"]
    timestamp: datetime


# ---------------------------------------------------------------------------
# Record-level models — one per @PREFIX.
# ---------------------------------------------------------------------------


class BatchRecord(BaseModel):
    """Maps to @BATCH — one per file. 13-field form when ``version_label`` is None."""

    model_config = ConfigDict(extra="forbid")

    uut_type: str
    uut_rev: str
    fixture_id: int
    testhead_num: int
    testhead_type: str = ""
    process_step: str
    batch_id: str
    operator_id: str
    controller: str
    testplan_id: str
    testplan_rev: str
    parent_panel_type: str
    parent_panel_rev: str
    version_label: str | None = None  # 14-field form only


class BoardTestRecord(BaseModel):
    """Maps to @BTEST — one per board within @BATCH."""

    model_config = ConfigDict(extra="forbid")

    board_id: str
    status: BTESTStatus
    start_ts: int
    duration_s: int
    multiple_test: bool = False
    log_level: Literal["none", "manual", "board", "failures", "indictments", "analog", "all"] = (
        "all"
    )
    log_set: int = 0
    learning: bool = False
    known_good: bool = False
    end_ts: int
    status_qualifier: str = ""
    board_number: int
    operator_id: str = Field(min_length=1)
    shift: Literal["A", "B", "C"]
    line_id: str = Field(min_length=1)
    parent_panel_id: str | None = None


class BlockRecord(BaseModel):
    """Maps to @BLOCK — wraps a single test record."""

    model_config = ConfigDict(extra="forbid")

    designator: str
    status: int


class Limits2(BaseModel):
    """Maps to @LIM2 — range-only limits."""

    model_config = ConfigDict(extra="forbid")

    high: float
    low: float


class Limits3(BaseModel):
    """Maps to @LIM3 — nominal + tolerance limits."""

    model_config = ConfigDict(extra="forbid")

    nominal: float
    high: float
    low: float


class AnalogRecord(BaseModel):
    """Maps to one of the 14 @A-* records plus its limits subrecord.

    Per Revision 1 #MINOR-9: a ``@model_validator`` enforces the LIM2/LIM3
    tagged-union rule at construction time — belt-and-suspenders with the
    grammar layer.
    """

    model_config = ConfigDict(extra="forbid")

    record_type: AnalogType
    status: AnalogStatus
    measured: float
    designator: str
    limits: Union[Limits2, Limits3]

    @model_validator(mode="after")
    def _limits_match_record_type(self) -> "AnalogRecord":
        if self.record_type in LIM2_TYPES and not isinstance(self.limits, Limits2):
            raise ValueError(
                f"{self.record_type} requires Limits2 (LIM2), got {type(self.limits).__name__}"
            )
        if self.record_type in LIM3_TYPES and not isinstance(self.limits, Limits3):
            raise ValueError(
                f"{self.record_type} requires Limits3 (LIM3), got {type(self.limits).__name__}"
            )
        return self


class DigitalRecord(BaseModel):
    """Maps to @D-T."""

    model_config = ConfigDict(extra="forbid")

    status: DigitalStatus
    substatus: int  # 6-bit bitmask
    failing_vector: int
    failing_pin_count: int
    designator: str


class ShortDestination(BaseModel):
    """One destination in an @TS-D list."""

    model_config = ConfigDict(extra="forbid")

    dest_node: str
    deviation: float


class ShortsSourceNodeDetail(BaseModel):
    """Maps to @TS-S with its child @TS-D list."""

    model_config = ConfigDict(extra="forbid")

    source_node: str
    shorts_count: int
    phantoms_count: int
    destinations: list[ShortDestination] = []


class ShortOpenDetail(BaseModel):
    """Maps to @TS-O."""

    model_config = ConfigDict(extra="forbid")

    source_node: str
    dest_node: str
    deviation: float


class ShortsRecord(BaseModel):
    """Maps to @TS plus child detail subrecords."""

    model_config = ConfigDict(extra="forbid")

    status: ShortsStatus
    shorts_count: int
    opens_count: int
    phantoms_count: int
    designator: str = "shorts_test"
    detail_source_nodes: list[ShortsSourceNodeDetail] = []
    detail_opens: list[ShortOpenDetail] = []
    detail_phantoms: list[float] = []


class TestJetRecord(BaseModel):
    """Maps to @TJET."""

    # Opt out of pytest's "Test*" class collection heuristic — this is a
    # Pydantic model, not a test class (BUG-010).
    __test__ = False

    model_config = ConfigDict(extra="forbid")

    status: TwoDigitStatus
    pin_count: int
    designator: str


class PinsFailedRecord(BaseModel):
    """Maps to @PF + nested @PIN list."""

    model_config = ConfigDict(extra="forbid")

    designator: str
    status: Literal[0, 1]
    total_pins: int
    pins: list[str]


# ---------------------------------------------------------------------------
# Composite hierarchy: BatchLog -> BoardLog -> TestBlock.
# ---------------------------------------------------------------------------


RecordUnion = Union[AnalogRecord, DigitalRecord, ShortsRecord, TestJetRecord, PinsFailedRecord]


class TestBlock(BaseModel):
    """One @BLOCK and its single child test record."""

    model_config = ConfigDict(extra="forbid")

    block: BlockRecord
    record: RecordUnion


class BoardLog(BaseModel):
    """One @BTEST and all its contained @BLOCKs."""

    model_config = ConfigDict(extra="forbid")

    panel: PanelInstance
    btest: BoardTestRecord
    blocks: list[TestBlock]


class BatchLog(BaseModel):
    """One @BATCH and all its child @BTESTs — represents one log file."""

    model_config = ConfigDict(extra="forbid")

    batch: BatchRecord
    boards: list[BoardLog]


# ---------------------------------------------------------------------------
# derive_btest_status — Revision 1 #BLOCKER-3 categorical precedence rule.
# ---------------------------------------------------------------------------


# Ordered precedence: SHORTS -> ANALOG -> DIGITAL -> PIN -> TJET -> POLARITY ->
# CCHK -> FUNCTIONAL -> POWER -> UNCATEGORIZED. First match wins. Codes 11-13
# and 80-82 are environmental — never derived from subtest status.
_PRECEDENCE: list[tuple[BTESTStatus, Callable[[RecordUnion], bool]]] = [
    (
        BTESTStatus.FAIL_SHORTS,
        lambda r: isinstance(r, ShortsRecord) and r.status != ShortsStatus.PASS,
    ),
    (
        BTESTStatus.FAIL_ANALOG,
        lambda r: isinstance(r, AnalogRecord) and r.status != AnalogStatus.PASS,
    ),
    (
        BTESTStatus.FAIL_DIGITAL,
        lambda r: isinstance(r, DigitalRecord) and r.status != DigitalStatus.PASS,
    ),
    (
        BTESTStatus.FAIL_PIN,
        lambda r: isinstance(r, PinsFailedRecord) and r.status != 0,
    ),
    (
        BTESTStatus.FAIL_TJET,
        lambda r: isinstance(r, TestJetRecord) and r.status != TwoDigitStatus.PASS,
    ),
    # Forward-extensibility slots — record types deferred to Phase 5 (boundary
    # scan / probe / functional). Predicates return False today; swap the
    # isinstance check when the matching record type is added. Order locked by
    # Revision 1 #BLOCKER-3 contract.
    (
        BTESTStatus.FAIL_POLARITY,
        lambda r: False,  # @PCHK polarity-check records — deferred
    ),
    (
        BTESTStatus.FAIL_CCHK,
        lambda r: False,  # @CCHK connect-check records (Mux only) — deferred
    ),
    (
        BTESTStatus.FAIL_FUNCTIONAL,
        lambda r: False,  # functional test records — deferred
    ),
    (
        BTESTStatus.FAIL_POWER,
        lambda r: False,  # power-supply test records — deferred
    ),
    (
        BTESTStatus.FAIL_UNCATEGORIZED,
        lambda r: False,  # catch-all; reserved for unclassified failures
    ),
]


def derive_btest_status(blocks: list[TestBlock]) -> BTESTStatus:
    """Derive the overall @BTEST status from contained subtest statuses.

    Algorithm (Revision 1 #BLOCKER-3 categorical precedence):
      1. Scan blocks in the priority order: SHORTS, ANALOG, DIGITAL, PIN, TJET.
      2. First category with any failing record wins.
      3. If no failures, return PASS.

    Environmental codes (FAIL_HANDLER=11, FAIL_BARCODE=12, XD_OUT=13,
    RUNTIME_ERROR=80, ABORTED_STOP=81, ABORTED_BREAK=82) are NEVER returned
    by this function — they're set externally by the orchestrator.
    """
    for status_code, predicate in _PRECEDENCE:
        for tb in blocks:
            if predicate(tb.record):
                return status_code
    return BTESTStatus.PASS
