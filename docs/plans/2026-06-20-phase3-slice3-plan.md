## Plan — 2026-06-20 — Phase 3 slice 3 (chat UI + 10-Q evaluation)

### Goal Contract
OBJECTIVE:    Add a Co-Pilot chat page to the Streamlit dashboard over `answer()`, and deliver
              the 10-question evaluation (offline citation-pattern tests + an env-gated live
              ≥8/10 accuracy harness = the Phase 3 exit criterion). Closes Phase 3.
SUCCESS-WHEN:
  - `ui/chat.py::render_chat` renders; `app.py` registers a 6th "Co-Pilot" page.
  - Chat backend injectable → `AppTest` smoke tests run offline (no model, no key): a question
    renders the answer + citations; a refusal renders `REFUSAL_TEXT`; history persists in
    `st.session_state`.
  - `docs/eval/phase3-eval-questions.md` + `tests/test_rag/eval_dataset.py` hold 10 (question →
    expected source doc) pairs.
  - Offline eval test: each of the 10 questions → non-refused answer citing the expected doc
    (scripted stub); an off-domain question → refused.
  - Env-gated live test (`RAG_RUN_LLM_EVAL=1`, default-skipped) measures ≥8/10 over the REAL
    retriever + GeminiClient.
  - `pytest -q` green; new code coverage ≥ 80%; full suite passes; unit suite makes ZERO
    network/API calls.
OUT-OF-SCOPE: retrieval/answer contract changes; DuckDB-row grounding; multi-turn retrieval
              context; approval-gated file edits.
CONSTRAINTS:  Branch `feature/phase3-slice3-chat-ui`; TDD; no new deps; one declared edit to the
              existing `ui/app.py` (register the page).

### Architecture
```
src/flying_probe_copilot/ui/chat.py   # render_chat() page + injectable backend
src/flying_probe_copilot/ui/app.py    # +1 st.Page("Co-Pilot")   (declared edit)
docs/eval/phase3-eval-questions.md     # human-readable 10-Q eval set
tests/test_rag/eval_dataset.py         # EVAL_QUESTIONS = [(question, expected_doc), ...] x10
tests/test_ui/test_chat_smoke.py       # AppTest offline (patched backend)
tests/test_rag/test_eval.py            # offline citation-pattern (stub) + env-gated live ≥8/10
```

- **`ui/chat.py`:**
  - `KB_DIR = "docs/knowledge-base"`.
  - `get_retriever()` `@st.cache_resource` → `build_retriever(KB_DIR)` — `# pragma: no cover`
    (real ST embedder, network). `get_client()` `@st.cache_resource` → `GeminiClient()` — pragma.
  - `answer_question(question) -> Answer` = `answer(question, retriever=get_retriever(),
    client=get_client())` — the live wiring, `# pragma: no cover`; **patched in tests**.
  - `render_chat()`: header + caption; init `st.session_state.chat_history`; read
    `st.chat_input`; on submit call `answer_question(prompt)`, append a turn dict; render every
    turn via `st.chat_message` (user q, assistant `answer_text`, citations in an `st.expander`
    as `code` chunk_ids). Refusal renders `answer_text` (== `REFUSAL_TEXT`) with no citations.
- **`ui/app.py`:** add `_chat()` calling `chat.render_chat()` and append
  `st.Page(_chat, title="Co-Pilot", icon="🤖")` to the `pages` list. (Chat needs no DB/Filters.)
- **`tests/test_rag/eval_dataset.py`:** `EVAL_QUESTIONS: list[tuple[str, str]]` — 10 questions
  mapping to the 8 KB docs (expected value = the source `doc_id`, e.g. `failure-modes/tombstoning.md`).
- **Offline eval** (`test_eval.py`): per question, a `StubRetriever` returns a hit whose chunk_id
  is `{expected_doc}#0` + a `FakeLLMClient` citing it → assert `answer()` not refused and cites
  `{expected_doc}#0`. Plus an off-domain question with empty stub → refused. Proves the
  citation-pattern contract for 10 representative cases, deterministically + offline.
- **Live eval** (`test_eval.py`, `@pytest.mark.skipif(not os.environ.get("RAG_RUN_LLM_EVAL"))`):
  real `build_retriever` + `GeminiClient` over the 10 questions; counts non-refused answers whose
  citations include a chunk from the expected doc; asserts `>= 8`. (GeminiClient re-loads the key
  via `_resolve_key`/`load_dotenv`, so the conftest autouse env-strip does not block it.)

### What / Why / Where / When
| # | File | What | Why | When | Test |
|---|------|------|-----|------|------|
| 1 | tests/test_rag/eval_dataset.py | 10 (question, expected_doc) pairs | P3 #7 | first | used by test_eval |
| 2 | docs/eval/phase3-eval-questions.md | human-readable eval set | P3 #7 | with 1 | — |
| 3 | ui/chat.py | render_chat + injectable backend | P3 #6 | after retr/answer exist | test_chat_smoke |
| 4 | ui/app.py | register Co-Pilot page (declared edit) | P3 #6 | after 3 | test_app_smoke (existing) |
| 5 | tests/test_ui/test_chat_smoke.py | AppTest offline (patched backend) | P3 #6 | after 3 | — |
| 6 | tests/test_rag/test_eval.py | offline citation-pattern + env-gated live | P3 #7 | after 1 | — |

### Ordered execution steps (TDD)
1. Create eval_dataset.py (10 pairs) + docs/eval doc.
2. RED test_eval.py offline: 10 questions via StubRetriever+FakeLLMClient cite expected doc; off-domain refuses. (no source yet → import ok, uses existing answer()) → it should already pass against slice-2 `answer()`; this is a data+wiring test → GREEN once dataset exists.
3. RED test_chat_smoke.py: AppTest.from_function(render_chat) with `chat.answer_question` patched → grounded turn renders answer + citation; refusal turn renders REFUSAL_TEXT; history accumulates. → implement ui/chat.py → GREEN.
4. Register page in app.py; extend/confirm test_app_smoke still green (6 pages). → GREEN.
5. Add env-gated live eval test (default-skipped). Confirm it is collected + skipped.
6. Full `python -m uv run pytest -q`; coverage ≥80% new code; full suite green.

### Resolved ambiguities (from Test-Case Plan FLAGs/GAPs)
- **R1 (FLAG-2 — env guard):** add an **autouse env-strip** fixture to `tests/test_ui/conftest.py`
  (delete `GOOGLE_API_KEY`/`ANTHROPIC_API_KEY`) — the slice-2 strip only covers `tests/test_rag/`.
  Every chat test ALSO patches `chat.answer_question`, so the real backend is never reached offline.
- **R2 (FLAG-5/CHAT-08 — backend errors):** `render_chat` wraps the `answer_question` call in
  `try/except Exception` → on failure render `st.error(...)` and append NO history turn (graceful UX;
  `not at.exception`). This also covers the live `ValueError`/network case. Chosen over propagating.
- **R3 (CHAT-09 — empty input):** `st.chat_input` only fires on a non-empty submit; guard `if prompt:`
  so no empty/whitespace turn is ever appended.
- **R4 (DATA-03 — path form):** `expected_doc` is the KB-relative POSIX doc_id, e.g.
  `"failure-modes/tombstoning.md"`. Offline stub builds `chunk_id = f"{expected_doc}#0"`; the
  dataset test asserts `docs/knowledge-base/<expected_doc>` exists; the live test counts a hit when
  any citation `startswith(expected_doc)`.
- **R5 (APP introspection):** AppTest can't cleanly enumerate `st.navigation` titles at 1.58, so the
  app test asserts the dashboard still runs without exception with the 6th page added (existing
  valid/empty/missing-DB smoke covers `main()`); the Co-Pilot page body is covered by the CHAT-* tests
  that call `render_chat` directly.
- **R6 (APP-04 — DB gate):** the chat page logic needs no DB, but the dashboard shell still requires a
  DB to launch (unchanged Phase-2 `st.stop()` behavior). Acceptable + documented; not a defect.
- **R7 (FLAG-1 — multi-turn):** CHAT-06 reuses ONE `AppTest` instance and submits twice; if 1.58
  chat_input re-fire is flaky, fall back to pre-seeding `st.session_state.chat_history` with one turn
  and asserting a submit appends the second.

### Plan Revision 1 (resolving Step 5 adversarial red-team)
**B1 (test seam — BLOCKER):** `AppTest.from_function` source-extracts only the passed function's body
(no module context), so `AppTest.from_function(render_chat)` fails on the first `st.` reference. Fix:
chat tests use self-contained `_smoke_chat(...)` wrappers with **inner imports** (mirroring
`test_views_smoke.py`'s `_smoke_*`): the wrapper does `from flying_probe_copilot.ui import chat;
chat.render_chat()`. The test `monkeypatch.setattr(chat, "answer_question", fake)` BEFORE `.run()`;
`render_chat` resolves `answer_question` from its module globals → the fake (red-team verified module-
global patch is honored in the in-process ScriptRunner). The plan step 3 / test-plan §A
"from_function(render_chat)" wording is superseded by this.

**B2 (offline safety net):** R1's autouse env-strip in `tests/test_ui/conftest.py` is **mandatory**
defense-in-depth. Verified nothing reads the key at import/render (`get_client`/`get_retriever` are
lazy `@st.cache_resource`; `GeminiClient.__init__` reads no key). With the backend patched + env
stripped, no real client/network is reachable offline.

**B3 (grounded path asserts no error):** CHAT-03 also asserts `not at.error` on the grounded path, so
the broad `except Exception → st.error` (R2) cannot silently mask a real regression in the happy path.

**B4 (live eval CI-safety):** EVAL-06 ("gate flips on") verifies the skipif/skip-reason by inspection
ONLY — it must NEVER execute the live body (which, via `_resolve_key`→`load_dotenv`, could fire a real
call if `.env` exists). The live test stays `skipif(not RAG_RUN_LLM_EVAL)`, default-skipped.

**B5 (chunk_id form verified):** slice-1 `kb_loader` ids are `f"{posix_relpath}#{ordinal}"`, so a real
citation is e.g. `"failure-modes/tombstoning.md#0"`. `expected_doc = "failure-modes/<name>.md"`; the
live test counts a hit when a citation `startswith(expected_doc)` — confirmed consistent.

**B6 (app.py doc drift):** the declared `app.py` edit also updates the "5 pages" docstring/comments
(lines ~10, ~36, ~82) to "6 pages" — no stale docs in the one file we edit.

**B7 (APP introspection):** reconciled — the app test asserts `not at.exception` with the 6th page
present (page-title enumeration isn't exposed by AppTest 1.58); the Co-Pilot page body is covered by
the CHAT-* tests. (R7 multi-turn fallback NOT needed — red-team verified two submits on one AppTest
yield two distinct turns with persisted session_state.)

### Guardrails
- Branch: `feature/phase3-slice3-chat-ui` (off dev).
- Approval-gated files: NONE. Declared non-additive edit: `ui/app.py` (+1 page).
- New deps: NONE.
- Offline: chat backend (`get_retriever`/`get_client`/`answer_question`) is `# pragma: no cover`;
  AppTest patches it. Live eval env-gated (`RAG_RUN_LLM_EVAL`), default-skipped. Autouse env-strip
  (slice 2) keeps offline tests keyless.
- Phase discipline: closes Phase 3; after merge owner runs the live ≥8/10 + promotes dev→main.
