# Phase 3 Evaluation — 15 Representative Questions

The Phase 3 exit criterion: the co-pilot correctly answers **≥12 of 15** representative
root-cause questions **with citations**, and refuses ungrounded questions.

Originally 10 questions / ≥8 threshold (Phase 3 exit, met 2026-06-21 on `gemini-3.5-flash`).
The 5 terse short-form questions (11–15) were appended 2026-06-21 after the portfolio capture
surfaced that very short queries like "what causes tombstoning?" were missing the per-section
"Likely causes" chunk under the original `top_k=5` retriever default. The set now exercises both
descriptive and terse shapes; the live threshold scales to ≥12/15 (80%, same pass rate).

This is the canonical question set. It is mirrored in code as `EVAL_QUESTIONS` in
`tests/test_rag/eval_dataset.py` (the offline citation-pattern test + the env-gated live
accuracy test both consume it). Keep the two in sync.

## How it is measured

- **Offline** (`tests/test_rag/test_eval.py`, always runs): each question is driven through
  `answer()` with a scripted stub retriever + fake LLM citing the expected document — proving
  the citation-pattern pipeline deterministically, with no model or key.
- **Live** (`tests/test_rag/test_eval.py`, `@skipif(not RAG_RUN_LLM_EVAL)`): runs the REAL
  retriever + `GeminiClient` over all 15 questions and asserts ≥12 cite the expected document.
  Run it yourself with a key:
  ```
  RAG_RUN_LLM_EVAL=1 python -m uv run pytest tests/test_rag/test_eval.py -q
  ```
  (On Windows PowerShell: `$env:RAG_RUN_LLM_EVAL=1; python -m uv run pytest tests/test_rag/test_eval.py -q`)
- **Retrieval (env-gated, model-only)** (`tests/test_rag/test_retrieval_real.py`,
  `@skipif(not RAG_RUN_MODEL_TESTS)`): runs the real `all-MiniLM-L6-v2` embedder over the KB
  and asserts each terse-form question's target doc is inside `top_k=DEFAULT_TOP_K`. Catches
  retrieval regressions without burning an API call.

## The questions

| # | Question | Expected source document |
|---|----------|--------------------------|
| 1 | Why would a chip component stand up on one end during reflow? | `failure-modes/tombstoning.md` |
| 2 | A part lifted on one end leaving one terminal unconnected after reflow — name the defect. | `failure-modes/tombstoning.md` |
| 3 | What causes two nets that should be isolated to read as connected? | `failure-modes/shorts.md` |
| 4 | Adjacent fine-pitch leads are bridged by excess solder — what is this called? | `failure-modes/shorts.md` |
| 5 | A resistor measures outside its tolerance limits — what should I check? | `failure-modes/out-of-tolerance-analog.md` |
| 6 | Why is there no continuity where the design expects a connection? | `failure-modes/opens.md` |
| 7 | A joint looks dull and grainy and fails intermittently with temperature — what is it? | `failure-modes/cold-solder-joint.md` |
| 8 | A polarized capacitor appears installed backwards — what failure mode is this? | `failure-modes/component-misorientation.md` |
| 9 | The footprint has bare pads where a part should be — what happened? | `failure-modes/missing-component.md` |
| 10 | A solder joint has too little fillet and is electrically marginal — what is the defect? | `failure-modes/insufficient-solder.md` |
| 11 | what causes tombstoning? | `failure-modes/tombstoning.md` |
| 12 | what are shorts? | `failure-modes/shorts.md` |
| 13 | what are opens? | `failure-modes/opens.md` |
| 14 | what is a cold solder joint? | `failure-modes/cold-solder-joint.md` |
| 15 | what is insufficient solder? | `failure-modes/insufficient-solder.md` |

Entries 1–10 are descriptive scenarios (the original Phase 3 exit set).
Entries 11–15 are terse short-form regressions added 2026-06-21.
All 8 seeded failure-mode documents remain covered.

## Refusal check

The co-pilot must refuse (no fabricated answer) for off-domain questions, e.g.:
- "What is the best pizza topping?"
- "" (empty)

These are asserted in `test_eval.py` (offline) and should be spot-checked in manual QA.
