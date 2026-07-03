# Resume bullets — flying-probe-copilot

Three variants at different length / density. Pick whichever fits the resume's format.

---

## A. One-liner (single-line resumes / dense tech section)

> Built and shipped an open-source AI co-pilot for PCBA flying-probe / ICT test-log analytics — parser → DuckDB spine → SPC + anomaly library → hybrid RAG (BM25 + ChromaDB + Reciprocal Rank Fusion) over an 8-doc failure-mode KB with strict anti-hallucination grounding · **667 tests / 97% coverage / 10/10 live RAG eval / MIT** · Python, DuckDB, Streamlit, Gemini · [github.com/Hrushiekesh-Reddy/flying-probe-copilot](https://github.com/Hrushiekesh-Reddy/flying-probe-copilot).

---

## B. Two-bullet (standard "Selected Projects" section) — recommended

> **Flying-Probe / ICT Test-Log Intelligence Co-Pilot** — Python · DuckDB · ChromaDB · Streamlit · Gemini
> [github.com/Hrushiekesh-Reddy/flying-probe-copilot](https://github.com/Hrushiekesh-Reddy/flying-probe-copilot) · MIT · 2026
>
> - Designed and shipped an open-source manufacturing-analytics + RAG co-pilot for PCBA in-circuit / flying-probe test logs: synthetic Keysight Log Record Format generator (~1 s / 1,000 panels), 9-table DuckDB spine, and a four-function analytics library (yield-over-time, failure Pareto, Wheeler XmR + run-of-8 SPC, leave-one-out z-score anomalies) driving a six-page Streamlit dashboard.
> - Built the Co-Pilot as hybrid retrieval (rank-bm25 + ChromaDB HNSW with Reciprocal Rank Fusion) over an 8-doc failure-mode knowledge base with a strict four-rule anti-hallucination contract that refuses when evidence is insufficient; verified end-to-end with 667 passing tests, 97% line coverage, and 10/10 correct citations on a live Gemini 3.5 Flash eval in 37 s.

---

## C. Three-bullet (deep-dive resumes for AI / process-engineering targets)

> **Flying-Probe / ICT Test-Log Intelligence Co-Pilot** — Python · DuckDB · ChromaDB · Streamlit · Gemini
> [github.com/Hrushiekesh-Reddy/flying-probe-copilot](https://github.com/Hrushiekesh-Reddy/flying-probe-copilot) · MIT · 2026
>
> - Shipped a synthetic Keysight Log Record Format generator (three board profiles, configurable fault-correlation, shift-physics-aware timestamps) + byte-precise-round-trip parser + 9-table DuckDB schema; benchmarked at ~1 s per 1,000 panels.
> - Built the analytics layer as four pure Python functions — yield-over-time, failure Pareto, Wheeler individuals-chart SPC (XmR baseline + rule-of-8 + optional zone rules), and leave-one-out per-group z-score anomaly detection — surfaced through a six-page Streamlit dashboard.
> - Designed the Co-Pilot as hybrid retrieval (rank-bm25 + ChromaDB HNSW cosine, Reciprocal Rank Fusion k=60) over an 8-doc failure-mode KB with a strict four-rule anti-hallucination contract; verified with 667 tests / 97% coverage / 10/10 correct citations on a live Gemini eval in 37 s.

---

## Notes on framing

- The stack list (Python · DuckDB · ChromaDB · Streamlit · Gemini) sits on the same line as the project name so ATS parsers pick it up.
- The 667/97%/10-of-10 triplet is your quantified impact — keep it verbatim.
- If the resume already has a "Test Engineering" or "Process Engineering" section, this belongs under a "Selected Projects" or "AI / Portfolio Projects" heading, not folded into work experience.
- If a JD emphasizes SPC or statistical process control specifically, promote the SPC clause; if it emphasizes LLMs / RAG, promote the hybrid-retrieval + anti-hallucination clause.
