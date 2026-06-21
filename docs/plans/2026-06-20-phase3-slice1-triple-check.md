## Parent Triple Comparison — 2026-06-20 — Phase 3 slice 1 (RAG retrieval core)

### What I FOUND (independent code read)
- `src/flying_probe_copilot/rag/` — 6 files:
  - `models.py`: `Chunk` (6 fields) + `RetrievedChunk` (chunk, score, lexical_rank|None, vector_rank|None), both frozen.
  - `kb_loader.py`: `load_kb(kb_dir)` — fence-aware ATX heading chunking, preamble→heading="", 1200-char cap with blank-line then hard-char fallback, skips README/`_*`, POSIX relpath ids, raises FileNotFoundError/NotADirectoryError. 99% cov (1 defensive line).
  - `lexical_index.py`: `LexicalIndex` (BM25Okapi) + `_tokenize` (Unicode `\w`). Match = token-overlap, NOT score sign. 100%.
  - `vector_index.py`: `VectorIndex` (chroma EphemeralClient, `hnsw:space="cosine"`, unique collection name), injectable `Embedder` protocol + lazy `SentenceTransformerEmbedder` (pragma:no-cover), all-zero embedding guard on add+search. 100%.
  - `retriever.py`: `HybridRetriever.retrieve(query,*,top_k=5,rrf_k=60)` RRF = Σ 1/(rrf_k+rank), rank base 1, sort score DESC then chunk_id ASC; `build_retriever`. 100%.
  - `__init__.py`: 7 public names + `__all__`. 100%.
- `docs/knowledge-base/`: README + 00-index + 8 synthetic failure-mode docs (opens, shorts, cold-solder-joint, tombstoning, insufficient-solder, component-misorientation, out-of-tolerance-analog, missing-component). Standards cited by section number only; no verbatim IPC/J-STD/Keysight text.
- `tests/test_rag/`: conftest (FakeEmbedder binary presence vectors + tmp-KB writer) + 80 tests across 6 files.

### What was PLANNED (SUCCESS-WHEN)
- 7 public names import; rag coverage ≥80%; full suite ≥373 passing; RRF both-list>one-list on the RET-01 corpus; each module has happy+edge tests; unit suite offline (fake embedder, no model download).

### What was EXECUTED (executor + verifier claim)
- 80 rag tests + KB scaffold; full suite 454 passed / 1 xfailed / 97%; rag 99–100% per file. Verifier verdict PASS with B1/B2/B3 confirmed in code, RRF hand-verified (1/61), offline + deterministic, KB compliant, API exact.

### Delta Analysis
- FOUND vs PLANNED: **match.** Every SUCCESS-WHEN criterion is realised in the code I read; coverage exceeds the gate; RRF/edge/offline behaviours present.
- FOUND vs EXECUTED: **match.** The code I read is exactly what the verifier described (cosine space, token-overlap match, scoped RRF, lazy ST). No report inflation.
- EXECUTED vs PLANNED: **match.** Plan Revision 1 BLOCKER fixes (B1 cosine+binary, B2 scoped claim, B3 token-overlap) are all present; OUT-OF-SCOPE respected (no LLM/UI/eval/row-grounding; no approval-gated edits).

### Two execution fixes (in-scope, during Execute — logged here for the record)
1. Chroma collection name `"kb"` rejected (min 3 chars) → renamed `kb_chunks` → then per-instance `kb_{uuid}` because EphemeralClient shares process-level state and a fixed name collided across test instances. Behaviour unchanged; tests green.
2. `# pragma: no cover` added to the two default-ST-embedder lines so the offline coverage story is clean (G12).

### Out-of-scope bugs (surfacing to owner)
- None new. Pre-existing BUG-011 (flaky parser test) remains xfailed; untouched this session.

### KB guardrail compliance (W6 — parent read)
- Confirmed independently: all seeded KB content is synthetic, paraphrased, operator-facing; standards
  referenced by section number only; no copyrighted standard text and no proprietary Keysight manual text
  in the retrievable corpus. COMPLIANT.

### Verdict
**CLEAN** — all three align. Proceed to Documentation (Step 10).
