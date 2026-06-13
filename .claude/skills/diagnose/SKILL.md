# Skill: diagnose

> Invoke: `/diagnose`
> Systematic root-cause analysis when a test fails, a feature misbehaves, or output is wrong.
> Do NOT guess. Do NOT retry randomly. Read the evidence, trace the cause.

---

## When to use

- A test that was GREEN is now RED (regression)
- A test stub is failing with an unexpected error (not the expected ImportError/AssertionError)
- CLI output is wrong despite the code looking correct
- DuckDB query returns unexpected results
- Generator produces malformed output

## When NOT to use

- You already know the cause — just fix it
- The test is supposed to be RED (you're in the TDD RED phase)

---

## Step 1 — Read the failure output (do not skip this)

Paste or read the full pytest output including:
- The test name
- The exact error type and message
- The traceback (every line)
- Any assertion comparison (`assert X == Y → X=..., Y=...`)

Do not assume. Read what the error actually says.

---

## Step 2 — Classify the failure

| Class | What it looks like | Next action |
|-------|--------------------|-------------|
| Import error | `ModuleNotFoundError`, `ImportError` | Module doesn't exist or is misspelled. Check `src/` structure. |
| Fixture error | `fixture 'x' not found` | Missing fixture in conftest.py or wrong import. |
| Wrong return value | `assert X == Y` | Implementation returns wrong thing. Trace the function. |
| Exception instead of value | `raises [unexpected error]` | Unhandled edge case. Read traceback. |
| DB error | DuckDB error, column not found | Schema mismatch. Check schema vs query. |
| File not found | `FileNotFoundError` | Wrong path. Check tmp_path fixture vs hardcoded path. |
| Timeout / performance | Test takes too long | Benchmark the slow operation. |

---

## Step 3 — Trace the cause

Walk the call stack from the error backwards:
1. Which line in the test triggered the failure?
2. Which function was called?
3. What did that function receive as input?
4. What did it return / raise?
5. Why?

Read the source file for the failing function. Do not rely on memory — read it now.

---

## Step 4 — Minimal reproduction

Narrow the failure to the smallest possible case:
- Can you reproduce with a simpler input?
- Does the test fail in isolation (`uv run pytest [test] -v`) or only in the full suite?
- If only in full suite: ordering issue (test pollution). Check `conftest.py` for shared state.

---

## Step 5 — Propose a fix

State:
```
ROOT CAUSE: [one sentence — what specifically is wrong]
AFFECTED:   [file:line or function name]
FIX:        [what to change — be specific]
RISK:       [does this fix affect other tests?]
```

Do NOT apply the fix yet. Present it to the parent agent or owner for approval if the change
touches >5 lines or an approval-gated file.

---

## Step 6 — Verify

After applying the fix:
1. Run the previously-failing test: `uv run pytest [test] -v` → GREEN
2. Run the full suite: `uv run pytest` → same or better pass rate
3. If new failures appear: STOP. The fix introduced a regression. Revert and diagnose again.

---

## Common patterns in this codebase

| Symptom | Likely cause |
|---------|-------------|
| DuckDB query returns 0 rows | Table not seeded in fixture. Use `tmp_db` fixture with schema + INSERT. |
| Generator output varies between runs | `random` not seeded. Add `random.seed(42)` in fixture. |
| ImportError on `flying_probe_copilot` | Package not installed. Run `uv pip install -e .` in the venv. |
| `ParseError` not defined | Need to define and export it from the parser module. |
| CLI test fails on path | Use `tmp_path` pytest fixture, not hardcoded paths. |
