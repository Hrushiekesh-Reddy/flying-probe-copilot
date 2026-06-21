## Manual QA — 2026-06-20 — Phase 3 slice 1 (RAG retrieval core)

Code passing tests ≠ feature working. Run these by hand. All commands use `python -m uv run`.

### §0 — Test suite + coverage (sanity)
```
cd E:\flying-probe-copilot
python -m uv run pytest tests/test_rag -q --cov=src/flying_probe_copilot/rag --cov-report=term-missing
python -m uv run pytest -q
```
**Expected:** rag suite 80 passed; rag files 99–100%. Full suite **454 passed, 1 xfailed, 0 failed**, 97%.

### §1 — Retrieve over the real seeded KB (interactive)
```
python -m uv run python -c "from flying_probe_copilot.rag import build_retriever; r=build_retriever('docs/knowledge-base', embedder=__import__('tests.test_rag.conftest', fromlist=['FakeEmbedder']))"
```
That import is awkward — instead use a short script. Save as `$env:TEMP\rag_smoke.py`:
```python
from flying_probe_copilot.rag import build_retriever, load_kb

chunks = load_kb("docs/knowledge-base")
print(f"loaded {len(chunks)} chunks from {len({c.doc_id for c in chunks})} docs")

# Real model path (downloads all-MiniLM-L6-v2 on first run; needs network ~90 MB).
r = build_retriever("docs/knowledge-base")  # default ST embedder
for q in ["why would a chip stand up on one end during reflow?",
          "two nets connected that should be isolated",
          "resistor reading outside its limits"]:
    print(f"\nQ: {q}")
    for rc in r.retrieve(q, top_k=3):
        print(f"  {rc.score:.4f}  {rc.chunk.chunk_id}  (lex={rc.lexical_rank}, vec={rc.vector_rank})  {rc.chunk.heading}")
```
Run: `python -m uv run python $env:TEMP\rag_smoke.py`

**What to look for:**
- "loaded 8+ chunks from 8 docs" (README + 00-index skipped/loaded per rules; README is skipped).
- Q1 ("stand up on one end") → top hit from `failure-modes/tombstoning.md`.
- Q2 ("nets connected that should be isolated") → top hit from `failure-modes/shorts.md`.
- Q3 ("resistor outside limits") → top hit from `failure-modes/out-of-tolerance-analog.md`.
- First run pauses to download the embedding model — that is expected, one-time, cached off-repo.

### §2 — Anti-spurious check
- Query something absent, e.g. `r.retrieve("how do I bake a cake", top_k=3)` → expect `[]` or only
  weakly-related chunks (no crash). Empty string `r.retrieve("", top_k=3)` → `[]`.

### §3 — Guardrail spot-check (content review)
- Open 2–3 files under `docs/knowledge-base/failure-modes/`. Confirm: no verbatim IPC-A-610 / J-STD-001
  text, no pasted Keysight manual text — only paraphrase + section-number citations.

### Pass/fail criteria
PASS: §0 green; §1 top hits match the expected failure-mode docs; §2 no crash on absent/empty queries;
§3 content is clean paraphrase. FAIL: any deviation — note exactly what was seen, log to BUG_LOG.

### Notes
- §1 uses the REAL embedding model (semantic match). The unit suite never does (fake embedder).
- If you have no network, skip §1's `build_retriever(...)` default-model line; the lexical path still
  works via `load_kb` + `LexicalIndex` directly.
