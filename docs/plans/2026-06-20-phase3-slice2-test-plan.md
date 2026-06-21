## Test-Case Plan — 2026-06-20 — Phase 3 slice 2 (Gemini LLM + grounded answers)

Role: Test Planner (test-generator). This document enumerates **behavior-level** test
cases (input/precondition → expected output/effect) for the Gemini answer layer. It is a
plan only: no production code, no test stubs/asserts, no edits to source or to the
implementation plan. Implementation-internal mechanics (RRF math, ChromaDB, BM25, how the
prompt string is concatenated) are deliberately NOT asserted — only externally observable
behavior is.

Modules under test:
- `src/flying_probe_copilot/rag/llm.py` — `LLMClient` Protocol + `GeminiClient` (lazy).
- `src/flying_probe_copilot/rag/prompts.py` — `build_answer_prompt(question, chunks) -> str`.
- `src/flying_probe_copilot/rag/answer.py` — frozen `Answer` + `answer(question, *, retriever, client, top_k=5)`.
- `src/flying_probe_copilot/rag/__init__.py` — public re-exports.

All cases are **fully offline**: every `answer()` path injects a fake client; `GeminiClient`
is exercised only at the construction boundary (no live `genai` call). This mirrors the
slice-1 style (`tests/test_rag/conftest.py` `FakeEmbedder`, `write_kb` factory, per-case
docstring IDs).

---

### Test fixtures / harness this plan assumes

- **`write_kb`** (existing, `conftest.py`) — write a tmp KB tree from `{relpath: markdown}`.
- **`fake_embedder`** (existing, `conftest.py`) — model-free deterministic embedder so the
  real `HybridRetriever` can be built offline (`build_retriever(kb, embedder=fake_embedder)`).
  Used where a case wants a *real* retriever over known chunks.
- **`FakeLLMClient`** (NEW, see design note) — scripted/callable client returning canned
  JSON, deterministic, with a recording of whether `generate()` was invoked.
- **`RaisingLLMClient`** (NEW) — a client whose `generate()` raises immediately; injected on
  every refusal-before-LLM path to *prove the client is never called*.
- **`StubRetriever`** (NEW, optional) — a minimal object exposing `retrieve(query, *, top_k)`
  returning a scripted `list[RetrievedChunk]` (or `[]`), and recording the `top_k` it was
  called with. Lets `answer()` cases assert behavior without standing up a full KB. Cases may
  use either `StubRetriever` or a real `build_retriever` KB; both are noted per case.

Note on the retriever contract: `HybridRetriever.retrieve` takes `top_k` **keyword-only**
(`retrieve(query, *, top_k=5, rrf_k=60)`); the plan states `answer()` calls
`retriever.retrieve(question, top_k=top_k)`. `StubRetriever` must mirror the keyword-only
shape so TK-passthrough cases are faithful (see GAP-7).

---

### `GeminiClient` — lazy construction + missing key (`tests/test_rag/test_llm.py`)

| Case ID | Unit | Input / precondition | Expected result | Deliverable |
|---------|------|----------------------|-----------------|-------------|
| LLM-01 | `GeminiClient.__init__` | Construct with defaults; `genai` module monkeypatched so any of `configure` / `GenerativeModel` / `generate_content` records a call | Construction succeeds; **none** of the patched `genai` functions were called (lazy — no network, no model build at construct time) | test_llm.py |
| LLM-02 | `GeminiClient.__init__` | Construct with explicit `model_name="gemini-2.0-flash"` and `api_key="x"` | Object constructed; still no `genai` activity; supplied config is retained for later use (observed indirectly via LLM-05 / manual QA, not by reading private attrs) | test_llm.py |
| LLM-03 | `GeminiClient` typing | Construct an instance | Instance is usable where an `LLMClient` is expected (it exposes a `generate(prompt: str) -> str` callable) — i.e. it structurally satisfies the Protocol | test_llm.py |
| LLM-04 | `LLMClient` Protocol | A trivial object exposing `generate(prompt:str)->str` (e.g. `FakeLLMClient`) | Is accepted as an `LLMClient` (runtime `isinstance` if Protocol is `@runtime_checkable`, else structural use in `answer()`) — confirms the seam is duck-typed, not class-bound | test_llm.py |
| LLM-05 | `GeminiClient.generate` (missing key) | `GOOGLE_API_KEY` absent from env AND no `api_key` passed; call `generate(...)` | Raises `ValueError` (never silently calls the API); see GAP-1 re exact message | test_llm.py |
| LLM-06 | `GeminiClient.generate` (live path) | Real key present, real network | **Untestable by automation** — live path is `# pragma: no cover`; see Manual QA. Listed only to document the coverage carve-out | (manual) |

Coverage carve-out notes:
- The body of `GeminiClient.generate()` that calls `genai.configure` / `GenerativeModel` /
  `generate_content` / returns `resp.text` is `# pragma: no cover` (live network). The unit
  suite must NOT exercise it. **Exception:** the *missing-key guard* (LLM-05) raises
  `ValueError` *before* any network call, so that branch is offline-testable and must NOT be
  under the no-cover pragma. The plan must confirm the pragma scopes the network statements
  only, not the key check (GAP-1 / GAP-8).

---

### `build_answer_prompt` — content guarantees + edges (`tests/test_rag/test_prompts.py`)

Input is `(question: str, chunks)` where `chunks` are the retrieved chunks (the plan renders
each as `[<chunk_id>] (<heading>)\n<text>`). Assertions are on **substring presence**, never
on exact formatting/whitespace (that is implementation detail).

| Case ID | Unit | Input / precondition | Expected result | Deliverable |
|---------|------|----------------------|-----------------|-------------|
| PRM-01 | `build_answer_prompt` | A question + 2 chunks with distinct ids/headings/text | Returned string contains the verbatim question | test_prompts.py |
| PRM-02 | `build_answer_prompt` | Same as PRM-01 | Returned string contains **every** chunk's `chunk_id` | test_prompts.py |
| PRM-03 | `build_answer_prompt` | Same as PRM-01 | Returned string contains **each** chunk's `text` body | test_prompts.py |
| PRM-04 | `build_answer_prompt` | Same as PRM-01 | Returned string contains a JSON-output instruction AND a citation instruction (i.e. tells model to emit JSON with `answer`/`citations`/`sufficient` and to cite chunk_ids) — assert on the contract keywords, not exact wording (GAP-3) | test_prompts.py |
| PRM-05 | `build_answer_prompt` | Same as PRM-01 | Returned string contains each chunk's `heading` (the renderer includes heading context) | test_prompts.py |
| PRM-06 | `build_answer_prompt` (edge: no chunks) | Question + empty chunk list | Returns a string without raising; still contains the question and the JSON/citation instruction (defines behavior even though `answer()` won't normally call it with zero chunks — see GAP-5) | test_prompts.py |
| PRM-07 | `build_answer_prompt` (edge: unicode) | A chunk whose text/heading contains non-ASCII (e.g. `漂移`) and a unicode question | Unicode question, chunk_id, heading, and text all appear in the prompt intact (no mojibake / no encoding error) | test_prompts.py |
| PRM-08 | `build_answer_prompt` (edge: many chunks) | 5+ chunks (e.g. top_k worth) | All N chunk_ids and all N text bodies are present (none dropped/truncated) | test_prompts.py |
| PRM-09 | `build_answer_prompt` (edge: empty heading) | A chunk with `heading == ""` (valid per `Chunk` docs — preamble/heading-less) | Returns without error; chunk_id and text still present (no crash on blank heading) | test_prompts.py |
| PRM-10 | `build_answer_prompt` (edge: duplicate-ish content) | Two chunks with identical text but different chunk_ids | Both chunk_ids appear (chunks distinguished by id, not deduped) | test_prompts.py |

---

### `answer()` — happy path + anti-hallucination + robustness (`tests/test_rag/test_answer.py`)

`answer(question, *, retriever, client, top_k=5) -> Answer`. Unless stated, the retriever is
either a `StubRetriever` returning scripted hits or a real `build_retriever` KB; the client is
a `FakeLLMClient` scripted to return a specific JSON string (or `RaisingLLMClient` for
no-call paths). Observable surface = the returned `Answer` fields + whether the client was
called.

#### Grounded happy path

| Case ID | Unit | Input / precondition | Expected result | Deliverable |
|---------|------|----------------------|-----------------|-------------|
| ANS-01 | `answer()` happy | Retriever returns chunks incl. id `"a.md#0"`; client returns `{"answer":"...","citations":["a.md#0"],"sufficient":true}` | `Answer.refused is False`; `answer_text` == model's answer; `citations == ("a.md#0",)`; `retrieved_ids` contains all retrieved ids; `question` echoes input | test_answer.py |
| ANS-02 | `answer()` happy multi-cite | Retriever returns ids `a.md#0`, `b.md#0`; client cites both, `sufficient:true` | `refused False`; `citations` == both ids (order = GAP-4); `retrieved_ids` has both | test_answer.py |
| ANS-03 | `answer()` happy — retrieved_ids fidelity | Retriever returns 3 chunks; model cites only 1 valid id | `refused False`; `citations` == the 1 cited id; `retrieved_ids` == all 3 retrieved ids (retrieved set is reported in full regardless of citations) | test_answer.py |

#### Anti-hallucination / refusal paths

| Case ID | Unit | Input / precondition | Expected result | Deliverable |
|---------|------|----------------------|-----------------|-------------|
| ANS-04 | `answer()` blank question | `question == ""`; client = `RaisingLLMClient` | `refused True`; client `generate()` **never called**; `retrieved_ids == ()`; `citations == ()`; `answer_text` = refusal contract (GAP-2) | test_answer.py |
| ANS-05 | `answer()` whitespace question | `question == "   "`; client = `RaisingLLMClient` | Same as ANS-04 — treated as blank, refuse with no client call (GAP-6: is whitespace blank?) | test_answer.py |
| ANS-06 | `answer()` no retrieval hits | Retriever returns `[]`; client = `RaisingLLMClient` | `refused True`; client **never called** (anti-hallucination); `citations == ()`; `retrieved_ids == ()` | test_answer.py |
| ANS-07 | `answer()` model self-refuses | Retriever returns hits; client returns `{"answer":"...","citations":["a.md#0"],"sufficient":false}` | `refused True` (model said insufficient); client WAS called once; `citations == ()` (GAP-9: are citations cleared on refusal?) | test_answer.py |
| ANS-08 | `answer()` hallucinated citation dropped | Retriever returns `a.md#0`; model cites `["a.md#0","ghost.md#9"]`, `sufficient:true` | `refused False`; `citations == ("a.md#0",)` (non-retrieved `ghost.md#9` dropped); answer kept | test_answer.py |
| ANS-09 | `answer()` all citations hallucinated | Retriever returns `a.md#0`; model cites `["ghost.md#9"]` only, `sufficient:true` | `refused True` (no valid citation remains → ungrounded); client WAS called; `citations == ()` | test_answer.py |
| ANS-10 | `answer()` partial valid | Retriever returns `a.md#0`,`b.md#0`; model cites `["a.md#0","ghost.md#9","b.md#0"]` | `refused False`; `citations` == `a.md#0`,`b.md#0` only (ghost dropped, ≥1 valid remains) | test_answer.py |
| ANS-11 | `answer()` empty citations array, sufficient true | Retriever returns hits; model returns `{"answer":"...","citations":[],"sufficient":true}` | `refused True` (no valid citation → ungrounded), even though model claimed sufficient | test_answer.py |

#### Malformed / defensive JSON parsing

| Case ID | Unit | Input / precondition | Expected result | Deliverable |
|---------|------|----------------------|-----------------|-------------|
| ANS-12 | `answer()` non-JSON output | Retriever returns hits; client returns `"I cannot comply"` (not JSON) | `refused True`, no exception raised/propagated; `citations == ()` | test_answer.py |
| ANS-13 | `answer()` empty-string output | Client returns `""` | `refused True`, no crash | test_answer.py |
| ANS-14 | `answer()` JSON but not an object | Client returns `"[1,2,3]"` (valid JSON, wrong shape) | `refused True`, no crash (defensive: top level not a dict) | test_answer.py |
| ANS-15 | `answer()` JSON missing `answer` key | Client returns `{"citations":["a.md#0"],"sufficient":true}` | `refused True` (GAP-10: missing answer → refuse) OR documented default; no crash | test_answer.py |
| ANS-16 | `answer()` JSON missing `citations` key | Client returns `{"answer":"x","sufficient":true}` | `refused True` (no citations → ungrounded), no crash | test_answer.py |
| ANS-17 | `answer()` JSON missing `sufficient` key | Client returns `{"answer":"x","citations":["a.md#0"]}` | Behavior per GAP-11 (default for missing `sufficient`): plan must fix whether absent → treated true (grounded if valid cite) or false (refuse). Test asserts the resolved contract; no crash either way | test_answer.py |
| ANS-18 | `answer()` `citations` not a list | Client returns `{"answer":"x","citations":"a.md#0","sufficient":true}` | `refused True` (or coerced) per GAP-12; no crash. Defensive: non-list citations must not throw | test_answer.py |
| ANS-19 | `answer()` `citations` list with non-string items | Client returns `{"answer":"x","citations":[123,null,"a.md#0"],"sufficient":true}` | Non-string entries ignored; `a.md#0` kept → `refused False`, `citations == ("a.md#0",)`; no crash | test_answer.py |
| ANS-20 | `answer()` duplicate citations | Retriever returns `a.md#0`; model cites `["a.md#0","a.md#0"]`, sufficient true | `refused False`; `citations` de-duplicated to `("a.md#0",)` (GAP-13: dedupe expected) | test_answer.py |
| ANS-21 | `answer()` `sufficient` non-bool truthy/falsey | Client returns `{"answer":"x","citations":["a.md#0"],"sufficient":"yes"}` (or `0`) | Defensive coercion per GAP-11/GAP-14; no crash; test pins resolved contract | test_answer.py |
| ANS-22 | `answer()` whitespace/None answer_text, valid cite, sufficient true | Client returns `{"answer":"","citations":["a.md#0"],"sufficient":true}` | Behavior per GAP-15 (empty answer string with valid cite → refuse, or accept empty answer?); test pins resolved contract; no crash | test_answer.py |

#### Wiring / passthrough / type

| Case ID | Unit | Input / precondition | Expected result | Deliverable |
|---------|------|----------------------|-----------------|-------------|
| ANS-23 | `answer()` top_k passthrough | `StubRetriever` recording its `top_k`; call `answer(q, retriever=..., client=..., top_k=3)` | Retriever was called with `top_k == 3` (and as keyword); proves the parameter is forwarded, not hard-coded | test_answer.py |
| ANS-24 | `answer()` default top_k | Call without `top_k` | Retriever called with `top_k == 5` (documented default) | test_answer.py |
| ANS-25 | `answer()` single retrieve call | Any grounded path | `retriever.retrieve` invoked exactly once per `answer()` call (no double retrieval) | test_answer.py |
| ANS-26 | `answer()` client call count, happy | Grounded path | `client.generate` invoked exactly once with the built prompt (prompt non-empty; contains the question — overlaps PRM but asserted at the seam) | test_answer.py |
| ANS-27 | `answer()` real-retriever integration | Real `build_retriever(kb, embedder=fake_embedder)` over a known KB; `FakeLLMClient` citing a real retrieved id | End-to-end offline: `refused False`, citation is a real KB chunk_id, `retrieved_ids` matches what the real retriever returned. Proves the answer layer composes with the actual slice-1 retriever, not just a stub | test_answer.py |

#### `Answer` dataclass

| Case ID | Unit | Input / precondition | Expected result | Deliverable |
|---------|------|----------------------|-----------------|-------------|
| ANS-28 | `Answer` frozen | Construct an `Answer`; attempt to set any field | Raises `FrozenInstanceError` (immutable, mirrors `Chunk`/`RetrievedChunk`) | test_answer.py |
| ANS-29 | `Answer` field set | Construct via a real `answer()` happy call | Instance exposes exactly `question, answer_text, citations, refused, retrieved_ids`; `citations` and `retrieved_ids` are tuples (not lists) | test_answer.py |
| ANS-30 | `Answer` equality/hashability | Two `Answer`s with identical fields | Compare equal and are hashable (frozen dataclass) — confirms tuple (not list) fields | test_answer.py |

---

### Representative-question set (scripted fake client) (`tests/test_rag/test_answer.py`)

A table-driven family proving the full pipeline over realistic failure-mode questions, each
deterministic via a scripted `FakeLLMClient`. Drives the same `answer()` surface; one
parametrized case per row keeps IDs stable.

| Case ID | Unit | Input / precondition | Expected result | Deliverable |
|---------|------|----------------------|-----------------|-------------|
| ANS-31 | `answer()` repr-set: grounded solder-bridge Q | KB w/ a solder-bridge chunk; client scripted to cite it, sufficient true | `refused False`; citation == the solder-bridge chunk id; answer_text == scripted answer | test_answer.py |
| ANS-32 | `answer()` repr-set: tombstone Q | KB w/ tombstone chunk; scripted grounded answer citing it | `refused False`; valid citation | test_answer.py |
| ANS-33 | `answer()` repr-set: off-domain Q (no evidence) | KB lacks any matching chunk so retriever returns `[]`; `RaisingLLMClient` | `refused True`; client never called | test_answer.py |
| ANS-34 | `answer()` repr-set: model-insufficient Q | Retriever returns weakly-relevant chunks; scripted client returns `sufficient:false` | `refused True`; client called once | test_answer.py |
| ANS-35 | `answer()` repr-set: model hallucinates citation | Retriever returns chunk X; scripted client cites only a non-retrieved id | `refused True` (all-hallucinated → ungrounded) | test_answer.py |

(Implementation may collapse ANS-31..ANS-35 into one `pytest.mark.parametrize`; IDs kept
separate here for traceability.)

---

### Public API (`tests/test_rag/test_public_api.py` — extend)

| Case ID | Unit | Input / precondition | Expected result | Deliverable |
|---------|------|----------------------|-----------------|-------------|
| API-01 | `rag.__init__` exports | `from flying_probe_copilot.rag import answer, Answer, GeminiClient, LLMClient` | All four import without error | test_public_api.py |
| API-02 | `rag.__all__` | Inspect `rag.__all__` | Contains `answer`, `Answer`, `GeminiClient`, `LLMClient` (in addition to existing slice-1 names, which remain) | test_public_api.py |
| API-03 | slice-1 names intact | Import existing names (`build_retriever`, `HybridRetriever`, `Chunk`, `RetrievedChunk`, `load_kb`, `VectorIndex`, `LexicalIndex`) | Still importable — additive change did not remove the slice-1 surface | test_public_api.py |

---

### FakeLLMClient design note (the determinism + no-call seam)

The whole anti-hallucination contract hinges on two assertions the fake must support:
(1) the client returns **canned JSON deterministically**, and (2) on refusal-before-LLM
paths the client is **provably never invoked**. Recommended shapes (offline, no genai):

1. **Scripted/canned `FakeLLMClient`** — constructed with a fixed return string (or a
   callable `prompt -> str`):
   - `FakeLLMClient(response='{"answer":"...","citations":["a.md#0"],"sufficient":true}')`
     returns that exact string from `generate(prompt)` regardless of prompt → deterministic.
   - Optionally `FakeLLMClient(responder=lambda prompt: ...)` to vary by prompt for the
     representative-question set (e.g. inspect which chunk_ids the prompt contains and answer
     accordingly), still 100% deterministic and offline.
   - Records every call: a `calls` list (or `call_count` + last `prompt`) so cases can assert
     `generate` was called exactly once (ANS-25/26) and inspect the prompt it received.
   - Satisfies the `LLMClient` Protocol structurally (`generate(prompt:str)->str`), so it is a
     drop-in for `answer(..., client=fake)`.

2. **`RaisingLLMClient`** — `generate()` raises immediately (e.g. `AssertionError` /
   `RuntimeError("LLM must not be called")`). Injected on **every** no-call refusal path
   (ANS-04, ANS-05, ANS-06, ANS-33). If `answer()` ever calls it, the test fails loudly —
   this is the positive proof of "refuse WITHOUT calling the client", which a call-count of 0
   alone could mask if wiring were wrong.

3. **`StubRetriever`** (companion) — exposes `retrieve(query, *, top_k)` returning a
   scripted `list[RetrievedChunk]` (build real `Chunk`/`RetrievedChunk` DTOs so the answer
   layer sees the true types) and records the `top_k` it was called with (for ANS-23/24) and
   its call count (ANS-25). Keyword-only `top_k` to mirror `HybridRetriever`.

These belong in `tests/test_rag/conftest.py` (the only slice-1 test file the plan permits
extending), exposed as fixtures alongside `fake_embedder` / `write_kb`, matching the existing
offline-injection style.

---

### Untestable by automation → Manual QA

These require the real model / real network / human judgment and MUST NOT be in the unit suite:

- **Live `GeminiClient.generate()`** end-to-end (real `genai.configure`, `GenerativeModel`,
  `generate_content`, `resp.text`). It is `# pragma: no cover`, env-gated by `GOOGLE_API_KEY`.
  → Manual QA with a real key in a gitignored `.env`.
- **Live answer quality** — whether a real Gemini response is actually correct/grounded for a
  real question. The fake client only proves *pipeline + citation enforcement*, never quality.
- **The ≥8/10 accuracy evaluation** over the 10-Q set (explicitly slice-3 / out of scope here;
  needs the real model). → Manual QA, slice 3.
- **`response_mime_type="application/json"` structured-output behavior** of the real API
  (that Gemini actually honors the JSON mime request) — only observable against the live API.
- **Real-key vs no-key environment wiring** beyond the offline `ValueError` guard (LLM-05),
  e.g. `.env` loading via python-dotenv in a real shell.

---

### Coverage gaps / ambiguities to resolve BEFORE approval

These are contract holes the *plan/spec* must pin down so the test expectations are
unambiguous. Each blocks one or more cases above.

- **GAP-1 (missing-key path & pragma scope):** Plan says missing key → `ValueError`, but
  `generate()` is `# pragma: no cover`. Confirm the key check raises *before* the network
  statements and is NOT swallowed by the pragma, so LLM-05 is offline-testable. Pin the exact
  exception type (`ValueError`) and whether the message is asserted.
- **GAP-2 (refusal text contract):** Is there a single canonical `REFUSAL_TEXT` constant
  used for `answer_text` on every refusal? Tests need the exact string (or a documented
  "starts with"/"contains" contract) to assert ANS-04/06/07/etc. Otherwise refusal-text
  assertions are unspecified.
- **GAP-3 (prompt instruction wording):** PRM-04 asserts a JSON+citation instruction exists.
  Define the *contract keywords* that must appear (e.g. the literal field names
  `answer`/`citations`/`sufficient`, or the word "JSON") so the test is robust to wording
  changes but still meaningful.
- **GAP-4 (citation ordering):** When the model cites multiple valid ids, is `citations`
  order = model order, retrieval order, or sorted? ANS-02/ANS-10 need a defined order.
- **GAP-5 (build_answer_prompt with 0 chunks):** `answer()` never calls it with zero chunks
  (no-hits refuses first), but PRM-06 defines direct behavior. Confirm it returns a string
  (not raise). If unsupported, drop PRM-06.
- **GAP-6 (blank detection):** Is a whitespace-only question (ANS-05) treated as blank? Plan
  says "blank question"; confirm strip()-based detection so whitespace refuses with no client
  call.
- **GAP-7 (retriever call signature):** Plan shows `retriever.retrieve(question, top_k=top_k)`;
  the real `retrieve` is `top_k` keyword-only. Confirm `answer()` passes `top_k` as a keyword
  (so ANS-23/24 assert keyword passthrough) and does NOT pass `rrf_k`.
- **GAP-8 (no-cover boundary):** Define exactly which lines of `GeminiClient.generate` carry
  the pragma so coverage ≥80% is achievable without faking the network and without
  accidentally excluding the testable guard.
- **GAP-9 (citations on refusal):** When refused (sufficient=false, all-hallucinated,
  malformed), are `Answer.citations` forced to `()`? ANS-07/09/11 assume yes — confirm.
- **GAP-10 (missing `answer` key):** ANS-15 — does a JSON object lacking `answer` refuse, or
  default to empty answer? Pin it.
- **GAP-11 (missing/`non-bool sufficient` default):** ANS-17/ANS-21 — if `sufficient` is
  absent or not a real bool, default to refuse (safe) or to true? Plan must state the default;
  recommend "absent/invalid → refuse" for an anti-hallucination posture.
- **GAP-12 (`citations` not a list):** ANS-18 — coerce, ignore, or refuse when `citations`
  is a string/object/number? Pin the defensive behavior.
- **GAP-13 (duplicate citations):** ANS-20 — are duplicate valid citations de-duplicated, and
  is original order preserved? Confirm dedupe + order rule.
- **GAP-14 (truthy non-bool sufficient):** ANS-21 — is `"true"`/`1` accepted as sufficient or
  rejected as not-a-bool? Tie to GAP-11.
- **GAP-15 (empty/blank answer_text on otherwise-grounded result):** ANS-22 — if the model
  returns a valid citation + sufficient true but an empty `answer` string, is that grounded
  (accept empty) or refused (no content)? Pin it.
- **GAP-16 (`answer_text` on refusal retained?):** Is the model's draft answer ever surfaced
  on a refusal, or always replaced by `REFUSAL_TEXT`? The plan implies always-replaced;
  confirm so ANS-07 etc. assert the refusal text, not the model's discarded answer.
- **GAP-17 (`LLMClient` runtime-checkable?):** LLM-04 prefers an `isinstance` Protocol check.
  Confirm whether `LLMClient` is `@runtime_checkable`; if not, the case reduces to structural
  use in `answer()` rather than an `isinstance` assertion.
- **GAP-18 (top_k <= 0 into answer):** Behavior if a caller passes `top_k=0` or negative to
  `answer()` — does it forward to the retriever (which returns `[]` for 0, raises for <0) and
  thus refuse / propagate `ValueError`? Not enumerated above; decide whether to add a case or
  declare it out of contract.
```