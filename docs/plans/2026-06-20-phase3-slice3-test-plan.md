## Test-Case Plan — 2026-06-20 — Phase 3 slice 3 (chat UI + 10-Q evaluation)

Role: Test Planner (test-generator). This document enumerates **behavior-level** test cases
(inputs → expected outputs/effects) for the modules under test. It contains **no production code,
no test stubs/asserts, and no edits to source or the implementation plan**. Coverage gaps and
ambiguities are flagged for resolution before approval.

### Scope / modules under test
- `src/flying_probe_copilot/ui/chat.py` — `render_chat()` page + injectable `answer_question`.
- `src/flying_probe_copilot/ui/app.py` — registers a 6th "Co-Pilot" `st.Page`.
- `tests/test_rag/eval_dataset.py` — `EVAL_QUESTIONS` (10 question/expected-doc pairs).
- `tests/test_rag/test_eval.py` — offline citation-pattern test (10) + off-domain refusal +
  env-gated live ≥8/10 test.

### Contracts the cases rely on (from reading source)
- `answer()` returns a frozen `Answer(question, answer_text, citations, refused, retrieved_ids)`.
  Non-refused requires hits + valid JSON + `sufficient is True` + non-empty answer + ≥1 citation
  that was actually retrieved. Else `refused=True`, `answer_text == REFUSAL_TEXT`, `citations == ()`.
- `REFUSAL_TEXT = "I don't have enough grounded evidence in the knowledge base to answer that."`
- `render_chat()` (per plan): header + caption; init `st.session_state.chat_history`; read
  `st.chat_input`; on submit call module-level `answer_question(prompt)`, append a turn, render
  each turn via `st.chat_message` (user question; assistant `answer_text`; citations as `code`
  chunk_ids inside an `st.expander`). Refusal → render `answer_text` with no citation expander.
- `answer_question(question) -> Answer` is the live-wiring seam (`# pragma: no cover`); **patched**
  in every offline chat test so no retriever/model/key is touched.
- The 8 real KB docs live under `docs/knowledge-base/failure-modes/`:
  `cold-solder-joint.md, component-misorientation.md, insufficient-solder.md,
  missing-component.md, opens.md, out-of-tolerance-analog.md, shorts.md, tombstoning.md`.
- Streamlit pinned `>=1.40`; resolved `1.58.0` (AppTest `chat_input` element is supported).
- Reuse fixtures from `tests/test_rag/conftest.py`: `FakeLLMClient`, `RaisingLLMClient`,
  `StubRetriever`, and the autouse `_strip_llm_env`. Reuse `ui_db_path` from
  `tests/test_ui/conftest.py`. Mirror `AppTest` style from `test_views_smoke.py` /
  `test_app_smoke.py`.

---

### A. `ui/chat.py` — `render_chat()` via `AppTest.from_function`
All cases patch the module-level `chat.answer_question` (monkeypatch or a wrapper passed through
`AppTest.from_function(..., kwargs=...)`) BEFORE `.run()`. Style mirrors the `_smoke_*`
self-contained functions in `test_views_smoke.py`.

| Case ID | Unit | Input / precondition | Expected result | Deliverable |
|---|---|---|---|---|
| CHAT-01 | render_chat (initial) | `answer_question` patched (never invoked); no chat input submitted; fresh AppTest | `at.run()` raises no exception (`not at.exception`); page header present (e.g. `at.header`/`at.title`/`at.markdown` non-empty); no `st.chat_message` blocks rendered; patched backend `call_count == 0`; `st.session_state.chat_history` exists and is empty | tests/test_ui/test_chat_smoke.py |
| CHAT-02 | render_chat (chat_input present) | Same as CHAT-01, initial render | A `chat_input` widget is present in the rendered app (`at.chat_input` non-empty) so a question can be submitted | tests/test_ui/test_chat_smoke.py |
| CHAT-03 | render_chat (grounded submit) | Patch `answer_question` to return a grounded `Answer(question=q, answer_text="<grounded text>", citations=("tombstoning.md#0",), refused=False, retrieved_ids=("tombstoning.md#0",))`; set `at.chat_input[0].set_value(q)` then `.run()` | No exception; exactly one user `chat_message` showing `q` and one assistant `chat_message`; assistant block contains the grounded `answer_text`; an expander is present and shows the citation chunk_id `tombstoning.md#0` as code; `chat_history` has 1 turn; backend `call_count == 1` and was called with `q` | tests/test_ui/test_chat_smoke.py |
| CHAT-04 | render_chat (multi-citation) | Patch backend to return `citations=("opens.md#0","shorts.md#1")` (both in `retrieved_ids`); submit one question | All cited chunk_ids rendered as code in the expander, in returned order; no exception; 1 turn | tests/test_ui/test_chat_smoke.py |
| CHAT-05 | render_chat (refusal submit) | Patch `answer_question` to return `Answer(answer_text=REFUSAL_TEXT, citations=(), refused=True, retrieved_ids=())`; submit an off-domain question | No exception; assistant `chat_message` shows `REFUSAL_TEXT`; **no citation expander** rendered (and/or no `code` chunk_id elements); `chat_history` has 1 turn | tests/test_ui/test_chat_smoke.py |
| CHAT-06 | render_chat (history accumulates, 2 turns) | On the **same** `at` instance: submit Q1 (grounded) → `.run()`; then set `chat_input` to Q2 (grounded) → `.run()` again | After the second run, `st.session_state.chat_history` length == 2 (Q1 then Q2), both prior + new turns rendered as `chat_message` pairs; no exception. **See FLAG-1 on AppTest session_state persistence — this case is only valid if state survives between `.run()` calls on the same `at`.** | tests/test_ui/test_chat_smoke.py |
| CHAT-07 | render_chat (no key/retriever touched) | Any of CHAT-01..06 with patched backend | Patched `answer_question` is the only path; the real `get_retriever()`/`get_client()`/`answer()` are never invoked (assert via the injected fake's call record); no network/model/key access. **See FLAG-2 (env guard).** | tests/test_ui/test_chat_smoke.py |
| CHAT-08 | render_chat (backend raises) | Patch `answer_question` to raise (e.g. `RuntimeError`/`ValueError`); submit a question | **Behavior is undecided — see FLAG-5.** Plan a single case for the chosen contract: either (a) page catches it and renders `st.error` with a friendly message (assert an `at.error` element, `not at.exception`, history unchanged), OR (b) error propagates (assert `at.exception` is set). MUST be resolved before this case is finalized. | tests/test_ui/test_chat_smoke.py |
| CHAT-09 | render_chat (whitespace/empty input) | Submit an empty or whitespace-only chat_input value (if AppTest allows submission) | No exception; either no turn is appended (preferred — mirrors `answer()` blank-question refusal-before-LLM) or a refusal turn is appended. **Resolve expected behavior — ambiguity, see Gaps.** | tests/test_ui/test_chat_smoke.py |

### B. `ui/app.py` — Co-Pilot page registration
Style mirrors `test_app_smoke.py` (`AppTest.from_file(APP_PATH)` with `FPC_DB_PATH` set to
`ui_db_path`). The page list is the unit of behavior; chat content is covered in section A.

| Case ID | Unit | Input / precondition | Expected result | Deliverable |
|---|---|---|---|---|
| APP-01 | app navigation (6 pages) | `FPC_DB_PATH=ui_db_path`; run app | App registers exactly 6 pages including one titled "Co-Pilot"; the other 5 (Overview, Yield, Failure Pareto, SPC, Anomalies) still present; no exception | tests/test_ui/test_app_smoke.py |
| APP-02 | app default page unchanged | Same | Default/landing page is still "Overview" (`default=True` on Overview only); "Co-Pilot" is not default | tests/test_ui/test_app_smoke.py |
| APP-03 | existing app smoke still green (regression) | Re-run existing `TestAppSmokeValid` / `EmptyDb` / `MissingDb` cases | All existing assertions still pass: valid DB → no exception + sidebar date_input present; empty DB → no exception; missing DB → `st.error` + stop, no Python exception | tests/test_ui/test_app_smoke.py (existing) |
| APP-04 | Co-Pilot page navigable without DB dependency | Navigate/select the Co-Pilot page (patch chat backend if the page imports a live seam at module import) | Co-Pilot page renders without requiring DB rows / Filters; no exception. **NOTE:** the missing-DB guard `st.stop()` runs before `st.navigation`, so with a missing DB the Co-Pilot page is unreachable — confirm whether that is acceptable (see Gaps). | tests/test_ui/test_app_smoke.py |

> **Note on APP test mechanics:** how to enumerate registered pages/titles via AppTest at
> Streamlit 1.58 needs confirmation (the existing smoke test only asserts `not at.exception` and
> sidebar widgets, not the page set). If `st.navigation` page titles are not directly inspectable
> through the AppTest API, APP-01/APP-02 may need to assert via the rendered nav elements or via a
> direct unit check of the `pages` list construction. **Flagged in Gaps (page-introspection).**

### C. `tests/test_rag/eval_dataset.py` — dataset integrity
Pure data tests; no AppTest, no LLM. The autouse `_strip_llm_env` (test_rag conftest) applies here.

| Case ID | Unit | Input / precondition | Expected result | Deliverable |
|---|---|---|---|---|
| DATA-01 | EVAL_QUESTIONS count | Import `EVAL_QUESTIONS` | Exactly 10 entries | tests/test_rag/test_eval.py |
| DATA-02 | pair shape | Each entry | Is a `(question:str, expected_doc:str)` 2-tuple; both non-empty strings | tests/test_rag/test_eval.py |
| DATA-03 | expected_doc resolves to a real file | For each `expected_doc` | A file exists under `docs/knowledge-base/failure-modes/` matching the value (resolve relative to repo root; account for the `failure-modes/<name>.md` form noted in the plan vs a bare `<name>.md`) — so the live test can actually pass | tests/test_rag/test_eval.py |
| DATA-04 | no duplicate questions | The 10 question strings | All distinct (set length == 10); ideally normalized (strip/casefold) to catch near-dupes | tests/test_rag/test_eval.py |
| DATA-05 | coverage of the 8 docs | The set of `expected_doc` values | Subset of the 8 real failure-mode docs; (advisory) spread across docs rather than all pointing at one — confirm intended coverage breadth with owner | tests/test_rag/test_eval.py |
| DATA-06 | docs/eval human-readable set parity | `docs/eval/phase3-eval-questions.md` exists and lists the same 10 questions | The markdown eval set and `EVAL_QUESTIONS` agree (same 10 questions / expected docs). **Advisory — may be manual; flag if not asserted in code.** | (manual or tests/test_rag/test_eval.py) |

### D. `tests/test_rag/test_eval.py` — offline citation-pattern + off-domain + live gate
Offline cases use `StubRetriever` + `FakeLLMClient` from the test_rag conftest. The autouse
`_strip_llm_env` keeps these keyless. They exercise the real `answer()` (no contract change).

| Case ID | Unit | Input / precondition | Expected result | Deliverable |
|---|---|---|---|---|
| EVAL-01 | offline pattern, all 10 | For each `(q, expected_doc)`: `StubRetriever` returns one hit whose `chunk_id == "{expected_doc}#0"`; `FakeLLMClient` returns JSON `{"sufficient": true, "answer": "...", "citations": ["{expected_doc}#0"]}`; call `answer(q, retriever=stub, client=fake)` | For all 10: `refused is False`; `answer_text` non-empty; `"{expected_doc}#0"` in `citations`; `client.call_count == 1` (parametrized — 10 logical cases) | tests/test_rag/test_eval.py |
| EVAL-02 | citation must be a retrieved id | (Robustness) FakeLLMClient cites a chunk_id NOT in retrieved_ids | `answer()` refuses (`refused is True`, empty citations) — confirms the offline pattern truly proves grounding, not just echo | tests/test_rag/test_eval.py |
| EVAL-03 | off-domain refuses | Off-domain question with an **empty** `StubRetriever` (no hits); `RaisingLLMClient` injected | `answer()` returns `refused is True`, `answer_text == REFUSAL_TEXT`, `citations == ()`; **LLM never called** (RaisingLLMClient would raise if it were) | tests/test_rag/test_eval.py |
| EVAL-04 | live test is collected | Collection with `RAG_RUN_LLM_EVAL` unset | The live ≥8/10 test is **collected** (it exists / is importable), not silently absent | tests/test_rag/test_eval.py |
| EVAL-05 | live test is skipped by default | Run suite with `RAG_RUN_LLM_EVAL` unset (default CI) | The live test is **skipped** (reports as skipped via `skipif`), makes zero network/model calls; suite stays green and offline | tests/test_rag/test_eval.py |
| EVAL-06 | live test gate flips on | Set `RAG_RUN_LLM_EVAL=1` (without a key, in unit env) | The test is **selected/not-skipped**; with the autouse env-strip removing `GOOGLE_API_KEY` and no real network, it would attempt the live path — this is the live-only path (see FLAG-3/FLAG-4). **Do NOT run this in the offline unit suite**; this case only verifies the gate flips, e.g. via collection/skip-reason inspection, not by executing the live body. | tests/test_rag/test_eval.py |

> **EVAL-06 caution:** verifying "gate flips on" must not actually fire a live call in CI. Plan
> this as a skip-reason / `skipif` condition check, or keep it strictly Manual QA. Resolve with
> owner (see Gaps).

---

### FLAGGED GAPS (must be resolved before approval)

**FLAG-1 — Does AppTest persist `st.session_state` across multiple `.run()` calls?**
The multi-turn history case (CHAT-06) is only meaningful if state survives between runs.
- AppTest preserves `session_state` across repeated `.run()` calls **on the same `at` instance**
  (it is one persistent ScriptRunner session). A **new** `AppTest.from_function(...)` per turn
  starts fresh and loses history.
- Required test discipline: build ONE `at`, set `chat_input`, `.run()`, then set `chat_input`
  again and `.run()` again; assert `at.session_state.chat_history` grows to 2.
- Open risk: AppTest may need `chat_input[0].set_value(...)` re-set each run, and whether a
  submitted `chat_input` value clears or repeats on the next run is version-dependent at 1.58 —
  **verify empirically** that two distinct submits produce two distinct turns (and not a
  duplicate/echo of turn 1). If AppTest cannot drive two independent chat submits, downgrade
  CHAT-06 to: directly seed `st.session_state.chat_history` with one turn pre-run and assert a
  new submit appends a second — and record the limitation here.

**FLAG-2 — The autouse env-strip is in `tests/test_rag/conftest.py`; it does NOT reach
`tests/test_ui/`.** Confirmed by reading the conftest tree:
- `tests/conftest.py` (root) does NOT strip `GOOGLE_API_KEY`/`ANTHROPIC_API_KEY`.
- `tests/test_ui/conftest.py` does NOT strip them either.
- Therefore the chat smoke tests in `tests/test_ui/` run with the real environment visible.
  Even though every chat case patches `answer_question` (so the live seam should never run), if a
  test forgets to patch, or the page eagerly constructs `get_client()`/`get_retriever()` at import,
  a real key/model/network could be touched.
- **Resolution required:** add a guard for the chat tests — either an autouse env-strip fixture in
  `tests/test_ui/conftest.py` (mirroring the test_rag one) or move the env-strip up to
  `tests/conftest.py` so it covers the whole suite. Plan an explicit guard case:
  *"with `answer_question` patched, no `GOOGLE_API_KEY` is read and no network call is made."*

**FLAG-3 — Live eval needs the real `GOOGLE_API_KEY`, but the autouse strip deletes it.**
Confirmed by reading `rag/llm.py`: `GeminiClient._resolve_key()` calls `load_dotenv()` and then
reads `os.environ.get("GOOGLE_API_KEY")` lazily inside `generate()`. So even after the autouse
fixture deletes the process-env var, `load_dotenv()` re-loads the key from the repo `.env` at call
time. **Conclusion: the live eval can still obtain the key via `.env` despite the env-strip** — the
slice-2 behavior holds. (Caveat: requires a valid, non-rotated key in `.env`; the brief notes the
key is to be rotated by the owner.) This is a live-only / Manual-QA path; do not rely on it in CI.

**FLAG-4 — Building the real retriever in the live test downloads a model.**
`get_retriever()` → `build_retriever(KB_DIR)` loads a real SentenceTransformer embedder (network
+ model download on first use) and is `# pragma: no cover`. The live ≥8/10 test therefore: (a) is
network/model dependent, (b) is slow, (c) must stay env-gated and default-skipped. **Acknowledged
as live-only / Manual QA — never part of the offline unit suite.**

**FLAG-5 — Undecided: how should `render_chat` behave when the backend raises?** (CHAT-08)
The plan does not specify. Two viable contracts:
- (a) **Catch + surface:** wrap `answer_question()` in try/except, render `st.error(...)`, leave
  `chat_history` unchanged → test asserts an `at.error` element and `not at.exception`. (Friendlier
  UX; recommended for a user-facing page.)
- (b) **Propagate:** let the exception bubble → AppTest records it in `at.exception`. (Simpler; but
  a transient model/network error would crash the page.)
  **Owner/implementer must choose before CHAT-08 is finalized.** This is a real gap: a live
  `GeminiClient.generate()` can raise (no key → `ValueError`; network/API errors) and there is no
  decided handling.

---

### "Untestable by automation" → Manual QA
- The **real answer quality** / wording of grounded answers from the live Gemini model.
- The **actual ≥8/10 accuracy number** (the Phase 3 exit criterion) — requires a real key + model
  download; run by the owner with `RAG_RUN_LLM_EVAL=1`.
- Real **citation links/click-through** rendering fidelity in a live browser (AppTest sees element
  trees, not rendered DOM/links).
- `_call_model` / live `GeminiClient.generate()` network behavior (`# pragma: no cover`).
- Visual layout: `st.chat_message` avatars, expander styling, caption text.

### Coverage gaps / ambiguities to resolve before approval
1. **CHAT-08 / FLAG-5:** decide backend-raise behavior (surface vs propagate).
2. **FLAG-2:** add an env-strip guard reachable by `tests/test_ui/` (autouse in test_ui conftest or
   promote to root conftest); add the explicit "no key read / no network" guard case.
3. **CHAT-06 / FLAG-1:** confirm AppTest multi-`.run()` session_state persistence empirically and
   that two chat submits yield two distinct turns; adjust the case if AppTest can't drive it.
4. **CHAT-09:** define expected behavior for empty/whitespace chat input (skip turn vs refusal
   turn). AppTest may also disallow submitting an empty `chat_input` — confirm.
5. **APP page-introspection:** confirm how to assert the page set / titles / default via the
   Streamlit 1.58 AppTest API; if not introspectable, choose an alternative assertion path for
   APP-01/APP-02.
6. **APP-04:** the missing-DB `st.stop()` runs before `st.navigation`, so the Co-Pilot page is
   unreachable when the DB is missing. Confirm whether chat should be reachable independent of the
   DB guard (the brief says "Chat needs no DB/Filters"). If yes, this is a design gap in app.py
   page ordering, not just a test gap.
7. **DATA-03 path form:** the plan shows `expected_doc` as `failure-modes/tombstoning.md` in one
   place and a bare doc id elsewhere; the offline stub builds `"{expected_doc}#0"`. Pin the exact
   string form so DATA-03 (file-exists) and EVAL-01 (chunk_id) agree with how `build_retriever`
   actually ids chunks. **Verify against the real chunk_id scheme** before approval.
8. **DATA-06:** decide whether `docs/eval/phase3-eval-questions.md` ↔ `EVAL_QUESTIONS` parity is
   asserted in code or left as Manual QA.
9. **EVAL-06:** ensure "gate flips on" is verified without firing a live call in CI (skip-reason
   inspection only), or move to Manual QA.
10. **Coverage ≥80% on new code:** `chat.py` live seams are `# pragma: no cover`; confirm the
    non-pragma body (render path, history append, refusal branch, citation expander) is fully
    exercised by CHAT-01..09 so the 80% target is met without the live paths.
