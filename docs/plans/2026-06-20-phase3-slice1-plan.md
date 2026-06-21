## Plan — 2026-06-20 — Phase 3 slice 1 (RAG retrieval core)

### Goal Contract
OBJECTIVE:    Ship an offline hybrid-retrieval core (`src/flying_probe_copilot/rag/`) that
              fuses ChromaDB vector search + rank_bm25 lexical search via reciprocal rank
              fusion over a seeded failure-mode knowledge base — zero LLM calls.
SUCCESS-WHEN:
  - `from flying_probe_copilot.rag import build_retriever, HybridRetriever, Chunk, RetrievedChunk, load_kb`
    all import.
  - `tests/test_rag/` green; new `rag` package coverage ≥ 80%; full suite still ≥ 373 passing.
  - RRF test proves a chunk ranked by BOTH retrievers outranks one ranked by only one.
  - Vector + lexical + fusion + kb_loader + models each have ≥1 happy + ≥1 edge test.
  - Unit suite runs with NO network and NO model download (injected fake embedder).
OUT-OF-SCOPE: Gemini/LLM, citation prompt, chat UI, the 10-Q eval + anti-hallucination test,
              retrieval over DuckDB rows, any edit to pyproject.toml / db/schema.py /
              .claude/settings.json / CLAUDE.md / .env.example.
CONSTRAINTS:  Branch `feature/phase3-slice1-rag-retrieval`; TDD RED→GREEN per step; no new
              deps (all present); Phase-3-only; additive — zero edits to existing source.

### Architecture

```
src/flying_probe_copilot/rag/
  __init__.py        # public re-export + __all__
  models.py          # Chunk, RetrievedChunk (frozen dataclasses, analytics style)
  kb_loader.py       # load_kb(kb_dir) -> list[Chunk]  (markdown heading-section chunking)
  lexical_index.py   # LexicalIndex (rank_bm25 BM25Okapi) + _tokenize
  vector_index.py    # VectorIndex (chromadb in-memory) + Embedder protocol +
                     #   SentenceTransformerEmbedder (lazy, default) — embeddings passed
                     #   to chroma explicitly so chroma never downloads its own model
  retriever.py       # HybridRetriever.retrieve(query,*,top_k,rrf_k); build_retriever(...)
```

**Embedder injection (key design):** `VectorIndex(embedder: Embedder | None = None)`.
`Embedder` is a `Protocol` with `embed(texts: list[str]) -> list[list[float]]`. Default is
`SentenceTransformerEmbedder("all-MiniLM-L6-v2")`, lazy-loaded only when no embedder is
injected and only on first embed call. Tests inject a deterministic bag-of-words fake
embedder → unit suite is fully offline + reproducible. One real-model integration test is
gated behind env var `RAG_RUN_MODEL_TESTS` (default-skipped).

**Chroma usage:** create an in-memory `chromadb.EphemeralClient()` collection with NO
embedding function; call `collection.add(ids=, embeddings=, documents=, metadatas=)` and
`collection.query(query_embeddings=, n_results=)` passing our own vectors. Distance →
similarity; we only need rank order for RRF.

**Chunking:** split each `.md` on ATX headings (`^#{1,6} `). Each section = heading text +
body until next heading. If a section body exceeds `MAX_CHUNK_CHARS` (1200), split on blank
lines into sub-chunks, each carrying the same heading. `chunk_id = f"{rel_posix_path}#{ordinal}"`
(deterministic, stable across runs). Frontmatter (`--- ... ---`) and code fences are kept as
plain text. Files whose name starts with `_` are skipped; `README.md` is skipped from indexing.

**RRF:** standard reciprocal rank fusion. For each retriever's ranked list (rank starts at 1),
`score(c) += 1 / (RRF_K + rank)`, `RRF_K = 60`, equal weights. Fused list sorted by score
DESC then `chunk_id` ASC (deterministic tiebreak). Return top_k `RetrievedChunk` with the
fused score + each retriever's rank (None if absent) for later citation transparency.

### What / Why / Where / When
| # | File | What changes | Why (deliverable) | When (after) | Test file |
|---|------|-------------|-------------------|--------------|-----------|
| 1 | docs/knowledge-base/ | README + 00-index + 6-8 synthetic failure-mode `.md` docs | ROADMAP P3 #2 KB scaffold | first | test_kb_loader (uses tmp KB, not these) |
| 2 | src/.../rag/models.py | `Chunk`, `RetrievedChunk` frozen dataclasses | P3 #1 module | after 1 | tests/test_rag/test_models.py |
| 3 | src/.../rag/kb_loader.py | `load_kb`, heading chunker, `_tokenize`-free | P3 #2 ingest | after 2 | test_kb_loader.py |
| 4 | src/.../rag/lexical_index.py | `LexicalIndex` + `_tokenize` (BM25Okapi) | P3 #3 lexical | after 2 | test_lexical_index.py |
| 5 | src/.../rag/vector_index.py | `VectorIndex`, `Embedder` proto, ST embedder | P3 #3 vector | after 2 | test_vector_index.py |
| 6 | src/.../rag/retriever.py | `HybridRetriever`, RRF, `build_retriever` | P3 #3 fusion | after 3,4,5 | test_retriever.py |
| 7 | src/.../rag/__init__.py | re-export public API + `__all__` | P3 #1 | after 6 | test_public_api.py |
| 8 | tests/test_rag/conftest.py | fake embedder, tmp-KB writer, built_retriever fixtures | tests | with each | — |

### Ordered execution steps (TDD)
1. Create `docs/knowledge-base/` scaffold (README, 00-index, 6-8 failure-mode docs). (content, no test)
2. RED `test_models.py`: Chunk/RetrievedChunk construct, frozen, fields → implement `models.py` → GREEN.
3. RED `test_kb_loader.py`: load tmp KB → N chunks; heading split; deterministic chunk_id; max-size sub-split; empty dir → []; README skipped → implement `kb_loader.py` → GREEN.
4. RED `test_lexical_index.py`: keyword query ranks matching chunk first; tokenizer lowercases/splits; top_k bound; empty query → [] → implement `lexical_index.py` → GREEN.
5. RED `test_vector_index.py` (fake embedder): add chunks; query returns nearest by injected vectors; top_k; empty index → [] → implement `vector_index.py` (+ default ST embedder, lazy) → GREEN.
6. RED `test_retriever.py`: build over fake-embedded tmp KB; RRF ranks both-list chunk above one-list chunk; deterministic order; top_k; empty query → [] → implement `retriever.py` → GREEN.
7. RED `test_public_api.py`: all public names import from `flying_probe_copilot.rag` → implement `__init__.py` → GREEN.
8. Full `uv run pytest -q`; confirm ≥373 prior pass + new green; check `rag` coverage ≥80%.
9. (Optional, env-gated) real-model integration test verifying ST embedder loads + embeds — default-skipped.

### Resolved ambiguities (from Test-Case Plan G1–G12)
- **G1 (preamble / heading-less / empty):** Text before the first heading → one chunk with
  `heading=""`, ordinal 0. A file with no headings → one chunk (whole file), `heading=""`.
  An empty or whitespace-only file → 0 chunks.
- **G2 (oversized body, no blank lines):** Fallback = hard character split at
  `MAX_CHUNK_CHARS` (1200) boundaries (each slice ≤ 1200), same heading on each sub-chunk.
- **G3 (code fences vs headings):** The chunker tracks fenced-code state (toggled by lines
  starting with ```` ``` ````). A `#`-line **inside** a fence does NOT start a new section.
- **G4 (bad kb_dir):** Non-existent dir → `FileNotFoundError`; path is a file → `NotADirectoryError`.
  Never a silent `[]`.
- **G5 (lexical no-match):** Drop zero-score results → return `[]` when nothing matches.
- **G6 (tokenizer unicode):** `_tokenize(text) = re.findall(r"\w+", text.lower())` (Unicode
  `\w`, Python3 default) — keeps accented/CJK letters + digits, splits on punctuation/space.
  Shared by lexical AND the test fake embedder's vocab counting.
- **G7 (top_k boundary):** `top_k == 0` → `[]`; `top_k < 0` → `ValueError`. Uniform across
  lexical, vector, retriever. `rrf_k` must be `>= 1` else `ValueError`.
- **G8 (vector zero-overlap):** If a query tokenizes to zero tokens, or its embedding is the
  all-zero vector, `VectorIndex.search` → `[]` (deterministic no-match).
- **G9 (vector re-add):** `VectorIndex.add` uses chroma `upsert` (idempotent by chunk_id);
  re-adding the same id overwrites, never raises. Distinct ids with identical text both stored.
- **G10 (RetrievedChunk fields):** `chunk: Chunk`, `score: float` (fused RRF),
  `lexical_rank: int | None`, `vector_rank: int | None` (None = absent from that retriever).
- **G11 (raw per-retriever scores):** NOT exposed in slice 1 — ranks suffice for RRF +
  citation. Raw scores deferred (note in DECISION_LOG).
- **G12 (coverage):** The default `SentenceTransformerEmbedder` real-load/embed body is
  marked `# pragma: no cover` (only the env-gated `RAG_RUN_MODEL_TESTS` integration test
  exercises it), so the ≥80% offline gate is attainable. All other rag code is unit-covered.

### Plan Revision 1 (resolving Step 5 adversarial red-team)
**B1 (Chroma L2 vs cosine — BLOCKER):** `VectorIndex` creates its collection with
`metadata={"hnsw:space": "cosine"}`. The TEST fake embedder produces **binary presence**
bag-of-words vectors (0/1 per closed-vocab term), so cosine similarity orders strictly by
vocabulary overlap → nearest = most-overlapping, hand-computable. Test-plan VEC-01/VEC-02/
RET-01 wording updated from "cosine/inner-product of counts" to "cosine of binary presence
vectors". (Production ST embeddings are already unit-norm-friendly under cosine.)

**B2 (RRF universal claim — BLOCKER):** RRF does NOT universally rank a both-list chunk above
a one-list chunk (crossover: a one-list rank-1 chunk at `1/(60+1)` can beat a both-list pair
at high ranks). SUCCESS-WHEN re-scoped: *"Over the constructed RET-01 corpus (small N, both-
list ranks below the RRF crossover), a chunk ranked by BOTH retrievers receives a higher
fused score than a chunk ranked by only one."* RET-01 fixture stays small so it holds; no
general guarantee is asserted.

**B3 (BM25 ≤0 scores — BLOCKER):** Lexical no-match is decided by **token overlap, not score
sign**. `LexicalIndex.search`: a chunk is a candidate iff it shares ≥1 query token with the
chunk's tokens; candidates are ranked by BM25 score (negative allowed); non-overlapping
chunks are dropped. Empty/whitespace query or zero overlap anywhere → `[]`. This supersedes
G5's "drop zero-score" wording (which would wrongly erase a sole matching chunk).

**W4 (zero-vector guard):** explicit pre-query guard — `VectorIndex.search` returns `[]` if
the query embedding is all-zero; `VectorIndex.add` skips any chunk whose embedding is all-zero
(would be un-rankable under cosine). Documented; only reachable via the fake embedder.

**W5 (coverage gate is advisory):** `pyproject.toml` has no `fail_under`; the ≥80% rag figure
is read from the `--cov-report=term-missing` output by the parent at Step 8/9, not CI-enforced.
No pyproject edit (approval-gated) — gate stays manual.

**W6 (KB guardrail compliance):** the seeded KB gets an explicit parent compliance read at
Triple Check (Step 9) against guardrails #2/#3 before any commit (MQA-5 is performed, not just
listed). All seeded content is synthetic; standards cited by section number only.

**W7 (tokenizer underscores):** `\w` keeps `_`; KB seed + test fixtures avoid underscore-joined
identifiers so token boundaries match expectations. Noted.

**W8 (negative-input tests):** add explicit cases — `top_k < 0 → ValueError` and
`rrf_k < 1 → ValueError` — to lexical/vector/retriever (LEX-15, VEC-17, RET-21).

### Guardrails
- Branch: `feature/phase3-slice1-rag-retrieval` (off dev).
- Critical/approval-gated files touched: NONE (pyproject deps already present).
- New dependencies: NONE.
- KB content: synthetic only; NO IPC-A-610 / J-STD-001 verbatim; NO proprietary Keysight text;
  cite standards by section number only.
- Phase discipline: Phase 3 slice 1 only; LLM/UI/eval deferred.
- Additive only: no edits to existing source/tests; `.gitignore` already covers chroma + model cache.
