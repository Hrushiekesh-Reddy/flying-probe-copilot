## Decision Gate — 2026-06-20 — Phase 3 slice 1 (RAG retrieval core)

### Decision Index — 9 decisions
1. (Scope) Run Phase 3 as **slice 1 only** this session — offline retrieval core + KB scaffold; defer LLM, citation prompt, chat UI, 10-Q eval to slices 2-3 — Recommended: **YES (slice it)**.
2. (KB) Seed `docs/knowledge-base/` with **6-8 synthetic failure-mode docs** now (vs empty scaffold) — Recommended: **seed 6-8**.
3. (Embedding) Default production embedder = **all-MiniLM-L6-v2** (~90 MB, auto-downloads on first real use) — Recommended: **all-MiniLM-L6-v2**.
4. (Chunking) Markdown **heading-section** chunking, 1200-char cap with blank-line then hard-char fallback, fence-aware — Recommended: **as specified**.
5. (Fusion) RRF **k=60, equal weights**, sort by score DESC then chunk_id ASC — Recommended: **as specified**.
6. (Testing) **Inject a deterministic fake embedder** for unit tests; gate the real-model test behind `RAG_RUN_MODEL_TESTS` (default-skipped) so the unit suite is fully offline — Recommended: **YES**.
7. (Model surface) `RetrievedChunk` exposes the fused score + per-retriever **ranks only** (not raw scores) in slice 1 — Recommended: **ranks only**.
8. (Grounding) Slice 1 retrieves over the **KB markdown corpus only**, not DuckDB rows (row-grounding is a slice-2/3 concern once the LLM can read query results) — Recommended: **KB only**.
9. (Git) Commit slice 1 on `feature/phase3-slice1-rag-retrieval` at Step 10; **do NOT push / open PR** unless you ask — Recommended: **commit, no push**.

### Coverage Check
- Scope / slicing: decision #1
- Knowledge base: decision #2
- Architecture (embedding/chunking/fusion/model surface/grounding): decisions #3, #4, #5, #7, #8
- Testing strategy: decision #6
- Git / delivery: decision #9
- Approval-gated files: **none touched** (all deps already in pyproject.toml + uv.lock; no db/schema.py, .claude/settings.json, CLAUDE.md, .env.example edits)

### Per-decision detail (consequential ones)
**#1 Slice it** — Problem: Phase 3 is 7 deliverables with a hard external dep (Gemini key). Building it all in one session is high-risk and blocks on a key you must supply. Options: (a) slice 1 offline core now [Recommended], (b) attempt full Phase 3 (blocks on key), (c) just scaffold empty module. Repercussions: (a) ships tested, mergeable value with zero external deps; (b) stalls mid-session; (c) under-delivers. 

**#2 Seed KB** — Problem: retrieval can't be meaningfully tested without some corpus, but the KB is "owner-authored." Options: (a) seed 6-8 synthetic guardrail-compliant docs you later expand [Recommended], (b) empty scaffold + README only. Repercussions: (a) real retrieval tests + a starting point; (b) thinner tests, you write all content. NOTE: all seeded content is synthetic; NO IPC-A-610 / J-STD-001 verbatim, NO proprietary Keysight text — parent does a compliance read at Triple Check.

**#3 Embedding model** — all-MiniLM-L6-v2 is the standard compact default (fast, ~90 MB). Larger all-mpnet-base-v2 is more accurate but ~420 MB + slower. The choice only matters when the real model runs (slice 2+); unit tests use the fake embedder either way. Repercussion: the persisted vector index is locked to whichever model embeds it.

**#6 Fake embedder / offline tests** — Problem: sentence-transformers downloads a model + needs network; that makes the unit suite slow, flaky, and non-deterministic. Options: (a) inject a deterministic fake embedder, gate the real one [Recommended], (b) let tests hit the real model. Repercussions: (a) fast, offline, reproducible; (b) network-dependent, slow, CI-fragile.

### External dependencies (do NOT block slice 1)
- **Gemini API key** — needed at slice 2 only. Not used this session.
- **KB content expansion** — you expand the seeded KB later with real field-learned failure modes.

### Owner answer
**APPROVED 2026-06-20 — "Use your recommendations."** All 9 decisions ratified as recommended.
Proceed to Execute (Step 7).
