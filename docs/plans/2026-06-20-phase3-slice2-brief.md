## Session Brief — 2026-06-20 — Phase 3 slice 2 (Gemini LLM + grounded answers)

### What the owner wants
> "i have the API key ready" → proceed to Phase 3 slice 2.

Build the LLM answer layer on top of slice 1's retrieval core: a Gemini-backed co-pilot
that answers natural-language root-cause questions **grounded in retrieved evidence**, forced
to cite the chunks it used, and that **refuses** when there is no supporting evidence.

### Goal statement (one sentence)
Ship `answer(question, *, retriever, client) -> Answer` that retrieves KB evidence (slice 1),
prompts Gemini with a citation-forcing structured-output template, validates the model's
citations against the retrieved chunk ids, and returns a grounded answer — or an explicit
refusal when retrieval yields no evidence — with the whole pipeline unit-tested offline via a
mockable LLM client (no live API call in the unit suite).

### Success looks like
- `src/flying_probe_copilot/rag/` gains: a mockable `LLMClient` protocol + `GeminiClient`
  (google-generativeai, lazy-configured from `GOOGLE_API_KEY`), a citation-forcing prompt
  builder, and an `answer()` orchestrator returning a frozen `Answer` (answer_text, citations,
  refused, used chunk ids).
- **Anti-hallucination:** when retrieval returns nothing, `answer()` refuses WITHOUT calling
  the LLM; when the model cites a chunk id that was not retrieved, that citation is rejected.
- Tests (mock client): grounded answer carries valid citations; refusal-on-no-evidence;
  refusal-on-model-insufficient; hallucinated-citation filtered; malformed-LLM-JSON handled;
  prompt contains the question + every retrieved chunk id; a set of representative-question
  cases driven by a scripted fake client.
- `pytest -q` green; new code coverage ≥ 80%; existing suite still passes; unit suite makes
  zero network/API calls (live Gemini path is `# pragma: no cover`, env-gated for manual QA).

### Out of scope (explicit — deferred to slice 3)
- ❌ Chat interface in the Streamlit dashboard (`ui/`).
- ❌ The live 10-question ≥8/10 accuracy evaluation (needs the real model — slice-3 manual QA).
  This slice proves the pipeline + citation enforcement with a scripted fake client.
- ❌ Retrieval/grounding over DuckDB *rows* (KB-corpus grounding only, as in slice 1).
- ❌ Any edit to approval-gated files (`pyproject.toml` — google-generativeai already declared;
  `db/schema.py`; `.claude/settings.json`; `CLAUDE.md` beyond the Step-10 session-log line).

### Phase / milestone
ROADMAP Phase 3 — delivers #4 (LLM integration via Gemini), #5 (citation-forcing prompt), and
the anti-hallucination half of #7 (refuse ungrounded questions). #6 (chat UI) + the live 10-Q
eval → slice 3.

### Branch
`feature/phase3-slice2-llm` — created off `dev` (after PR #25 merged; clean working tree).

### Dependencies
- `google-generativeai>=0.8` already declared + locked. `GOOGLE_API_KEY` lives in gitignored
  `.env` (created from `.env.example`; owner fills the value). NOT needed for the unit suite.
