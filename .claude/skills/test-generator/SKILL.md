# Skill: test-generator

> Invoke: `/test-generator`
> Use BEFORE /execute-plan. Generates failing test stubs so implementation has a clear target.

---

## When to use

- After `/plan-architect` produces a plan and before any implementation starts
- When adding a new module or function
- When coverage is missing for existing code (stretch goal)

---

## Before generating

1. Read the approved plan from `docs/plans/`.
2. Read any existing tests in `tests/` to avoid duplication and match fixture style.
3. Read `conftest.py` to know what fixtures are available.
4. Read the target source file (if it exists) to understand the interface being tested.

---

## Step 1 — Map the test surface

For each function/module in the plan, list:

```
Function: parse_header(line: str) -> dict
Tests needed:
  - valid input with all fields → returns correct dict
  - valid input with optional field missing → returns dict with None
  - malformed line (no colon separator) → raises ParseError
  - empty string → raises ParseError
  - line with extra whitespace → strips and parses correctly
```

---

## Step 2 — Generate test stubs (RED by design)

Write tests that are complete but will FAIL because the implementation doesn't exist yet.

```python
# tests/test_parser/test_log_parser.py
import pytest
from flying_probe_copilot.parser.log_parser import parse_header, ParseError


def test_parse_header_valid_all_fields():
    line = "BOARD: SN-001 | DATE: 2024-01-15 | OP: J.SMITH"
    result = parse_header(line)
    assert result["board_sn"] == "SN-001"
    assert result["date"] == "2024-01-15"
    assert result["operator"] == "J.SMITH"


def test_parse_header_missing_optional_field():
    line = "BOARD: SN-001 | DATE: 2024-01-15"
    result = parse_header(line)
    assert result["board_sn"] == "SN-001"
    assert result["operator"] is None


def test_parse_header_malformed_raises_parse_error():
    with pytest.raises(ParseError, match="no separator"):
        parse_header("this is not a valid header line")


def test_parse_header_empty_string_raises_parse_error():
    with pytest.raises(ParseError):
        parse_header("")


def test_parse_header_strips_whitespace():
    line = "BOARD:   SN-001  | DATE:  2024-01-15 "
    result = parse_header(line)
    assert result["board_sn"] == "SN-001"
```

---

## Step 3 — Verify tests are RED

Run `uv run pytest tests/[module]/test_[file].py -v` and confirm:
- All new tests show as FAILED or ERROR (ImportError is acceptable — module doesn't exist yet)
- No new tests are accidentally PASSING (that would mean the stub is wrong)

Output the pytest summary so the owner can see the RED state.

---

## Step 4 — Fixture checklist

Confirm or add to `conftest.py`:

```python
# For generator tests
@pytest.fixture
def small_board():
    return {"name": "small", "component_count": 50, "fault_rate": 0.02}

# For parser tests
@pytest.fixture
def sample_log_path(tmp_path):
    log = tmp_path / "test.log"
    log.write_text("BOARD: SN-001 | DATE: 2024-01-15 | OP: J.SMITH\n")
    return log

# For DB tests
@pytest.fixture
def tmp_db():
    import duckdb
    conn = duckdb.connect(":memory:")
    yield conn
    conn.close()
```

---

## Quality rules for generated tests

1. **One behavior per test** — not one test for everything.
2. **Assertion messages** — every `assert` has a failure message: `assert x == y, f"Expected {y}, got {x}"`.
3. **No magic numbers** — use named variables or fixtures.
4. **Edge cases included** — empty, null, max, malformed, boundary.
5. **No real I/O** — use `tmp_path`, in-memory DuckDB, mocked API calls.
6. **Deterministic** — seed any random calls: `random.seed(42)`.

---

## TDD loop hand-off

After test-generator completes:
1. Stubs exist → all RED ✓
2. Hand off to `/execute-plan`
3. Execute-plan makes them GREEN one by one

Never move to execute-plan until at least the first stub is confirmed RED.
