## Manual QA — 2026-06-20 — Phase 3 slice 2 (Gemini answer layer)

The unit suite proves the pipeline + grounding offline (mock client). This QA exercises the
REAL Gemini model — it needs a valid `GOOGLE_API_KEY` in `.env` and network. All commands use
`python -m uv run`.

### §0 — Test suite (offline sanity)
```
cd E:\flying-probe-copilot
python -m uv run pytest tests/test_rag -q
python -m uv run pytest -q
```
**Expected:** rag 122 passed; full suite **496 passed, 1 xfailed, 0 failed**, 97%.

### §1 — Prereq: key in .env
- Confirm `.env` has `GOOGLE_API_KEY=<your real key>` (rotate first — it surfaced in a subagent).
- `.env` is gitignored; never commit it.

### §2 — Live grounded answer (script)
Save as `$env:TEMP\answer_smoke.py`:
```python
from flying_probe_copilot.rag import build_retriever, answer, GeminiClient

retriever = build_retriever("docs/knowledge-base")   # downloads all-MiniLM-L6-v2 once
client = GeminiClient()                                # reads GOOGLE_API_KEY from .env

for q in [
    "why would a chip component stand up on one end during reflow?",
    "what causes two nets that should be isolated to read connected?",
    "a resistor reads outside its tolerance limits - what should I check?",
]:
    a = answer(q, retriever=retriever, client=client)
    print(f"\nQ: {q}")
    print(f"  refused: {a.refused}")
    print(f"  answer : {a.answer_text}")
    print(f"  cites  : {a.citations}")
```
Run: `python -m uv run python $env:TEMP\answer_smoke.py`

**What to look for:**
- Q1 grounded, cites `failure-modes/tombstoning.md#...`; Q2 cites `shorts.md#...`;
  Q3 cites `out-of-tolerance-analog.md#...`.
- `refused: False` for all three; every citation is a real chunk_id from the KB.
- Answers read sensibly and stay within the KB content (no invented standards/part numbers).

### §3 — Anti-hallucination (refusal) check
Add to the script (or run interactively):
```python
print(answer("what is the best pizza topping?", retriever=retriever, client=client).refused)  # True
print(answer("", retriever=retriever, client=client).refused)                                  # True
```
**Expected:** off-domain question → `refused True` with the refusal text; empty question → `refused True`.
A refusal must NEVER include a fabricated answer.

### §4 — Missing-key behavior (optional)
- Temporarily blank `GOOGLE_API_KEY` in `.env`, run §2 → expect a clear `ValueError` mentioning
  `GOOGLE_API_KEY` (no crash, no silent empty answer). Restore the key after.

### Pass/fail criteria
PASS: §0 green; §2 three grounded answers with correct real citations; §3 both refuse with no
fabricated content; §4 clear ValueError. FAIL: any ungrounded answer, any citation not in the KB,
any crash — note exactly what was seen and log to BUG_LOG.

### Notes
- This is the slice-2 (single-question) check. The full **10-question ≥8/10 accuracy eval** (the
  Phase 3 exit criterion) is slice 3.
- Strict refusal is intentional. If answers refuse too often, expand `docs/knowledge-base/` or tune
  the prompt — do not weaken the grounding rule.
