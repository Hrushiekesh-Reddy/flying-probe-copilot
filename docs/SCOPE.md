# SCOPE.md

## In scope (v1 — shipping target)

### Inputs
- Flying-probe / ICT test log files in **HP3070 / Keysight i3070 report format** (synthetic for repo; real for local validation only).
- Optional: BOM and centroid (XY pick-and-place) files for cross-reference, light integration.

### Core functionality
1. **Synthetic log generator** producing realistic HP3070-style reports from configurable parameters (board, panel size, fault injection profile, drift over time).
2. **Parser** that ingests logs and writes structured rows to DuckDB.
3. **Schema** for boards, panels, test runs, tests, measurements, results, operators.
4. **Analytics module:**
   - Yield over time (board / line / shift)
   - Failure Pareto (by test, by component, by network)
   - SPC control charts (X-bar, R, individual)
   - Anomaly detection (z-score + isolation forest)
5. **Streamlit dashboard** for the analytics above.
6. **Hybrid RAG co-pilot** (BM25 + vector) that:
   - Indexes failure-mode → root-cause knowledge base (hand-curated by owner)
   - Indexes structured query results as retrievable context
   - Answers questions like "What's the most common failure on board X this week, and what's the likely cause?"
   - Grounds answers in citations to specific log rows / KB entries
7. **Failure-mode knowledge base** in markdown — owner-authored, the domain IP layer.

### Quality gates
- Synthetic data realistic enough to be visually indistinguishable from real i3070 reports to an experienced engineer.
- Parser handles ≥99% of generator output without errors.
- RAG answers cite specific evidence; no ungrounded claims.
- Dashboard loads <2s on 100k synthetic test records.

## Out of scope (v1)

- Real customer log data in the public repo.
- Takaya / Teradyne / Spectrum log formats (Phase 5+ if pursued).
- Functional test / boundary scan integration.
- Real-time streaming ingestion (batch-only v1).
- Multi-user authentication, role-based access.
- Cloud deployment (local-only).
- Custom-trained models (use pre-trained embeddings + LLM API).
- Production-grade observability (logging beyond Python stdlib `logging`).
- A web frontend in React/Next.js — Streamlit only.
- MES integration.
- Mobile UI.

## Stretch goals (only if v1 ships ahead of schedule)

- A second log format (Takaya) to demonstrate parser extensibility.
- Failure-mode KB editor inside the Streamlit UI.
- LLM-generated 8D report drafts.
- Dockerized deployment.
- GitHub Actions CI.

## Success criteria (project-level)

1. **Functional:** All four phases ship; demo gif on portfolio site.
2. **Hireable:** Demonstrates the four EMS-hiring-manager keywords — SMT data analytics, test data analysis, SPC, RAG/LLM tooling.
3. **Defensible:** Owner can explain every line of code in an interview; no black-box dependencies.
4. **Repeatable:** Synthetic data + one-command setup means any reviewer can clone and run in <10 minutes.

## Non-goals

- Becoming a commercial product. This is a portfolio demonstration; it competes with Nick's NS-HPDCA in spirit, not in market.
- Replacing existing factory-floor tools. It is a *companion* analytic, not a system of record.
- Supporting all manufacturers. HP3070/i3070 is the lighthouse format; everything else is later.
