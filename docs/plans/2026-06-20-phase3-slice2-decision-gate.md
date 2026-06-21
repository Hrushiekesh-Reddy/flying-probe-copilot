## Decision Gate — 2026-06-20 — Phase 3 slice 2 (Gemini LLM + grounded answers)

### Decision Index — 8 decisions
1. (Anti-hallucination) Strict grounding: a non-refused answer requires retrieval hits **AND**
   `sufficient is True` **AND** non-empty answer **AND** ≥1 citation that was actually retrieved;
   any failure → refuse with a fixed `REFUSAL_TEXT` — Recommended: **strict (refuse by default)**.
2. (Citations) Represent citations as **chunk_ids in retrieval order** (deduped); the `Answer`
   also carries all retrieved ids — Recommended: **chunk_ids, retrieval order**.
3. (SDK) Lock to installed **google-generativeai 0.8.6**; defer the newer `google-genai` migration
   to a parking-lot item — Recommended: **lock 0.8.6**.
4. (Fallback) **No Claude fallback** this slice (CLAUDE.md parks that until after Phase 3);
   Gemini only — Recommended: **Gemini only**.
5. (Test edit) Edit the one slice-1 test `tests/test_rag/test_public_api.py` so its `__all__`
   exact-set assertion expects the 4 new names (required to keep the full suite green) —
   Recommended: **yes, edit it**.
6. (Security) **Rotate the Google API key** — it is correctly in gitignored `.env` (not committed)
   but surfaced in an automated subagent's analysis this session — Recommended: **rotate** (owner action).
7. (Scope) Defer the **live 10-question ≥8/10 eval and the chat UI to slice 3**; this slice proves
   the pipeline + citation enforcement + refusal with a scripted fake client — Recommended: **defer**.
8. (Git) Commit on `feature/phase3-slice2-llm`; **do NOT push / open PR** unless you ask —
   Recommended: **commit, no push**.

### Coverage Check
- Anti-hallucination / grounding: decisions #1, #2
- LLM integration: decisions #3, #4
- Tests: decision #5
- Security: decision #6
- Scope: decision #7
- Git: decision #8
- Approval-gated files: **none** (google-generativeai + python-dotenv already declared+locked;
  no db/schema, .claude/settings.json, .env.example, or CLAUDE.md-guardrail edits)

### Per-decision detail (consequential ones)
**#1 Strict grounding** — Problem: an LLM may answer plausibly without real support, or cite
sources it didn't use. Options: (a) strict — refuse unless every grounding condition holds
[Recommended]; (b) lenient — accept the model's answer if it claims sufficiency. Repercussions:
(a) some answerable questions get refused, but no ungrounded answer escapes (the portfolio point
of the project); (b) higher answer rate, hallucination risk. The exit criterion is "refuses
ungrounded questions" → strict.

**#6 Rotate key** — Problem: the real key was read by a subagent and appears in this session's
transcript/logs. It is NOT in git (`.env` is ignored), so repo exposure is nil, but session logs
are not a secret store. Options: (a) rotate now [Recommended]; (b) keep — accept the residual risk.
Repercussion of (a): a 30-second regenerate at aistudio.google.com/apikey; paste the new value into
`.env`. I never need the value myself.

**#5 Edit slice-1 test** — `test_api03` asserts `__all__` equals exactly the 7 slice-1 names;
adding 4 exports breaks it. The only correct fix is to update that assertion to the 11-name set.
This is a declared, necessary deviation from "additive only".

### Owner answer
**APPROVED 2026-06-20 — "Use your recommendations."** All 8 decisions ratified as recommended
(strict grounding confirmed). Proceed to Execute (Step 7).
