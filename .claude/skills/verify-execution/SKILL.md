# Skill: verify-execution

> Invoke: `/verify-execution`
> Post-implementation verification. Confirms the output meets the plan's success criteria.
> Run after /execute-plan completes. This is Step 9 of the session workflow.
> See /skill-sergeant for routing.

---

## When to use

- After /execute-plan completes — before the session-end commit
- "Is this implementation correct?"
- "Does this meet the spec?"
- "Verify the implementation against the plan"

## When NOT to use

- To find bugs in failing code (use /diagnose)
- To review code quality or style (use /evidence-dialogue or code-review)
- Before implementation exists (there's nothing to verify yet)

---

## Step 1 — Load the success criteria

Read the plan document at `docs/plans/YYYY-MM-DD-[name].md`.
Find the `SUCCESS-WHEN` section. These are the acceptance criteria.
Read them carefully — this is what you're verifying against, not your own opinion.

---

## Step 2 — Run the test suite

```bash
# Full suite
pytest -v

# With coverage
pytest --cov=src --cov-report=term-missing

# Or your project's test command
```

Record:
- Total passing / failing / errored
- Coverage delta vs baseline
- Any new failures that weren't in the plan

---

## Step 3 — Check each SUCCESS-WHEN criterion

For every criterion in the plan, produce a verdict:

```
Criterion: "yield by board query returns correct result"
Evidence:  test_parser/test_roundtrip.py::test_yield_query_result — PASS
Verdict:   ✓ MEETS criterion

Criterion: "1,000 logs generate in <30 seconds"
Evidence:  test_generator/test_performance.py::test_1000_logs_under_30s — PASS (24.3s)
Verdict:   ✓ MEETS criterion

Criterion: "malformed lines are skipped, not crash"
Evidence:  test_parser/test_log_parser.py::test_malformed_line_skipped — PASS
Verdict:   ✓ MEETS criterion
```

---

## Step 4 — Spot-check manually (if applicable)

For CLI tools, database queries, or UI output — run the actual command and observe the output.

```bash
# Example: CLI spot-check
uv run generator --board-profile=small --count=10 --out=tmp/
# Check: does the output directory contain the expected files?
# Check: are the files non-empty and valid?
```

Document what you ran and what you saw.

---

## Step 5 — Output verdict

```
## Verification Report — YYYY-MM-DD

### Test suite
- Passing: N
- Failing: 0
- Coverage: X% (delta: +Y%)

### SUCCESS-WHEN criteria
- [x] Criterion 1 — PASS (evidence: test name or manual check)
- [x] Criterion 2 — PASS
- [ ] Criterion 3 — FAIL (evidence: test name or what you saw)

### Overall verdict
PASS — all criteria met. Ready to commit.
  OR
FAIL — criteria not met. Do NOT commit. Return to /execute-plan or /diagnose.

### Notes
- [Any observations that aren't criteria failures but are worth noting]
```

---

## Escalation on failure

If any SUCCESS-WHEN criterion is not met:
1. Do NOT commit.
2. Document exactly which criterion failed and what the evidence shows.
3. Return to `/diagnose` if it's a bug, or `/execute-plan` if the implementation is simply incomplete.
4. Re-run verify-execution after the fix — a new verification pass is required before committing.
