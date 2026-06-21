## Plan — 2026-06-20 — Phase 3 slice 2 (Gemini LLM + grounded answers)

### Goal Contract
OBJECTIVE:    Add a Gemini-backed answer layer over slice-1 retrieval that produces grounded,
              citation-forced answers and refuses ungrounded questions — unit-tested offline
              via a mockable LLM client.
SUCCESS-WHEN:
  - `from flying_probe_copilot.rag import answer, Answer, GeminiClient` imports.
  - `answer(question, *, retriever, client, top_k=5) -> Answer` works against a fake client.
  - Anti-hallucination: no retrieval hits → refuse WITHOUT calling the client; model citing a
    non-retrieved chunk_id → that citation is dropped; a "grounded" answer requires ≥1 valid
    citation else it is refused.
  - Malformed LLM JSON → refusal, never a crash.
  - `tests/test_rag/` green; new code coverage ≥ 80%; full suite still passes; unit suite makes
    ZERO network/API calls (live Gemini path `# pragma: no cover`, env-gated for manual QA).
OUT-OF-SCOPE: chat UI; the live 10-Q ≥8/10 eval; DuckDB-row grounding; Claude fallback;
              multi-turn chat; approval-gated file edits.
CONSTRAINTS:  Branch `feature/phase3-slice2-llm`; TDD RED→GREEN; no new deps
              (google-generativeai + python-dotenv already present); additive only.

### Resolved open questions (from Explore)
- **Citations = chunk_ids** (strings). They map back to source_path/heading via the retrieved
  chunks; `Answer` also carries the retrieved chunk_ids for display. Minimal + verifiable.
- **No Claude fallback** this slice (CLAUDE.md parks that decision until after Phase 3). Gemini only.
- **Single-turn** (no `start_chat`). Chat history is a slice-3 / UI concern.
- **Lock to google-generativeai 0.8.6.** Migrating to the newer `google-genai` is a parking-lot
  item (note in DECISION_LOG); not installed here.
- **Structured output:** real `GeminiClient` requests `response_mime_type="application/json"`; the
  orchestrator parses + validates JSON DEFENSIVELY regardless (never trusts the model blindly).

### Architecture
```
src/flying_probe_copilot/rag/
  llm.py       # LLMClient Protocol (generate(prompt)->str) + GeminiClient (lazy, 0.8.6)
  prompts.py   # ANSWER_SYSTEM + build_answer_prompt(question, chunks)->str (citation-forcing)
  answer.py    # Answer (frozen) + answer(question,*,retriever,client,top_k=5) + REFUSAL_TEXT
  __init__.py  # + answer, Answer, GeminiClient, LLMClient
```

- `LLMClient` Protocol: `generate(prompt: str) -> str` (returns the model's raw text / JSON string).
- `GeminiClient`: `__init__(model_name="gemini-2.0-flash", api_key=None)` stores config, loads
  nothing. `generate()` (`# pragma: no cover`) lazily `genai.configure(api_key or env GOOGLE_API_KEY)`,
  builds `GenerativeModel(model_name, generation_config=...json...)`, calls `generate_content`,
  returns `resp.text`. Missing key → `ValueError`.
- `build_answer_prompt(question, chunks)`: system instructions + each chunk rendered as
  `[<chunk_id>] (<heading>)\n<text>`; instructs the model to answer ONLY from the evidence, cite
  the chunk_ids it used, and set `sufficient=false` (refuse) when evidence is inadequate; output
  strict JSON `{"answer": str, "citations": [chunk_id...], "sufficient": bool}`.
- `Answer` (frozen): `question, answer_text, citations: tuple[str,...], refused: bool,
  retrieved_ids: tuple[str,...]`.
- `answer(question, *, retriever, client, top_k=5)`:
  1. blank question → refuse, no client call.
  2. `hits = retriever.retrieve(question, top_k=top_k)`.
  3. no hits → refuse, **no client call** (anti-hallucination), citations=().
  4. build prompt from hit chunks; `raw = client.generate(prompt)`.
  5. parse JSON defensively (`json.loads` in try/except) → malformed → refuse.
  6. `sufficient=false` → refuse (model self-refused).
  7. keep only citations ∈ retrieved ids (drop hallucinated); if none remain → refuse (ungrounded).
  8. else return grounded `Answer(refused=False, ...)`.

### What / Why / Where / When
| # | File | What | Why (deliverable) | When | Test |
|---|------|------|-------------------|------|------|
| 1 | rag/llm.py | LLMClient proto + GeminiClient (lazy) | P3 #4 LLM | first | test_llm.py |
| 2 | rag/prompts.py | build_answer_prompt + system text | P3 #5 citation prompt | after 1 | test_prompts.py |
| 3 | rag/answer.py | Answer + answer() orchestrator | P3 #4/#5/#7-refuse | after 1,2 | test_answer.py |
| 4 | rag/__init__.py | export answer, Answer, GeminiClient, LLMClient | P3 #1 | after 3 | test_public_api.py (extend) |
| 5 | tests/test_rag/conftest.py | FakeLLMClient (scripted/callable) + raising client | tests | with each | — |

### Ordered execution steps (TDD)
1. RED test_llm.py: GeminiClient constructs without configuring/calling genai (monkeypatch genai → assert not called at construct); LLMClient protocol shape. → implement llm.py → GREEN.
2. RED test_prompts.py: build_answer_prompt contains the question + every chunk_id + each chunk text + a JSON/citation instruction. → implement prompts.py → GREEN.
3. RED test_answer.py: (a) grounded happy path w/ valid citation; (b) no-hits → refuse + client NOT called; (c) sufficient=false → refuse; (d) hallucinated citation dropped, real kept; (e) all-citations-hallucinated → refuse; (f) malformed JSON → refuse; (g) blank question → refuse + no client call; (h) representative-question set via scripted fake client. → implement answer.py → GREEN.
4. RED test_public_api.py additions: answer/Answer/GeminiClient/LLMClient import + in __all__. → update __init__.py → GREEN.
5. Full `python -m uv run pytest -q`; confirm prior suite still green + new green; new-code coverage ≥80%.

### Resolved ambiguities (from Test-Case Plan GAP-1..18)
- **G1/G8 (missing-key + pragma scope):** `GeminiClient.generate` resolves the key via
  `_resolve_key()` (not pragma): returns `self._api_key` or, failing that, `load_dotenv()` then
  `os.environ["GOOGLE_API_KEY"]`. If empty → `raise ValueError("GOOGLE_API_KEY not set; add it to
  .env or pass api_key=")`. Only the live call helper `_call_model(...)` (and the line that calls
  it) carry `# pragma: no cover`. LLM-05 monkeypatches `llm.load_dotenv` to a no-op + deletes the
  env var → covers the guard offline.
- **G2/G16 (refusal text):** a single `REFUSAL_TEXT` constant is the `answer_text` on EVERY
  refusal; the model's draft answer is never surfaced on refusal.
  `REFUSAL_TEXT = "I don't have enough grounded evidence in the knowledge base to answer that."`
- **G3 (prompt contract keywords):** `build_answer_prompt` output must contain the literal tokens
  `JSON`, `citations`, and `sufficient` (PRM-04 asserts these).
- **G4/G13 (citation order + dedupe):** valid citations are returned in **retrieval order**,
  de-duplicated: `tuple(cid for cid in retrieved_ids if cid in valid_set)`.
- **G5 (0-chunk prompt):** `build_answer_prompt(q, [])` returns a string (no raise); `answer()`
  never calls it with 0 chunks (refuses first).
- **G6 (blank query):** `not question.strip()` → refuse before retrieval, no client call.
- **G7 (retriever call):** `retriever.retrieve(question, top_k=top_k)` — `top_k` keyword-only,
  `rrf_k` not passed; `StubRetriever` mirrors keyword-only `top_k`.
- **G9 (citations on refusal):** every refusal sets `citations=()`.
- **G10/G15 (answer field):** missing `answer`, or non-str / empty-after-strip `answer` → refuse.
- **G11/G14/G21 (sufficient):** grounded ONLY when `data.get("sufficient") is True` (strict
  boolean True). Missing / `"yes"` / `0` / `false` → refuse. Safest anti-hallucination default.
- **G12 (citations not a list):** if `citations` is not a `list`, treat as `[]`; non-str items
  ignored → typically refuse (no valid citation).
- **G17 (Protocol):** `LLMClient` is `@runtime_checkable`.
- **G18 (top_k bounds):** `top_k` forwarded to the retriever as-is — `0 → [] → refuse`;
  `< 0 → ValueError` from the retriever (propagated; documented, not re-guarded).

**Grounding rule (the core of answer()):** a non-refused `Answer` requires ALL of:
retrieval hits exist, valid JSON dict, `sufficient is True`, non-empty `answer_text`, and ≥1
citation that is in `retrieved_ids`. Any failure → refuse with `REFUSAL_TEXT` + `citations=()`.

### Plan Revision 1 (resolving Step 5 adversarial red-team)
**B-A (load_dotenv leaks the real key into the test suite — BLOCKER):** the repo `.env` now holds a
REAL key; `load_dotenv()` (override=False, cwd-upward search) would inject it during a repo-root
pytest run. Fixes:
  1. `tests/test_rag/conftest.py` gains an **autouse** fixture that `monkeypatch.delenv`s
     `GOOGLE_API_KEY` + `ANTHROPIC_API_KEY` for every test — suite-wide, not just LLM-05.
  2. LLM-05 additionally monkeypatches `llm.load_dotenv` to a no-op so `_resolve_key` cannot reload
     `.env`. Net: key absent → `ValueError`, deterministic, offline.
  3. No unit test ever calls `GeminiClient.generate` (all use the fake client) except LLM-05's
     missing-key guard, so `load_dotenv` real-load is unreachable in the suite.

**B-B (genai import side effects — was WARNING, fold in):** import `google.generativeai` **lazily
inside `_call_model`** (the pragma'd live path), NOT at module top. Keeps the deprecation
`FutureWarning` and the heavy import out of every `import flying_probe_copilot.rag`, and
strengthens LLM-01 (no genai activity at construct).

**B-C (API-03 exact-set break — BLOCKER):** the existing
`tests/test_rag/test_public_api.py::test_api03_all_lists_exactly_the_public_names` asserts
`set(__all__) == {7 slice-1 names}`. Adding the 4 new exports breaks it. **This slice explicitly
edits that one slice-1 test** to expect the 11-name set (7 + answer, Answer, GeminiClient,
LLMClient). Declared deviation from "additive only" — it is required for the full suite to stay green.

**B-D (citation-order tests — WARNING):** ANS-02 / ANS-10 assert citations in a specific order;
they MUST use a `StubRetriever` with an explicitly scripted hit order (a real retriever orders by
score, so `a.md#0` before `b.md#0` is not guaranteed). Test-plan note honored.

**B-E (non-str / blank question — MINOR→fold in):** `answer()` guards
`if not isinstance(question, str) or not question.strip(): refuse` (covers `None` and whitespace;
no crash).

**B-F (coverage gate is advisory):** no `fail_under` in pyproject; the ≥80% new-code figure is read
from `term-missing` by the parent. With `generate`/`_call_model` pragma'd, the coverable `llm.py`
surface is the constructor + `_resolve_key` + missing-key guard — confirm ≥80% on `answer.py` +
`prompts.py` + the non-pragma `llm.py` lines at Step 8/9.

**Security (B1 from red-team):** the real key sits in gitignored `.env` (NOT committed) but surfaced
in a subagent's analysis — recommend the owner rotate it. No code change; flagged in handoff.

### Guardrails
- Branch: `feature/phase3-slice2-llm` (off dev, post-#25-merge).
- Approval-gated files touched: NONE (google-generativeai + python-dotenv already declared+locked).
- New dependencies: NONE.
- Offline: the only live-API code path (`GeminiClient.generate`) is `# pragma: no cover`; every
  test injects a fake client. `GOOGLE_API_KEY` is read lazily from env/.env, never in tests.
- Phase discipline: slice 2 only; chat UI + live 10-Q eval deferred to slice 3.
- Additive: no edits to slice-1 source/tests except extending `tests/test_rag/conftest.py` and
  `rag/__init__.py` (public re-export).
