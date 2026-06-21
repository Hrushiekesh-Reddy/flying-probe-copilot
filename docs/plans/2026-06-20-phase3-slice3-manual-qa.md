## Manual QA — 2026-06-20 — Phase 3 slice 3 (chat UI + live eval)

Exercises the real chat page + the live ≥8/10 evaluation (Phase 3 exit criterion). Needs a valid
(rotated) `GOOGLE_API_KEY` in `.env` and network. Commands use `python -m uv run`.

### §0 — Test suite (offline sanity)
```
cd E:\flying-probe-copilot
python -m uv run pytest tests/test_ui/test_chat_smoke.py tests/test_rag/test_eval.py -q
python -m uv run pytest -q
```
**Expected:** chat+eval pass with 1 skipped (live eval). Full suite **519 passed, 1 skipped, 1 xfailed**, 97%.

### §1 — Prereq: key + sample DB
- `.env` has a rotated `GOOGLE_API_KEY`.
- The dashboard requires the DuckDB to launch — regenerate the gitignored sample DB if needed:
  ```
  uv run generator --board-profile=small --count=30 --out=data/synthetic/
  uv run parser --input=data/synthetic/<run_dir> --db=data/db/sample.duckdb
  ```

### §2 — Live ≥8/10 evaluation (the Phase 3 exit criterion)
PowerShell:
```
$env:RAG_RUN_LLM_EVAL=1; python -m uv run pytest tests/test_rag/test_eval.py -q
```
**Expected:** `test_eval_live_at_least_8_of_10` runs (not skipped) and PASSES — ≥8 of the 10
questions cite the expected failure-mode doc. First run downloads the embedding model (~90 MB) and
calls Gemini 10×. If it fails (<8/10), that is a KB-coverage / prompt-tuning task, not a grounding-rule
change. Unset after: `Remove-Item Env:RAG_RUN_LLM_EVAL`.

### §3 — Chat page (live, interactive)
```
python -m uv run streamlit run src/flying_probe_copilot/ui/app.py
```
In the browser: open the **🤖 Co-Pilot** page (6th in the sidebar nav). Then:
1. Ask: "Why would a chip stand up on one end during reflow?" →
   **Expect:** a grounded answer + a Citations expander listing `failure-modes/tombstoning.md#…`.
2. Ask: "What is the best pizza topping?" →
   **Expect:** the refusal message, no fabricated answer, no citations.
3. Ask a second on-domain question →
   **Expect:** chat history shows both turns in order.

**What to look for:** answers stay within KB content (no invented standards/part numbers); citations
are real chunk_ids; refusals never fabricate; the page never shows a traceback (backend errors surface
as a friendly `st.error`).

### Pass/fail criteria
PASS: §0 green; §2 live eval ≥8/10; §3 grounded answers with real citations + clean refusal + history.
FAIL: live eval <8/10, any ungrounded answer / fake citation, or a page crash — note specifics, log to
BUG_LOG, and (for accuracy) consider expanding `docs/knowledge-base/`.

### After QA
- Merge the slice-3 PR → `dev`, then promote `dev → main` at the Phase 3 boundary. Phase 4 (polish) next.
