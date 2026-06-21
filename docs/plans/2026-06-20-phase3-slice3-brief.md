## Session Brief — 2026-06-20 — Phase 3 slice 3 (chat UI + 10-Q evaluation)

### What the owner wants
> "lets start slice 3" (after merging slice 2, PR #26).

Finish Phase 3: wire a **chat interface** into the Streamlit dashboard over the slice-2
`answer()` function, and deliver the **10 representative-question evaluation** (the Phase 3
exit criterion: ≥8/10 root-cause questions answered with citations; ungrounded refused).

### Goal statement (one sentence)
Add a "Co-Pilot" chat page to `ui/` that calls `answer()` and renders grounded answers with
clickable citations (and the refusal message when ungrounded), plus a 10-question evaluation
harness — an offline citation-pattern test suite (mocked) and an env-gated live-accuracy test
that measures the ≥8/10 exit criterion against the real Gemini model.

### Success looks like
- A new `ui/chat.py` with a `render_chat()` page; `app.py` registers it as a 6th page in
  `st.navigation`. The page: takes a question (`st.chat_input`), calls `answer()` over a cached
  real retriever + `GeminiClient`, renders the answer + its citations (each linking to / showing
  the cited chunk), shows `REFUSAL_TEXT` plainly when `refused`, and keeps chat history in
  `st.session_state`.
- The chat backend is injectable so `AppTest` smoke tests run fully offline (no model, no key).
- A 10-question eval dataset (question → expected source doc) committed under `docs/eval/`.
- Offline test: each of the 10 questions, run through `answer()` with a scripted stub, yields a
  non-refused answer citing the expected chunk (proves the citation-pattern pipeline) + the
  anti-hallucination refusal still holds.
- Env-gated live test (`RAG_RUN_LLM_EVAL=1`, default-skipped) that runs the REAL retriever +
  `GeminiClient` over the 10 questions and asserts ≥8/10 cite the expected source doc — the
  measurable exit criterion, runnable by the owner with a key.
- `pytest -q` green; new code coverage ≥ 80%; existing suite passes; unit suite makes zero
  network/API calls.

### Out of scope (explicit)
- ❌ Changing the slice-1/2 retrieval or answer contracts.
- ❌ DuckDB-row grounding (KB-corpus grounding only, as established).
- ❌ Multi-turn conversational memory beyond a simple displayed history (no follow-up context
  passed back into retrieval this slice).
- ❌ Approval-gated file edits (`pyproject.toml`, `db/schema.py`, `.claude/settings.json`,
  `.env.example`; `CLAUDE.md` only its Step-10 session-log line).

### Phase / milestone
ROADMAP Phase 3 — delivers #6 (chat UI) and #7 (10 representative-question tests). Completing
this slice **closes Phase 3**; the live ≥8/10 measurement is the owner's env-gated/manual run.

### Branch
`feature/phase3-slice3-chat-ui` — off `dev` (after #26 merged; clean).

### Dependencies
- streamlit + plotly + google-generativeai all already declared + locked. `GOOGLE_API_KEY` in
  gitignored `.env` (owner to ROTATE — surfaced in a subagent last session) — needed only for the
  live eval / manual QA, NOT for the unit suite.
