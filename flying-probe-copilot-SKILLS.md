# Flying-Probe / ICT Test-Log Co-Pilot — SKILLS Requirements

**Project:** Flagship — Flying Probe / ICT Test-Log Intelligence Co-Pilot
**Owner:** Hrushiekesh Reddy Kanjula
**Purpose:** Identify which skills you already have, which need brushing up, and which need to be learned new — so we can plan the build around your actual readiness, not assumed readiness.

---

## Legend
- ✅ **Already have** — from your background; just apply it
- 🟡 **Brush up** — you've touched it but need a short refresher
- 🔴 **Learn new** — not in your stack yet; budget time for it
- ⭐ **Your moat** — domain skills no generic ML candidate has

---

## Tier 1 — Domain skills (your unfair advantage)

| Skill | Status | Notes |
|---|---|---|
| Flying probe / ICT test workflow | ⭐ ✅ | You write the programs. Nobody else has this. |
| HP3070 / Keysight i3070 BT-Basic log structure | ⭐ ✅ | If targeting Takaya/Teradyne later, you'd need to learn their format. |
| Failure-mode → root-cause mapping (PCBA) | ⭐ ✅ | This becomes the knowledge base the LLM grounds on. |
| IPC-A-610 inspection criteria | ⭐ ✅ | Used for cross-referencing test failures to inspection. |
| SMT process knowledge (paste, place, reflow) | ⭐ ✅ | Powers root-cause reasoning. |
| SPC fundamentals (Cp/Cpk, control charts) | ✅ | Standard process-engineer toolkit. |
| Root cause analysis (5-Why, fishbone) | ✅ | Used in the "explain failure" output layer. |

**Verdict:** Tier 1 is fully covered. This is exactly why this project beats a generic ML portfolio piece.

---

## Tier 2 — Software engineering skills (the core build)

| Skill | Status | Notes |
|---|---|---|
| Python 3.11+ (intermediate) | ✅ | You have Python automation experience. |
| SQL (joins, aggregations, window functions) | ✅ | You have SQL background. |
| Pandas / data wrangling | 🟡 | Brush up on `groupby`, `pivot_table`, time-series resampling. |
| Regex for log parsing | 🟡 | Critical for the parser phase. ~2 hours to refresh. |
| Git / GitHub workflow | ✅ | Already using it. |
| Markdown documentation | ✅ | You write CLAUDE.md / SKILL.md regularly. |
| Type hints + dataclasses (Python) | 🟡 | For clean schema definitions. Optional but recommended. |
| Logging & error handling (production-ish code) | 🟡 | Beyond `print()` debugging. |
| Unit testing (pytest basics) | 🔴 | New territory — but only basic level needed. ~1 evening. |

**Verdict:** Most gaps here are 1-2 evenings of brush-up. AI-assisted coding (Claude Code / Cursor) absorbs most of this.

---

## Tier 3 — Data engineering & analytics (the SQL spine)

| Skill | Status | Notes |
|---|---|---|
| DuckDB Python API | 🔴 | New, but trivially close to SQLite/Postgres. ~1 day to feel fluent. |
| Schema design (star schema for test data) | 🟡 | You understand normalized data; just need to design for test logs. |
| SPC charts in Python (matplotlib/plotly) | 🟡 | Control chart math is straightforward; libraries do it. |
| Pareto / yield-over-time analytics | ✅ | Process-engineer bread and butter, just in code now. |
| Anomaly detection — z-score, IQR | 🟡 | Easy stats; ~half day. |
| Anomaly detection — Isolation Forest, LOF | 🔴 | Optional Phase-2 stretch. Skip if time pressed. |

**Verdict:** DuckDB is the only fully new item, and it's deliberately the easiest of the analytical DBs to learn.

---

## Tier 4 — RAG & LLM integration (the co-pilot layer)

| Skill | Status | Notes |
|---|---|---|
| RAG architecture (high-level) | ✅ | You've already studied Hybrid + Agentic RAG. |
| Claude API / OpenAI API basics | 🟡 | You use Claude Code daily; using the API directly is a 1-evening shift. |
| Structured output / function calling | 🔴 | Important for grounding LLM responses in retrieved data. ~1 day. |
| Vector embeddings (sentence-transformers) | 🔴 | Just import + run; no training. Conceptual learning ~half day. |
| FAISS or ChromaDB | 🔴 | Pick one; ChromaDB is simpler. ~1 day. |
| BM25 / lexical retrieval (hybrid RAG) | 🔴 | `rank_bm25` library; trivial integration. |
| Prompt engineering for grounded Q&A | 🟡 | You do this conversationally; codifying it is the new part. |

**Verdict:** RAG plumbing is the largest *new* learning area, but every piece has excellent docs and starter repos. Budget ~1 week of focused learning across Phase 3.

---

## Tier 5 — Frontend / delivery (the dashboard)

| Skill | Status | Notes |
|---|---|---|
| Streamlit basics | 🔴 | Easiest Python UI framework. ~1 day to first working app. |
| Plotly / interactive charts | 🟡 | Strongly recommended over matplotlib for the dashboard. |
| Basic HTML/CSS (for portfolio page) | 🟡 | You have a Next.js portfolio site already. |

**Verdict:** Streamlit is the only thing to learn here, and it's intentionally beginner-friendly.

---

## Tier 6 — Deployment & polish (Phase 3+)

| Skill | Status | Notes |
|---|---|---|
| Docker basics | 🟡 | Recommended but not blocking. ~1 day. |
| `requirements.txt` / `uv` / `poetry` | 🟡 | Pick `uv` — fastest, modern. |
| Environment variables / `.env` files | 🟡 | For API keys. Trivial. |
| GitHub Actions (CI for tests) | 🔴 | Stretch goal; skip for v1. |

---

## Skill Gap Summary

| Severity | Items | Estimated learning time |
|---|---|---|
| 🔴 Truly new | pytest basics, DuckDB API, structured LLM output, embeddings, FAISS/Chroma, BM25, Streamlit | ~1.5 weeks total (spread across phases) |
| 🟡 Brush up | regex, pandas advanced, anomaly stats, Claude API, Plotly, Docker | ~3-4 days total |
| ✅ Already have | Python, SQL, Git, SPC, all domain knowledge | 0 |

**Total skill ramp-up before/during the build: ~2 weeks of focused learning, interleaved with the 8-week build timeline.** This is highly viable.

---

## What you should NOT try to learn for this project
- ❌ Training your own neural network from scratch — use pre-trained embeddings + Claude API.
- ❌ Building your own vector database — use Chroma or FAISS.
- ❌ Fine-tuning an LLM — RAG + good prompting solves this without fine-tuning.
- ❌ Kubernetes / cloud infrastructure — Streamlit + Docker is enough for portfolio v1.
- ❌ Full-stack web dev (React backend etc.) — Streamlit covers it.

**Principle:** Every skill on the "learn new" list is glue code, not algorithm work. AI-assisted coding (your existing Claude Code / Cursor workflow) is exactly the right tool for this.

---

## Recommended pre-build warm-up (1 week, optional)
1. Build a 50-line DuckDB + Streamlit demo with any CSV (e.g., your photography metadata).
2. Build a 100-line ChromaDB + Claude API RAG demo over 3-5 PDFs you already have.
3. Re-read one hybrid RAG tutorial end-to-end.

If you can do these three in a week, you're ready for Phase 1.
