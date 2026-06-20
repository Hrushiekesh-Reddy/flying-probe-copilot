# Features Index

Central hub for all feature documentation and status tracking.

## Feature Status Overview

### ✅ Shipped

| Feature | Module | Shipped |
|---------|--------|---------|
| Synthetic HP3070 log generator | `generator/` | 2026-06-13 |
| 3 board profiles (small/medium/large) | `generator/` | 2026-06-13 |
| 4 fault injection profiles | `generator/` | 2026-06-13 |
| Log parser (Keysight Log Record Format) | `parser/` | 2026-06-14 |
| DuckDB 9-table schema | `db/schema.py` | 2026-06-14 |
| Parser CLI + round-trip integrity | `parser/cli.py` | 2026-06-14 |
| Yield-over-time analytics | `analytics/yield.py` | 2026-06-16 |
| Failure Pareto analytics | `analytics/pareto.py` | 2026-06-16 |
| SPC individuals chart (XmR, Wheeler) | `analytics/spc.py` | 2026-06-18 |
| Z-score anomaly detection | `analytics/anomaly.py` | 2026-06-18 |

### 🔵 Next Up

| Feature | Phase | Notes |
|---------|-------|-------|
| Streamlit dashboard (yield + Pareto + SPC + anomaly) | Phase 2 slice 3 | `ui/` module |
| Board/date range filters in UI | Phase 2 slice 3 | Streamlit widgets |

### ⬜ Planned (Phase 3 — RAG Co-Pilot)

| Feature | Notes |
|---------|-------|
| Failure-mode knowledge base | Markdown KB in `docs/knowledge-base/` |
| ChromaDB vector index | Local, no service required |
| BM25 lexical search | `rank-bm25` over KB + query results |
| Reciprocal Rank Fusion (RRF) | Combines vector + lexical results |
| Gemini LLM integration | Structured-output prompt with citations |
| Co-pilot chat in Streamlit | `ui/chat.py` |

### ⬜ Planned (Phase 4 — Polish)

| Feature | Notes |
|---------|-------|
| GitHub Actions CI | Lint + tests on PR |
| Demo gif + screenshots | For portfolio README |
| Case-study writeup | Portfolio site |
| Repo goes public | After guardrails checklist |

---

## Browse by Category

- **Data Generation**: Synthetic log generator, board profiles, fault injection
- **Data Ingestion**: Parser, DuckDB schema, CLI
- **Analytics**: Yield, Pareto, SPC, Anomaly detection
- **UI**: Streamlit dashboard, charts, filters
- **RAG**: Knowledge base, vector search, LLM chat
- **DevOps**: CI/CD, testing, coverage

---

## Key Contracts & Constraints

- `yield_over_time` returns `group_key ASC` ordering (not notebook Q4 ordering)
- `failure_pareto` v1 groups by `record_type` only (2-column key deferred)
- Percentages in analytics are unrounded floats
- `window_days <= 0` / `top_n <= 0` / tz-aware `as_of` raise `ValueError`
- SPC sigma = `MR̄ / 1.128` (never sample stdev)
- Z-score uses leave-one-out baseline (group excluded from its own mean+std)

**Tags:** #features #planning #status
