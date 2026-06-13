# Skill: evidence-dialogue

> Invoke: `/evidence-dialogue`
> Structured Q&A where every claim requires cited evidence.
> Prevents hallucination on architectural, design, and domain questions.
> See /skill-sergeant for routing.

---

## When to use

- "Walk me through X with evidence" — you want a grounded, not hallucinated, explanation
- "Is X true for this codebase?" — you want a checked answer, not an assumed one
- "Justify this decision" — you want a decision to be backed by actual evidence
- "Challenge this assumption" — you want someone to actively try to refute a belief
- "Explain why X was built this way" — architecture discussion with evidence

## When NOT to use

- Quick factual questions where you trust the answer (no need for formal evidence)
- Research on external libraries (use /deep-research instead)
- Code implementation (use /execute-plan)

---

## The evidence-dialogue contract

Every claim made in this dialogue must follow this format:

```
CLAIM: [statement being made]
EVIDENCE: [file:line or quote from the code / docs / log — not memory]
CONFIDENCE: HIGH / MEDIUM / LOW
```

If evidence cannot be found:
```
CLAIM: [statement]
EVIDENCE: Not found — I cannot verify this from the current codebase.
CONFIDENCE: NONE — treat as unverified
```

**A claim without evidence is an opinion, not a finding.**

---

## Step 1 — State the question precisely

Before starting, restate the question in one sentence:
```
QUESTION: [exact question — no ambiguity]
SCOPE:    [which files / docs / logs are in scope for evidence]
```

---

## Step 2 — Gather evidence first

Before forming a claim, read the relevant files:
- Source code (specific function or module)
- `docs/logs/DECISION_LOG.md` (why decisions were made)
- `docs/logs/BUG_LOG.md` (known issues that may be relevant)
- Tests (what behavior is actually tested and verified)

Do not answer from memory. Read first, then claim.

---

## Step 3 — Present claims with evidence

```
QUESTION: Is the parser handling malformed lines gracefully?

CLAIM: The parser skips malformed lines and logs them.
EVIDENCE: src/parser/log_parser.py:72 — `except ParseError: logger.warning(f"Skipping line {i}: {e}")`
CONFIDENCE: HIGH

CLAIM: All skipped lines are counted in the summary report.
EVIDENCE: Not found — no summary counter in src/parser/log_parser.py or tests/test_parser/
CONFIDENCE: NONE — this behavior is unverified
```

---

## Step 4 — Adversarial check (for high-stakes questions)

For architectural or design questions that will affect a decision:

Spawn a skeptic agent with:
> Read [claim] and try to refute it using only evidence from [files].
> Find counter-examples, edge cases, or conditions where it breaks.
> Default to "refuted" if uncertain.

If the skeptic refutes the claim: mark it as `[CONTESTED]` and note the counter-evidence.

---

## Step 5 — Conclusion

After the dialogue, produce a summary:

```
## Evidence Dialogue — [topic] — YYYY-MM-DD

QUESTION: [restated]

VERIFIED CLAIMS:
- [Claim 1] — HIGH confidence (file:line)
- [Claim 2] — HIGH confidence (file:line)

UNVERIFIED CLAIMS (need investigation):
- [Claim 3] — NONE confidence — evidence not found

CONTESTED CLAIMS (refuted by adversarial check):
- [Claim 4] — refuted: [counter-evidence]

RECOMMENDATION:
[What to do with this information — which skill to invoke next]
```

---

## Evidence-dialogue guardrails

1. **Never cite a file without reading it.** Memory is not evidence.
2. **Never cite a line number without verifying it's current.** Files change.
3. **Contested claims are not facts.** Don't act on a contested claim without more investigation.
4. **Unverified claims need investigation.** If it matters, find the evidence before acting.
5. **Stop when the question is answered.** Don't keep adding claims beyond what's needed for the decision.
