# Architecture Decision Records (ADRs)

Full source of truth lives in `docs/DECISIONS.md`. This is the Obsidian-linked summary.

---

## ADR-001 — Start fresh (no fork)
- **Status**: Accepted | **Date**: 2026-06-13
- **Decision**: Build from scratch, not from existing RAG repos (rag-document-assistant, Industrial-Docs-RAG-Chatbot, RAG-Anything).
- **Rationale**: None combine parser + DB + analytics + RAG for flying-probe logs. Clean MIT license, full architectural freedom.

---

## ADR-002 — Synthetic-data-first development
- **Status**: Accepted | **Date**: 2026-06-13
- **Decision**: Build a synthetic HP3070 log generator first. All committed code uses synthetic data only.
- **Rationale**: Real logs can't leave the work network. Public portfolio piece needs shareable data. Generator itself is a portfolio asset.
- **Risk**: Synthetic data may miss edge cases → mitigated by extensive parameterization.

---

## ADR-003 — Target HP3070 / Keysight i3070 format first
- **Status**: Accepted | **Date**: 2026-06-13
- **Decision**: HP3070/i3070 first. Takaya/Teradyne are Phase 5 stretch goals.
- **Rationale**: Most public documentation available (Keysight manuals, Virinco public mirror for Keysight Log Record Format).

---

## ADR-004 — DuckDB for the SQL spine
- **Status**: Accepted | **Date**: 2026-06-13
- **Alternatives**: SQLite (too row-oriented), PostgreSQL (requires a running service)
- **Decision**: DuckDB.
- **Rationale**: File-based like SQLite + columnar analytics speed like Postgres. No service to run. Hot 2025-2026 data-engineering signal → hireability bonus.
- **Consequence**: Owner needed ~1 day to learn Python API.

---

## ADR-005 — Google Gemini as primary LLM API
- **Status**: Accepted | **Date**: 2026-06-13
- **Alternatives**: Claude API, OpenAI
- **Decision**: Gemini (primary), Claude (backup).
- **Rationale**: Already configured in Google AI Studio. Free tier covers full dev cycle. Claude Code Max plan used for IDE-side AI only.
- **Decision point**: Swap to Claude if Gemini quality disappoints at Phase 3 testing.

---

## ADR-006 — Hybrid RAG (BM25 + vector + RRF)
- **Status**: Accepted | **Date**: 2026-06-13
- **Decision**: ChromaDB (semantic) + rank_bm25 (lexical) + Reciprocal Rank Fusion.
- **Rationale**: Pure vector search underperforms on exact-term queries like "C42" or "U17 pin 3" which are common in PCB failure analysis.

---

## ADR-007 — Wheeler SPC rules (not Western Electric/Nelson)
- **Status**: Accepted | **Date**: 2026-06-18
- **Decision**: `individuals_chart` uses Wheeler doctrine: rule_1 (beyond 3σ) + rule_4 (run of 8) by default. Rule_2/rule_3 opt-in.
- **Rationale**: Wheeler is the authoritative source for XmR charts; Nelson/WECO rules were designed for X-bar charts and produce false positives on individual measurements. sigma = MR̄/1.128 (never sample stdev).

---

## ADR-008 — Z-score leave-one-out baseline for anomaly detection
- **Status**: Accepted | **Date**: 2026-06-18
- **Decision**: `z_score_anomalies` computes failure-rate anomalies with leave-one-out baseline (group excluded from its own mean+std). Isolation Forest deferred.
- **Rationale**: No new sklearn dependency. Deterministic and explainable. Isolation Forest deferred — revisit if false-positive rate is high in Phase 3 testing.

---

## Template for New ADRs

```markdown
### ADR-XXX: [Clear Decision Title]
- **Status**: Proposed
- **Date**: YYYY-MM-DD
- **Context**: Why is this needed?
- **Decision**: What did we decide?
- **Rationale**: Why this choice over others?
- **Consequences**: What changes as a result?
```

**Tags:** #architecture #decisions #adrs
