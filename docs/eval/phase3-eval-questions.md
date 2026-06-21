# Phase 3 Evaluation — 10 Representative Questions

The Phase 3 exit criterion: the co-pilot correctly answers **≥8 of 10** representative
root-cause questions **with citations**, and refuses ungrounded questions.

This is the canonical question set. It is mirrored in code as `EVAL_QUESTIONS` in
`tests/test_rag/eval_dataset.py` (the offline citation-pattern test + the env-gated live
accuracy test both consume it). Keep the two in sync.

## How it is measured

- **Offline** (`tests/test_rag/test_eval.py`, always runs): each question is driven through
  `answer()` with a scripted stub retriever + fake LLM citing the expected document — proving
  the citation-pattern pipeline deterministically, with no model or key.
- **Live** (`tests/test_rag/test_eval.py`, `@skipif(not RAG_RUN_LLM_EVAL)`): runs the REAL
  retriever + `GeminiClient` over all 10 questions and asserts ≥8 cite the expected document.
  Run it yourself with a key:
  ```
  RAG_RUN_LLM_EVAL=1 python -m uv run pytest tests/test_rag/test_eval.py -q
  ```
  (On Windows PowerShell: `$env:RAG_RUN_LLM_EVAL=1; python -m uv run pytest tests/test_rag/test_eval.py -q`)

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

All 8 seeded failure-mode documents are covered (tombstoning and shorts each get two phrasings).

## Refusal check

The co-pilot must refuse (no fabricated answer) for off-domain questions, e.g.:
- "What is the best pizza topping?"
- "" (empty)

These are asserted in `test_eval.py` (offline) and should be spot-checked in manual QA.
