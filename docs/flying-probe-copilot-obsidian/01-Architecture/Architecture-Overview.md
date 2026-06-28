# Architecture Overview

> Parses PCBA flying-probe / ICT test logs into a SQL database, runs yield + anomaly analytics, and answers natural-language root-cause questions via hybrid RAG.

## System Diagram

```
Test logs (HP3070 / i3070 reports)
        │
        ▼
┌──────────────────┐
│  Parser (Python) │   src/flying_probe_copilot/parser/
└────────┬─────────┘
         │  structured rows
         ▼
┌──────────────────┐
│   DuckDB spine   │   src/flying_probe_copilot/db/schema.py
└────────┬─────────┘   9 tables: 5 dim + runs + 3 fact
         │
   ┌─────┴────────────────────────┐
   ▼                              ▼
┌────────────┐          ┌──────────────────┐
│ Analytics  │          │  Hybrid RAG      │
│ - Yield    │          │  (BM25 + vector) │
│ - Pareto   │          │  over failure-   │
│ - SPC/XmR  │          │  mode KB +       │
│ - Anomaly  │          │  query results   │
└─────┬──────┘          └──────────┬───────┘
      │                            │
      └───────────┬────────────────┘
                  ▼
        ┌─────────────────┐
        │ Streamlit UI    │   src/flying_probe_copilot/ui/
        │ - Dashboard     │   (Phase 2 slice 3 — NEXT)
        │ - Co-pilot chat │   (Phase 3)
        └─────────────────┘
```

## Module Overview

| Module | Path | Status | Purpose |
|--------|------|--------|---------|
| `generator` | `src/.../generator/` | ✅ Complete | Synthetic HP3070 log generator |
| `parser` | `src/.../parser/` | ✅ Complete | Log parser + DuckDB ingest |
| `db` | `src/.../db/schema.py` | ✅ Complete | 9-table DuckDB schema |
| `analytics` | `src/.../analytics/` | 🟡 In Progress | Yield, Pareto, SPC, Anomaly |
| `rag` | `src/.../rag/` | ⬜ Phase 3 | Hybrid RAG over results + KB |
| `ui` | `src/.../ui/` | ⬜ Phase 2 slice 3 | Streamlit dashboard |

## Database Schema (9 Tables)

### Dimension Tables (5)
- `boards` — board profiles (small/medium/large)
- `panels` — individual panels with scheduled_ts, shift, line_id, operator_id
- `operators` — operator identifiers
- `components` — refdes, component type per board profile
- `tests` — test type definitions

### Fact Tables (3)
- `test_runs` — per-panel test execution (status, operator, shift, line)
- `measurements` — analog measurement values per component
- `failures` — failure records (record_type, refdes, fault details)

### Metadata (1)
- `runs` — ingest run metadata

## Analytics Functions (Current)

| Function | Module | Description |
|----------|--------|-------------|
| `yield_over_time` | `analytics/yield.py` | Per-board yield % over a rolling window |
| `failure_pareto` | `analytics/pareto.py` | Top-N failures by record_type |
| `individuals_chart` | `analytics/spc.py` | Shewhart XmR chart (Wheeler rules 1+4) |
| `z_score_anomalies` | `analytics/anomaly.py` | Leave-one-out z-score failure rate anomalies |

## Data Flow

```
generator CLI
    → .log / .csv / .json files (synthetic HP3070 format)
        → parser CLI
            → DuckDB tables
                → analytics functions
                    → Streamlit dashboard (slice 3 next)
```

## Key Design Constraints

- **No real data in repo** — synthetic data only (see [[ADRs#ADR-002]])
- **No cloud deployment in v1** — local + GitHub only
- **No custom model training** — pre-trained embeddings + LLM API
- **Streamlit only** — no React/Next.js frontend
- **DuckDB only** — no Postgres, no SQLite migration needed

## Related Notes

- [[ADRs|Architecture Decision Records]] — Why we made these choices
- [[Technical-Stack|Technical Stack]] — Full dependency list
- [[03-Domain-Knowledge/Probe-Technology|Probe Technology]] — Domain context

**Tags:** #architecture #core-system
