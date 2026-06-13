# DECISIONS.md — Architecture Decision Records

Each ADR captures a non-trivial choice, the alternatives considered, and the reasoning. Future-you (and an interviewer) will want this trail.

Format: short, blame-free, factual.

---

## ADR-001 — Don't fork; start fresh

**Date:** 2026-06-13
**Status:** Accepted

**Context:** Several PCBA-adjacent open-source repos exist (rag-document-assistant, Industrial-Docs-RAG-Chatbot, RAG-Anything), but none combines the parser + DB + analytics + RAG layers we need for flying-probe logs.

**Decision:** Start the repo from scratch. Treat the three RAG repos as reference reading for Phase 3 only.

**Consequences:** More upfront design work; full architectural freedom; clean license story (MIT, no derivative obligations).

---

## ADR-002 — Synthetic-data-first development

**Date:** 2026-06-13
**Status:** Accepted

**Context:** Owner has access to real flying-probe logs at work but cannot exfiltrate them. A public repo or GitHub portfolio piece needs shareable test data.

**Decision:** Build a synthetic HP3070-style log generator as the first deliverable. All committed code uses synthetic logs only. Real-data validation happens on the work network and produces only structural metrics that come home.

**Consequences:**
- The generator itself becomes a portfolio asset.
- Hiring managers see IP-safe architecture.
- Risk: synthetic data may not reflect all edge cases; mitigate by extensive parameterization.

---

## ADR-003 — Target HP3070 / Keysight i3070 format first

**Date:** 2026-06-13
**Status:** Accepted

**Context:** Three plausible target formats: HP3070/i3070 (Keysight), Takaya APT/Seica, Teradyne. Owner has format-pick latitude.

**Decision:** HP3070/i3070 first because it has the most public documentation (free Keysight manuals).

**Consequences:** Easier to design a realistic synthetic generator. Future expansion to Takaya/Teradyne is a Phase 5 stretch goal.

---

## ADR-004 — DuckDB for the SQL spine

**Date:** 2026-06-13
**Status:** Accepted

**Alternatives considered:** SQLite, PostgreSQL.

**Decision:** DuckDB.

**Reasons:**
- File-based simplicity of SQLite, no service to run.
- Columnar storage and vectorized execution → orders-of-magnitude faster for analytics workloads (Pareto, yield over time, time-series).
- Same SQL dialect family as Postgres, so port path is open if needed.
- Hot 2025-2026 data-engineering signal — additional hireability bonus.

**Consequences:** Owner has to learn the Python API (~1 day). Some tooling assumes Postgres-compatible drivers; DuckDB has its own driver.

---

## ADR-005 — Google Gemini as primary LLM API

**Date:** 2026-06-13
**Status:** Accepted

**Alternatives considered:** Anthropic Claude API, OpenAI API.

**Decision:** Use Google Gemini (already configured in Google AI Studio for the portfolio project) as the primary LLM API. Hold Claude as a backup option.

**Reasons:**
- Already set up; zero new account friction.
- Free tier on Gemini 2.0 Flash is generous enough for the entire dev cycle.
- Owner's $100 Claude Code Max plan covers IDE-side AI usage; reserving it makes sense.
- Quality of Gemini 2.0 Flash is sufficient for grounded RAG; we are not asking the model to reason from scratch.

**Consequences:**
- Code uses `google-generativeai` SDK.
- If Gemini quality disappoints in Phase 3 testing, swap to Claude (cost ~$20-60). Decision point recorded at Phase 3 review.

---

## ADR-006 — Hybrid RAG (BM25 + vector + RRF)

**Date:** 2026-06-13
**Status:** Accepted

**Context:** Phase 3 needs retrieval over a small but technical corpus (failure-mode KB + query results). Pure vector search underperforms on exact-term queries like "C42" or "U17 pin 3."

**Decision:** Hybrid retrieval: ChromaDB for semantic + rank_bm25 for lexical + reciprocal rank fusion (RRF) for combination.

**Reasons:**
- Hybrid RAG is the modal pattern in 2026 production deployments.
- Owner has prior interest and study in Hybrid RAG architectures.
- BM25 handles the abundant identifier-style terms in PCBA data (refdes, net names, part numbers) that embeddings often miss.

**Consequences:** Slightly more plumbing than pure vector RAG. Pays off in retrieval quality on the test domain.

---

## ADR-007 — Streamlit for v1 UI

**Date:** 2026-06-13
**Status:** Accepted

**Alternatives considered:** FastAPI + Next.js frontend, Gradio, Panel.

**Decision:** Streamlit.

**Reasons:**
- Fastest path from analytic functions to a usable dashboard.
- Owner already has Next.js for the portfolio site; no need to duplicate that complexity here.
- Reviewer-friendly: `uv run streamlit run app.py` and they see the UI.

**Consequences:** Streamlit has known limitations on layout customization and concurrency. Acceptable for portfolio v1. If a production use case emerges later, port the UI then.

---

## ADR-008 — uv for dependency management

**Date:** 2026-06-13
**Status:** Accepted

**Alternatives considered:** Poetry, pip + requirements.txt, conda.

**Decision:** `uv`.

**Reasons:** Fastest install and lockfile generation. Modern, batteries-included. Lighter than Poetry.

---

## Parking lot

Ideas captured during development, to evaluate at phase boundaries:

- (empty so far)

---

## How to add an ADR

1. Increment the number.
2. Date it.
3. Set status: Proposed / Accepted / Superseded.
4. Be brief; this is a trail, not an essay.
