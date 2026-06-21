## Session Brief — 2026-06-20 — Phase 3 slice 1 (RAG retrieval core)

### What the owner wants
> "lets execute phase 3 of the plan"

Phase 3 = **RAG Co-Pilot Layer** (ROADMAP.md lines 101-117): natural-language Q&A
grounded in the test data + a failure-mode knowledge base, with hybrid retrieval and
forced citations.

### Slicing decision (proposed — confirm at Decision Gate)
Phase 3 has 7 deliverables and a hard external dependency (Gemini API key) that the owner
must supply. Following the Phase 2 precedent (sliced into 3), Phase 3 is proposed as:

- **Slice 1 (THIS SESSION):** Offline retrieval core + KB scaffold. Everything that can be
  built and unit-tested *without* the Gemini key.
- **Slice 2 (next):** Gemini LLM integration + citation-forcing structured-output prompt +
  anti-hallucination refusal. Needs the API key.
- **Slice 3 (last):** Chat interface wired into the Streamlit dashboard + the 10-question
  representative Q&A evaluation. Exercises the full stack.

### Goal statement (one sentence)
Ship a tested, offline hybrid-retrieval core (`src/flying_probe_copilot/rag/`) that, given a
natural-language query, returns ranked evidence chunks fused from a ChromaDB vector index
and a rank_bm25 lexical index via reciprocal rank fusion — over a seeded failure-mode
knowledge base — with zero LLM calls.

### Success looks like
- `src/flying_probe_copilot/rag/` package exists with: a document/chunk model, a KB loader,
  a vector index (ChromaDB + sentence-transformers), a lexical index (rank_bm25), and a
  reciprocal-rank-fusion retriever exposing one public `retrieve(query, *, top_k) -> list[RetrievedChunk]`.
- A failure-mode KB scaffold under `docs/knowledge-base/` (synthetic, guardrail-compliant
  starter docs — owner expands later) that the loader ingests.
- Unit tests prove: KB loads + chunks correctly; vector search returns semantically-near
  chunks; lexical search returns keyword-matched chunks; RRF fusion ranks a doc that scores
  in BOTH retrievers above one that scores in only one; deterministic ordering; empty-query
  and no-result edge paths handled.
- `pytest -q` green; new `rag` package coverage ≥ 80%; existing 373+ tests still pass.

### Out of scope (explicit — deferred to slice 2/3)
- ❌ Gemini API integration / any live LLM call / API key handling.
- ❌ Citation-forcing prompt template.
- ❌ Chat UI in Streamlit (`ui/`).
- ❌ The 10 representative Q&A tests + anti-hallucination refusal test (need the LLM).
- ❌ Retrieval over the DuckDB *rows* (structured data) — slice 1 retrieves over the KB
  markdown corpus only; row-grounding is a slice-2/3 concern once the LLM can read results.
- ❌ Any edit to `db/schema.py` or other approval-gated files.

### Phase / milestone
ROADMAP Phase 3 — RAG co-pilot. This session delivers deliverable #1 (rag module
foundation), #2 (KB scaffold), and #3 (hybrid retrieval: ChromaDB + rank_bm25 + RRF).
Deliverables #4-#7 (LLM, citation prompt, chat UI, eval) deferred to slices 2-3.

### Branch
`feature/phase3-slice1-rag-retrieval` — created off `dev` (confirmed; clean working tree).

### Known external dependencies (do NOT block slice 1)
- Gemini API key — needed only at slice 2. Not used this session.
- Owner-authored KB content — slice 1 seeds a *synthetic, guardrail-compliant* starter KB
  (no IPC-A-610 / J-STD-001 verbatim, no proprietary Keysight text). Owner expands it later.
- All Python deps (chromadb, sentence-transformers, rank-bm25) are already in
  `pyproject.toml` + `uv.lock` — no new-dependency approval gate.
