## Decision Gate — 2026-06-20 — Phase 3 slice 3 (chat UI + 10-Q eval)

### Decision Index — 7 decisions
1. (UI) Add the Co-Pilot chat as a **6th page** in the existing `st.navigation` dashboard (inside the
   current DB-gated shell) — Recommended: **6th page**.
2. (UX) On any backend error (no key / network / bad response), the chat page renders a friendly
   `st.error` and appends no turn (vs propagating a crash) — Recommended: **graceful st.error**.
3. (Eval) Deliver the 10-question eval as: an **offline citation-pattern test** (scripted stub, proves
   each question→expected-doc citation deterministically) **plus an env-gated live ≥8/10 test**
   (`RAG_RUN_LLM_EVAL=1`, default-skipped). The actual ≥8/10 measurement is your manual/env-gated run
   with a key — Recommended: **offline test + env-gated live harness**.
4. (Edit) Declared edit to `ui/app.py` to register the page (+ update its "5 pages" docs to 6) —
   Recommended: **yes**.
5. (Scope) This **closes Phase 3**. After merge, you run the live ≥8/10 eval and promote `dev → main`
   at the Phase 3 boundary — Recommended: **treat as Phase 3 close**.
6. (Tests) Add an autouse env-strip to `tests/test_ui/conftest.py` so chat tests are guaranteed offline
   (the slice-2 strip only covered `tests/test_rag/`) — Recommended: **yes**.
7. (Git) Commit on `feature/phase3-slice3-chat-ui`; **do NOT push / open PR** unless you ask —
   Recommended: **commit, no push**.

### Coverage Check
- UI: decisions #1, #2, #4
- Evaluation: decision #3
- Scope/phase: decision #5
- Tests: decision #6
- Git: decision #7
- Approval-gated files: **none** (streamlit/plotly/google-generativeai already declared+locked; the
  `app.py` edit is normal source, declared).

### Per-decision detail (consequential ones)
**#1 6th page (DB-gated shell)** — Problem: the dashboard `app.py` does `st.stop()` if the DuckDB is
missing, BEFORE navigation. So the chat page is only reachable once a DB exists. Options: (a) chat as a
6th dashboard page [Recommended] — consistent, minimal; (b) a separate chat-only entrypoint outside the
DB gate. Repercussion: (a) you need the sample DB present to open the dashboard (already true for Phase
2); the chat logic itself uses no DB. (b) more surface, splits the app. Recommend (a).

**#3 Eval split** — Problem: the Phase 3 exit criterion (≥8/10 with citations) fundamentally needs the
real Gemini model + real embeddings (network + key), which can't run in the offline unit suite. Options:
(a) offline pattern test + env-gated live harness [Recommended]; (b) try to fake the whole thing offline
(wouldn't measure real accuracy). Repercussion: (a) the unit suite proves the pipeline deterministically;
you run the real ≥8/10 number once with your key (it's wired + documented in manual QA).

**#5 Phase 3 close** — after this merges, Phase 3's deliverables are all shipped; the live ≥8/10 run +
`dev→main` promotion are your boundary actions. Phase 4 (polish/portfolio) is next.

### Owner answer
**APPROVED 2026-06-20 — "Use your recommendations."** All 7 decisions ratified. Proceed to Execute (Step 7).
