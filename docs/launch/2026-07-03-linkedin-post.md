# LinkedIn launch post

**Paste-ready.** ~1,200 chars incl. hashtags. Fits LinkedIn's 3,000 limit with room for a comment thread.

**Suggested media:** `docs/img/demo.gif` (12 s loop, 748 KB, shows the 6-page dashboard tour) OR the 2×3 hero strip from the README.

---

Shipped my flagship AI portfolio project this week: an ICT / flying-probe test-log intelligence co-pilot for PCBA lines.

Four gaps most factory analytics tools leave open — and how this closes them:

▪ No queryable spine → parser → DuckDB (9-table schema, byte-precise round-trips)
▪ No SPC automation → Wheeler XmR + run-of-8 as a pure Python library function
▪ No anomaly detection → leave-one-out per-group z-score with severity-first ordering
▪ No grounded root-cause Q&A → hybrid RAG (BM25 + ChromaDB + Reciprocal Rank Fusion) with strict anti-hallucination grounding — the co-pilot refuses when evidence is insufficient rather than making things up

Built over 8 weeks of evenings and weekends as a Manufacturing Engineer with ~4 years of PCBA experience. Everything is synthetic-data, local-first, MIT-licensed.

Verified end-to-end: 667 passing tests, 97% line coverage, 10/10 on the live RAG eval in 37 s on Gemini 3.5 Flash.

The case study walks through three of the bugs I learned the most from — a shift-snap that lied about time, a Gemini model that got retired mid-eval, and a test that only broke under concurrency. Each surfaced a class of error I now actively look for.

Repo + 5-minute demo walkthrough + long-form case study:
🔗 https://github.com/Hrushiekesh-Reddy/flying-probe-copilot

I'm looking for a Manufacturing / Process Engineer with AI role in the Dallas–Fort Worth area. If your team is thinking about closing any of those four gaps on your own line, I'd love to talk.

#ManufacturingEngineering #PCBA #ProcessEngineering #TestEngineering #AI #RAG #Python #DuckDB #Streamlit #DallasJobs
