"""DuckDB schema for the Flying-Probe Co-Pilot — Phase 1b.

Defines 9 tables (5 dimension + 1 run-metadata + 3 fact) via
``CREATE TABLE IF NOT EXISTS`` so that ``init_database`` is idempotent.

Schema decisions are documented in ``docs/logs/DECISION_LOG.md`` (2026-06-14
Phase 1b entries).

Surrogate PKs (``component_id``, ``test_id``, ``test_run_id``,
``measurement_id``, ``failure_id``) are assigned by the ingest layer using
Python-side counters; DuckDB has no auto-increment in the DDL.

Per #WARNING-5: ``test_runs.operator_id`` is nullable — per-panel operator
recovery is deferred to Phase 2 (see DECISION_LOG entry).
"""

from __future__ import annotations

import duckdb

# ---------------------------------------------------------------------------
# DDL — one CREATE TABLE IF NOT EXISTS per entity.
# ---------------------------------------------------------------------------

_DDL_BOARDS = """
CREATE TABLE IF NOT EXISTS boards (
    board_profile_id   VARCHAR PRIMARY KEY,
    name               VARCHAR NOT NULL,
    component_count    INTEGER NOT NULL,
    net_count          INTEGER NOT NULL,
    typical_test_count INTEGER NOT NULL
)
"""

_DDL_PANELS = """
CREATE TABLE IF NOT EXISTS panels (
    panel_serial       VARCHAR PRIMARY KEY,
    board_profile_id   VARCHAR NOT NULL,
    panel_position     INTEGER NOT NULL,
    line_id            VARCHAR NOT NULL,
    shift              CHAR(1) NOT NULL,
    scheduled_ts       TIMESTAMP NOT NULL
)
"""

_DDL_OPERATORS = """
CREATE TABLE IF NOT EXISTS operators (
    operator_id        VARCHAR PRIMARY KEY
)
"""

_DDL_COMPONENTS = """
CREATE TABLE IF NOT EXISTS components (
    component_id       BIGINT PRIMARY KEY,
    board_profile_id   VARCHAR NOT NULL,
    refdes             VARCHAR NOT NULL,
    component_family   VARCHAR NOT NULL,
    UNIQUE (board_profile_id, refdes)
)
"""

_DDL_TESTS = """
CREATE TABLE IF NOT EXISTS tests (
    test_id            BIGINT PRIMARY KEY,
    board_profile_id   VARCHAR NOT NULL,
    block_designator   VARCHAR NOT NULL,
    record_type        VARCHAR NOT NULL,
    target_refdes      VARCHAR,
    UNIQUE (board_profile_id, block_designator, record_type)
)
"""

_DDL_RUNS = """
CREATE TABLE IF NOT EXISTS runs (
    run_id             VARCHAR PRIMARY KEY,
    board_profile_id   VARCHAR NOT NULL,
    seed               INTEGER NOT NULL,
    fault_rate         DOUBLE NOT NULL,
    fault_profile      VARCHAR NOT NULL,
    panel_count        INTEGER NOT NULL,
    failing_boards     INTEGER NOT NULL,
    ingested_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

_DDL_TEST_RUNS = """
CREATE TABLE IF NOT EXISTS test_runs (
    test_run_id        BIGINT PRIMARY KEY,
    panel_serial       VARCHAR NOT NULL,
    run_id             VARCHAR NOT NULL,
    operator_id        VARCHAR,
    btest_status       SMALLINT NOT NULL,
    start_ts           TIMESTAMP NOT NULL,
    end_ts             TIMESTAMP NOT NULL,
    duration_s         INTEGER NOT NULL,
    multiple_test      BOOLEAN NOT NULL,
    learning           BOOLEAN NOT NULL,
    known_good         BOOLEAN NOT NULL,
    board_number       INTEGER NOT NULL
)
"""

_DDL_MEASUREMENTS = """
CREATE TABLE IF NOT EXISTS measurements (
    measurement_id     BIGINT PRIMARY KEY,
    test_run_id        BIGINT NOT NULL,
    test_id            BIGINT NOT NULL,
    component_id       BIGINT,
    record_type        VARCHAR NOT NULL,
    status             SMALLINT NOT NULL,
    measured_value     DOUBLE,
    limit_high         DOUBLE,
    limit_low          DOUBLE,
    limit_nominal      DOUBLE,
    substatus          INTEGER,
    failing_vector     BIGINT,
    failing_pin_count  INTEGER,
    shorts_count       INTEGER,
    opens_count        INTEGER,
    phantoms_count     INTEGER,
    pin_count          INTEGER
)
"""

_DDL_FAILURES = """
CREATE TABLE IF NOT EXISTS failures (
    failure_id         BIGINT PRIMARY KEY,
    measurement_id     BIGINT NOT NULL,
    test_run_id        BIGINT NOT NULL,
    panel_serial       VARCHAR NOT NULL,
    board_profile_id   VARCHAR NOT NULL,
    record_type        VARCHAR NOT NULL,
    status             SMALLINT NOT NULL,
    failure_category   VARCHAR NOT NULL,
    target_refdes      VARCHAR
)
"""

# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

TABLES: tuple[str, ...] = (
    "boards",
    "panels",
    "operators",
    "components",
    "tests",
    "runs",
    "test_runs",
    "measurements",
    "failures",
)

_ALL_DDL: list[str] = [
    _DDL_BOARDS,
    _DDL_PANELS,
    _DDL_OPERATORS,
    _DDL_COMPONENTS,
    _DDL_TESTS,
    _DDL_RUNS,
    _DDL_TEST_RUNS,
    _DDL_MEASUREMENTS,
    _DDL_FAILURES,
]


def init_database(con: duckdb.DuckDBPyConnection) -> None:
    """Create all 9 tables in ``con`` if they do not already exist.

    Safe to call multiple times — idempotent due to ``IF NOT EXISTS``.
    """
    for ddl in _ALL_DDL:
        con.execute(ddl)
