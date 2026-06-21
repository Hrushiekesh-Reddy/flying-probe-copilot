# Test-Case Plan — Phase 3 slice 1 (RAG retrieval core)

> Behavior-level test cases (test-generator role) for the offline hybrid-retrieval core
> `src/flying_probe_copilot/rag/`. Each case is described by observable behavior
> (inputs / preconditions -> expected outputs / effects) only — NO implementation detail,
> NO production code, NO test stubs/asserts. Mirrors the case-ID-docstring + fixture style
> of `tests/test_analytics/`. Execute (TDD RED->GREEN) implements each case later.
>
> Source of truth: `2026-06-20-phase3-slice1-plan.md` and `-brief.md`.
> Module surface under test: `models.py`, `kb_loader.py`, `lexical_index.py`,
> `vector_index.py`, `retriever.py`, `__init__.py`.

---

## Fake embedder design note (deterministic, model-free)

The fake `Embedder` (`embed(texts) -> list[list[float]]`) embeds each text as a fixed-length
**bag-of-words count vector over a closed, test-controlled vocabulary**. The fixture defines an
ordered vocabulary list (e.g. `["solder","bridge","void","tombstone","open","short"]`); each
text's embedding is the per-term occurrence count at that term's index (tokenized the same way
the lexical tokenizer does — lowercase, split on non-alphanumeric), so two texts sharing more
vocabulary terms produce vectors with greater cosine/inner-product similarity. Because the
mapping is pure, deterministic, and hand-computable, a test can **know in advance which corpus
chunk is nearest to a given query** (the one with the most overlapping vocabulary terms) and
assert exact rank order without any real model, download, or network. A "no-overlap" query maps
to the zero vector (or an all-zero/orthogonal vector), which the vector tests use to exercise
the no-match path deterministically.

---

## Test cases

One row per behavior. **Neg?** = negative/edge/error path.

### Unit: `models.py` (Chunk, RetrievedChunk frozen dataclasses)

| Case ID | Unit | Input / precondition | Expected result | Deliverable it proves |
|---------|------|----------------------|-----------------|-----------------------|
| MOD-01 | Chunk | Construct a Chunk with all documented fields (chunk_id, text, source-path/heading metadata as the model defines). | Instance constructs; every field reads back the value passed in. | P3 #1 chunk model |
| MOD-02 | Chunk | Construct a Chunk, then attempt to reassign any field. | Reassignment raises `dataclasses.FrozenInstanceError` (frozen). | P3 #1 immutable model |
| MOD-03 | Chunk | Construct two Chunks with identical field values; construct a third differing in one field. | Equal-valued instances compare `==`; the differing instance compares `!=` (value semantics from frozen dataclass). | P3 #1 chunk model |
| MOD-04 | RetrievedChunk | Construct a RetrievedChunk carrying a Chunk + fused score + each retriever's rank (lexical_rank / vector_rank), with one rank present and the other `None`. | Instance constructs; fused score and both rank fields (incl. the `None`) read back exactly. | P3 #3 citation-transparency fields |
| MOD-05 | RetrievedChunk | Construct a RetrievedChunk, then attempt to reassign a field. | Reassignment raises `dataclasses.FrozenInstanceError` (frozen). | P3 #1 immutable model |
| MOD-06 | RetrievedChunk | Inspect the declared field set of both dataclasses. | Field set matches exactly what the public API/plan documents (no stray/placeholder fields); the rank fields admit `None`. | P3 #1 model schema |

### Unit: `kb_loader.py` (`load_kb(kb_dir) -> list[Chunk]`)

| Case ID | Unit | Input / precondition | Expected result | Deliverable it proves |
|---------|------|----------------------|-----------------|-----------------------|
| KB-01 | load_kb | tmp KB with one `.md` containing N ATX heading sections (each `# ...` + body). | Returns N Chunks (one per heading section); each chunk's text contains its heading and the body up to the next heading. | P3 #2 heading-section chunking |
| KB-02 | load_kb | A `.md` with text **before** the first heading (preamble) and/or frontmatter `--- ... ---`. | Preamble/frontmatter handled per documented rule (kept as plain text in a chunk or attributed deterministically); no content silently dropped, no crash. *(Plan must pin the exact preamble rule — see gaps G1.)* | P3 #2 ingest robustness |
| KB-03 | load_kb | A `.md` whose single section body exceeds MAX_CHUNK_CHARS (1200) and contains blank-line separators. | Section is sub-split into >1 chunks on blank lines; each sub-chunk carries the same heading; each sub-chunk body <= 1200 chars (boundary). | P3 #2 max-size sub-split |
| KB-04 | load_kb | A `.md` whose single section body is exactly at / just under / just over 1200 chars (boundary trio). | At/under 1200 -> single chunk (no split); just over -> splits. Proves the boundary is 1200 inclusive, not off-by-one. | P3 #2 max-size boundary |
| KB-05 | load_kb | A section body over 1200 chars with **no blank lines** to split on. | Documented fallback applied (e.g. single oversized chunk kept, or hard-split); no crash; no data loss. *(Plan must pin the no-blank-line fallback — see gaps G2.)* | P3 #2 ingest robustness |
| KB-06 | load_kb | A KB with multiple files and multiple sections per file. | Each chunk_id equals `"{rel_posix_path}#{ordinal}"`; ordinals restart per file and increase in document order; all chunk_ids are unique across the KB. | P3 #2 deterministic chunk_id |
| KB-07 | load_kb | Load the **same** unchanged KB twice. | Both calls return chunks with identical chunk_ids in identical order (deterministic / stable across runs). | P3 #2 determinism |
| KB-08 | load_kb | KB containing a nested subdirectory with a `.md` file. | That file's chunk_id rel-path uses POSIX `/` separators (not OS backslash on Windows) and is relative to kb_dir. | P3 #2 stable cross-platform ids |
| KB-09 | load_kb | KB containing `README.md` plus a normal doc. | README.md contributes no chunks; the normal doc is loaded. | P3 #2 skip README |
| KB-10 | load_kb | KB containing a file named `_draft.md` (starts with `_`) plus a normal doc. | The `_`-prefixed file contributes no chunks; the normal doc is loaded. | P3 #2 skip underscore files |
| KB-11 | load_kb | Empty directory (exists, no files). | Returns `[]`. | P3 #2 empty-dir edge |
| KB-12 | load_kb | Directory containing only skipped files (README.md and `_*.md`). | Returns `[]` (no chunks from skipped-only corpus). | P3 #2 skip-only edge |
| KB-13 | load_kb | A `.md` file that is empty or whitespace-only. | Produces no chunks (or the documented zero-content handling); no crash. *(Plan must state whether a heading-less empty file yields 0 chunks — see gaps G1.)* | P3 #2 whitespace-only edge |
| KB-14 | load_kb | A `.md` whose content includes a fenced code block containing lines that look like `# heading`. | Documented heading rule applied to code fences (per plan, fences kept as plain text — confirm the `#` inside a fence does/does not start a new section). *(Plan must pin fence-vs-heading precedence — see gaps G3.)* | P3 #2 chunking correctness |
| KB-15 | load_kb | A `.md` containing non-ASCII / unicode content (accented chars, CJK, emoji) in heading and body. | Loaded without error; unicode preserved verbatim in chunk text; chunk_id still well-formed. | P3 #2 unicode handling |
| KB-16 | load_kb | A non-Markdown file (e.g. `.txt`, `.png`) present alongside `.md` files. | Only `.md` files are ingested; non-`.md` files are ignored. | P3 #2 file-type filter |
| KB-17 | load_kb | `kb_dir` path that does not exist. | Raises a clear error (e.g. `FileNotFoundError` / documented exception); does **not** silently return `[]`. *(Plan must pin missing-dir behavior — see gaps G4.)* | P3 #2 error path |
| KB-18 | load_kb | `kb_dir` that points at a file, not a directory. | Raises a clear, documented error (not a silent empty list, not an unhandled traceback). *(See gaps G4.)* | P3 #2 error path |

### Unit: `lexical_index.py` (LexicalIndex over BM25Okapi, `_tokenize`, `search(query, top_k)`)

| Case ID | Unit | Input / precondition | Expected result | Deliverable it proves |
|---------|------|----------------------|-----------------|-----------------------|
| LEX-01 | search | Index over chunks where exactly one chunk contains the query keyword(s). | That chunk is ranked first (highest score); result is a ranked `[(Chunk, score)]` list. | P3 #3 lexical relevance |
| LEX-02 | search | Index over chunks with varying keyword frequency for the query term. | Returned order is by BM25 score DESC (more/better keyword matches rank higher than weaker matches). | P3 #3 ranked ordering |
| LEX-03 | _tokenize | A string mixing uppercase, punctuation, digits, and separators (e.g. `"Solder-Bridge, R12!"`). | Tokens are lowercased and split on non-alphanumeric boundaries (`solder`, `bridge`, `r12`); punctuation produces no empty tokens. | P3 #3 tokenizer contract |
| LEX-04 | search | Query whose casing/punctuation differs from corpus (e.g. query `"SOLDER."` vs corpus `"solder"`). | Still matches the relevant chunk first (tokenization makes match case/punctuation insensitive). | P3 #3 tokenizer-driven match |
| LEX-05 | search | top_k smaller than the number of matching chunks. | Returns exactly top_k results, the top-ranked ones. | P3 #3 top_k truncation |
| LEX-06 | search | top_k larger than the corpus size. | Returns at most corpus-size results (no padding, no error). | P3 #3 top_k over-corpus edge |
| LEX-07 | search | Empty query string (`""`). | Returns `[]`. | P3 #3 empty-query edge |
| LEX-08 | search | Whitespace-only query (`"   "`) — tokenizes to zero tokens. | Returns `[]` (treated like empty query). | P3 #3 whitespace-only edge |
| LEX-09 | search | Query whose terms appear in **no** chunk. | Returns `[]` or all-zero-score results per documented convention; never raises. *(Plan must pin no-match output: empty list vs zero-scored list — see gaps G5.)* | P3 #3 no-match edge |
| LEX-10 | search | LexicalIndex built over an empty chunk list. | Any query returns `[]`; construction does not raise. | P3 #3 empty-index edge |
| LEX-11 | search | Index over a single chunk; query matches it. | Returns that one chunk; `len == 1`. | P3 #3 single-item edge |
| LEX-12 | search | Corpus containing two chunks with identical text (duplicate). | Both appear in results; ranking does not crash on duplicate documents; scores are equal. | P3 #3 duplicate handling |
| LEX-13 | search | Query and corpus with unicode tokens (accented / CJK terms). | Unicode terms tokenize and match; the unicode-bearing chunk ranks first for its term. *(Depends on `_tokenize` unicode policy — see gaps G6.)* | P3 #3 unicode handling |
| LEX-14 | search | top_k == 0. | Returns `[]` (documented zero-k behavior), no error. *(Plan should confirm top_k==0 semantics — see gaps G7.)* | P3 #3 top_k boundary |

### Unit: `vector_index.py` (VectorIndex over in-memory chromadb, injected fake Embedder, `add`, `search`)

| Case ID | Unit | Input / precondition | Expected result | Deliverable it proves |
|---------|------|----------------------|-----------------|-----------------------|
| VEC-01 | search | VectorIndex(embedder=fake); add chunks whose vocabulary overlap with the query is known; query for a term. | The chunk with the greatest vocabulary overlap (nearest by fake embedding) ranks first; result is ranked `[(Chunk, score)]`. | P3 #3 vector relevance (model-free) |
| VEC-02 | search | Same as VEC-01 with several chunks of decreasing overlap. | Returned order matches the known nearest->farthest order by the deterministic embedding. | P3 #3 ranked ordering |
| VEC-03 | search | top_k smaller than number of added chunks. | Returns exactly top_k nearest results. | P3 #3 top_k truncation |
| VEC-04 | search | top_k larger than number of added chunks. | Returns at most the number of added chunks (no error, no padding). | P3 #3 top_k over-corpus edge |
| VEC-05 | search | Query on a VectorIndex with no chunks added (empty index). | Returns `[]`; no crash. | P3 #3 empty-index edge |
| VEC-06 | search | Empty query string. | Returns `[]`. | P3 #3 empty-query edge |
| VEC-07 | search | Whitespace-only query. | Returns `[]` (zero-token query handled like empty). | P3 #3 whitespace-only edge |
| VEC-08 | search | Query whose embedding has zero overlap with every chunk (orthogonal / zero vector under fake embedder). | Returns results without error; documented no-overlap behavior (e.g. arbitrary-but-stable order or empty) is honored. *(Plan must pin zero-overlap output — see gaps G8.)* | P3 #3 no-match edge |
| VEC-09 | add/search | add a single chunk; query for it. | Returns that one chunk; `len == 1`. | P3 #3 single-item edge |
| VEC-10 | add | add an empty chunk list, then query. | No crash; query returns `[]`. | P3 #3 empty-add edge |
| VEC-11 | add | add chunks where two chunks have identical text (duplicate) but distinct chunk_ids. | Both are stored under distinct ids; both can be returned; chroma `add` does not error on duplicate documents. | P3 #3 duplicate handling |
| VEC-12 | add | add chunks twice / add the same chunk_id again. | Documented re-add behavior (upsert vs duplicate-id error) is honored; no silent index corruption. *(Plan must pin re-add semantics — see gaps G9.)* | P3 #3 add idempotency |
| VEC-13 | search | Chunks/query containing unicode text under the fake embedder. | Stored and retrieved without error; unicode chunk retrievable. | P3 #3 unicode handling |
| VEC-14 | Embedder injection | VectorIndex(embedder=fake) used end to end. | The injected embedder is the only embedding source; **no SentenceTransformer load, no network, no model download** occurs during the test. | P3 #3 offline injectable embedder (SUCCESS-WHEN) |
| VEC-15 | default embedder laziness | Construct VectorIndex with no embedder injected, but never call add/search. | Construction does **not** load/download the default ST model (lazy: only on first embed call). | P3 #3 lazy default embedder |
| VEC-16 | search | top_k == 0. | Returns `[]`, no error (consistent with LEX-14). *(See gaps G7.)* | P3 #3 top_k boundary |

### Unit: `retriever.py` (HybridRetriever.retrieve / RRF, build_retriever)

| Case ID | Unit | Input / precondition | Expected result | Deliverable it proves |
|---------|------|----------------------|-----------------|-----------------------|
| RET-01 | retrieve | Build over fake-embedded tmp KB. Construct corpus so chunk **B** appears in BOTH the lexical and vector ranked lists while chunk **A** appears in only one. | B's fused RRF score > A's; B is ranked above A in the returned list. **(Critical fusion case a.)** | P3 #3 RRF correctness (SUCCESS-WHEN) |
| RET-02 | retrieve | Construct a scenario where two chunks earn an **equal** fused RRF score. | Tie is broken by `chunk_id` ASC; ordering is deterministic and repeatable across runs. **(Critical fusion case b.)** | P3 #3 deterministic ordering |
| RET-03 | retrieve | A query that returns more fused candidates than top_k (default 5 and an explicit small top_k). | Returns exactly top_k RetrievedChunks, the highest-scored ones; remainder truncated. **(Critical fusion case c.)** | P3 #3 top_k truncation |
| RET-04 | retrieve | Empty query string. | Returns `[]` (no RetrievedChunks). **(Critical fusion case d.)** | P3 #3 empty-query edge |
| RET-05 | retrieve | A chunk appearing at rank r in one list and absent from the other; hand-compute expected RRF. | Fused score equals `1/(rrf_k + r)` for the single-list chunk (rank starts at 1, rrf_k=60); a both-list chunk equals the sum over both lists. Numbers are hand-computable and pinned. | P3 #3 RRF formula (rank base 1, k=60) |
| RET-06 | retrieve | Same dataset, two different `rrf_k` values (e.g. 60 vs 1). | Fused scores change in the documented direction (smaller k -> rank differences matter more); ordering reflects the supplied rrf_k, proving the parameter is honored. | P3 #3 configurable rrf_k |
| RET-07 | retrieve | A query that matches in lexical only (vector returns nothing) and vice versa. | Retriever still returns the matched chunks from the contributing retriever; the absent retriever's rank is recorded as `None` on the RetrievedChunk. | P3 #3 partial-retriever fusion + transparency |
| RET-08 | retrieve | Whitespace-only query. | Returns `[]` (consistent with empty query). | P3 #3 whitespace-only edge |
| RET-09 | retrieve | Query whose terms match no chunk in either retriever. | Returns `[]`; no crash. | P3 #3 no-match edge |
| RET-10 | retrieve | top_k larger than the entire corpus. | Returns at most corpus-size RetrievedChunks (de-duplicated across the two lists); no duplicates of the same chunk_id. | P3 #3 top_k over-corpus + dedup |
| RET-11 | retrieve | A chunk that appears in BOTH ranked lists. | It appears **once** in the fused output (not twice); its RetrievedChunk carries both lexical_rank and vector_rank (neither `None`). | P3 #3 fusion de-duplication |
| RET-12 | retrieve | Build over an empty KB (no chunks). | Any query returns `[]`; build/retrieve do not crash. | P3 #3 empty-corpus edge |
| RET-13 | retrieve | Single-chunk KB; query matches it. | Returns one RetrievedChunk; ranks/score populated; `len == 1`. | P3 #3 single-item edge |
| RET-14 | retrieve | Unicode query against a KB with a unicode chunk. | The unicode chunk is retrieved and fused correctly; no encoding error. | P3 #3 unicode handling |
| RET-15 | retrieve | Default call (no top_k / rrf_k passed). | Behaves as `top_k=5`, `rrf_k=60`. | P3 #3 default kwargs contract |
| RET-16 | retrieve | top_k == 0. | Returns `[]`, no error (consistent with LEX-14 / VEC-16). *(See gaps G7.)* | P3 #3 top_k boundary |
| RET-17 | retrieve | Inspect every returned RetrievedChunk. | Output is sorted by fused score DESC then chunk_id ASC; each carries the underlying Chunk, fused score, and per-retriever ranks for citation transparency. | P3 #3 output contract |
| RET-18 | build_retriever | `build_retriever(tmp_kb_dir, embedder=fake)`. | Returns a working HybridRetriever whose `retrieve` answers queries over that KB using the injected embedder (no model download). | P3 #3 build_retriever wiring |
| RET-19 | build_retriever | `build_retriever(nonexistent_kb_dir, embedder=fake)`. | Surfaces the same clear error as `load_kb` on a bad dir (does not silently build an empty retriever). *(Ties to KB-17 / gaps G4.)* | P3 #3 error path |
| RET-20 | build_retriever | `build_retriever(empty_kb_dir, embedder=fake)`. | Builds successfully; queries return `[]` (empty but valid retriever). | P3 #3 empty-corpus build |

### Unit: `__init__.py` (public API re-export)

| Case ID | Unit | Input / precondition | Expected result | Deliverable it proves |
|---------|------|----------------------|-----------------|-----------------------|
| API-01 | public API | `from flying_probe_copilot.rag import build_retriever, HybridRetriever, Chunk, RetrievedChunk, load_kb`. | All five import without error; functions are callable; classes/dataclasses are types. | P3 #1 public surface (SUCCESS-WHEN) |
| API-02 | public API | Import `VectorIndex` and `LexicalIndex` from `flying_probe_copilot.rag`. | Both import without error and are types. | P3 #1 public surface |
| API-03 | public API | Inspect `flying_probe_copilot.rag.__all__`. | `__all__` lists exactly the documented public names (build_retriever, HybridRetriever, Chunk, RetrievedChunk, load_kb, VectorIndex, LexicalIndex); no missing/extra entries. | P3 #1 explicit public contract |

---

## Untestable by automation (-> Manual QA cases)

These cannot be asserted deterministically in the offline unit suite and become Manual QA items:

- **MQA-1: Real SentenceTransformer model download + load.** `SentenceTransformerEmbedder("all-MiniLM-L6-v2")` actually fetching/loading the model requires network + large download; covered only by the env-gated (`RAG_RUN_MODEL_TESTS`, default-skipped) integration test, run manually with connectivity.
- **MQA-2: Real-model embedding dimensionality / shape sanity.** That the real ST embedder returns 384-dim float vectors and that chroma accepts them — verifiable only with the real model loaded (manual, env-gated).
- **MQA-3: Semantic-quality judgement.** Whether real-model vector search returns *genuinely semantically relevant* chunks for a paraphrased query (no shared keywords) is a subjective relevance judgement, not a deterministic assert.
- **MQA-4: End-to-end retrieval quality over the seeded KB content.** Whether the synthetic failure-mode KB returns sensible evidence for realistic operator questions is human-judged.
- **MQA-5: Guardrail / content compliance of the seeded KB.** That the seeded `docs/knowledge-base/` docs contain no IPC-A-610 / J-STD-001 verbatim text and no proprietary Keysight text is a manual content review.
- **MQA-6: Performance / latency.** Retrieval latency with the real model and a realistic KB size is a manual/observational check, not a unit assertion.
- **MQA-7: No-network guarantee of the unit suite at the process level.** That the *whole* unit run performs zero network calls is best confirmed manually (e.g. running offline / with sockets blocked); individual tests can only assert the default embedder was never instantiated.

---

## Coverage gaps / ambiguities the plan MUST resolve before approval

These are flagged, not fixed. Each blocks an unambiguous assertion in the cases above.

- **G1 (KB preamble / heading-less content):** The plan says sections start at ATX headings but does not state what happens to text **before the first heading** or to a file with **no headings at all** (and an empty/whitespace-only file). KB-02 and KB-13 cannot pin expected output until this is specified (drop? one preamble chunk? whole-file chunk with ordinal 0?).
- **G2 (oversized section, no blank lines):** Sub-splitting is defined "on blank lines" for bodies > 1200 chars. The plan does not define the fallback when a > 1200-char body has **no blank lines** (hard char-split? keep one oversized chunk?). Blocks KB-05.
- **G3 (code fences vs headings):** Plan says code fences are "kept as plain text" but also splits on `^#{1,6} `. A `#`-prefixed line **inside a fenced block** is ambiguous — does it start a new section or stay in the fence? Blocks KB-14.
- **G4 (bad kb_dir contract):** No specified behavior for a non-existent `kb_dir` or a path that is a file. Blocks KB-17, KB-18, RET-19 — need the exact exception type (or documented empty-list contract).
- **G5 (lexical no-match output):** Not stated whether a query matching no chunk yields `[]` or a list of zero-scored chunks. Blocks LEX-09.
- **G6 (tokenizer unicode policy):** "splits on non-alphanumeric" is ambiguous for unicode — does "alphanumeric" mean ASCII `[a-z0-9]` (which would strip accented/CJK letters) or Unicode word chars? Determines whether LEX-13 / VEC-13 / RET-14 can match unicode terms or must expect them stripped.
- **G7 (top_k == 0 and negative top_k):** Behavior for `top_k=0` (and `top_k < 0`) is unspecified across lexical, vector, and retriever. Blocks LEX-14, VEC-16, RET-16 — need empty-list vs ValueError decision.
- **G8 (vector zero-overlap / orthogonal query):** With the fake bag-of-words embedder, a query sharing no vocabulary maps to a zero vector. Chroma's distance for a zero query vector and the resulting order are unspecified. Blocks VEC-08 — need documented expected output (empty, or stable arbitrary order).
- **G9 (vector re-add / duplicate chunk_id):** Whether `add` of an already-present chunk_id upserts or raises (chroma raises on duplicate ids by default) is unspecified. Blocks VEC-12.
- **G10 (RetrievedChunk field names):** The plan describes "fused score + each retriever's rank (None if absent)" but does not name the fields. MOD-04 / MOD-06 / RET-17 reference rank fields generically; the exact field names must be fixed so the schema test can assert them.
- **G11 (score semantics in output):** RRF returns a fused score, but it is unspecified whether the per-retriever raw scores (lexical/vector) are also exposed on RetrievedChunk or only the ranks. Affects MOD-06 / RET-17 assertions.
- **G12 (coverage target attribution):** SUCCESS-WHEN requires `rag` package coverage >= 80%. The default `SentenceTransformerEmbedder` branch is intentionally never exercised offline (only env-gated). The plan should confirm whether that branch is excluded from the 80% denominator (e.g. via `# pragma: no cover`) or whether the env-gated test must run in CI to hit it — otherwise the 80% gate may be unattainable offline.
