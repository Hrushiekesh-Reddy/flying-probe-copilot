# Flying-Probe / ICT Test-Log Intelligence Co-Pilot

> A Python tool that parses flying-probe / ICT test logs into a structured SQL database, runs yield / Pareto / anomaly analytics, and exposes a natural-language RAG interface for root-cause investigation.

**Owner:** Hrushiekesh Reddy Kanjula
**Status:** 📋 Phase 0 — Documentation & Setup
**Target completion:** 8-10 weeks (evenings + weekends)
**License:** MIT

---

## Why this exists

PCBA manufacturers run flying-probe and in-circuit testers that produce massive volumes of test logs, but the analytics layer is either commercial-and-expensive (Nick's Software NS-HPDCA) or non-existent. This project closes that gap with an open, AI-assisted, IPC-aware co-pilot.

It is also the **flagship portfolio project** for landing a Manufacturing/Process Engineer with AI role at a Dallas-area EMS firm (Celestica, Jabil, Sanmina, Lockheed).

## Architecture (target end state)

```
Test logs (HP3070 / i3070 reports)
        │
        ▼
┌──────────────────┐
│  Parser (Python) │
└────────┬─────────┘
         │  structured rows
         ▼
┌──────────────────┐
│   DuckDB spine   │  ← SQL queries, joins, time-series
└────────┬─────────┘
         │
   ┌─────┴────────────────────────┐
   ▼                              ▼
┌────────────┐          ┌──────────────────┐
│ Analytics  │          │  Hybrid RAG      │
│ - Yield    │          │  (BM25 + vector) │
│ - Pareto   │          │  over failure-   │
│ - SPC      │          │  mode KB +       │
│ - Anomaly  │          │  query results   │
└─────┬──────┘          └──────────┬───────┘
      │                            │
      └───────────┬────────────────┘
                  ▼
        ┌─────────────────┐
        │ Streamlit UI    │
        │ - Dashboard     │
        │ - Co-pilot chat │
        └─────────────────┘
```

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Default for ML/data |
| Package manager | `uv` | Fastest modern tool |
| Database | DuckDB | File-based + analytics-fast |
| Vector store | ChromaDB | Local, no service required |
| Lexical search | `rank-bm25` | Hybrid RAG completeness |
| Embeddings | sentence-transformers | Free, local, GPU-accelerated |
| LLM API | Google Gemini (primary), Claude (backup) | Free tier + already configured |
| UI | Streamlit + Plotly | Fastest path to working dashboard |
| Test framework | pytest | Standard |
| CI | GitHub Actions (Phase 4) | Free for public repos |

## Repo structure (target)

```
flying-probe-copilot/
├── README.md
├── CLAUDE.md                    # Memory bridge for Claude Code
├── LICENSE
├── .gitignore
├── .cursor/rules/               # Cursor IDE rules
├── pyproject.toml               # uv / dependencies
├── docs/                        # All design docs
│   ├── SCOPE.md
│   ├── GUARDRAILS.md
│   ├── REQUIREMENTS.md
│   ├── ROADMAP.md
│   ├── DECISIONS.md             # Architecture Decision Records
│   └── prompts/                 # Reusable IDE prompts
├── specs/                       # Per-component specs
│   └── synthetic-log-generator.md
├── src/
│   └── flying_probe_copilot/
│       ├── generator/           # Phase 1a: synthetic data
│       ├── parser/              # Phase 1b
│       ├── analytics/           # Phase 2
│       ├── rag/                 # Phase 3
│       └── ui/                  # Phase 3
├── tests/
├── data/
│   ├── synthetic/               # generated logs (gitignored if large)
│   └── real/                    # NEVER COMMITTED — see GUARDRAILS.md
└── notebooks/                   # exploration only
```

## Quick links

- 📋 [SCOPE](docs/SCOPE.md) — what's in and out of scope
- 🛡️ [GUARDRAILS](docs/GUARDRAILS.md) — non-negotiable rules (esp. real data handling)
- 📋 [REQUIREMENTS](docs/REQUIREMENTS.md) — skills & resources checklist
- 🗺️ [ROADMAP](docs/ROADMAP.md) — phased plan
- 🧭 [DECISIONS](docs/DECISIONS.md) — architecture decision records
- 🛠️ [Synthetic Log Generator Spec](specs/synthetic-log-generator.md) — Phase 1a

## How to develop on this repo

This project uses a multi-IDE workflow:
- **Claude Code** — exploration, planning, debugging, doc generation
- **Cursor** — primary builder for component code
- **Both share `CLAUDE.md`** as the memory bridge

Start each session by pointing your IDE at `CLAUDE.md` and the relevant phase doc.
