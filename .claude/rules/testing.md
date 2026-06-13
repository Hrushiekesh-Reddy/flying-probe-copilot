# Testing Rules — Flying-Probe Co-Pilot

## TDD is non-negotiable

**Write tests before implementation. Every time. No exceptions.**

```
RED   → write a failing test
GREEN → write the minimum code to pass it
REFACTOR → clean up while keeping it green
REPEAT
```

Never commit implementation code without a corresponding test file.

---

## Test directory structure

```
tests/
├── conftest.py                        # Shared fixtures (tmp DuckDB, board profiles, etc.)
├── test_generator/
│   ├── test_board_profile.py          # Profile configs produce correct component ranges
│   ├── test_fault_injection.py        # Fault rates within tolerance
│   └── test_output_formats.py         # Log/CSV/JSON are valid and parseable
├── test_parser/
│   ├── test_log_parser.py             # Parser ingests every generator output
│   └── test_roundtrip.py              # Generator → parser → DuckDB → query = expected
├── test_analytics/
│   ├── test_yield.py                  # Yield-over-time returns correct values
│   └── test_pareto.py                 # Failure Pareto orders correctly
└── test_rag/
    ├── test_retrieval.py              # Hybrid retrieval returns relevant rows
    └── test_qa.py                     # 10 representative questions pass/fail
```

---

## Naming conventions

- Files: `test_[module_name].py`
- Functions: `test_[what]_[condition]_[expected_outcome]()`
- Examples:
  - `test_fault_injection_opens_rate_within_tolerance()`
  - `test_parser_malformed_line_logged_and_skipped()`
  - `test_yield_query_returns_correct_value_for_known_dataset()`

---

## Running tests

```bash
# Full suite
uv run pytest -v

# With coverage report
uv run pytest --cov=src --cov-report=term-missing

# One module
uv run pytest tests/test_generator/ -v

# Stop on first failure
uv run pytest -x

# Run a single test
uv run pytest tests/test_generator/test_fault_injection.py::test_fault_injection_opens_rate_within_tolerance -v
```

---

## Coverage targets by phase

| Phase | Target | Focus |
|-------|--------|-------|
| 1a — Generator | ≥90% | Output format logic, fault injection |
| 1b — Parser | ≥95% | Round-trip paths, malformed-line handling |
| 2 — Analytics | ≥80% | Yield, Pareto, SPC helpers |
| 3 — RAG | 10 fixed Q&A tests | Correctness over coverage |

---

## Test quality rules

1. **Deterministic** — seed `random` with a fixed value; no date-dependent assertions without mocking.
2. **No silent passes** — every assertion has a clear failure message.
3. **Test behavior, not internals** — test what the function does, not how.
4. **Integration tests use tmp fixtures** — in-memory DuckDB or `tmp_path` for file I/O.
5. **No real API calls** — mock Gemini/Claude API in tests.
6. **No production data** — all test data is synthetic, generated in fixtures.
7. **Edge cases are first-class** — empty input, zero faults, max components, malformed lines.

---

## Phase 1a — Generator test checklist

Before Phase 1a is considered done, ALL of these must pass:

- [ ] 3 board profiles (small/medium/large) produce distinct component counts
- [ ] Fault injection rate for each fault type is within ±10% of configured rate
- [ ] Output `.log` file is parseable (no corrupt lines)
- [ ] Output `.csv` file passes `csv.reader` without error
- [ ] Output `.json` file passes `json.loads` without error
- [ ] CLI `uv run generator --board-profile=medium --count=100` produces files in target dir
- [ ] 1,000 logs generate in <30 seconds (performance test)

## Phase 1b — Parser test checklist

- [ ] Parser ingests all 3 board profile formats without error
- [ ] Round-trip: generator output → parser → DuckDB → "yield by board last week" = expected
- [ ] Malformed lines are skipped (not crash) and logged
- [ ] Round-trip integrity for ≥99% of generator output

---

## conftest.py essentials

```python
import pytest
import duckdb

@pytest.fixture
def tmp_db(tmp_path):
    """In-memory DuckDB for tests. Never touches the real database."""
    conn = duckdb.connect(":memory:")
    yield conn
    conn.close()

@pytest.fixture
def small_board_profile():
    """Fixed small board profile for deterministic tests."""
    return {"name": "small", "component_count": 50, "fault_rate": 0.02}
```
